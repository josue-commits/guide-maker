#!/usr/bin/env python3
"""LeadShark adapter. Reference implementation of a networked DM tool.

Talks to the documented REST API (https://apex.leadshark.io/docs/api) with
the x-api-key header. Key resolution order: LEADSHARK_API_KEY env var, then
~/.config/leadshark/api_key, then providers.leadshark.api_key in the config.

Config block (all optional, shown with defaults):

    dm_tool:
      provider: leadshark
      leadshark:
        base_url: https://apex.leadshark.io
        auto_connect: true
        comment_replies: ["Sent!", "Sent over, check your DMs"]
        non_first_degree_reply: "Please connect with me so I can send it!"
        attachment_max_bytes: 4194304
        create_as: Paused
        timezone: America/New_York
        post_as: personal          # or organization
        organization_id: ""        # required when post_as is organization

Rate limits are enforced server side (250/hr, 1000/day, 100/min); 429 backs
off automatically. With dry_run=True nothing here opens a socket.
"""

from __future__ import annotations

import json
import mimetypes
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

from _config_shim import cfg_get, secret

from .base import DMTool

DEFAULT_BASE_URL = "https://apex.leadshark.io"
DEFAULT_ATTACHMENT_MAX_BYTES = 4 * 1024 * 1024  # 4 MiB, measured; the API returns a bare 413 above it

# Endpoints gated above the Pro plan. Used to give a readable error on 403.
TIER_NOTES = {
    "/api/v1/signals": "Apex",
    "/api/v1/signals/events": "Apex",
    "/api/v1/discover": "Apex",
    "/api/v1/pages": "Pro+",
    "/api/v1/links": "Pro+",
    "/api/v1/activity-limits": "Pro+",
}

_URN_RE = re.compile(r"urn:li:(?:activity|share|ugcPost):\d+")
_ACTIVITY_ID_RE = re.compile(r"activity[-:](\d{10,})")


class ApiError(Exception):
    def __init__(self, status: int, body: str, path: str):
        self.status = status
        self.body = body
        self.path = path
        super().__init__(f"HTTP {status} on {path}: {body}")


def post_urn_from_url(post_url: str) -> Optional[str]:
    """Pull the activity URN out of any LinkedIn post URL shape."""
    m = _URN_RE.search(urllib.parse.unquote(post_url))
    if m:
        return m.group(0)
    m = _ACTIVITY_ID_RE.search(post_url)
    if m:
        return f"urn:li:activity:{m.group(1)}"
    return None


class LeadSharkTool(DMTool):
    name = "leadshark"

    def __init__(self, cfg: dict, dry_run: bool = False, out_dir: Optional[str] = None):
        super().__init__(cfg, dry_run=dry_run, out_dir=out_dir)
        self.base_url = str(cfg_get(cfg, "dm_tool.leadshark.base_url", DEFAULT_BASE_URL)).rstrip("/")
        self.attachment_max_bytes = int(
            cfg_get(cfg, "dm_tool.leadshark.attachment_max_bytes", DEFAULT_ATTACHMENT_MAX_BYTES)
        )
        self.create_as = str(cfg_get(cfg, "dm_tool.leadshark.create_as", "Paused"))
        self._key: Optional[str] = None

    # ------------------------------------------------------------------ auth

    def api_key(self) -> str:
        if self._key:
            return self._key
        key = secret(self.cfg, "leadshark")
        if not key:
            raise SystemExit(
                "No LeadShark API key found. Copy it from the LeadShark dashboard (Settings, API Access), then:\n"
                "  mkdir -p ~/.config/leadshark && printf '%s' 'YOUR_KEY' > ~/.config/leadshark/api_key "
                "&& chmod 600 ~/.config/leadshark/api_key\n"
                "or export LEADSHARK_API_KEY, or set providers.leadshark.api_key in the config."
            )
        self._key = key
        return key

    # ------------------------------------------------------------- transport

    def request(self, method: str, path: str, params: Optional[dict] = None, body=None, retries: int = 3):
        if self.dry_run:
            raise SystemExit(f"dry-run: refusing to open a socket for {method} {path}")
        url = self.base_url + path
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        data = None
        headers = {"x-api-key": self.api_key(), "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        for attempt in range(retries):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                payload = e.read().decode("utf-8", "replace")
                if e.code == 429 and attempt < retries - 1:
                    time.sleep(2 ** attempt * 5)
                    continue
                if e.code == 403:
                    tier = TIER_NOTES.get(path.split("?")[0])
                    if tier:
                        payload += f"\n(This endpoint requires the {tier} plan.)"
                raise ApiError(e.code, payload, path)
            except urllib.error.URLError as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise ApiError(0, str(e), path)
        raise ApiError(0, "retries exhausted", path)

    def request_multipart(self, path: str, fields: dict, file_path: str, file_field: str = "file"):
        """POST multipart/form-data. Needed for scheduled posts that carry an image."""
        if self.dry_run:
            raise SystemExit(f"dry-run: refusing to open a socket for POST {path}")
        boundary = "----dmautomation" + uuid.uuid4().hex
        fp = Path(file_path).expanduser()
        if not fp.is_file():
            raise SystemExit(f"File not found: {fp}")
        payload = fp.read_bytes()
        ctype = mimetypes.guess_type(fp.name)[0] or "application/octet-stream"

        parts = []
        for key, value in fields.items():
            if value is None:
                continue
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode("utf-8")
            )
        parts.append(
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
                f"filename=\"{fp.name}\"\r\nContent-Type: {ctype}\r\n\r\n"
            ).encode("utf-8")
        )
        parts.append(payload)
        parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)

        req = urllib.request.Request(
            self.base_url + path,
            data=body,
            method="POST",
            headers={
                "x-api-key": self.api_key(),
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
        )
        try:
            # Large attachments are the documented cause of "socket hang up", so give the upload room.
            with urllib.request.urlopen(req, timeout=300) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", "replace")
            if e.code == 413:
                body_text += (
                    f"\n(Attachment rejected. The measured ceiling is {self.attachment_max_bytes} bytes. "
                    "Run: dm_cli.py image-fit <path>)"
                )
            raise ApiError(e.code, body_text, path)
        except urllib.error.URLError as e:
            raise ApiError(0, str(e), path)

    # ------------------------------------------------------------- interface

    def test(self) -> dict:
        if self.dry_run:
            return {"ok": True, "adapter": self.name, "dry_run": True, "would_call": "GET /api/automations?limit=1"}
        result = self.request("GET", "/api/automations", params={"limit": 1})
        return {
            "ok": True,
            "adapter": self.name,
            "base_url": self.base_url,
            "automations_total": (result.get("pagination") or {}).get("total"),
        }

    def list_keywords(self) -> list[str]:
        """Paginate every automation and collect keywords. Costs several calls."""
        if self.dry_run:
            print("dry-run: would page through GET /api/automations", file=sys.stderr)
            return []
        page, seen = 1, {}
        while True:
            result = self.request("GET", "/api/automations", params={"page": page, "limit": 100})
            for item in result.get("data", []) or []:
                for kw in item.get("keywords") or []:
                    seen.setdefault(str(kw).upper(), []).append(
                        {"automation": item.get("name"), "status": item.get("status")}
                    )
            if not (result.get("pagination") or {}).get("has_more"):
                break
            page += 1
        self.keyword_detail = seen
        return sorted(seen)

    def _check_attachment(self, image_path: Optional[str]) -> None:
        if not image_path:
            return
        fp = Path(image_path).expanduser()
        if not fp.is_file():
            raise SystemExit(f"Graphic not found: {fp}")
        size = fp.stat().st_size
        if size > self.attachment_max_bytes:
            raise SystemExit(
                f"Graphic is {size} bytes, over the {self.attachment_max_bytes} byte ceiling "
                f"(the API answers with a bare 413 above it). Re-encode first:\n"
                f"  python3 dm_cli.py image-fit {fp}"
            )

    def schedule_post(self, content: str, time_iso: str, image_path: Optional[str], automation: dict) -> dict:
        fields: dict = {"content": content, "scheduled_time": time_iso}
        block = {k: v for k, v in automation.items() if v not in (None, [], "")}
        if block:
            fields["automation"] = block
        post_as = cfg_get(self.cfg, "dm_tool.leadshark.post_as")
        if post_as:
            fields["post_as"] = post_as
        org_id = cfg_get(self.cfg, "dm_tool.leadshark.organization_id")
        if org_id:
            fields["organization_id"] = org_id
        if fields.get("post_as") == "organization" and not fields.get("organization_id"):
            raise SystemExit("dm_tool.leadshark.post_as is 'organization' but organization_id is empty.")

        self._check_attachment(image_path)
        transport = "multipart" if image_path else "json"
        if self.dry_run:
            return {
                "dry_run": True,
                "adapter": self.name,
                "endpoint": "POST /api/scheduled-posts",
                "transport": transport,
                "image": str(Path(image_path).expanduser()) if image_path else None,
                "payload": fields,
            }
        if not image_path:
            print(
                "Warning: scheduling without --image. The keyword lives in the graphic, so this post "
                "asks the reader for nothing.",
                file=sys.stderr,
            )
            return self.request("POST", "/api/scheduled-posts", body=fields)
        return self.request_multipart("/api/scheduled-posts", fields, image_path)

    def attach_automation(
        self, post_url: str, keyword: str, dm_text: str, dm_variants: list[str], status: str
    ) -> dict:
        urn = post_urn_from_url(post_url)
        if not urn:
            raise SystemExit(
                f"Could not find an activity id in {post_url}. Use the post's own URL "
                "(the one containing urn:li:activity:<digits> or activity-<digits>)."
            )
        body = {
            "name": f"{keyword} - {urn.rsplit(':', 1)[-1]}",
            "post_id": urn,
            "linkedin_post_url": post_url,
            "keywords": [keyword],
            "dm_template": dm_text,
            "dm_templates": [dm_text] + list(dm_variants or []),
            "auto_connect": bool(cfg_get(self.cfg, "dm_tool.leadshark.auto_connect", True)),
            "status": status or self.create_as,
        }
        replies = cfg_get(self.cfg, "dm_tool.leadshark.comment_replies") or []
        if replies:
            body["comment_reply_template"] = list(replies)
        nfd = cfg_get(self.cfg, "dm_tool.leadshark.non_first_degree_reply")
        if nfd:
            body["non_first_degree_reply_template"] = [nfd] if isinstance(nfd, str) else list(nfd)
        if self.dry_run:
            return {"dry_run": True, "adapter": self.name, "endpoint": "POST /api/automations", "payload": body}
        return self.request("POST", "/api/automations", body=body)

    def set_status(self, automation_id: str, status: str) -> dict:
        if self.dry_run:
            return {"dry_run": True, "endpoint": f"PUT /api/automations/{automation_id}/status", "status": status}
        return self.request("PUT", f"/api/automations/{automation_id}/status", body={"status": status})

    def stats(self, range: str = "weekly") -> dict:
        if self.dry_run:
            return {
                "dry_run": True,
                "adapter": self.name,
                "would_call": [f"GET /api/v1/dashboard-activity?range={range}", "GET /api/automations?limit=100"],
            }
        out: dict = {"adapter": self.name, "range": range}
        try:
            out["activity"] = self.request("GET", "/api/v1/dashboard-activity", params={"range": range})
        except ApiError as e:
            out["activity_error"] = {"status": e.status, "body": e.body}
        listing = self.request("GET", "/api/automations", params={"page": 1, "limit": 100})
        rows = []
        for item in listing.get("data", []) or []:
            st = item.get("stats") or {}
            rows.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "status": item.get("status"),
                    "keywords": item.get("keywords"),
                    "comments": st.get("total_comments"),
                    "dms_sent": st.get("total_dms_sent"),
                    "connections_sent": st.get("total_connections_sent"),
                    "connections_accepted": st.get("total_connections_accepted"),
                }
            )
        out["automations"] = rows
        out["note"] = (
            "The gap between comments and dms_sent is mostly commenters outside your network "
            "who have not connected yet."
        )
        return out
