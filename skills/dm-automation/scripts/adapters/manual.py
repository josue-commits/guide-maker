#!/usr/bin/env python3
"""Manual adapter: the default. No network, no account, no API key.

schedule_post and attach_automation write a bundle folder you open next to
whatever DM tool you use (or your own hands):

    <out_dir>/dm-bundle/
      post.txt              the post copy, ready to paste
      dm-primary.txt        the DM your tool sends on the keyword comment
      dm-variant-N.txt      rotated variants, when given
      comment-replies.txt   public replies, one per line, when given
      graphic.<ext>         a copy of the post graphic
      schedule.json         keyword, time, adapter, file list
      checklist.md          the steps to do in your tool, in order

This module must never import urllib, http, socket or requests.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

from .base import DMTool

_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")


def _cfg(cfg: dict, dotted: str, default=None):
    node = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return default if node is None else node


def local_time_line(time_iso: str, tz_name: Optional[str]) -> str:
    """Render an ISO timestamp in the configured zone, or say why not."""
    if not time_iso:
        return ""
    try:
        dt = _dt.datetime.fromisoformat(time_iso.replace("Z", "+00:00"))
    except ValueError:
        return f"{time_iso} (could not parse as ISO 8601)"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    utc = dt.astimezone(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC %A")
    if not tz_name:
        return utc
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+

        local = dt.astimezone(ZoneInfo(tz_name)).strftime("%Y-%m-%d %H:%M %Z %A")
        return f"{local} ({utc})"
    except Exception:  # unknown zone or missing tz database
        return f"{utc} (timezone '{tz_name}' not available on this machine)"


class ManualTool(DMTool):
    name = "manual"

    # ----------------------------------------------------------------- helpers

    def _bundle_dir(self) -> Path:
        base = Path(self.out_dir or ".").expanduser().resolve()
        bundle = base / "dm-bundle"
        bundle.mkdir(parents=True, exist_ok=True)
        return bundle

    def _timezone(self) -> Optional[str]:
        return _cfg(self.cfg, "dm_tool.timezone") or _cfg(self.cfg, "dm_tool.leadshark.timezone")

    def _write_dms(self, bundle: Path, dm_text: str, variants: list[str]) -> list[str]:
        written = []
        primary = bundle / "dm-primary.txt"
        primary.write_text(dm_text.rstrip("\n") + "\n", encoding="utf-8")
        written.append(primary.name)
        for i, variant in enumerate(variants or [], start=1):
            path = bundle / f"dm-variant-{i}.txt"
            path.write_text(variant.rstrip("\n") + "\n", encoding="utf-8")
            written.append(path.name)
        return written

    def _write_replies(self, bundle: Path, automation: dict) -> Optional[str]:
        replies = list(automation.get("comment_reply_template") or [])
        nfd = list(automation.get("non_first_degree_reply_template") or [])
        if not replies and not nfd:
            return None
        lines = []
        if replies:
            lines.append("# Public replies under the comment (rotate):")
            lines.extend(replies)
        if nfd:
            lines.append("")
            lines.append("# Reply for people outside your network (they cannot be DMed until they connect):")
            lines.extend(nfd)
        path = bundle / "comment-replies.txt"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path.name

    def _copy_graphic(self, bundle: Path, image_path: Optional[str]) -> Optional[str]:
        if not image_path:
            return None
        src = Path(image_path).expanduser()
        if not src.is_file():
            raise SystemExit(f"Graphic not found: {src}")
        dest = bundle / f"graphic{src.suffix.lower() or '.png'}"
        shutil.copyfile(src, dest)
        return dest.name

    @staticmethod
    def _guide_urls(*texts: str) -> list[str]:
        seen = []
        for text in texts:
            for url in _URL_RE.findall(text or ""):
                url = url.rstrip(".,;:")
                if url not in seen:
                    seen.append(url)
        return seen

    def _checklist(
        self,
        bundle: Path,
        keyword: Optional[str],
        time_iso: Optional[str],
        post_url: Optional[str],
        graphic_name: Optional[str],
        dm_files: list[str],
        reply_file: Optional[str],
        automation: dict,
        urls: list[str],
    ) -> str:
        kw = keyword or "(no keyword set)"
        tool = _cfg(self.cfg, "dm_tool.provider", "manual")
        lines = ["# DM bundle checklist", ""]
        lines.append(f"Keyword: {kw}")
        if time_iso:
            lines.append(f"Post window: {local_time_line(time_iso, self._timezone())}")
        if post_url:
            lines.append(f"Post: {post_url}")
        lines.append(f"Folder: {bundle}")
        lines.append("")
        lines.append("Do these in order, in whatever DM tool you use.")
        lines.append("")
        step = 1
        if graphic_name:
            lines.append(
                f"{step}. Attach the graphic `{graphic_name}`. It carries the keyword bar, so the post asks "
                "for nothing without it. Read the keyword on the graphic character by character before you post."
            )
            step += 1
        elif not post_url:
            lines.append(
                f"{step}. No graphic was given. A lead magnet post needs one: the keyword lives in the graphic, "
                "not in the copy. Generate it with graphics-maker before posting."
            )
            step += 1
        if not post_url:
            lines.append(f"{step}. Paste `post.txt` as the post copy. The copy must not name the keyword.")
            step += 1
        lines.append(
            f"{step}. In your tool, set the trigger keyword to `{kw}` on this post. One keyword per guide, "
            "unique across your account."
        )
        step += 1
        dm_list = ", ".join(f"`{f}`" for f in dm_files)
        lines.append(
            f"{step}. Paste the DM(s): {dm_list}. Keep every paragraph on one line; the DM pane wraps text itself. "
            "Leave the merge tag exactly as written so the tool substitutes the first name."
        )
        step += 1
        if reply_file:
            lines.append(f"{step}. Add the public replies from `{reply_file}` if your tool supports rotated replies.")
            step += 1
        if automation.get("auto_connect"):
            lines.append(
                f"{step}. Turn on auto-connect (or the equivalent). Commenters outside your network cannot receive "
                "the DM until they connect."
            )
            step += 1
        if urls:
            lines.append(f"{step}. Confirm every guide link in the DM resolves for someone who is NOT in your workspace:")
            for url in urls:
                lines.append(f'   curl -s -o /dev/null -w "%{{http_code}}\\n" -L "{url}"')
            lines.append(
                "   A Notion page returns 200 only after you publish it to the web from the Notion app. "
                "Until then every commenter gets a dead link."
            )
        else:
            lines.append(f"{step}. Confirm the public guide URL in the DM resolves for someone outside your workspace.")
        step += 1
        if time_iso:
            lines.append(f"{step}. Post (or schedule) inside your window: {local_time_line(time_iso, self._timezone())}.")
        else:
            lines.append(f"{step}. Activate the automation once the DM reads right.")
        step += 1
        lines.append(f"{step}. After the first comment lands, check that the DM actually fired and the link opens.")
        lines.append("")
        lines.append(f"dm_tool.provider is `{tool}`. Switch it to an adapter to have the CLI do the tool steps for you.")
        path = bundle / "checklist.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path.name

    # ------------------------------------------------------------- interface

    def test(self) -> dict:
        bundle_parent = Path(self.out_dir or ".").expanduser().resolve()
        return {
            "ok": True,
            "adapter": self.name,
            "network": False,
            "out_dir": str(bundle_parent),
            "note": "Manual adapter: schedule and attach write a bundle you paste into your DM tool.",
        }

    def list_keywords(self) -> list[str]:
        print(
            "Manual adapter has no keyword registry. Check keywords in your DM tool and in your "
            "Content Board (guide-maker's keyword_check.py covers the Notion side).",
            file=sys.stderr,
        )
        return []

    def schedule_post(self, content: str, time_iso: str, image_path: Optional[str], automation: dict) -> dict:
        bundle = self._bundle_dir()
        (bundle / "post.txt").write_text(content.rstrip("\n") + "\n", encoding="utf-8")
        dm_text = automation.get("dm_template") or ""
        variants = [v for v in (automation.get("dm_templates") or [])[1:]]
        dm_files = self._write_dms(bundle, dm_text, variants) if dm_text else []
        reply_file = self._write_replies(bundle, automation)
        graphic_name = self._copy_graphic(bundle, image_path)
        keywords = list(automation.get("keywords") or [])
        keyword = keywords[0] if keywords else None
        urls = self._guide_urls(dm_text, *variants)
        checklist = self._checklist(
            bundle, keyword, time_iso, None, graphic_name, dm_files, reply_file, automation, urls
        )
        meta = {
            "adapter": self.name,
            "dry_run": self.dry_run,
            "keywords": keywords,
            "scheduled_time": time_iso,
            "scheduled_time_local": local_time_line(time_iso, self._timezone()),
            "automation_name": automation.get("name"),
            "auto_connect": bool(automation.get("auto_connect")),
            "files": ["post.txt"] + dm_files + [f for f in (reply_file, graphic_name, checklist) if f],
        }
        (bundle / "schedule.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "bundle": str(bundle), **meta}

    def attach_automation(
        self, post_url: str, keyword: str, dm_text: str, dm_variants: list[str], status: str
    ) -> dict:
        bundle = self._bundle_dir()
        automation = {
            "keywords": [keyword],
            "dm_template": dm_text,
            "dm_templates": [dm_text] + list(dm_variants or []),
            "auto_connect": bool(_cfg(self.cfg, "dm_tool.leadshark.auto_connect", True)),
        }
        dm_files = self._write_dms(bundle, dm_text, list(dm_variants or []))
        urls = self._guide_urls(dm_text, *(dm_variants or []))
        checklist = self._checklist(bundle, keyword, None, post_url, None, dm_files, None, automation, urls)
        meta = {
            "adapter": self.name,
            "dry_run": self.dry_run,
            "post_url": post_url,
            "keywords": [keyword],
            "status": status,
            "files": dm_files + [checklist],
        }
        (bundle / "schedule.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "bundle": str(bundle), **meta}

    def stats(self, range: str = "weekly") -> dict:
        return {
            "ok": False,
            "adapter": self.name,
            "range": range,
            "note": "Manual adapter has no stats. Read comments, DMs sent and leads from your DM tool's dashboard.",
        }
