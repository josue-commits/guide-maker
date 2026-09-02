#!/usr/bin/env python3
"""Shared Notion HTTP helper for guide-maker scripts. Stdlib only.

Two API versions are used on purpose:

- NOTION_VERSION (2022-06-28) for pages, blocks and database queries. The
  block payload shapes every script builds were written against this version
  and they still work unchanged.
- NOTION_VERSION_UPLOAD (2025-09-03) for the /file_uploads endpoints, which do
  not exist on the older version. A page cover or a files property that points
  at a file_upload id has to be PATCHed with this version too.

Keep both. Bumping the page version silently changes response shapes for
databases (data sources) and would break every property write in this repo.

Public functions:
    init(cfg=None, token=None)      set the token once; otherwise it is read
                                    from the config on first use
    request(method, path, body=None, version=None, retry=4, raw_data=None,
            content_type=None, timeout=90)
    upload_file(path, content_type=None) -> upload_id
    set_page_cover(page_id, upload_id)
    set_files_property(page_id, prop, upload_id, name)
    public_url(page_json, domain) -> str
    paginate(path, body=None, method="GET") -> list of result objects
    children(block_id) -> list of child blocks
    query_database(db_id, filter_=None) -> list of pages
    plain_text(rich_text_list) -> str
    check_url(url) -> (ok, status)
"""

import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"          # pages, blocks, databases
NOTION_VERSION_UPLOAD = "2025-09-03"   # /file_uploads and file_upload refs

SINGLE_PART_LIMIT = 20 * 1024 * 1024   # Notion single_part upload ceiling

_TOKEN = ""


class NotionError(RuntimeError):
    """Raised when the API returns an error after retries are exhausted."""

    def __init__(self, code, body, method, path):
        super().__init__(f"Notion {method} {path} failed: {code}\n{body}")
        self.code = code
        self.body = body


def init(cfg=None, token=None):
    """Set the token explicitly. Scripts call this after loading their config."""
    global _TOKEN
    if token:
        _TOKEN = token
        return
    if cfg is not None:
        _TOKEN = _token_from_cfg(cfg)


def _token_from_cfg(cfg):
    try:
        from _config import secret  # v2 config API
        return secret(cfg, "notion")
    except ImportError:
        return (cfg or {}).get("notion_api_key", "")


def _token():
    global _TOKEN
    if _TOKEN:
        return _TOKEN
    from _config import load_config
    _TOKEN = _token_from_cfg(load_config())
    if not _TOKEN:
        raise SystemExit(
            "No Notion token. Set NOTION_API_KEY, write it to "
            "~/.config/notion/api_key, or put notion.api_key in config.yaml.")
    return _TOKEN


def request(method, path, body=None, version=None, retry=4, raw_data=None,
            content_type=None, timeout=90):
    """Authenticated request with retry on 429/502/503 and network errors.

    `path` is relative to NOTION_BASE unless it starts with http(s)://, which
    the file upload flow needs (Notion hands back an absolute upload_url).
    """
    url = path if path.startswith("http") else f"{NOTION_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Notion-Version": version or NOTION_VERSION,
    }
    if raw_data is not None:
        data = raw_data
        headers["Content-Type"] = content_type or "application/octet-stream"
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    else:
        data = None
        if content_type:
            headers["Content-Type"] = content_type

    last_err = None
    for attempt in range(retry):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", "replace")
            if err.code in (429, 502, 503) and attempt < retry - 1:
                wait = 1.5 * (attempt + 1)
                retry_after = err.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = max(wait, float(retry_after))
                time.sleep(wait)
                continue
            print(f"Notion API error {err.code}: {err_body}", file=sys.stderr)
            raise NotionError(err.code, err_body, method, path)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
            last_err = err
            if attempt < retry - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise last_err  # pragma: no cover


# --- Files -------------------------------------------------------------------

def upload_file(path, content_type=None):
    """Upload a local file with the single-part flow. Returns the file_upload id.

    1. POST /file_uploads (mode single_part) -> {id, upload_url}
    2. POST {upload_url} as multipart/form-data with the bytes
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    name = os.path.basename(path)
    ctype = content_type or mimetypes.guess_type(name)[0] or "application/octet-stream"
    size = os.path.getsize(path)
    if size > SINGLE_PART_LIMIT:
        raise ValueError(f"{name} is {size} bytes; single-part upload caps at 20 MB")

    created = request("POST", "/file_uploads", {
        "mode": "single_part", "filename": name, "content_type": ctype,
    }, version=NOTION_VERSION_UPLOAD)
    upload_id = created["id"]
    upload_url = created.get("upload_url") or f"{NOTION_BASE}/file_uploads/{upload_id}/send"

    boundary = "----GuideMakerUpload" + str(int(time.time()))
    with open(path, "rb") as fh:
        file_bytes = fh.read()
    parts = [
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{name}"'.encode(),
        f"Content-Type: {ctype}".encode(),
        b"",
        file_bytes,
        f"--{boundary}--".encode(),
        b"",
    ]
    sent = request("POST", upload_url, raw_data=b"\r\n".join(parts),
                   content_type=f"multipart/form-data; boundary={boundary}",
                   version=NOTION_VERSION_UPLOAD, timeout=300)
    status = sent.get("status")
    if status and status != "uploaded":
        raise RuntimeError(f"Upload did not complete: {json.dumps(sent)[:400]}")
    return upload_id


def set_page_cover(page_id, upload_id):
    """Set an uploaded file as the page cover."""
    return request("PATCH", f"/pages/{page_id}", {
        "cover": {"type": "file_upload", "file_upload": {"id": upload_id}},
    }, version=NOTION_VERSION_UPLOAD)


def set_files_property(page_id, prop, upload_id, name):
    """Attach an uploaded file to a files property (for example `Graphic`).

    This replaces the property's file list. It is the only supported way to
    put a post graphic on a Content Board card; an image block in the page
    body does not show up in calendar or gallery views.
    """
    return request("PATCH", f"/pages/{page_id}", {
        "properties": {prop: {"files": [
            {"type": "file_upload", "file_upload": {"id": upload_id}, "name": name},
        ]}},
    }, version=NOTION_VERSION_UPLOAD)


# --- URLs ---------------------------------------------------------------------

def public_url(page_json, domain):
    """Public notion.site URL for a page, or "" when no domain is configured.

    Notion's public renderer serves https://<domain>/<slug>-<id32>. The slug
    is the one already in the page's own `url` field, so the public address is
    deterministic. It only resolves after the page has been published to web
    from the Notion UI; check_url() tells you whether that happened.
    """
    domain = (domain or "").strip().rstrip("/")
    if not domain:
        return ""
    domain = re.sub(r"^https?://", "", domain)
    page_id = (page_json.get("id") or "").replace("-", "")
    url = page_json.get("url") or ""
    slug = url.rsplit("/", 1)[-1] if url else ""
    slug = re.sub(r"-?[0-9a-fA-F]{32}$", "", slug)
    tail = f"{slug}-{page_id}" if slug else page_id
    return f"https://{domain}/{tail}"


def workspace_url(page_json):
    """The in-app URL Notion returns (notion.so / app.notion.com). Not public."""
    return page_json.get("url") or ""


def check_url(url, timeout=20):
    """GET a URL and report (ok, status). ok means HTTP 200."""
    req = urllib.request.Request(url, headers={"User-Agent": "guide-maker/2"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200, resp.status
    except urllib.error.HTTPError as err:
        return False, err.code
    except (urllib.error.URLError, TimeoutError) as err:
        return False, str(err)


# --- Reads --------------------------------------------------------------------

def paginate(path, body=None, method="GET"):
    """Follow has_more/next_cursor and return every result object."""
    out, cursor = [], None
    while True:
        if method == "GET":
            sep = "&" if "?" in path else "?"
            url = path + (f"{sep}start_cursor={cursor}" if cursor else "")
            page = request("GET", url)
        else:
            payload = dict(body or {})
            if cursor:
                payload["start_cursor"] = cursor
            page = request(method, path, payload)
        out.extend(page.get("results", []))
        if not page.get("has_more"):
            return out
        cursor = page.get("next_cursor")


def children(block_id):
    return paginate(f"/blocks/{block_id}/children?page_size=100")


def query_database(db_id, filter_=None):
    body = {"page_size": 100}
    if filter_:
        body["filter"] = filter_
    return paginate(f"/databases/{db_id}/query", body, method="POST")


def retrieve_database(db_id):
    return request("GET", f"/databases/{db_id}")


def retrieve_page(page_id):
    return request("GET", f"/pages/{page_id}")


def plain_text(rich):
    return "".join(x.get("plain_text", "") for x in (rich or []))


def block_text(block):
    inner = block.get(block.get("type", ""), {}) or {}
    return plain_text(inner.get("rich_text") or inner.get("caption") or [])


def title_of(page, prop="Guide Title"):
    props = page.get("properties", {})
    if prop in props and props[prop].get("type") == "title":
        return plain_text(props[prop]["title"])
    for value in props.values():
        if value.get("type") == "title":
            return plain_text(value["title"])
    return ""


def prop_text(page, prop):
    value = page.get("properties", {}).get(prop) or {}
    kind = value.get("type")
    if kind == "rich_text":
        return plain_text(value["rich_text"])
    if kind == "title":
        return plain_text(value["title"])
    if kind == "select":
        return (value.get("select") or {}).get("name", "")
    if kind == "url":
        return value.get("url") or ""
    return ""
