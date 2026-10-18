"""Tolerant discovery for proven collection capabilities."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class RegistryError(ValueError):
    """Raised when the registry as a whole or a requested selector is unusable."""


@dataclass(frozen=True)
class Capability:
    platform_id: str
    platform_name: str
    id: str
    name: str
    entrypoint: Path
    entrypoint_text: str
    route: str
    requires_auth: bool
    unique_key: str | None
    required_fields: tuple[str, ...]
    verification_ttl_days: int
    proof: Path | None
    proof_text: str | None
    proof_status: str
    proof_run: Path | None
    proof_run_text: str | None
    available: bool

    @property
    def selector(self) -> str:
        return f"{self.platform_id}/{self.id}"


@dataclass(frozen=True)
class RegistryView:
    capabilities: tuple[Capability, ...]
    warnings: tuple[str, ...]
    document: dict[str, Any]


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"{key} must be a non-empty string")
    return value.strip()


def _path_within(root: Path, value: str, field: str) -> Path:
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise RegistryError(f"{field} must stay inside the workspace") from error
    return candidate


def _read_document(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RegistryError(f"registry is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise RegistryError(f"registry is not valid JSON: {error.msg}") from error
    if not isinstance(payload, dict):
        raise RegistryError("registry must be a top-level JSON object")
    if payload.get("schema_version") != 1:
        raise RegistryError("registry schema_version must be 1")
    if not isinstance(payload.get("platforms"), list):
        raise RegistryError("registry platforms must be a list")
    return payload


def _portable_proof_status(
    proof: Path,
    *,
    selector: str,
    entrypoint: Path,
    unique_key: str | None,
    required_fields: tuple[str, ...],
    verification_ttl_days: int,
    now: datetime,
) -> tuple[str, str | None]:
    if not proof.is_file():
        return "missing", f"{selector}: proof is missing"
    try:
        payload = json.loads(proof.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "stale", f"{selector}: proof is invalid JSON"
    if not isinstance(payload, dict):
        return "stale", f"{selector}: proof is invalid: expected object"
    allowed_top_level = {
        "schema_version",
        "selector",
        "source_run_id",
        "verified_at",
        "status",
        "completeness",
        "records",
        "collector_sha256",
        "validation",
        "observed",
    }
    allowed_validation = {
        "passed",
        "unique_key",
        "required_fields",
        "errors_count",
    }
    allowed_observed = {"route", "backend", "source_exhausted"}
    validation = payload.get("validation")
    observed = payload.get("observed")
    if (
        set(payload) != allowed_top_level
        or not isinstance(validation, dict)
        or set(validation) != allowed_validation
        or not isinstance(observed, dict)
        or set(observed) != allowed_observed
    ):
        return "stale", f"{selector}: proof is invalid: unsafe schema"
    records = payload.get("records")
    if (
        payload.get("schema_version") != 1
        or payload.get("selector") != selector
        or not isinstance(payload.get("source_run_id"), str)
        or not payload["source_run_id"].strip()
        or not isinstance(payload.get("verified_at"), str)
        or not payload["verified_at"].strip()
        or payload.get("status") != "completed"
        or not isinstance(payload.get("completeness"), str)
        or not payload["completeness"].strip()
        or isinstance(records, bool)
        or not isinstance(records, int)
        or records < 0
        or validation.get("passed") is not True
        or validation.get("unique_key") != unique_key
        or validation.get("required_fields") != list(required_fields)
        or validation.get("errors_count") != 0
        or not isinstance(observed.get("route"), str)
        or not observed["route"].strip()
        or not isinstance(observed.get("backend"), str)
        or not observed["backend"].strip()
        or not isinstance(observed.get("source_exhausted"), bool)
    ):
        return "stale", f"{selector}: proof is invalid: contract mismatch"
    try:
        verified_at = datetime.fromisoformat(payload["verified_at"].replace("Z", "+00:00"))
    except ValueError:
        return "stale", f"{selector}: proof is invalid: verified_at"
    if verified_at.tzinfo is None:
        return "stale", f"{selector}: proof is invalid: verified_at"
    verified_at = verified_at.astimezone(timezone.utc)
    if verified_at > now:
        return "stale", f"{selector}: proof is invalid: verified_at is in the future"
    if now > verified_at + timedelta(days=verification_ttl_days):
        return "stale", f"{selector}: proof has expired"
    expected_hash = payload.get("collector_sha256")
    if (
        not isinstance(expected_hash, str)
        or len(expected_hash) != 64
        or any(character not in "0123456789abcdef" for character in expected_hash)
    ):
        return "stale", f"{selector}: proof is invalid: collector hash"
    if not entrypoint.is_file():
        return "stale", f"{selector}: proof collector hash cannot be checked"
    actual_hash = hashlib.sha256(entrypoint.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        return "stale", f"{selector}: proof collector hash does not match entrypoint"
    return "verified", None


def load_registry(root: Path, *, now: datetime | None = None) -> RegistryView:
    root = root.resolve()
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        raise RegistryError("now must be timezone-aware")
    else:
        now = now.astimezone(timezone.utc)
    document = _read_document(root / "platforms" / "registry.json")
    capabilities: list[Capability] = []
    warnings: list[str] = []
    for platform_index, raw_platform in enumerate(document["platforms"], start=1):
        label = f"platform {platform_index}"
        if not isinstance(raw_platform, dict):
            warnings.append(f"{label}: entry must be an object")
            continue
        try:
            platform_id = _required_text(raw_platform, "id")
            platform_name = _required_text(raw_platform, "name")
            raw_capabilities = raw_platform.get("capabilities")
            if not isinstance(raw_capabilities, list):
                raise RegistryError("capabilities must be a list")
        except RegistryError as error:
            warnings.append(f"{label}: {error}")
            continue
        for capability_index, raw_capability in enumerate(raw_capabilities, start=1):
            capability_label = f"{platform_id} capability {capability_index}"
            if not isinstance(raw_capability, dict):
                warnings.append(f"{capability_label}: entry must be an object")
                continue
            try:
                capability_id = _required_text(raw_capability, "id")
                name = _required_text(raw_capability, "name")
                entrypoint_text = _required_text(raw_capability, "entrypoint")
                route = _required_text(raw_capability, "route")
                requires_auth = raw_capability.get("requires_auth")
                if not isinstance(requires_auth, bool):
                    raise RegistryError("requires_auth must be boolean")
                unique_key_value = raw_capability.get("unique_key")
                if unique_key_value is not None and (
                    not isinstance(unique_key_value, str) or not unique_key_value.strip()
                ):
                    raise RegistryError("unique_key must be null or a non-empty string")
                raw_required = raw_capability.get("required_fields", [])
                if not isinstance(raw_required, list) or not all(
                    isinstance(field, str) and field.strip() for field in raw_required
                ):
                    raise RegistryError("required_fields must be a list of non-empty strings")
                verification_ttl_days = raw_capability.get("verification_ttl_days", 30)
                if (
                    not isinstance(verification_ttl_days, int)
                    or isinstance(verification_ttl_days, bool)
                    or not 1 <= verification_ttl_days <= 3650
                ):
                    raise RegistryError(
                        "verification_ttl_days must be an integer from 1 to 3650"
                    )
                entrypoint = _path_within(root, entrypoint_text, "entrypoint")
                proof_run_text = raw_capability.get("proof_run")
                if proof_run_text is not None and (
                    not isinstance(proof_run_text, str) or not proof_run_text.strip()
                ):
                    raise RegistryError("proof_run must be null or a non-empty string")
                proof_run = (
                    _path_within(root, proof_run_text, "proof_run")
                    if proof_run_text
                    else None
                )
                proof_text = raw_capability.get("proof")
                if proof_text is not None and (
                    not isinstance(proof_text, str) or not proof_text.strip()
                ):
                    raise RegistryError("proof must be null or a non-empty string")
                proof = (
                    _path_within(root, proof_text, "proof") if proof_text else None
                )
            except RegistryError as error:
                warnings.append(f"{capability_label}: {error}")
                continue
            selector = f"{platform_id}/{capability_id}"
            available = entrypoint.is_file()
            if not available:
                warnings.append(f"{selector}: entrypoint is missing: {entrypoint_text}")
            if proof_run is not None and not proof_run.is_dir():
                warnings.append(f"{selector}: proof run is missing: {proof_run_text}")
            required_fields = tuple(field.strip() for field in raw_required)
            unique_key = unique_key_value.strip() if unique_key_value else None
            if proof is not None:
                proof_status, proof_warning = _portable_proof_status(
                    proof,
                    selector=selector,
                    entrypoint=entrypoint,
                    unique_key=unique_key,
                    required_fields=required_fields,
                    verification_ttl_days=verification_ttl_days,
                    now=now,
                )
                if proof_warning:
                    warnings.append(proof_warning)
            elif proof_run is not None and proof_run.is_dir():
                proof_status = "legacy"
            else:
                proof_status = "missing"
                if proof_run is None:
                    warnings.append(f"{selector}: proof evidence is missing")
            capabilities.append(
                Capability(
                    platform_id=platform_id,
                    platform_name=platform_name,
                    id=capability_id,
                    name=name,
                    entrypoint=entrypoint,
                    entrypoint_text=entrypoint_text,
                    route=route,
                    requires_auth=requires_auth,
                    unique_key=unique_key,
                    required_fields=required_fields,
                    verification_ttl_days=verification_ttl_days,
                    proof=proof,
                    proof_text=proof_text,
                    proof_status=proof_status,
                    proof_run=proof_run,
                    proof_run_text=proof_run_text,
                    available=available,
                )
            )
    return RegistryView(tuple(capabilities), tuple(warnings), document)


def find_capability(root: Path, selector: str) -> Capability:
    parts = selector.split("/")
    if len(parts) != 2 or not all(parts):
        raise RegistryError("expected platform/capability selector")
    view = load_registry(root)
    for capability in view.capabilities:
        if capability.selector == selector:
            if not capability.available:
                raise RegistryError(f"collector is unavailable: {selector}")
            return capability
    raise RegistryError(f"capability is not registered: {selector}")


def write_registry(root: Path, payload: dict[str, object]) -> None:
    registry_path = root.resolve() / "platforms" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = registry_path.with_name(f"{registry_path.name}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary_path, registry_path)
