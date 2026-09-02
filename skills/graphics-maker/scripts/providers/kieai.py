#!/usr/bin/env python3
"""
KieAI provider (reference adapter).

Ported from a production pipeline. Two request shapes, chosen by model name:

    gpt-image-2*          {prompt, aspect_ratio, resolution, input_urls}
    everything else       {prompt, aspect_ratio, output_format, resolution,
                           image_input, thinking}   (nano-banana family)

Models come from config: graphics.scene_model (default nano-banana-pro) and
graphics.text_model (default gpt-image-2-image-to-image). generate() uses
the scene model, edit() the text model.

KieAI fetches reference images by URL, so needs_public_ref_urls() is True and
edit() uploads the local image through _upload.upload_public first.

Key resolution: env KIEAI_API_KEY, then ~/.config/kieai/api_key, then
providers.kieai.api_key in config.

Returns the result image URL; graphics_generate.py downloads it.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from _cfg import secret  # noqa: E402
from providers.base import ImageProvider, ProviderError, dget  # noqa: E402

API_BASE = "https://api.kie.ai/api/v1"
DEFAULT_SCENE_MODEL = "nano-banana-pro"
DEFAULT_TEXT_MODEL = "gpt-image-2-image-to-image"
GPT_IMAGE_2_PREFIX = "gpt-image-2"
MAX_REFS = 14

# Approximate USD per call at 2K. Check https://kie.ai pricing for current numbers.
COST = {"generate": 0.05, "edit": 0.06}


def _request(method, path, body=None, api_key=None, retries=3):
    """Authenticated request, retrying transient errors (502/503/429/525)."""
    url = API_BASE + path
    headers = {"Authorization": "Bearer %s" % api_key, "Content-Type": "application/json"}
    data = json.dumps(body).encode("utf-8") if body else None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (525, 502, 503, 429) and attempt < retries - 1:
                wait = (attempt + 1) * 10
                print("  HTTP %d, retrying in %ds (attempt %d/%d)..." % (e.code, wait, attempt + 1, retries))
                time.sleep(wait)
            else:
                raise
    return None


def build_input_body(prompt, model, aspect_ratio="1:1", resolution="2K",
                     ref_images=None, thinking_high=False):
    """Build the KieAI `input` body, branching on the model's request shape."""
    refs = list(ref_images or [])[:MAX_REFS]
    if model.startswith(GPT_IMAGE_2_PREFIX):
        body = {"prompt": prompt, "aspect_ratio": aspect_ratio, "resolution": resolution}
        if refs:
            body["input_urls"] = refs
    else:
        body = {"prompt": prompt, "aspect_ratio": aspect_ratio,
                "output_format": "png", "resolution": resolution}
        if refs:
            body["image_input"] = refs
        if thinking_high:
            body["thinking"] = "high"
    return body


def submit_task(prompt, model, api_key, **kw):
    result = _request("POST", "/jobs/createTask",
                      {"model": model, "input": build_input_body(prompt, model, **kw)},
                      api_key=api_key)
    data = (result or {}).get("data") or {}
    task_id = data.get("task_id") or data.get("taskId")
    if not task_id:
        raise ProviderError("KieAI returned no task_id: %s" % result)
    return task_id


def _extract_result_url(data):
    output = data.get("output") or {}
    if output:
        url = output.get("image_url") or output.get("result_url")
        if url:
            return url
        results = output.get("results") or []
        if results:
            return results[0] if isinstance(results[0], str) else results[0].get("url")
    raw = data.get("resultJson", "")
    if raw:
        try:
            urls = json.loads(raw).get("resultUrls", [])
            if urls:
                return urls[0]
        except (json.JSONDecodeError, AttributeError):
            pass
    return None


def poll_and_extract(task_id, api_key, poll_interval=5, max_polls=60):
    """Poll until the task completes. Returns the result URL or raises."""
    for i in range(max_polls):
        time.sleep(poll_interval)
        try:
            status = _request("GET", "/jobs/recordInfo?taskId=%s" % task_id, api_key=api_key)
        except urllib.error.HTTPError:
            continue
        data = (status or {}).get("data") or {}
        state = data.get("state", "")
        if state in ("completed", "success"):
            url = _extract_result_url(data)
            if not url:
                raise ProviderError("KieAI task completed without a result URL: %s" % data)
            return url
        if state in ("fail", "failed", "error"):
            raise ProviderError("KieAI generation failed: %s"
                                % (data.get("failMsg") or data.get("error") or "unknown error"))
        if (i + 1) % 6 == 0:
            print("  still generating... (%ds)" % ((i + 1) * poll_interval))
    raise ProviderError("Timed out after %ds waiting for KieAI task %s"
                        % (max_polls * poll_interval, task_id))


class KieAIProvider(ImageProvider):
    name = "kieai"

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.scene_model = dget(self.cfg, "graphics.scene_model", "") or DEFAULT_SCENE_MODEL
        self.text_model = dget(self.cfg, "graphics.text_model", "") or DEFAULT_TEXT_MODEL
        self.upload_endpoint = dget(self.cfg, "graphics.upload_endpoint", "") or None
        self._key = None

    def _api_key(self):
        if self._key is None:
            self._key = secret(self.cfg, "kieai")
        if not self._key:
            raise ProviderError("No KieAI key. Set env KIEAI_API_KEY, write it to "
                                "~/.config/kieai/api_key, or set providers.kieai.api_key in config.")
        return self._key

    def describe(self):
        return "kieai (scene=%s, text=%s)" % (self.scene_model, self.text_model)

    def needs_public_ref_urls(self):
        return True

    def estimate_cost(self, op):
        return COST.get(op, 0.0)

    def _run(self, prompt, model, **kw):
        key = self._api_key()
        print("KieAI generate (model=%s, resolution=%s, aspect=%s)"
              % (model, kw.get("resolution"), kw.get("aspect_ratio")))
        print("  prompt: %s..." % prompt[:120].replace("\n", " "))
        try:
            task_id = submit_task(prompt, model, key, **kw)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            raise ProviderError("KieAI submit error: %s" % e)
        print("  task: %s" % task_id)
        return poll_and_extract(task_id, key)

    def generate(self, prompt, *, ref_images=(), aspect_ratio="1:1", resolution="2K",
                 thinking_high=False):
        for r in ref_images:
            if not str(r).startswith("http"):
                raise ProviderError("KieAI needs public URLs for references, got %s "
                                    "(graphics_generate.py uploads local paths for you)" % r)
        return self._run(prompt, self.scene_model, ref_images=list(ref_images),
                         aspect_ratio=aspect_ratio, resolution=resolution,
                         thinking_high=thinking_high)

    def edit(self, image_path, instruction, *, aspect_ratio="1:1", resolution="2K"):
        if str(image_path).startswith("http"):
            url = image_path
        else:
            from _upload import upload_public
            print("Uploading %s for the edit..." % os.path.basename(image_path), flush=True)
            try:
                url = upload_public(image_path, endpoint=self.upload_endpoint)
            except (RuntimeError, FileNotFoundError) as e:
                raise ProviderError(str(e))
        return self._run(instruction, self.text_model, ref_images=[url],
                         aspect_ratio=aspect_ratio, resolution=resolution)


PROVIDER = KieAIProvider
