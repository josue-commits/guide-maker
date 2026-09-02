"""Smoke test for guide-maker v2.

Runs on a fresh machine with only `pip install -r requirements.txt`. No tokens,
no network: every command here is a dry run, a Pillow render, a lint, or an
offline check. If it fails on your machine, open an issue with the output.

    python3 -m unittest tests/test_smoke.py -v
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GM = ROOT / "skills" / "guide-maker" / "scripts"
GX = ROOT / "skills" / "graphics-maker" / "scripts"
DM = ROOT / "skills" / "dm-automation" / "scripts"
FIX = ROOT / "tests" / "fixtures"
CFG = FIX / "config.test.yaml"
PY = sys.executable

ENV = dict(os.environ)
for k in ("NOTION_API_KEY", "KIEAI_API_KEY", "OPENAI_API_KEY", "APIFY_TOKEN", "LEADSHARK_API_KEY"):
    ENV.pop(k, None)
ENV["GUIDE_MAKER_CONFIG"] = str(CFG)
# Point HOME at an empty dir so no ~/.config/*/api_key leaks in, but keep the
# user site-packages reachable (PyYAML and Pillow are often installed there).
import site
_USER_SITE = site.getusersitepackages() if hasattr(site, "getusersitepackages") else ""
ENV["HOME"] = tempfile.mkdtemp(prefix="gm-home-")
ENV["PYTHONPATH"] = os.pathsep.join(p for p in (_USER_SITE, ENV.get("PYTHONPATH", "")) if p)


def future_iso(days=2):
    import datetime
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(*args, ok=True, cwd=None):
    proc = subprocess.run([PY, *map(str, args)], capture_output=True, text=True, env=ENV, cwd=cwd or ROOT)
    if ok and proc.returncode != 0:
        raise AssertionError(f"exit {proc.returncode}\n$ {' '.join(map(str, args))}\n{proc.stdout}\n{proc.stderr}")
    return proc


class TmpDirMixin:
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="gm-smoke-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestConfigAndDoctor(TmpDirMixin, unittest.TestCase):
    def test_doctor_offline_json_is_green_or_skip(self):
        proc = run(GM / "doctor.py", "--offline", "--json", "--config", CFG)
        report = json.loads(proc.stdout)
        levels = {c["level"] for c in report["checks"]}
        self.assertTrue(levels <= {"OK", "WARN", "SKIP"}, report)

    def test_v1_config_shim_loads_with_one_warning(self):
        v1 = self.tmp / "config.yaml"
        v1.write_text(
            'notion_api_key: ""\nguide_database_id: "0123456789abcdef0123456789abcdef"\n'
            'author_name: "Sam"\nlinkedin_url: "https://www.linkedin.com/in/sam/"\n'
            'community_name: "Ops Club"\ncommunity_url: "https://example.com/club"\n'
            'accounts:\n  - name: "Sam"\n    voice: founder\n    cta_type: community\n'
        )
        proc = run(GM / "doctor.py", "--offline", "--json", "--config", v1)
        self.assertIn("deprecat", (proc.stdout + proc.stderr).lower())
        report = json.loads(proc.stdout)
        self.assertEqual(report["config"]["author"]["name"], "Sam")
        self.assertEqual(report["config"]["accounts"][0]["dm_destination"], "community")

    def test_migrate_config_prints_v2(self):
        proc = run(GM / "doctor.py", "--migrate-config", "--config", CFG)
        self.assertIn("schema_version: 2", proc.stdout)


class TestNotionConversion(TmpDirMixin, unittest.TestCase):
    def test_code_languages_normalized_and_directives_stripped(self):
        proc = run(GM / "md_to_notion.py", "blocks", FIX / "sample-guide" / "01-setup.md", "--config", CFG)
        blocks = json.loads(proc.stdout)
        langs = [b["code"]["language"] for b in blocks if b.get("type") == "code"]
        self.assertTrue(langs, "no code blocks parsed")
        allowed = {"javascript", "shell", "yaml", "plain text", "docker", "bash", "python", "json"}
        for lang in langs:
            self.assertIn(lang, allowed, lang)
        text = json.dumps(blocks)
        self.assertNotIn("Page icon", text)
        self.assertIn("Icons: here is why", text)

    def test_publish_hub_dry_run_respects_community_and_source_policy(self):
        base = [GM / "publish_guide_hub.py", "--dry-run", "--config", CFG,
                "--title", "Sample Guide", "--description", "A sample", "--keyword", "SAMPLEKW",
                "--type", "Technical Tutorial", "--week", "2026-01-05", "--icon", "🛠️",
                "--build-item", "A working setup", "--audience-item", "Operators",
                "--nav-note", "Skip to step 2 if installed.",
                "--step", f"🚀|Setup|Install and configure|{FIX / 'sample-guide' / '01-setup.md'}",
                "--source", "official|Docs|https://example.com/docs"]
        proc = run(*base)
        self.assertNotIn("Join", proc.stdout)   # community.url is empty in the test config
        proc = run(*base, "--source", "youtube|A video|https://youtube.com/watch?v=x", ok=False)
        self.assertNotEqual(proc.returncode, 0)

    def test_content_entry_dry_run_builds_dm_toggles(self):
        proc = run(GM / "md_to_notion.py", "create-content-entry", "--dry-run", "--config", CFG,
                   "--title", "SAMPLEKW | Mon Jan 05", "--keyword", "SAMPLEKW", "--post-date", "2026-01-05",
                   "--day", "Monday",
                   "--variation", f"Contrarian Hook|@{FIX / 'copy' / 'good-prose-1.txt'}",
                   "--dm", f"Direct|@{FIX / 'dm' / 'good-combined.txt'}")
        self.assertIn("DM Templates", proc.stdout)
        self.assertIn("Draft", proc.stdout)


class TestCoverAndGraphic(TmpDirMixin, unittest.TestCase):
    def test_simple_banner_creates_dirs_and_size(self):
        out = self.tmp / "deep" / "dir" / "banner.png"
        run(GM / "banner_generator.py", "simple", "--title", "Sample Guide", "--output", out, "--config", CFG)
        from PIL import Image
        with Image.open(out) as im:
            self.assertEqual(im.size, (1500, 600))

    def test_banner_refuses_keyword_as_title(self):
        proc = run(GM / "banner_generator.py", "simple", "--title", "SAMPLEKW", "--keyword", "SAMPLEKW",
                   "--output", self.tmp / "kw.png", "--config", CFG, ok=False)
        self.assertNotEqual(proc.returncode, 0)

    def test_card_has_cta_bar_and_prints_exact_string(self):
        out = self.tmp / "post.png"
        proc = run(GX / "graphics_generate.py", "card", "--title", "Automate your CRM follow-ups",
                   "--subtitle", "5 workflows", "--stat", "3|tools", "--keyword", "SAMPLEKW",
                   "--output", out, "--config", CFG)
        self.assertIn('COMMENT "SAMPLEKW" TO GET IT FOR FREE', proc.stdout)
        from PIL import Image, ImageStat
        im = Image.open(out).convert("L")
        w, h = im.size
        self.assertEqual((w, h), (2048, 2048))
        mid = ImageStat.Stat(im.crop((0, int(h * 0.4), w, int(h * 0.6)))).mean[0]
        band = ImageStat.Stat(im.crop((0, int(h * 0.92), w, h))).mean[0]
        self.assertGreater(abs(mid - band), 40, "CTA band does not differ from the art")

    def test_cta_bar_rejects_bad_keyword(self):
        src = self.tmp / "src.png"
        from PIL import Image
        Image.new("RGB", (512, 512), "#333333").save(src)
        proc = run(GX / "cta_bar.py", "--image", src, "--keyword", "BAD-KW", "--output", self.tmp / "o.png", ok=False)
        self.assertNotEqual(proc.returncode, 0)

    def test_strip_credentials_removes_injected_chunk(self):
        src = self.tmp / "c2pa.png"
        from PIL import Image
        Image.new("RGB", (64, 64), "#A6CB17").save(src)
        raw = src.read_bytes()
        # inject a fake caBX chunk after IHDR (length, type, data, crc)
        import struct, zlib
        ihdr_end = raw.index(b"IHDR") + 4 + 13 + 4
        data = b"c2pa.assertions"
        chunk = struct.pack(">I", len(data)) + b"caBX" + data + struct.pack(">I", zlib.crc32(b"caBX" + data) & 0xFFFFFFFF)
        src.write_bytes(raw[:ihdr_end] + chunk + raw[ihdr_end:])
        self.assertIn(b"caBX", src.read_bytes())
        out = self.tmp / "clean.png"
        run(GX / "strip_credentials.py", src, "-o", out)
        self.assertNotIn(b"caBX", out.read_bytes())

    def test_scene_estimate_makes_no_call(self):
        proc = run(GX / "graphics_generate.py", "scene", "--prompt", "x", "--output-prefix", self.tmp / "s",
                   "--estimate", "--config", CFG)
        self.assertIn("$", proc.stdout)


class TestLint(unittest.TestCase):
    def test_good_copy_passes(self):
        run(GM / "lint_copy.py", "copy", FIX / "copy" / "good-prose-1.txt", FIX / "copy" / "good-prose-2.txt",
            "--keyword", "SAMPLEKW", "--config", CFG)

    def test_bad_copy_fails_with_rule_ids(self):
        for name, rule in (("bad-keyword-in-copy.txt", "keyword-in-copy"), ("bad-emdash.txt", "em-dash"),
                           ("bad-too-long.txt", "word-count"), ("bad-old-cta.txt", "banned-cta")):
            proc = run(GM / "lint_copy.py", "copy", FIX / "copy" / name, "--keyword", "SAMPLEKW", "--config", CFG, ok=False)
            self.assertEqual(proc.returncode, 1, name)
            self.assertIn(rule, proc.stdout + proc.stderr, name)

    def test_copy_mode_downgrades_keyword_to_warning_with_evidence(self):
        proc = run(GM / "lint_copy.py", "copy", FIX / "copy" / "bad-keyword-in-copy.txt", "--keyword", "SAMPLEKW",
                   "--cta-mode", "copy", "--config", CFG, ok=False)
        self.assertIn(proc.returncode, (0, 2))
        self.assertIn("11,432", proc.stdout + proc.stderr)

    def test_dm_lint(self):
        run(GM / "lint_copy.py", "dm", FIX / "dm" / "good-combined.txt", "--config", CFG)
        for name, rule in (("bad-name-tag.txt", "name-tag"), ("bad-hardwrap.txt", "hard-wrap"), ("bad-app-url.txt", "public-url")):
            proc = run(GM / "lint_copy.py", "dm", FIX / "dm" / name, "--config", CFG, ok=False)
            self.assertEqual(proc.returncode, 1, name)
            self.assertIn(rule, proc.stdout + proc.stderr, name)


class TestKeywordCheck(unittest.TestCase):
    def test_shape_rejected_offline(self):
        proc = run(GM / "keyword_check.py", "SAMPLE-KW", "--offline", "--config", CFG, ok=False)
        self.assertNotEqual(proc.returncode, 0)
        run(GM / "keyword_check.py", "SAMPLEKW", "--offline", "--config", CFG)


class TestDM(TmpDirMixin, unittest.TestCase):
    def test_render_all_versions_and_merge_tag(self):
        out = self.tmp / "dm"
        run(DM / "dm_cli.py", "render", "--guide-url",
            "https://example.notion.site/sample-guide-0123456789abcdef0123456789abcdef",
            "--guide-title", "Sample Guide", "--version", "all", "--out-dir", out, "--config", CFG)
        files = sorted(p.name for p in out.glob("*.txt"))
        self.assertTrue(files, "no DM files written")
        for p in out.glob("*.txt"):
            body = p.read_text()
            self.assertIn("{{firstName}}", body, p.name)
            self.assertNotIn("{name}", body, p.name)

    def test_render_rejects_workspace_url(self):
        proc = run(DM / "dm_cli.py", "render", "--guide-url", "https://app.notion.com/p/abc",
                   "--out-dir", self.tmp / "dm2", "--config", CFG, ok=False)
        self.assertNotEqual(proc.returncode, 0)

    def test_manual_schedule_dry_run_writes_checklist_without_network(self):
        post = self.tmp / "post.txt"; post.write_text("A post body.\nFree access 👇\n")
        dm = self.tmp / "dm.txt"; dm.write_text("Hey {{firstName}}, here it is: https://example.notion.site/x-0123456789abcdef0123456789abcdef\n\nSam\n")
        img = self.tmp / "g.png"
        from PIL import Image
        Image.new("RGB", (64, 64), "#000").save(img)
        out = self.tmp / "bundle"
        # block sockets: any adapter that opens one fails loudly
        sitecustom = self.tmp / "sitecustomize.py"
        sitecustom.write_text("import socket\n_o=socket.socket.__init__\ndef _b(*a,**k): raise RuntimeError('network blocked in smoke test')\nsocket.socket.__init__=_b\n")
        env = dict(ENV); env["PYTHONPATH"] = os.pathsep.join(p for p in (str(self.tmp), ENV.get("PYTHONPATH", "")) if p)
        proc = subprocess.run([PY, str(DM / "dm_cli.py"), "schedule", "--content", f"@{post}", "--image", str(img),
                               "--time", future_iso(), "--keyword", "SAMPLEKW", "--dm", f"@{dm}",
                               "--out-dir", str(out), "--dry-run", "--config", str(CFG)],
                              capture_output=True, text=True, env=env, cwd=ROOT)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(any(out.rglob("checklist.md")), "checklist.md not written")

    def test_image_fit_under_ceiling(self):
        big = self.tmp / "big.png"
        from PIL import Image
        import random
        # a plausible post graphic: gradient background with a noisy texture band, big enough to exceed 4 MiB as PNG
        random.seed(7)
        w = h = 3000
        im = Image.new("RGB", (w, h))
        px = im.load()
        for y in range(h):
            for x in range(0, w, 3):
                base = (x * 255 // w, y * 255 // h, 140)
                n = random.randrange(-60, 60)
                px[x, y] = (max(0, min(255, base[0] + n)), max(0, min(255, base[1] + n)), base[2])
                if x + 1 < w: px[x + 1, y] = px[x, y]
                if x + 2 < w: px[x + 2, y] = px[x, y]
        im.save(big, optimize=False)
        self.assertGreater(big.stat().st_size, 4194304)
        out = self.tmp / "fit.jpg"
        run(DM / "dm_cli.py", "image-fit", big, "--output", out, "--config", CFG)
        self.assertLessEqual(out.stat().st_size, 4194304)


class TestTopicFinderIfPresent(TmpDirMixin, unittest.TestCase):
    def test_scan_all_none_writes_health_and_fails(self):
        tf = ROOT / "skills" / "topic-finder" / "scripts" / "scan_all.py"
        if not tf.exists():
            self.skipTest("topic-finder not installed in this checkout (install.sh fetches it)")
        proc = run(tf, "--sources", "none", "--out-dir", self.tmp, ok=False)
        self.assertEqual(proc.returncode, 1)
        health = json.loads((self.tmp / "health.json").read_text())
        self.assertFalse(any(health["config_present"].values()))
        self.assertFalse(health["web_search_used"])


if __name__ == "__main__":
    unittest.main()
