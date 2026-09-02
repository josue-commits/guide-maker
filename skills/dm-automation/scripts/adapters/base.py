#!/usr/bin/env python3
"""Adapter interface for keyword-comment DM tools.

Every adapter receives tool-neutral inputs and returns a plain dict the CLI
prints as JSON. The `automation` dict passed to schedule_post uses these keys
(the LeadShark field names double as the neutral vocabulary):

    name                            str    label for the automation
    keywords                        [str]  comment keywords that trigger the DM
    dm_template                     str    primary DM, plain text, merge tag inside
    dm_templates                    [str]  primary plus rotated variants
    comment_reply_template          [str]  public replies rotated under the comment
    non_first_degree_reply_template [str]  reply for people who cannot be DMed yet
    auto_connect                    bool   send a connection request to those people
    auto_like                       bool   like the comment (tool-dependent)

Adapters that do not support a key ignore it and say so in the returned dict.
"""

from __future__ import annotations

import importlib
from typing import Any, Optional


class DMTool:
    """Base class. Subclasses override every method they support."""

    name = "base"

    def __init__(self, cfg: dict, dry_run: bool = False, out_dir: Optional[str] = None):
        self.cfg = cfg
        self.dry_run = dry_run
        self.out_dir = out_dir

    def test(self) -> dict:
        """Cheapest possible check that the adapter is usable."""
        raise NotImplementedError(f"{self.name}: test() not implemented")

    def list_keywords(self) -> list[str]:
        """Every keyword already in use, upper-cased, for collision checks."""
        raise NotImplementedError(f"{self.name}: list_keywords() not implemented")

    def schedule_post(
        self,
        content: str,
        time_iso: str,
        image_path: Optional[str],
        automation: dict,
    ) -> dict:
        """Schedule a post with its graphic and keyword automation."""
        raise NotImplementedError(f"{self.name}: schedule_post() not implemented")

    def attach_automation(
        self,
        post_url: str,
        keyword: str,
        dm_text: str,
        dm_variants: list[str],
        status: str,
    ) -> dict:
        """Attach a keyword automation to a post that is already live."""
        raise NotImplementedError(f"{self.name}: attach_automation() not implemented")

    def stats(self, range: str = "weekly") -> dict:
        """Rollup of comments, DMs sent, connections, leads."""
        raise NotImplementedError(f"{self.name}: stats() not implemented")


# provider name -> "module:Class". Modules load lazily so the manual adapter
# never imports networking code.
PROVIDERS: dict[str, str] = {
    "manual": "adapters.manual:ManualTool",
    "leadshark": "adapters.leadshark:LeadSharkTool",
}


def get_adapter(cfg: dict, provider: Optional[str] = None, **kwargs: Any) -> DMTool:
    """Instantiate the adapter named by `provider` or by dm_tool.provider."""
    if not provider:
        provider = _cfg_provider(cfg)
    provider = (provider or "manual").strip().lower()
    spec = PROVIDERS.get(provider)
    if not spec:
        raise SystemExit(
            f"Unknown dm_tool.provider '{provider}'. Known: {', '.join(sorted(PROVIDERS))}."
        )
    module_name, class_name = spec.split(":")
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls(cfg, **kwargs)


def _cfg_provider(cfg: dict) -> str:
    node = cfg.get("dm_tool") if isinstance(cfg, dict) else None
    if isinstance(node, dict) and node.get("provider"):
        return str(node["provider"])
    return "manual"
