"""Image provider adapters for graphics-maker.

    from providers.base import get_provider
    provider = get_provider(cfg)            # graphics.provider: none | kieai | openai
    provider = get_provider(cfg, "kieai")   # explicit override (--provider)

Adding a provider: copy providers/openai.py, implement generate() and edit(),
return a local PNG path or an http(s) URL, and register the module name in
providers/base.py:KNOWN_PROVIDERS.
"""
