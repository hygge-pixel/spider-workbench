"""Read-only discovery for collection experiments and verified run evidence."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .registry import load_registry


@dataclass(frozen=True)
class Experiment:
    name: str
    status: str
    collector: str
    task: str | None
    selector: str | None
    latest_verified_run: str | None
    records: int | None
    completeness: str | None
    route: str | None
    backend: str | None
    command: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExperimentView:
    experiments: tuple[Experiment, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class _RunEvidence:
    run: str
    records: int
    completeness: str
    route: str
    backend: str


def _read_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "file is missing"
    except json.JSONDecodeError:
        return None, "invalid JSON"
    except (OSError, UnicodeError):
        return None, "file is unreadable"
    if not isinstance(payload, dict):
        return None, "expected a JSON object"
    return payload, None


def _workspace_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _workspace_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = Path(value.strip())
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _experiment_selector(
    root: Path, directory: Path, warnings: list[str]
) -> str | None:
    path = directory / "capability.json"
    if not path.is_file():
        return None
    payload, error = _read_object(path)
    if error is not None or payload is None:
        warnings.append(f"{directory.name}: capability.json {error}")
        return None
    platform_id = payload.get("platform_id")
    capability_id = payload.get("id")
    if not isinstance(platform_id, str) or not platform_id.strip():
        warnings.append(f"{directory.name}: capability.json platform_id is invalid")
        return None
    if not isinstance(capability_id, str) or not capability_id.strip():
        warnings.append(f"{directory.name}: capability.json id is invalid")
        return None
    return f"{platform_id.strip()}/{capability_id.strip()}"


def _matching_entrypoint(root: Path, payload: dict[str, Any], collector: Path) -> bool:
    entrypoint = _workspace_path(root, payload.get("entrypoint"))
    return entrypoint == collector


def _run_evidence_error(
    run_payload: dict[str, Any],
    current_collector_sha256: str,
    validation: dict[str, Any] | None,
    validation_error: str | None,
    result: dict[str, Any] | None,
    result_error: str | None,
) -> str | None:
    records = run_payload.get("records")
    completeness = run_payload.get("completeness")
    collector_sha256 = run_payload.get("collector_sha256")
    if run_payload.get("status") != "completed":
        return "status is not completed"
    if (
        not isinstance(collector_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", collector_sha256) is None
    ):
        return "collector_sha256 is invalid"
    if collector_sha256 != current_collector_sha256:
        return "collector_sha256 does not match current collector"
    if isinstance(records, bool) or not isinstance(records, int) or records < 0:
        return "records is invalid"
    if not isinstance(completeness, str) or not completeness.strip():
        return "completeness is invalid"
    if validation_error is not None or validation is None:
        return f"validation.json {validation_error}"
    if validation.get("passed") is not True or validation.get("errors") != []:
        return "validation did not pass"
    if result_error is not None or result is None:
        return f"collector_result.json {result_error}"
    route = result.get("route")
    backend = result.get("backend")
    if not isinstance(route, str) or not route.strip():
        return "collector route is invalid"
    if not isinstance(backend, str) or not backend.strip():
        return "collector backend is invalid"
    return None


def _latest_verified_run(
    root: Path, collector: Path, warnings: list[str]
) -> _RunEvidence | None:
    runs_dir = root / "runs"
    if not runs_dir.is_dir():
        return None
    try:
        current_collector_sha256 = hashlib.sha256(collector.read_bytes()).hexdigest()
    except OSError:
        warnings.append(f"{collector.parent.name}: collector is unreadable")
        return None
    run_dirs = sorted(
        (path for path in runs_dir.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    )
    newest_invalid_warning: str | None = None
    for run_dir in run_dirs:
        run_payload, run_error = _read_object(run_dir / "run.json")
        if run_error is not None or run_payload is None:
            continue
        if not _matching_entrypoint(root, run_payload, collector):
            continue
        validation, validation_error = _read_object(run_dir / "validation.json")
        result, result_error = _read_object(run_dir / "collector_result.json")
        evidence_error = _run_evidence_error(
            run_payload,
            current_collector_sha256,
            validation,
            validation_error,
            result,
            result_error,
        )
        if evidence_error is not None:
            if newest_invalid_warning is None:
                newest_invalid_warning = (
                    f"{collector.parent.name}: run {run_dir.name} is not verified: "
                    f"{evidence_error}"
                )
            continue
        assert validation is not None
        assert result is not None
        if newest_invalid_warning is not None:
            warnings.append(newest_invalid_warning)
        return _RunEvidence(
            run=_workspace_relative(root, run_dir),
            records=int(run_payload["records"]),
            completeness=str(run_payload["completeness"]).strip(),
            route=str(result["route"]).strip(),
            backend=str(result["backend"]).strip(),
        )
    if newest_invalid_warning is not None:
        warnings.append(newest_invalid_warning)
    return None


def _preferred_task(directory: Path) -> Path | None:
    for name in ("task.json", "task.example.json"):
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def discover_experiments(root: Path) -> ExperimentView:
    """Derive experiment lifecycle and latest verified evidence without mutation."""

    root = root.resolve()
    registry = load_registry(root)
    registered_selectors = {capability.selector for capability in registry.capabilities}
    warnings = list(registry.warnings)
    experiments: list[Experiment] = []
    experiments_dir = root / "experiments"
    if not experiments_dir.is_dir():
        return ExperimentView(experiments=(), warnings=tuple(warnings))

    directories = sorted(
        (path for path in experiments_dir.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    )
    for directory in directories:
        collector_path = (directory / "collector.py").resolve()
        if not collector_path.is_file():
            continue
        task_path = _preferred_task(directory)
        if task_path is None:
            warnings.append(f"{directory.name}: no task.json or task.example.json")
        selector = _experiment_selector(root, directory, warnings)
        if selector in registered_selectors:
            evidence = None
            status = "registered_source"
        else:
            evidence = _latest_verified_run(root, collector_path, warnings)
            if task_path is None or task_path.name != "task.json":
                status = "example"
            elif evidence is not None:
                status = "verified_unregistered"
            else:
                status = "unverified"

        collector = _workspace_relative(root, collector_path)
        task = (
            _workspace_relative(root, task_path) if task_path is not None else None
        )
        command = None
        if task is not None and status != "registered_source":
            command = f"py -3.11 spider.py run {collector} --task {task}"
        experiments.append(
            Experiment(
                name=directory.name,
                status=status,
                collector=collector,
                task=task,
                selector=selector,
                latest_verified_run=evidence.run if evidence is not None else None,
                records=evidence.records if evidence is not None else None,
                completeness=evidence.completeness if evidence is not None else None,
                route=evidence.route if evidence is not None else None,
                backend=evidence.backend if evidence is not None else None,
                command=command,
            )
        )
    return ExperimentView(experiments=tuple(experiments), warnings=tuple(warnings))
