"""Aggregate drift comparison for two validated standard runs."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from spider_core.registry import RegistryError, find_capability


class RunComparisonError(ValueError):
    """Raised when two standard runs cannot be compared safely."""


def _run_dir(workspace_root: Path, value: Path) -> Path:
    runs_root = (workspace_root / "runs").resolve()
    run_dir = value.resolve()
    if run_dir.parent != runs_root or not run_dir.is_dir():
        raise RunComparisonError("run directory must be an immediate child of workspace runs")
    return run_dir


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunComparisonError(f"invalid comparison evidence: {path.name}") from error
    if not isinstance(value, dict):
        raise RunComparisonError(f"invalid comparison evidence: {path.name}")
    return value


def _rows(path: Path, unique_key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RunComparisonError("invalid comparison evidence: normalized.jsonl") from error
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise RunComparisonError(
                f"normalized.jsonl line {line_number} is invalid"
            ) from error
        if not isinstance(row, dict):
            raise RunComparisonError(
                f"normalized.jsonl line {line_number} is not an object"
            )
        value = row.get(unique_key)
        if value is None or not str(value).strip():
            raise RunComparisonError("normalized.jsonl contains a blank unique key")
        key = str(value)
        if key in result:
            raise RunComparisonError("normalized.jsonl contains a duplicate unique key")
        result[key] = row
    return result


def _collector_identity(workspace_root: Path, entrypoint: Any) -> str:
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        raise RunComparisonError("run entrypoint is invalid")
    path = Path(entrypoint)
    resolved = path.resolve() if path.is_absolute() else (workspace_root / path).resolve()
    try:
        return resolved.relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _proof_linked_selector(
    workspace_root: Path,
    baseline_meta: Mapping[str, Any],
    current_meta: Mapping[str, Any],
) -> str:
    baseline_selector = baseline_meta.get("selector")
    current_selector = current_meta.get("selector")
    registered_meta, unregistered_meta = (
        (baseline_meta, current_meta)
        if isinstance(baseline_selector, str) and baseline_selector
        else (current_meta, baseline_meta)
    )
    selector = registered_meta.get("selector")
    if not isinstance(selector, str) or not selector:
        raise RunComparisonError("runs must use the same selector or proof lineage")
    try:
        capability = find_capability(workspace_root, selector)
    except RegistryError as error:
        raise RunComparisonError(
            "runs must use the same selector or proof lineage"
        ) from error
    if capability.proof_status != "verified" or capability.proof is None:
        raise RunComparisonError("runs must use the same selector or proof lineage")
    proof = _json_object(capability.proof)
    if proof.get("source_run_id") != unregistered_meta.get("run_id"):
        raise RunComparisonError("runs must use the same selector or proof lineage")
    return selector


def compare_runs(
    workspace_root: Path,
    baseline_run: Path,
    current_run: Path,
    *,
    ignore_fields: Iterable[str] = (),
) -> dict[str, Any]:
    """Compare two completed, validated runs without exposing row values."""
    root = workspace_root.resolve()
    baseline_dir = _run_dir(root, baseline_run)
    current_dir = _run_dir(root, current_run)
    baseline_meta = _json_object(baseline_dir / "run.json")
    current_meta = _json_object(current_dir / "run.json")
    baseline_validation = _json_object(baseline_dir / "validation.json")
    current_validation = _json_object(current_dir / "validation.json")

    if baseline_meta.get("status") != "completed" or current_meta.get("status") != "completed":
        raise RunComparisonError("both runs must be completed")
    if baseline_validation.get("passed") is not True or current_validation.get("passed") is not True:
        raise RunComparisonError("both runs must have passed validation")
    baseline_key = baseline_validation.get("unique_key")
    current_key = current_validation.get("unique_key")
    if (
        not isinstance(baseline_key, str)
        or not baseline_key.strip()
        or baseline_key != current_key
    ):
        raise RunComparisonError("runs must use the same nonblank unique key")
    unique_key = baseline_key.strip()

    baseline_selector = baseline_meta.get("selector")
    current_selector = current_meta.get("selector")
    baseline_collector = _collector_identity(root, baseline_meta.get("entrypoint"))
    current_collector = _collector_identity(root, current_meta.get("entrypoint"))
    selector: str | None = None
    collector = baseline_collector
    if baseline_selector is not None or current_selector is not None:
        if (
            isinstance(baseline_selector, str)
            and baseline_selector
            and baseline_selector == current_selector
        ):
            selector = baseline_selector
        elif (baseline_selector is None) != (current_selector is None):
            selector = _proof_linked_selector(root, baseline_meta, current_meta)
            collector = (
                baseline_collector if baseline_selector else current_collector
            )
        else:
            raise RunComparisonError("runs must use the same selector or proof lineage")
    elif baseline_collector != current_collector:
        raise RunComparisonError("runs must use the same collector")

    baseline_rows = _rows(baseline_dir / "normalized.jsonl", unique_key)
    current_rows = _rows(current_dir / "normalized.jsonl", unique_key)
    baseline_ids = set(baseline_rows)
    current_ids = set(current_rows)
    shared_ids = baseline_ids & current_ids
    ignored = {"collected_at"}
    for field in ignore_fields:
        if not isinstance(field, str) or not field.strip():
            raise RunComparisonError("ignored fields must be nonblank strings")
        ignored.add(field.strip())
    fields = sorted(
        set().union(
            *(set(baseline_rows[key]) | set(current_rows[key]) for key in shared_ids)
        )
        - ignored
        - {unique_key}
    )
    changed = {
        field: sum(
            baseline_rows[key].get(field) != current_rows[key].get(field)
            for key in shared_ids
        )
        for field in fields
    }
    return {
        "schema_version": 1,
        "baseline_run_id": baseline_meta.get("run_id"),
        "current_run_id": current_meta.get("run_id"),
        "selector": selector,
        "collector": collector,
        "unique_key": unique_key,
        "baseline_records": len(baseline_rows),
        "current_records": len(current_rows),
        "baseline_unique_ids": len(baseline_ids),
        "current_unique_ids": len(current_ids),
        "shared_unique_ids": len(shared_ids),
        "baseline_only_unique_ids": len(baseline_ids - current_ids),
        "current_only_unique_ids": len(current_ids - baseline_ids),
        "ignored_fields": sorted(ignored),
        "changed_fields_on_shared_ids": changed,
    }


def write_comparison(
    report: Mapping[str, Any], current_run: Path, output_path: Path
) -> None:
    """Write one explicit comparison report without replacing existing evidence."""
    current = current_run.resolve()
    output = output_path.resolve()
    if output.parent != current or output.suffix.lower() != ".json":
        raise RunComparisonError(
            "comparison output must be a new JSON file in current run"
        )
    payload = json.dumps(dict(report), ensure_ascii=False, indent=2) + "\n"
    try:
        with output.open("x", encoding="utf-8", newline="") as stream:
            stream.write(payload)
    except FileExistsError:
        raise RunComparisonError("comparison output already exists") from None
    except OSError as error:
        raise RunComparisonError("comparison output could not be written") from error
