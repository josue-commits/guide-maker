#!/usr/bin/env python3
"""
OpenAI Images provider. Best effort: community-tested wanted.

This adapter was written against the documented `images.generate` and
`images.edit` calls of the `openai` Python package but has not been run
against a live account by the maintainers. If you use it, please report what
worked and what did not (model names, size limits, error text).

    generate()  images.generate(model, prompt, size, quality) -> b64 -> local PNG
                with ref_images: images.edit with the references as input files
    edit()      images.edit(model, image=<local file>, prompt, size) -> local PNG

Models: graphics.scene_model and graphics.text_model, both default to
"gpt-image-1". Set them to whatever image model your account exposes.

Size comes from the aspect ratio (1:1 -> 1024x1024, 16:9 -> 1536x1024,
9:16 and 4:5 -> 1024x1536). Quality comes from the resolution flag
(1K low, 2K medium, 4K high). The API returns base64; the adapter writes a
PNG into a temp folder and returns its path.

`openai` is optional. It is imported lazily, so the rest of graphics-maker
never needs it. Install with: pip install -r requirements-optional.txt

Key resolution: env OPENAI_API_KEY, then ~/.config/openai/api_key, then
providers.openai.api_key in config.
"""
import base64
import os
import sys
import tempfile
import urllib.request

_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from _cfg import secret  # noqa: E402
from providers.base import ImageProvider, ProviderError, dget  # noqa: E402

DEFAULT_MODEL = "gpt-image-1"

SIZE_BY_ASPECT = {"1:1": "1024x1024", "16:9": "1536x1024", "9:16": "1024x1536", "4:5": "1024x1536"}
QUALITY_BY_RES = {"1K": "low", "2K": "medium", "4K": "high"}

# Approximate USD per 1024-square image by quality, from the public price list
# at the time of writing. Check https://openai.com/api/pricing before relying on it.
COST_BY_QUALITY = {"low": 0.011, "medium": 0.042, "high": 0.167}


def _import_openai():
    try:
        import openai  # noqa: F401
        return openai
    except ImportError:
        raise ProviderError("The openai package is not installed. Run: "
                            "pip install -r requirements-optional.txt "
                            "(or pip install openai). The rest of graphics-maker does not need it.")


class OpenAIProvider(ImageProvider):
    name = "openai"

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.scene_model = dget(self.cfg, "graphics.scene_model", "") or DEFAULT_MODEL
        self.text_model = dget(self.cfg, "graphics.text_model", "") or DEFAULT_MODEL
        self._client = None

    def describe(self):
        return "openai (scene=%s, text=%s, community-tested wanted)" % (self.scene_model, self.text_model)

    def needs_public_ref_urls(self):
        return False

    def estimate_cost(self, op, resolution="2K"):
        return COST_BY_QUALITY.get(QUALITY_BY_RES.get(resolution, "medium"), 0.042)

    def _client_or_raise(self):
        if self._client is None:
            openai = _import_openai()
            key = secret(self.cfg, "openai")
            if not key:
                raise ProviderError("No OpenAI key. Set env OPENAI_API_KEY, write it to "
                                    "~/.config/openai/api_key, or set providers.openai.api_key in config.")
            self._client = openai.OpenAI(api_key=key)
        return self._client

    @staticmethod
    def _write_result(response):
        try:
            item = response.data[0]
            b64 = getattr(item, "b64_json", None)
            url = getattr(item, "url", None)
        except (AttributeError, IndexError):
            raise ProviderError("OpenAI returned no image data: %r" % (response,))
        out_dir = tempfile.mkdtemp(prefix="graphics-maker-openai-")
        out = os.path.join(out_dir, "result.png")
        if b64:
            with open(out, "wb") as f:
                f.write(base64.b64decode(b64))
            return out
        if url:
            return url
        raise ProviderError("OpenAI response had neither b64_json nor url")

    @staticmethod
    def _local_copy(ref):
        """References may be URLs; images.edit wants file objects."""
        if str(ref).startswith("http"):
            tmp = os.path.join(tempfile.mkdtemp(prefix="graphics-maker-ref-"), "ref.png")
            urllib.request.urlretrieve(ref, tmp)
            return tmp
        return ref

    def generate(self, prompt, *, ref_images=(), aspect_ratio="1:1", resolution="2K",
                 thinking_high=False):
        client = self._client_or_raise()
        size = SIZE_BY_ASPECT.get(aspect_ratio, "1024x1024")
        quality = QUALITY_BY_RES.get(resolution, "medium")
        print("OpenAI images (model=%s, size=%s, quality=%s)" % (self.scene_model, size, quality))
        try:
            if ref_images:
                files = [open(self._local_copy(r), "rb") for r in ref_images]
                try:
                    resp = client.images.edit(model=self.scene_model, image=files,
                                              prompt=prompt, size=size, quality=quality)
                finally:
                    for f in files:
                        f.close()
            else:
                resp = client.images.generate(model=self.scene_model, prompt=prompt,
                                              size=size, quality=quality)
        except Exception as e:  # the SDK raises many types; surface them all as one
            raise ProviderError("OpenAI images call failed: %s" % e)
        return self._write_result(resp)

    def edit(self, image_path, instruction, *, aspect_ratio="1:1", resolution="2K"):
        client = self._client_or_raise()
        if not os.path.exists(image_path):
            raise ProviderError("Image not found: %s" % image_path)
        size = SIZE_BY_ASPECT.get(aspect_ratio, "1024x1024")
        quality = QUALITY_BY_RES.get(resolution, "medium")
        print("OpenAI images.edit (model=%s, size=%s, quality=%s)" % (self.text_model, size, quality))
        try:
            with open(image_path, "rb") as f:
                resp = client.images.edit(model=self.text_model, image=f, prompt=instruction,
                                          size=size, quality=quality)
        except Exception as e:
            raise ProviderError("OpenAI images.edit failed: %s" % e)
        return self._write_result(resp)


PROVIDER = OpenAIProvider
