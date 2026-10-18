from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from spider_core.browser import WorkspaceBrowserError
from spider_core.health import COLLECTION_SKILLS, collection_health


def write_browser_pool(root: Path, default: str = "chrome") -> None:
    path = root / "config" / "workspace_browser.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "schema_version": 2, "default_candidate": default,
        "candidates": {name: {
            "executable": str(root / name / "chrome.exe"),
            "user_data_dir": str(root / "tmp" / name),
            "cdp_url": f"http://127.0.0.1:{port}",
            "startup_timeout_seconds": 10, "launch_args": [], "environment": {},
        } for name, port in (("chrome", 9222), ("cloak", 9232))},
    }), encoding="utf-8")


class CollectionHealthTests(unittest.TestCase):
    def test_configured_cloak_is_ready_when_chrome_is_offline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_browser_pool(root, "cloak")
            before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))

            def status(workspace: Path, candidate: str):
                if candidate == "chrome":
                    raise WorkspaceBrowserError("browser_unavailable")
                return {"status": "ready", "candidate": candidate}

            health = collection_health(root, find_spec=lambda _: None,
                                       browser_status=status, skill_names=(),
                                       optional_inspector=lambda *_: {})
            self.assertEqual(health["browser"], {"status": "ready", "candidate": "cloak"})
            self.assertEqual(health["default_browser_candidate"], "cloak")
            self.assertEqual(health["available_browser_candidates"], ["cloak"])
            self.assertEqual(before, sorted(str(p.relative_to(root)) for p in root.rglob("*")))

    def test_available_alternative_does_not_hide_default_browser_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_browser_pool(root, "cloak")
            health = collection_health(
                root, find_spec=lambda _: None, skill_names=(), optional_inspector=lambda *_: {},
                browser_status=lambda _, name: {"status": "ready" if name == "chrome" else "unavailable"},
            )
            self.assertEqual(health["browser"]["status"], "unavailable")
            self.assertEqual(health["available_browser_candidates"], ["chrome"])

    def test_invalid_default_is_reported_without_choosing_a_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_browser_pool(root, "unknown")
            health = collection_health(root, find_spec=lambda _: None, skill_names=(),
                                       browser_status=lambda *_: {"status": "ready"},
                                       optional_inspector=lambda *_: {})
            self.assertEqual(health["browser"], {"status": "unavailable", "error": "browser_config_invalid"})
            self.assertIsNone(health["default_browser_candidate"])

    def test_default_health_excludes_removed_miniapp_skill(self) -> None:
        self.assertNotIn("wechat-miniapp-collector", COLLECTION_SKILLS)

    def test_default_health_reports_playwright_cli_skill(self) -> None:
        self.assertIn("playwright-cli", COLLECTION_SKILLS)

    def test_default_health_excludes_removed_android_reverse_skill(self) -> None:
        self.assertNotIn("android-reverse-engineering", COLLECTION_SKILLS)

    def test_default_health_excludes_removed_native_and_captcha_skills(self) -> None:
        self.assertNotIn("native-reverse-master", COLLECTION_SKILLS)
        self.assertNotIn("captcha-solver", COLLECTION_SKILLS)

    def test_reports_packages_skills_and_ready_browser_without_starting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_browser_pool(root)
            canonical = root / "skills" / "web-collection-router"
            discovery = root / ".agents" / "skills" / "web-collection-router"
            canonical.mkdir(parents=True)
            discovery.mkdir(parents=True)
            (canonical / "SKILL.md").write_text("skill", encoding="utf-8")
            (discovery / "SKILL.md").write_text("skill", encoding="utf-8")
            looked_up: list[str] = []
            browser_calls: list[tuple[Path, str]] = []

            def find_spec(name: str):
                looked_up.append(name)
                return object() if name in {"requests", "playwright"} else None

            health = collection_health(
                root,
                find_spec=find_spec,
                browser_status=lambda workspace, candidate: browser_calls.append(
                    (workspace, candidate)
                )
                or {
                    "status": "ready",
                    "candidate": candidate,
                    "action": "available",
                    "cdp_url": f"http://127.0.0.1:{9222 if candidate == 'chrome' else 9232}",
                    "browser": "Chrome/151.0.7922.137",
                    "protocol_version": "1.3",
                    "page_targets": 1,
                },
                skill_names=("web-collection-router", "web-reverse-workflow"),
                optional_inspector=lambda workspace, backend: {
                    "status": "browser_ready" if backend == "scrapling" else "unavailable",
                    "package_version": "0.4.12" if backend == "scrapling" else None,
                    "browser_ready": backend == "scrapling",
                    "remediation": "",
                },
            )

        self.assertTrue(health["packages"]["requests"]["available"])
        self.assertTrue(health["packages"]["playwright"]["available"])
        self.assertNotIn("camoufox", health["packages"])
        self.assertIn("DrissionPage", looked_up)
        self.assertEqual(
            browser_calls,
            [(root.resolve(), "chrome"), (root.resolve(), "cloak")],
        )
        self.assertEqual(health["browser"]["status"], "ready")
        self.assertEqual(set(health["browser_candidates"]), {"chrome", "cloak"})
        self.assertEqual(health["browser"], health["browser_candidates"]["chrome"])
        self.assertEqual(
            health["skills"]["web-collection-router"],
            {"canonical": True, "discoverable": True},
        )
        self.assertEqual(
            health["skills"]["web-reverse-workflow"],
            {"canonical": False, "discoverable": False},
        )
        self.assertEqual(
            health["optional_backends"]["scrapling"]["status"],
            "browser_ready",
        )
        self.assertEqual(
            health["optional_backends"]["camoufox"]["status"],
            "unavailable",
        )

    def test_browser_error_becomes_read_only_health_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_browser_pool(root)

            def unavailable(_: Path, candidate: str):
                if candidate == "chrome":
                    raise WorkspaceBrowserError("browser_unavailable")
                raise WorkspaceBrowserError("browser_executable_missing")

            health = collection_health(
                root,
                find_spec=lambda _: None,
                browser_status=unavailable,
                skill_names=(),
                optional_inspector=lambda workspace, backend: {
                    "status": "unavailable",
                    "package_version": None,
                    "browser_ready": False,
                    "remediation": "setup",
                },
            )

        self.assertEqual(
            health["browser"],
            {"status": "unavailable", "error": "browser_unavailable"},
        )
        self.assertEqual(
            health["browser_candidates"]["cloak"],
            {"status": "unavailable", "error": "browser_executable_missing"},
        )


if __name__ == "__main__":
    unittest.main()
