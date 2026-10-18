"""Deterministic evidence-based routing for webpage collection tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Mapping


class RoutingError(ValueError):
    """Raised when collection evidence is invalid or inconsistent."""


@dataclass(frozen=True)
class CollectionEvidence:
    stable_api: bool = False
    protocol_ready: bool = False
    protocol_unavailable: bool = False
    has_signature: bool = False
    has_dynamic_token: bool = False
    has_waf_state: bool = False
    requires_javascript: bool = False
    requires_resilient_html: bool = False
    requires_login: bool = False
    requires_interaction: bool = False
    reuse_existing_chrome: bool = False
    document_collection: bool = False
    fingerprint_pressure: bool = False
    allow_stealth: bool = False
    scrapling_stealth_failed: bool = False
    allow_experimental_camoufox: bool = False
    captcha_present: bool = False
    authorized_captcha_research: bool = False

    def __post_init__(self) -> None:
        for item in fields(self):
            if not isinstance(getattr(self, item.name), bool):
                raise RoutingError(f"{item.name} must be boolean")
        if self.protocol_ready and self.protocol_unavailable:
            raise RoutingError("protocol_ready and protocol_unavailable are mutually exclusive")
        if self.authorized_captcha_research and not self.captcha_present:
            raise RoutingError(
                "authorized captcha research requires captcha evidence"
            )
        if self.scrapling_stealth_failed and not self.fingerprint_pressure:
            raise RoutingError(
                "Scrapling stealth failure requires fingerprint pressure evidence"
            )

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CollectionEvidence":
        known = {item.name for item in fields(cls)}
        unknown = sorted(set(payload) - known)
        if unknown:
            raise RoutingError(f"unknown evidence fields: {', '.join(unknown)}")
        return cls(**dict(payload))


@dataclass(frozen=True)
class RouteDecision:
    route: str
    backend: str | None
    executable: bool
    reason_codes: tuple[str, ...]
    next_skill: str | None = None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _decision(
    route: str,
    backend: str | None,
    executable: bool,
    *reasons: str,
    next_skill: str | None = None,
    warnings: tuple[str, ...] = (),
) -> RouteDecision:
    return RouteDecision(
        route=route,
        backend=backend,
        executable=executable,
        reason_codes=tuple(reasons),
        next_skill=next_skill,
        warnings=warnings,
    )


def decide_route(evidence: CollectionEvidence) -> RouteDecision:
    """Return one reproducible priority decision from validated evidence."""
    if evidence.captcha_present:
        authorization_note = (
            "captcha research scope is authorized, but handling still requires "
            "a user instruction and one-time --allow-captcha"
            if evidence.authorized_captcha_research
            else "report the captcha and wait for user instruction; after explicit "
            "authorization, use one-time --allow-captcha"
        )
        return _decision(
            "reverse",
            None,
            False,
            "captcha_user_instruction_required",
            warnings=(authorization_note,),
        )

    if evidence.protocol_ready:
        return _decision("http", "requests", True, "protocol_ready")

    reverse_reasons = tuple(
        name
        for name, present in (
            ("has_signature", evidence.has_signature),
            ("has_dynamic_token", evidence.has_dynamic_token),
            ("has_waf_state", evidence.has_waf_state),
        )
        if present
    )
    if reverse_reasons:
        return _decision(
            "reverse",
            None,
            False,
            *reverse_reasons,
            next_skill="web-reverse-workflow",
        )

    if evidence.stable_api and not evidence.protocol_unavailable:
        return _decision("http", "requests", True, "stable_api")

    if (
        evidence.requires_login
        or evidence.requires_interaction
        or evidence.reuse_existing_chrome
    ):
        reason = (
            "reuse_existing_chrome"
            if evidence.reuse_existing_chrome
            else "requires_login_or_interaction"
        )
        return _decision(
            "browser_context",
            "chrome_cdp",
            False,
            reason,
            next_skill="playwright-cli",
            warnings=(
                "reuse the authorized workspace session; do not persist credentials",
            ),
        )

    if evidence.document_collection:
        return _decision(
            "html",
            "crawl4ai",
            False,
            "document_collection",
            warnings=("use a task collector for durable output and validation",),
        )

    if evidence.fingerprint_pressure:
        if not evidence.allow_stealth:
            return _decision(
                "stealth",
                None,
                False,
                "stealth_not_authorized",
                next_skill="web-reverse-workflow",
            )
        if not evidence.protocol_unavailable:
            return _decision(
                "reverse", None, False, "protocol_investigation_required",
                next_skill="web-reverse-workflow",
                warnings=("verify local protocol coverage before browser collection",),
            )
        if evidence.scrapling_stealth_failed:
            if evidence.allow_experimental_camoufox:
                return _decision(
                    "stealth",
                    "camoufox",
                    True,
                    "experimental_camoufox_after_scrapling_failure",
                    warnings=("Camoufox is experimental and not a captcha bypass",),
                )
            return _decision(
                "stealth",
                None,
                False,
                "camoufox_not_authorized",
                next_skill="web-reverse-workflow",
                warnings=("preserve Scrapling failure evidence before escalation",),
            )
        return _decision(
            "stealth",
            "scrapling_stealth",
            True,
            "fingerprint_pressure",
            warnings=("stealth settings do not guarantee challenge avoidance",),
        )

    if evidence.requires_javascript:
        return _decision(
            "browser",
            "scrapling_dynamic",
            evidence.protocol_unavailable,
            "requires_javascript",
            "protocol_unavailable" if evidence.protocol_unavailable else "protocol_investigation_required",
            next_skill=None if evidence.protocol_unavailable else "web-reverse-workflow",
            warnings=() if evidence.protocol_unavailable else (
                "use the browser for Network reconnaissance and test local protocol replay first",
            ),
        )

    if evidence.requires_resilient_html:
        return _decision(
            "html",
            "scrapling_static",
            True,
            "requires_resilient_html",
        )

    if evidence.protocol_unavailable:
        return _decision(
            "browser_context", "chrome_cdp", False, "protocol_unavailable",
            next_skill="playwright-cli",
            warnings=("collect only the portions not covered by local protocol requests",),
        )

    return _decision("html", "requests", True, "static_html_default")
