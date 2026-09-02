#!/usr/bin/env python3
"""Shared configuration loader for guide-maker scripts."""

import json
import os
from pathlib import Path

_config = None
_SKILL_DIR = Path(__file__).resolve().parent.parent


def load_config():
    """Load config.yaml from the skill directory. Returns dict."""
    global _config
    if _config is not None:
        return _config

    config_path = _SKILL_DIR / "config.yaml"

    # Try YAML first (if PyYAML is installed)
    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                _config = yaml.safe_load(f)
            return _config
        except ImportError:
            pass

        # Fall back to JSON config
        json_path = _SKILL_DIR / "config.json"
        if json_path.exists():
            with open(json_path) as f:
                _config = json.load(f)
            return _config

        raise ImportError(
            "PyYAML is required to read config.yaml. "
            "Install it with: pip install pyyaml\n"
            "Or create a config.json instead."
        )

    # Try JSON fallback
    json_path = _SKILL_DIR / "config.json"
    if json_path.exists():
        with open(json_path) as f:
            _config = json.load(f)
        return _config

    raise FileNotFoundError(
        f"Config not found at {config_path}\n"
        f"Copy config.example.yaml to config.yaml and fill in your details.\n"
        f"See README.md for setup instructions."
    )


def get_notion_token():
    """Get the Notion API token from config."""
    token = load_config().get("notion_api_key", "")
    if not token:
        raise ValueError("notion_api_key is required in config.yaml")
    return token


def get_guide_db():
    """Get the Guide Database ID from config."""
    db_id = load_config().get("guide_database_id", "")
    if not db_id:
        raise ValueError("guide_database_id is required in config.yaml")
    return db_id


def get_content_board_db():
    """Get the Content Board Database ID from config (optional)."""
    return load_config().get("content_board_database_id", "")


def get_author_info():
    """Get author name and LinkedIn URL from config."""
    cfg = load_config()
    return {
        "name": cfg.get("author_name", ""),
        "linkedin_url": cfg.get("linkedin_url", ""),
    }


def get_community_info():
    """Get community info from config (optional)."""
    cfg = load_config()
    return {
        "name": cfg.get("community_name", ""),
        "url": cfg.get("community_url", ""),
        "description": cfg.get("community_description", ""),
    }


def get_brand_colors():
    """Get brand colors from config, with defaults."""
    cfg = load_config()
    colors = cfg.get("brand_colors", {})
    return {
        "dark": colors.get("dark", "#1A1A1C"),
        "light": colors.get("light", "#F7F7F7"),
        "accent_1": colors.get("accent_1", "#A6CB17"),
        "accent_2": colors.get("accent_2", "#8033F4"),
    }


def get_kieai_key():
    """Get KieAI API key from config or default file path."""
    cfg = load_config()
    key = cfg.get("kieai_api_key", "")
    if key:
        return key
    # Fall back to default file path
    key_path = os.path.expanduser("~/.config/kieai/api_key")
    if os.path.exists(key_path):
        with open(key_path) as f:
            return f.read().strip()
    return ""


def get_ytdlp_path():
    """Get yt-dlp binary path from config."""
    return load_config().get("ytdlp_path", "yt-dlp")


def get_skill_dir():
    """Get the skill directory path."""
    return _SKILL_DIR
