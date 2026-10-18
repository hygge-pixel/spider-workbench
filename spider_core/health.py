"""Read-only health reporting for collection resources."""

from __future__ import annotations

import importlib.util
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .browser import (
    WorkspaceBrowserError,
    load_workspace_browser_configs,
    status_browser_candidate,
)
from .optional_backends import inspect_optional_backend


PACKAGE_MODULES = {
    "requests": "requests",
    "httpx": "httpx",
    "crawl4ai": "crawl4ai",
    "playwright": "playwright",
    "DrissionPage": "DrissionPage",
}

COLLECTION_SKILLS = (
    "web-collection-router",
    "web-reverse-workflow",
    "web-reverse-master",
    "web-reverse-field-guide",
    "web-reverse-brainstorming",
    "web-reverse-writing-plans",
    "web-reverse-executing-plans",
    "web-reverse-test-driven-development",
    "web-reverse-systematic-debugging",
    "param-encryptor",
    "env-patcher",
    "ast-deobfuscation",
    "captcha-solver",
    "playwright-cli",
    "wechat-miniapp-collector",
    "android-reverse-engineering",
    "native-reverse-master",
)

FindSpec = Callable[[str], object | None]
BrowserStatus = Callable[[Path, str], dict[str, Any]]
OptionalInspector = Callable[[Path, str], dict[str, Any]]


def _package_health(find_spec: FindSpec) -> dict[str, dict[str, bool]]:
    result: dict[str, dict[str, bool]] = {}
    for label, module in PACKAGE_MODULES.items():
        try:
            available = find_spec(module) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            available = False
        result[label] = {"available": available}
    return result


def _skill_health(
    workspace: Path, skill_names: Sequence[str]
) -> dict[str, dict[str, bool]]:
    return {
        name: {
            "canonical": (workspace / "skills" / name / "SKILL.md").is_file(),
            "discoverable": (
                workspace / ".agents" / "skills" / name / "SKILL.md"
            ).is_file(),
        }
        for name in skill_names
    }


def collection_health(
    workspace: Path,
    *,
    find_spec: FindSpec = importlib.util.find_spec,
    browser_status: BrowserStatus = status_browser_candidate,
    skill_names: Sequence[str] = COLLECTION_SKILLS,
    optional_inspector: OptionalInspector = inspect_optional_backend,
) -> dict[str, Any]:
    """Inspect packages, Skill discovery and browsers without starting anything."""
    root = Path(workspace).resolve()
    browser_candidates: dict[str, dict[str, Any]] = {}
    for candidate in ("chrome", "cloak"):
        try:
            browser_candidates[candidate] = browser_status(root, candidate)
        except WorkspaceBrowserError as error:
            browser_candidates[candidate] = {
                "status": "unavailable",
                "error": error.code,
            }
    try:
        default_candidate = load_workspace_browser_configs(root).default_candidate
        default_browser = browser_candidates[default_candidate]
    except WorkspaceBrowserError as error:
        default_candidate = None
        default_browser = {"status": "unavailable", "error": error.code}
    return {
        "packages": _package_health(find_spec),
        "optional_backends": {
            backend: optional_inspector(root, backend)
            for backend in ("scrapling", "camoufox")
        },
        "skills": _skill_health(root, skill_names),
        "browser": default_browser,
        "default_browser_candidate": default_candidate,
        "available_browser_candidates": [
            name for name, result in browser_candidates.items()
            if result.get("status") == "ready"
        ],
        "browser_candidates": browser_candidates,
    }
