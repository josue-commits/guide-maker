#!/usr/bin/env python3
"""
Provider interface for image generation.

Every provider is a class with four methods. graphics_generate.py never talks
to an API directly; it only calls these.

    generate(prompt, *, ref_images=(), aspect_ratio="1:1", resolution="2K",
             thinking_high=False) -> str
        Render a new image. ref_images are http(s) URLs or local paths; if
        needs_public_ref_urls() is True the caller uploads local paths first.
        Returns either an http(s) URL to download or a local file path.

    edit(image_path, instruction, *, aspect_ratio="1:1", resolution="2K") -> str
        Apply a delta-only instruction to a local image (the text pass, the
        tweak loop). Same return contract as generate().

    needs_public_ref_urls() -> bool
        True when the API fetches references by URL (KieAI). False when it
        accepts file uploads (OpenAI).

    estimate_cost(op) -> float
        Approximate USD for one call, op in {"generate", "edit"}. Used by
        --estimate. Numbers are ballpark; check the provider's pricing page.

Return values are interpreted by graphics_generate.fetch_result(): a string
starting with http is downloaded, anything else is treated as a local path
and moved into place.

Failure contract: raise ProviderError with a message a stranger can act on.
Never call sys.exit() inside a provider.

`none` is the default provider. It refuses to generate and points at the
zero-cost `card` subcommand, which needs no API at all.
"""
import importlib

KNOWN_PROVIDERS = ("none", "kieai", "openai")

ASPECT_RATIOS = ("1:1", "16:9", "4:5", "9:16")
RESOLUTIONS = ("1K", "2K", "4K")


class ProviderError(RuntimeError):
    """Raised for any provider-side failure (missing key, API error, timeout)."""


def dget(cfg, dotted, default=None):
    """Dotted accessor kept local so providers do not depend on the config shim."""
    node = cfg or {}
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return default if node is None else node


class ImageProvider:
    name = "base"

    def __init__(self, cfg=None):
        self.cfg = cfg or {}

    def generate(self, prompt, *, ref_images=(), aspect_ratio="1:1", resolution="2K",
                 thinking_high=False):
        raise NotImplementedError

    def edit(self, image_path, instruction, *, aspect_ratio="1:1", resolution="2K"):
        raise NotImplementedError

    def needs_public_ref_urls(self):
        return False

    def estimate_cost(self, op):
        return 0.0

    def describe(self):
        return self.name


class NoneProvider(ImageProvider):
    """Default. No API, no cost, no generation."""
    name = "none"

    _MSG = ("graphics.provider is none: no image API is configured. Use the `card` "
            "subcommand (Pillow, zero cost), or set graphics.provider to kieai or openai "
            "in config and add the key (env KIEAI_API_KEY / OPENAI_API_KEY, a key file "
            "under ~/.config/<provider>/api_key, or providers.<provider>.api_key).")

    def generate(self, prompt, *, ref_images=(), aspect_ratio="1:1", resolution="2K",
                 thinking_high=False):
        raise ProviderError(self._MSG)

    def edit(self, image_path, instruction, *, aspect_ratio="1:1", resolution="2K"):
        raise ProviderError(self._MSG)


def get_provider(cfg, name=None):
    """Instantiate the provider named by `name` or graphics.provider (default none)."""
    name = (name or dget(cfg, "graphics.provider", "none") or "none").strip().lower()
    if name == "none":
        return NoneProvider(cfg)
    if name not in KNOWN_PROVIDERS:
        raise ProviderError("Unknown graphics.provider '%s'. Known: %s"
                            % (name, ", ".join(KNOWN_PROVIDERS)))
    pkg = __package__ or "providers"
    try:
        module = importlib.import_module("%s.%s" % (pkg, name))
    except ImportError as e:
        raise ProviderError("Provider '%s' could not be imported (%s). Is providers/%s.py "
                            "present next to base.py?" % (name, e, name))
    cls = getattr(module, "PROVIDER", None)
    if cls is None:
        raise ProviderError("providers/%s.py does not define PROVIDER" % name)
    return cls(cfg)
