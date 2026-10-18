"""Install optional collection backends into workspace-local environments."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
Runner = Callable[..., Any]
_BACKENDS = frozenset({"scrapling", "camoufox"})


@dataclass(frozen=True)
class RuntimeSpec:
    name: str
    runtime_dir: Path
    lock_file: Path

    @property
    def python(self) -> Path:
        if os.name == "nt":
            return self.runtime_dir / "Scripts" / "python.exe"
        return self.runtime_dir / "bin" / "python"

    @property
    def scrapling_cli(self) -> Path:
        if os.name == "nt":
            return self.runtime_dir / "Scripts" / "scrapling.exe"
        return self.runtime_dir / "bin" / "scrapling"


def selected_backends(value: str) -> tuple[str, ...]:
    if value == "all":
        return ("scrapling", "camoufox")
    if value in _BACKENDS:
        return (value,)
    raise ValueError("unsupported optional backend")


def get_runtime_spec(workspace_root: Path, backend: str) -> RuntimeSpec:
    if backend not in _BACKENDS:
        raise ValueError("unsupported optional backend")
    root = workspace_root.resolve()
    runtime_dir = (root / "tmp" / "runtimes" / backend).resolve()
    lock_file = (root / "requirements-backends" / f"{backend}.lock").resolve()
    runtime_dir.relative_to(root / "tmp" / "runtimes")
    lock_file.relative_to(root / "requirements-backends")
    return RuntimeSpec(backend, runtime_dir, lock_file)


def build_setup_commands(
    workspace_root: Path,
    backend: str,
    *,
    install_browser: bool,
    base_python: Path | None = None,
) -> list[list[str]]:
    spec = get_runtime_spec(workspace_root, backend)
    if not spec.lock_file.is_file():
        raise FileNotFoundError(f"missing optional backend lock: {spec.lock_file.name}")
    commands: list[list[str]] = []
    if not spec.python.is_file():
        commands.append(
            [
                str(base_python or Path(sys.executable)),
                "-m",
                "venv",
                str(spec.runtime_dir),
            ]
        )
    commands.append(
        [
            str(spec.python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            str(spec.lock_file),
        ]
    )
    if install_browser:
        if backend == "scrapling":
            commands.append([str(spec.scrapling_cli), "install"])
        else:
            commands.append([str(spec.python), "-m", "camoufox", "fetch"])
    return commands


def _command_step(command: list[str]) -> str:
    if command[1:3] == ["-m", "venv"]:
        return "environment"
    if len(command) >= 4 and command[1:4] == ["-m", "pip", "install"]:
        return "package"
    return "browser"


def run_setup(
    workspace_root: Path,
    backend: str,
    *,
    install_browser: bool,
    runner: Runner = subprocess.run,
) -> dict[str, object]:
    root = workspace_root.resolve()
    spec = get_runtime_spec(root, backend)
    commands = build_setup_commands(
        root,
        backend,
        install_browser=install_browser,
    )
    runtime_name = spec.runtime_dir.relative_to(root).as_posix()
    for command in commands:
        try:
            completed = runner(
                command,
                cwd=str(root),
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            )
            returncode = int(completed.returncode)
        except OSError:
            returncode = 1
        if returncode != 0:
            return {
                "backend": backend,
                "ok": False,
                "failed_step": _command_step(command),
                "returncode": returncode,
                "browser_requested": install_browser,
                "runtime": runtime_name,
            }
    return {
        "backend": backend,
        "ok": True,
        "browser_requested": install_browser,
        "runtime": runtime_name,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install isolated Scrapling or Camoufox runtimes."
    )
    parser.add_argument(
        "--backend",
        choices=("scrapling", "camoufox", "all"),
        required=True,
    )
    parser.add_argument(
        "--install-browser",
        action="store_true",
        help="Also download the selected backend's browser resources.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reports: list[dict[str, object]] = []
    for backend in selected_backends(args.backend):
        report = run_setup(
            ROOT,
            backend,
            install_browser=args.install_browser,
        )
        reports.append(report)
        if not report["ok"]:
            print(json.dumps({"runtimes": reports}, ensure_ascii=False))
            return 1
    print(json.dumps({"runtimes": reports}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
