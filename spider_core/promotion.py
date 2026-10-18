"""Promote a proven experiment into the reusable capability registry."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .registry import RegistryError, find_capability, load_registry, write_registry
from .runner import SECRET_FRAGMENTS


IDENTIFIER = re.compile(r"^[a-z0-9_]+$")


class PromotionError(ValueError):
    """Raised when an experiment has not earned registration."""


@dataclass(frozen=True)
class PromotionOutcome:
    selector: str
    target_dir: Path


@dataclass(frozen=True)
class ProofRefreshOutcome:
    selector: str
    proof_path: Path
    source_run_id: str
    proof_status: str


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PromotionError(f"{label} is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise PromotionError(f"{label} is not valid JSON: {error.msg}") from error
    if not isinstance(payload, dict):
        raise PromotionError(f"{label} must contain a JSON object")
    return payload


def _inside(path: Path, parent: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(parent.resolve())
    except ValueError as error:
        raise PromotionError(f"{label} must stay inside {parent.name}") from error
    return resolved


def _identifier(metadata: dict[str, Any], field: str) -> str:
    value = metadata.get(field)
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise PromotionError(f"{field} must match [a-z0-9_]+")
    return value


def _text(metadata: dict[str, Any], field: str) -> str:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PromotionError(f"{field} must be a non-empty string")
    return value.strip()


def _metadata(path: Path) -> dict[str, Any]:
    payload = _load_object(path, "capability metadata")
    secret_key = _find_secret_key(payload)
    if secret_key:
        raise PromotionError(
            f"capability metadata contains a secret-like key: {secret_key}"
        )
    platform_id = _identifier(payload, "platform_id")
    platform_name = _text(payload, "platform_name")
    capability_id = _identifier(payload, "id")
    name = _text(payload, "name")
    route = _text(payload, "route")
    requires_auth = payload.get("requires_auth")
    if not isinstance(requires_auth, bool):
        raise PromotionError("requires_auth must be boolean")
    unique_key = payload.get("unique_key")
    if unique_key is not None and (
        not isinstance(unique_key, str) or not unique_key.strip()
    ):
        raise PromotionError("unique_key must be null or a non-empty string")
    required_fields = payload.get("required_fields", [])
    if not isinstance(required_fields, list) or not all(
        isinstance(field, str) and field.strip() for field in required_fields
    ):
        raise PromotionError("required_fields must be a list of non-empty strings")
    verification_ttl_days = payload.get("verification_ttl_days", 30)
    if (
        not isinstance(verification_ttl_days, int)
        or isinstance(verification_ttl_days, bool)
        or not 1 <= verification_ttl_days <= 3650
    ):
        raise PromotionError(
            "verification_ttl_days must be an integer from 1 to 3650"
        )
    return {
        "platform_id": platform_id,
        "platform_name": platform_name,
        "id": capability_id,
        "name": name,
        "route": route,
        "requires_auth": requires_auth,
        "unique_key": unique_key.strip() if isinstance(unique_key, str) else None,
        "required_fields": [field.strip() for field in required_fields],
        "verification_ttl_days": verification_ttl_days,
    }


def _find_secret_key(value: Any, prefix: str = "") -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            current = f"{prefix}.{key_text}" if prefix else key_text
            if any(fragment in key_text.lower() for fragment in SECRET_FRAGMENTS):
                return current
            found = _find_secret_key(item, current)
            if found:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _find_secret_key(item, f"{prefix}[{index}]")
            if found:
                return found
    return None


def _validate_proof(
    proof_run: Path,
    collector: Path,
    metadata: dict[str, Any],
    *,
    expected_selector: str | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    run = _load_object(proof_run / "run.json", "proof run")
    validation = _load_object(proof_run / "validation.json", "proof validation")
    collector_result = _load_object(
        proof_run / "collector_result.json", "proof collector result"
    )
    if run.get("status") != "completed":
        raise PromotionError("proof run must be completed")
    if run.get("selector") != expected_selector:
        raise PromotionError("proof run selector does not match the expected selector")
    if validation.get("passed") is not True:
        raise PromotionError("proof run validation must have passed")
    entrypoint = run.get("entrypoint")
    if not isinstance(entrypoint, str) or Path(entrypoint).resolve() != collector.resolve():
        raise PromotionError("proof run belongs to a different collector")
    collector_sha256 = run.get("collector_sha256")
    current_sha256 = hashlib.sha256(collector.read_bytes()).hexdigest()
    if (
        not isinstance(collector_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", collector_sha256) is None
        or collector_sha256 != current_sha256
    ):
        raise PromotionError("proof run collector_sha256 does not match the collector")
    if validation.get("unique_key") != metadata["unique_key"]:
        raise PromotionError("proof validation unique_key does not match capability metadata")
    if validation.get("required_fields") != metadata["required_fields"]:
        raise PromotionError("proof validation required_fields do not match capability metadata")
    return run, validation, collector_result


def _proof_snapshot(
    selector: str,
    collector: Path,
    run: dict[str, Any],
    validation: dict[str, Any],
    collector_result: dict[str, Any],
) -> dict[str, Any]:
    run_id = _text(run, "run_id")
    verified_at = _text(run, "completed_at")
    completeness = _text(run, "completeness")
    records = run.get("records")
    if isinstance(records, bool) or not isinstance(records, int) or records <= 0:
        raise PromotionError("proof run records must be a positive integer")
    errors = validation.get("errors")
    if not isinstance(errors, list):
        raise PromotionError("proof validation errors must be a list")
    if errors:
        raise PromotionError("proof validation errors must be empty")
    route = _text(collector_result, "route")
    backend = _text(collector_result, "backend")
    source_exhausted = collector_result.get("source_exhausted")
    if not isinstance(source_exhausted, bool):
        raise PromotionError("proof collector result source_exhausted must be boolean")
    snapshot = {
        "schema_version": 1,
        "selector": selector,
        "source_run_id": run_id,
        "verified_at": verified_at,
        "status": "completed",
        "completeness": completeness,
        "records": records,
        "collector_sha256": run["collector_sha256"],
        "validation": {
            "passed": True,
            "unique_key": validation.get("unique_key"),
            "required_fields": validation.get("required_fields"),
            "errors_count": len(errors),
        },
        "observed": {
            "route": route,
            "backend": backend,
            "source_exhausted": source_exhausted,
        },
    }
    secret_key = _find_secret_key(snapshot)
    if secret_key:
        raise PromotionError(f"proof snapshot contains a secret-like key: {secret_key}")
    return snapshot


def promote_experiment(
    root: Path, experiment_dir: Path, proof_run: Path
) -> PromotionOutcome:
    root = root.resolve()
    experiment_dir = _inside(experiment_dir, root / "experiments", "experiment")
    proof_run = _inside(proof_run, root / "runs", "proof run")
    if not experiment_dir.is_dir():
        raise PromotionError(f"experiment directory is missing: {experiment_dir}")
    if not proof_run.is_dir():
        raise PromotionError(f"proof run directory is missing: {proof_run}")
    collector = experiment_dir / "collector.py"
    if not collector.is_file():
        raise PromotionError(f"collector is missing: {collector}")
    metadata = _metadata(experiment_dir / "capability.json")
    example_task = experiment_dir / "task.example.json"
    if example_task.is_file():
        task_payload = _load_object(example_task, "example task")
        secret_key = _find_secret_key(task_payload)
        if secret_key:
            raise PromotionError(f"example task contains a secret-like key: {secret_key}")
    run, validation, collector_result = _validate_proof(
        proof_run, collector, metadata, expected_selector=None
    )
    try:
        view = load_registry(root)
    except RegistryError as error:
        raise PromotionError(str(error)) from error
    selector = f"{metadata['platform_id']}/{metadata['id']}"
    if any(capability.selector == selector for capability in view.capabilities):
        raise PromotionError(f"capability is already registered: {selector}")
    target_dir = root / "platforms" / metadata["platform_id"] / metadata["id"]
    if target_dir.exists():
        raise PromotionError(f"target directory already exists: {target_dir}")
    document = json.loads(json.dumps(view.document))
    platform = next(
        (
            item
            for item in document["platforms"]
            if isinstance(item, dict) and item.get("id") == metadata["platform_id"]
        ),
        None,
    )
    if platform is None:
        platform = {
            "id": metadata["platform_id"],
            "name": metadata["platform_name"],
            "capabilities": [],
        }
        document["platforms"].append(platform)
    elif platform.get("name") != metadata["platform_name"]:
        raise PromotionError("platform_name does not match the registered platform")
    entrypoint_text = (
        Path("platforms")
        / metadata["platform_id"]
        / metadata["id"]
        / "collector.py"
    ).as_posix()
    proof_text = (
        Path("platforms")
        / metadata["platform_id"]
        / metadata["id"]
        / "proof.json"
    ).as_posix()
    platform["capabilities"].append(
        {
            "id": metadata["id"],
            "name": metadata["name"],
            "entrypoint": entrypoint_text,
            "route": metadata["route"],
            "requires_auth": metadata["requires_auth"],
            "unique_key": metadata["unique_key"],
            "required_fields": metadata["required_fields"],
            "verification_ttl_days": metadata["verification_ttl_days"],
            "proof": proof_text,
        }
    )
    platform_dir = target_dir.parent
    platform_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{metadata['id']}-", dir=platform_dir))
    installed = False
    try:
        shutil.copy2(collector, staging / "collector.py")
        (staging / "capability.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if example_task.is_file():
            shutil.copy2(example_task, staging / "task.example.json")
        snapshot = _proof_snapshot(
            selector,
            staging / "collector.py",
            run,
            validation,
            collector_result,
        )
        (staging / "proof.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, target_dir)
        installed = True
        write_registry(root, document)
    except Exception:
        if installed and target_dir.exists():
            shutil.rmtree(target_dir)
        elif staging.exists():
            shutil.rmtree(staging)
        if platform_dir.exists() and not any(platform_dir.iterdir()):
            platform_dir.rmdir()
        raise
    return PromotionOutcome(selector, target_dir)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def refresh_capability_proof(
    root: Path, selector: str, proof_run: Path
) -> ProofRefreshOutcome:
    root = root.resolve()
    proof_run = _inside(proof_run, root / "runs", "proof run")
    if not proof_run.is_dir():
        raise PromotionError(f"proof run directory is missing: {proof_run}")
    try:
        capability = find_capability(root, selector)
    except RegistryError as error:
        raise PromotionError(str(error)) from error
    if capability.proof is None:
        raise PromotionError(f"capability has no configured portable proof: {selector}")
    metadata = {
        "unique_key": capability.unique_key,
        "required_fields": list(capability.required_fields),
    }
    run, validation, collector_result = _validate_proof(
        proof_run,
        capability.entrypoint,
        metadata,
        expected_selector=selector,
    )
    snapshot = _proof_snapshot(
        selector,
        capability.entrypoint,
        run,
        validation,
        collector_result,
    )
    try:
        verified_at = datetime.fromisoformat(
            str(snapshot["verified_at"]).replace("Z", "+00:00")
        )
    except ValueError as error:
        raise PromotionError("proof run completed_at is invalid") from error
    if verified_at.tzinfo is None:
        raise PromotionError("proof run completed_at is invalid")
    verified_at = verified_at.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if (
        verified_at > now
        or now > verified_at + timedelta(days=capability.verification_ttl_days)
    ):
        raise PromotionError("proof run is outside the verification TTL")
    proof_path = capability.proof.resolve()
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(proof_path, snapshot)
    try:
        refreshed = find_capability(root, selector)
    except RegistryError as error:
        raise PromotionError(str(error)) from error
    if refreshed.proof_status != "verified":
        raise PromotionError(
            f"refreshed proof is not verified: {refreshed.proof_status}"
        )
    return ProofRefreshOutcome(
        selector=selector,
        proof_path=proof_path,
        source_run_id=str(snapshot["source_run_id"]),
        proof_status=refreshed.proof_status,
    )
