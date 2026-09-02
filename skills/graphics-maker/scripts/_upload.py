#!/usr/bin/env python3
"""
Upload a local image to a public URL.

Only used when an image provider reports needs_public_ref_urls() == True
(KieAI fetches reference images by URL). Providers that accept local files
(OpenAI) never call this, and neither does the zero-cost `card` path.

The default endpoint is catbox.moe's anonymous upload API. Override it with
`graphics.upload_endpoint` in config. Any endpoint that accepts the same
multipart form (reqtype=fileupload, fileToUpload=<file>) and answers with
the public URL in the response body works.

Usage:
    python3 _upload.py /absolute/path/to/image.png [--config /path/config.yaml]
"""
import argparse
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cfg import load_config, cfg_get  # noqa: E402

DEFAULT_ENDPOINT = "https://catbox.moe/user/api.php"


def _multipart(fields, file_field, file_path):
    boundary = "----graphics-maker-" + uuid.uuid4().hex
    body = bytearray()
    for k, v in fields.items():
        body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                 % (boundary, k, v)).encode("utf-8")
    ctype = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        data = f.read()
    body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
             "Content-Type: %s\r\n\r\n" % (boundary, file_field, os.path.basename(file_path), ctype)
             ).encode("utf-8")
    body += data
    body += ("\r\n--%s--\r\n" % boundary).encode("utf-8")
    return bytes(body), "multipart/form-data; boundary=%s" % boundary


def upload_public(file_path, endpoint=None, max_retries=3, timeout=120):
    """Upload file_path and return its public URL. Raises RuntimeError on failure."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)
    endpoint = endpoint or DEFAULT_ENDPOINT
    last = ""
    for attempt in range(1, max_retries + 1):
        try:
            body, ctype = _multipart({"reqtype": "fileupload"}, "fileToUpload", file_path)
            req = urllib.request.Request(endpoint, data=body, method="POST",
                                         headers={"Content-Type": ctype,
                                                  "User-Agent": "graphics-maker/2"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", "replace").strip()
            if text.startswith("http"):
                return text
            last = text[:80] or "empty response"
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            last = str(e)
        if attempt < max_retries:
            wait = attempt * 5
            print("  upload attempt %d failed (%s), retrying in %ds..." % (attempt, last, wait),
                  file=sys.stderr, flush=True)
            time.sleep(wait)
    raise RuntimeError("Upload failed after %d attempts via %s: %s. "
                       "Providers that read local files (openai) do not need this step; "
                       "for kieai, retry later or host the image yourself and pass its URL."
                       % (max_retries, endpoint, last))


def main():
    ap = argparse.ArgumentParser(description="Upload a local image to a public URL.")
    ap.add_argument("path", help="Absolute path to the image")
    ap.add_argument("--config", default=None, help="Config file (default: auto-discover)")
    args = ap.parse_args()
    cfg = load_config(args.config)
    endpoint = cfg_get(cfg, "graphics.upload_endpoint", "") or DEFAULT_ENDPOINT
    try:
        print(upload_public(args.path, endpoint=endpoint))
    except (RuntimeError, FileNotFoundError) as e:
        print("Error: %s" % e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
