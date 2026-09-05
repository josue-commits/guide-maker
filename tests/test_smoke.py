"""Smoke test for guide-maker v3.

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
GM = ROOT / "skills" / "make-guide" / "scripts"
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
# Every subprocess runs from a scratch cwd outside the repo, so a script that
# resolves .guide-maker/ from the working directory never writes into the
# checkout. The last test class asserts nothing under skills/ changed.
CWD = pathlib.Path(tempfile.mkdtemp(prefix="gm-cwd-"))


def future_iso(days=2):
    import datetime
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(*args, ok=True, cwd=None, env=None):
    proc = subprocess.run([PY, *map(str, args)], capture_output=True, text=True, env=env or ENV, cwd=cwd or CWD)
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

    def test_init_project_writes_skeleton_and_refuses_overwrite(self):
        proj = self.tmp / "proj"
        proc = run(GM / "doctor.py", "--init", "--project", proj, env=env_without_config())
        gm = proj / ".guide-maker"
        self.assertTrue((gm / "config.yaml").is_file(), proc.stdout)
        for name in ("youtube-channels", "subreddits", "x-accounts", "topics"):
            self.assertTrue((gm / "topic-finder" / f"{name}.json").is_file(), name)
        self.assertFalse(list((gm / "topic-finder").glob("*.example.json")))
        self.assertTrue((gm / "formats").is_dir())
        self.assertTrue((gm / "state").is_dir())
        gi = (gm / ".gitignore").read_text()
        self.assertIn("state/", gi)
        self.assertNotIn("config.yaml", gi, "no secret inlined, config.yaml must stay committable")
        # the example is a valid config: the doctor finds it from a nested cwd
        sub = proj / "sub"; sub.mkdir()
        proc = run(GM / "doctor.py", "--print-paths", "--json", cwd=sub, env=env_without_config())
        paths = json.loads(proc.stdout)
        self.assertEqual(paths["config_source"], "project")
        self.assertEqual(pathlib.Path(paths["config_path"]).resolve(), (gm / "config.yaml").resolve())
        self.assertEqual(pathlib.Path(paths["project_dir"]).resolve(), proj.resolve())
        for name in ("make-guide", "topic-finder", "graphics-maker", "dm-automation"):
            self.assertIn(name, paths["siblings"])
            self.assertTrue(paths["siblings"][name], name)
        # second run refuses
        proc = run(GM / "doctor.py", "--init", "--project", proj, env=env_without_config(), ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--force", proc.stdout + proc.stderr)
        run(GM / "doctor.py", "--init", "--project", proj, "--force", env=env_without_config())

    def test_init_from_old_copies_config_state_sources_and_edited_references(self):
        old = self.tmp / "old" / "skills"
        (old / "guide-maker" / "references" / "writing").mkdir(parents=True)
        (old / "graphics-maker").mkdir()
        (old / "topic-finder" / "config").mkdir(parents=True)
        old_cfg = old / "guide-maker" / "config.yaml"
        old_cfg.write_text(CFG.read_text().replace('api_key: ""', 'api_key: "ntn_FAKEKEY12345"', 1))
        (old / "guide-maker" / "references" / "writing" / "voice.md").write_text("# edited voice\n")
        (old / "graphics-maker" / "format-usage-log.jsonl").write_text('{"date": "2026-01-01", "format_slug": "x"}\n')
        (old / "topic-finder" / "config" / "youtube-channels.json").write_text('{"channels": [{"name": "mine"}]}\n')
        (old / "topic-finder" / "config" / "subreddits.example.json").write_text("{}\n")
        proj = self.tmp / "proj"
        proc = run(GM / "doctor.py", "--init", "--project", proj, "--from", old_cfg, env=env_without_config())
        gm = proj / ".guide-maker"
        self.assertIn("ntn_FAKEKEY12345", (gm / "config.yaml").read_text())
        self.assertIn("config.yaml", (gm / ".gitignore").read_text(), "inlined key: config.yaml must be ignored")
        self.assertEqual((gm / "voice.md").read_text(), "# edited voice\n")
        self.assertFalse((gm / "examples.md").exists(), "unedited references are not copied")
        self.assertIn('"x"', (gm / "state" / "format-usage-log.jsonl").read_text())
        self.assertFalse((old / "graphics-maker" / "format-usage-log.jsonl").exists(), "usage log is moved, not copied")
        self.assertIn("mine", (gm / "topic-finder" / "youtube-channels.json").read_text())
        self.assertTrue((gm / "topic-finder" / "subreddits.json").is_file(), "example seeded when no real file")
        self.assertIn(str(old_cfg.resolve()), proc.stdout)

    def test_init_from_v1_migrates(self):
        v1 = self.tmp / "config.yaml"
        v1.write_text('notion_api_key: ""\nguide_database_id: "0123456789abcdef0123456789abcdef"\nauthor_name: "Sam"\n')
        proj = self.tmp / "proj"
        run(GM / "doctor.py", "--init", "--project", proj, "--from", v1, env=env_without_config())
        text = (proj / ".guide-maker" / "config.yaml").read_text()
        self.assertIn("schema_version: 2", text)
        self.assertIn("Sam", text)
        proc = run(GM / "doctor.py", "--offline", "--json", cwd=proj, env=env_without_config())
        report = json.loads(proc.stdout)
        self.assertEqual(report["config"]["author"]["name"], "Sam")
        self.assertFalse(report["config"].get("_v1"))

    def test_print_paths_without_config_reports_none(self):
        proc = run(GM / "doctor.py", "--print-paths", "--json", cwd=self.tmp, env=env_without_config())
        paths = json.loads(proc.stdout)
        self.assertEqual(paths["config_source"], "none")
        self.assertEqual(paths["config_path"], "")

    def test_print_paths_reports_env_and_arg_sources(self):
        proc = run(GM / "doctor.py", "--print-paths", "--json")
        self.assertEqual(json.loads(proc.stdout)["config_source"], "env")
        proc = run(GM / "doctor.py", "--print-paths", "--json", "--config", CFG)
        self.assertEqual(json.loads(proc.stdout)["config_source"], "arg")

    def test_list_databases_offline_skips(self):
        proc = run(GM / "doctor.py", "--list-databases", "--offline", "--config", CFG)
        self.assertIn("SKIP", proc.stdout)
        proc = run(GM / "doctor.py", "--list-databases", "--offline", "--json", "--config", CFG)
        self.assertEqual(json.loads(proc.stdout)["databases"], [])

    def test_gitignore_check_is_about_inline_secrets(self):
        proj = self.tmp / "proj"
        gm = proj / ".guide-maker"; gm.mkdir(parents=True)
        shutil.copy(CFG, gm / "config.yaml")
        proc = run(GM / "doctor.py", "--offline", "--json", cwd=proj, env=env_without_config())
        rows = [r for r in json.loads(proc.stdout)["checks"] if r["name"] == "gitignore"]
        self.assertEqual(rows[0]["level"], "OK", rows)
        self.assertIn("no inline API key", rows[0]["message"])
        # an inlined key inside a git repo that does not ignore the file: WARN
        if shutil.which("git"):
            (gm / "config.yaml").write_text(CFG.read_text().replace('api_key: ""', 'api_key: "ntn_FAKEKEY12345"', 1))
            subprocess.run(["git", "init", "-q", str(proj)], check=True, capture_output=True)
            proc = run(GM / "doctor.py", "--offline", "--json", cwd=proj, env=env_without_config())
            rows = [r for r in json.loads(proc.stdout)["checks"] if r["name"] == "gitignore"]
            self.assertEqual(rows[0]["level"], "WARN", rows)
            (gm / ".gitignore").write_text("config.yaml\n")
            proc = run(GM / "doctor.py", "--offline", "--json", cwd=proj, env=env_without_config())
            rows = [r for r in json.loads(proc.stdout)["checks"] if r["name"] == "gitignore"]
            self.assertEqual(rows[0]["level"], "OK", rows)


def env_without_config():
    """ENV minus GUIDE_MAKER_CONFIG, so the loader's own search order runs."""
    env = dict(ENV)
    env.pop("GUIDE_MAKER_CONFIG", None)
    return env


LOADER_PROBE = (
    "import sys, json; sys.path.insert(0, sys.argv[1]); "
    "from _config import load_config, project_dir, resource, state_path; "
    "c = load_config(); "
    "print(json.dumps({'path': c['_path'], 'source': c['_source'], 'project': str(project_dir(c)), "
    "'voice': str(resource(c, 'voice')), 'examples': str(resource(c, 'examples')), "
    "'state': str(state_path(c, 'closer-log.jsonl'))}))"
)


class TestProjectConfig(TmpDirMixin, unittest.TestCase):
    """The v3 search order: .guide-maker/ found by walking up from cwd, overrides, state."""

    def _project(self):
        proj = self.tmp / "proj"
        (proj / ".guide-maker").mkdir(parents=True)
        shutil.copy(CFG, proj / ".guide-maker" / "config.yaml")
        nested = proj / "a" / "b"
        nested.mkdir(parents=True)
        return proj, nested

    def test_config_found_from_nested_cwd(self):
        proj, nested = self._project()
        proc = run("-c", LOADER_PROBE, GM, cwd=nested, env=env_without_config())
        info = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(pathlib.Path(info["path"]).resolve(), (proj / ".guide-maker" / "config.yaml").resolve())
        self.assertEqual(info["source"], "project")
        self.assertEqual(pathlib.Path(info["project"]).resolve(), proj.resolve())
        self.assertNotIn("deprecat", proc.stderr.lower())

    def test_resource_prefers_project_override(self):
        proj, nested = self._project()
        (proj / ".guide-maker" / "voice.md").write_text("# my voice\n")
        proc = run("-c", LOADER_PROBE, GM, cwd=nested, env=env_without_config())
        info = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(pathlib.Path(info["voice"]).resolve(), (proj / ".guide-maker" / "voice.md").resolve())
        # no examples.md override: the shipped file
        self.assertEqual(pathlib.Path(info["examples"]).resolve(),
                         (ROOT / "skills" / "make-guide" / "references" / "linkedin" / "examples.md").resolve())

    def test_state_path_lives_under_project_state(self):
        proj, nested = self._project()
        proc = run("-c", LOADER_PROBE, GM, cwd=nested, env=env_without_config())
        info = json.loads(proc.stdout.strip().splitlines()[-1])
        state = pathlib.Path(info["state"])
        self.assertEqual(state.resolve(), (proj / ".guide-maker" / "state" / "closer-log.jsonl").resolve())
        self.assertTrue(state.parent.is_dir(), "state/ parent was not created")

    def test_explicit_config_outside_project_still_resolves_project_from_cwd(self):
        proj, nested = self._project()
        # --config points at the fixture, cwd is inside the project: project_dir comes from cwd
        probe = LOADER_PROBE.replace("c = load_config(); ", "c = load_config(sys.argv[2]); ")
        proc = run("-c", probe, GM, CFG, cwd=nested, env=env_without_config())
        info = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(info["source"], "arg")
        self.assertEqual(pathlib.Path(info["project"]).resolve(), proj.resolve())

    def test_legacy_skill_folder_config_loads_with_deprecation_line(self):
        # a copy of the scripts folder acts as an old-style skill with config.yaml inside it
        fake = self.tmp / "fake-skill"
        shutil.copytree(GM, fake / "scripts")
        shutil.copy(CFG, fake / "config.yaml")
        proc = run("-c", LOADER_PROBE, fake / "scripts", cwd=self.tmp, env=env_without_config())
        info = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(info["source"], "legacy")
        self.assertIn("config inside the skill folder is deprecated", proc.stderr)
        self.assertIn("doctor.py --init", proc.stderr)

    def test_no_config_anywhere_fails_with_init_hint(self):
        proc = run("-c", LOADER_PROBE, GM, cwd=self.tmp, env=env_without_config(), ok=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("doctor.py --init", proc.stderr)

    def test_sibling_shims_walk_up_standalone(self):
        # graphics-maker and dm-automation without make-guide next to them: their own
        # fallback loaders must still find <project>/.guide-maker/config.yaml
        proj, nested = self._project()
        for skill, module in (("graphics-maker", "_cfg"), ("dm-automation", "_config_shim")):
            alone = self.tmp / "alone" / "skills" / skill
            shutil.copytree(ROOT / "skills" / skill / "scripts", alone / "scripts")
            probe = (f"import sys, json; sys.path.insert(0, sys.argv[1]); import {module} as m; "
                     "c = m.load_config(); print(json.dumps({'shared': bool(getattr(m, 'USING_SHARED_LOADER', "
                     "getattr(m, 'SHARED_LOADER', None))), 'project': str(m.project_dir(c)), "
                     "'state': str(m.state_path(c, 'format-usage-log.jsonl'))}))")
            proc = run("-c", probe, alone / "scripts", cwd=nested, env=env_without_config())
            info = json.loads(proc.stdout.strip().splitlines()[-1])
            self.assertFalse(info["shared"], skill)
            self.assertEqual(pathlib.Path(info["project"]).resolve(), proj.resolve(), skill)
            self.assertEqual(pathlib.Path(info["state"]).resolve(),
                             (proj / ".guide-maker" / "state" / "format-usage-log.jsonl").resolve(), skill)
            shutil.rmtree(self.tmp / "alone")


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
                              capture_output=True, text=True, env=env, cwd=CWD)
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


class TestRuntimeStateLocations(TmpDirMixin, unittest.TestCase):
    """Run-time writers land in <project>/.guide-maker/, never in a skill folder."""

    def _project(self):
        proj = self.tmp / "proj"
        (proj / ".guide-maker").mkdir(parents=True)
        shutil.copy(CFG, proj / ".guide-maker" / "config.yaml")
        nested = proj / "a"
        nested.mkdir()
        return proj, nested

    def test_usage_log_goes_to_project_state(self):
        proj, nested = self._project()
        proc = run(GX / "graphics_generate.py", "log", "--format", "title-card-pillow", "--keyword", "SAMPLEKW",
                   "--title", "Sample", cwd=nested, env=env_without_config())
        log = proj / ".guide-maker" / "state" / "format-usage-log.jsonl"
        self.assertTrue(log.is_file(), proc.stdout)
        self.assertIn("title-card-pillow", log.read_text())
        proc = run(GX / "graphics_generate.py", "rotation", cwd=nested, env=env_without_config())
        self.assertIn("title-card-pillow", proc.stdout)

    def test_ingest_reference_writes_cards_to_project_formats(self):
        proj, nested = self._project()
        from PIL import Image
        src = self.tmp / "my-layout.png"
        Image.new("RGB", (64, 64), "#333333").save(src)
        proc = run(GX / "ingest_reference.py", src, "--dry-run", cwd=nested, env=env_without_config())
        self.assertIn("would", proc.stdout)
        self.assertFalse((proj / ".guide-maker" / "formats").exists(), "dry run wrote something")
        run(GX / "ingest_reference.py", src, cwd=nested, env=env_without_config())
        lib = proj / ".guide-maker" / "formats"
        self.assertTrue((lib / "my-layout.png").is_file())
        self.assertTrue((lib / "my-layout.md").is_file())
        index = (lib / "INDEX.md").read_text()
        self.assertIn("[my-layout](my-layout.md)", index)
        self.assertIn("<!-- ingest: new rows go above this line -->", index)
        shipped_index = (ROOT / "skills" / "graphics-maker" / "references" / "format-library" / "INDEX.md").read_text()
        self.assertNotIn("my-layout", shipped_index)

    def test_rotation_reads_project_closer_log_by_default(self):
        proj, nested = self._project()
        state = proj / ".guide-maker" / "state"
        state.mkdir()
        (state / "closer-log.jsonl").write_text('{"date": "2026-01-05", "closer": "Free Access"}\n')
        run(GM / "lint_copy.py", "rotation", cwd=nested, env=env_without_config())
        (state / "closer-log.jsonl").write_text('{"date": "2026-01-05", "closer": "Free Access"}\n'
                                                '{"date": "2026-01-07", "closer": "Free Access"}\n')
        proc = run(GM / "lint_copy.py", "rotation", cwd=nested, env=env_without_config(), ok=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("closer-repeat-week", proc.stdout + proc.stderr)

    def test_doctor_reports_which_reference_is_in_use(self):
        proj, nested = self._project()
        (proj / ".guide-maker" / "voice.md").write_text("# mine\n")
        proc = run(GM / "doctor.py", "--offline", "--json", cwd=nested, env=env_without_config())
        rows = [r for r in json.loads(proc.stdout)["checks"] if r["name"] == "resources"]
        self.assertTrue(any("voice: project override" in r["message"] for r in rows), rows)
        self.assertTrue(any("examples: shipped" in r["message"] for r in rows), rows)


class TestTopicFinder(TmpDirMixin, unittest.TestCase):
    def test_scan_all_none_writes_health_and_fails(self):
        # topic-finder is a git subtree under skills/, so it is always present
        tf = ROOT / "skills" / "topic-finder" / "scripts" / "scan_all.py"
        self.assertTrue(tf.exists(), f"{tf} missing: the topic-finder subtree is gone")
        proc = run(tf, "--sources", "none", "--out-dir", self.tmp, ok=False)
        self.assertEqual(proc.returncode, 1)
        health = json.loads((self.tmp / "health.json").read_text())
        self.assertFalse(any(health["config_present"].values()))
        self.assertFalse(health["web_search_used"])


class TestZNothingWrittenUnderSkills(unittest.TestCase):
    """Runs last (unittest loads classes in name order): after every test above,
    the checkout under skills/ must be exactly what git tracks. A script that
    writes into a skill folder at run time is a bug (skills are replaced on
    update). __pycache__ is gitignored and does not count."""

    def test_git_status_under_skills_is_empty(self):
        if not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        proc = subprocess.run(["git", "status", "--porcelain", "--", "skills/"],
                              capture_output=True, text=True, cwd=ROOT)
        if proc.returncode != 0:
            self.skipTest(f"git unavailable: {proc.stderr.strip()}")
        # Only run-time artefacts count. An uncommitted source edit (a developer
        # running the suite mid-change) is a modified tracked file, which is
        # allowed; anything untracked or any *.jsonl / format card is not.
        offenders = []
        for line in proc.stdout.splitlines():
            status, path = line[:2], line[3:]
            if status.strip() in ("??", "A") or path.endswith((".jsonl", ".png")) or "/formats/" in path:
                offenders.append(line)
            elif path.endswith(("config.yaml", "config.json")):
                offenders.append(line)
        self.assertEqual(offenders, [], "run-time writes under skills/:\n" + proc.stdout)


if __name__ == "__main__":
    unittest.main()
