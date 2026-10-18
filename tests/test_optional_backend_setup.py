from __future__ import annotations

import io
import json
import os
import tempfile
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts import setup_optional_backend
from scripts.setup_optional_backend import (
    build_setup_commands,
    get_runtime_spec,
    run_setup,
    selected_backends,
)


ROOT = Path(__file__).resolve().parents[1]


class OptionalBackendSetupTests(unittest.TestCase):
    def test_lock_files_pin_incompatible_browser_stacks_separately(self) -> None:
        scrapling = (ROOT / "requirements-backends" / "scrapling.lock").read_text(
            encoding="utf-8"
        )
        camoufox = (ROOT / "requirements-backends" / "camoufox.lock").read_text(
            encoding="utf-8"
        )

        self.assertIn("scrapling[fetchers]==0.4.12", scrapling)
        self.assertIn("camoufox==0.5.4", camoufox)
        self.assertIn("playwright==1.60.0", camoufox)
        self.assertNotIn("camoufox", scrapling)
        self.assertNotIn("scrapling", camoufox)

    def test_backend_selection_is_fixed(self) -> None:
        self.assertEqual(selected_backends("scrapling"), ("scrapling",))
        self.assertEqual(selected_backends("camoufox"), ("camoufox",))
        self.assertEqual(selected_backends("all"), ("scrapling", "camoufox"))
        with self.assertRaisesRegex(ValueError, "unsupported"):
            selected_backends("other")

    def test_runtime_specs_are_contained_under_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for backend in ("scrapling", "camoufox"):
                spec = get_runtime_spec(root, backend)
                self.assertEqual(spec.name, backend)
                spec.runtime_dir.relative_to(root / "tmp" / "runtimes")
                spec.lock_file.relative_to(root / "requirements-backends")
            with self.assertRaisesRegex(ValueError, "unsupported"):
                get_runtime_spec(root, "../escape")

    def test_setup_commands_create_venv_install_lock_and_skip_browser_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "requirements-backends" / "scrapling.lock"
            lock.parent.mkdir()
            lock.write_text("scrapling[fetchers]==0.4.12\n", encoding="utf-8")

            commands = build_setup_commands(
                root,
                "scrapling",
                install_browser=False,
                base_python=Path(sys.executable),
            )

        self.assertEqual(commands[0][0], str(Path(sys.executable)))
        self.assertEqual(commands[0][1:3], ["-m", "venv"])
        self.assertEqual(commands[1][1:4], ["-m", "pip", "install"])
        self.assertIn("--disable-pip-version-check", commands[1])
        self.assertEqual(len(commands), 2)
        self.assertNotIn("remove", " ".join(sum(commands, [])))

    def test_existing_runtime_is_reused_and_browser_commands_are_specific(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock_dir = root / "requirements-backends"
            lock_dir.mkdir()
            for backend in ("scrapling", "camoufox"):
                (lock_dir / f"{backend}.lock").write_text("pin\n", encoding="utf-8")
                spec = get_runtime_spec(root, backend)
                spec.python.parent.mkdir(parents=True)
                spec.python.write_text("", encoding="utf-8")

            scrapling = build_setup_commands(root, "scrapling", install_browser=True)
            camoufox = build_setup_commands(root, "camoufox", install_browser=True)

        self.assertNotIn("venv", " ".join(sum(scrapling, [])))
        self.assertEqual(scrapling[-1][-1], "install")
        self.assertEqual(Path(scrapling[-1][0]).name, "scrapling.exe" if os.name == "nt" else "scrapling")
        self.assertEqual(camoufox[-1][-3:], ["-m", "camoufox", "fetch"])

    def test_runtime_executables_have_explicit_windows_and_posix_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            spec = get_runtime_spec(Path(directory), "scrapling")
            for platform, folder, python, cli in (("nt", "Scripts", "python.exe", "scrapling.exe"),
                                                  ("posix", "bin", "python", "scrapling")):
                with self.subTest(platform=platform), mock.patch.object(setup_optional_backend, "os", SimpleNamespace(name=platform)):
                    self.assertEqual(spec.python, spec.runtime_dir / folder / python)
                    self.assertEqual(spec.scrapling_cli, spec.runtime_dir / folder / cli)

    def test_missing_lock_is_rejected_before_any_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "lock"):
                build_setup_commands(
                    Path(directory), "scrapling", install_browser=False
                )

    def test_run_setup_stops_on_failure_and_returns_only_safe_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "requirements-backends" / "scrapling.lock"
            lock.parent.mkdir()
            lock.write_text("pin\n", encoding="utf-8")
            calls: list[list[str]] = []

            def runner(command: list[str], **kwargs: object) -> SimpleNamespace:
                calls.append(command)
                return SimpleNamespace(
                    returncode=0 if len(calls) == 1 else 7,
                    stdout="token-secret",
                    stderr="cookie-secret",
                )

            report = run_setup(
                root,
                "scrapling",
                install_browser=True,
                runner=runner,
            )

        self.assertEqual(len(calls), 2)
        self.assertEqual(
            report,
            {
                "backend": "scrapling",
                "ok": False,
                "failed_step": "package",
                "returncode": 7,
                "browser_requested": True,
                "runtime": "tmp/runtimes/scrapling",
            },
        )
        rendered = json.dumps(report)
        self.assertNotIn("token-secret", rendered)
        self.assertNotIn("cookie-secret", rendered)
        self.assertNotIn(str(root), rendered)

    def test_main_emits_one_json_report(self) -> None:
        stdout = io.StringIO()
        report = {
            "backend": "scrapling",
            "ok": True,
            "browser_requested": False,
            "runtime": "tmp/runtimes/scrapling",
        }
        with (
            mock.patch.object(setup_optional_backend, "run_setup", return_value=report),
            mock.patch.object(setup_optional_backend.sys, "stdout", stdout),
        ):
            code = setup_optional_backend.main(["--backend", "scrapling"])

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue()), {"runtimes": [report]})
        self.assertEqual(len(stdout.getvalue().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
