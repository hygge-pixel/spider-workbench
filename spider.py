"""Minimal command line for collection experiments and proven capabilities."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from spider_core.experiments import discover_experiments
from spider_core.promotion import (
    PromotionError,
    promote_experiment,
    refresh_capability_proof,
)
from spider_core.browser import (
    BrowserEvidence,
    WorkspaceBrowserError,
    ensure_browser_candidate,
    ensure_workspace_browser,
    load_workspace_browser_configs,
    select_browser_candidate,
    status_browser_candidate,
    status_workspace_browser,
)
from spider_core.health import collection_health
from spider_core.registry import RegistryError, find_capability, load_registry
from spider_core.run_comparison import (
    RunComparisonError,
    compare_runs,
    write_comparison,
)
from spider_core.routing import CollectionEvidence, RoutingError, decide_route
from spider_core.runner import RunError, run_collector


def _configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run first, verify the result, then register proven collectors."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    list_parser = subcommands.add_parser("list", help="list registered capabilities")
    list_parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    experiments_parser = subcommands.add_parser(
        "experiments", help="list experiment collectors and verified run evidence"
    )
    experiments_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )

    run_parser = subcommands.add_parser(
        "run", help="run a collector path or platform/capability selector"
    )
    run_parser.add_argument("target")
    run_parser.add_argument("--task", required=True, type=Path)
    run_parser.add_argument(
        "--allow-captcha",
        action="store_true",
        help="one-time permission after explicit user instruction to handle a CAPTCHA",
    )

    compare_parser = subcommands.add_parser(
        "compare", help="compare aggregate drift between two validated runs"
    )
    compare_parser.add_argument("baseline", type=Path)
    compare_parser.add_argument("current", type=Path)
    compare_parser.add_argument(
        "--ignore-field", action="append", default=[], dest="ignore_fields"
    )
    compare_parser.add_argument("--output", type=Path)

    register_parser = subcommands.add_parser(
        "register", help="promote a successfully verified experiment"
    )
    register_parser.add_argument("experiment", type=Path)
    register_parser.add_argument("--proof-run", required=True, type=Path)

    refresh_parser = subcommands.add_parser(
        "refresh-proof", help="refresh a registered capability proof from a matching run"
    )
    refresh_parser.add_argument("selector")
    refresh_parser.add_argument("--proof-run", required=True, type=Path)

    route_parser = subcommands.add_parser(
        "route", help="choose a collection route from explicit evidence"
    )
    route_parser.add_argument(
        "--evidence-json",
        default="{}",
        help="JSON object, or '-' to read from standard input",
    )

    browser_parser = subcommands.add_parser(
        "browser", help="inspect or ensure the configured workspace browser"
    )
    browser_commands = browser_parser.add_subparsers(
        dest="browser_command", required=True
    )
    for name in ("status", "ensure"):
        command = browser_commands.add_parser(name)
        command.add_argument(
            "--candidate",
            choices=("auto", "chrome", "cloak", "all"),
            default="auto",
        )
        command.add_argument("--evidence-json", default="{}")
        command.add_argument("--json", action="store_true")

    doctor_parser = subcommands.add_parser(
        "doctor", help="report collection resources without starting them"
    )
    doctor_parser.add_argument("--json", action="store_true")
    return parser


def _path(root: Path, value: Path) -> Path:
    return value.resolve() if value.is_absolute() else (root / value).resolve()


def _list(root: Path, *, as_json: bool) -> int:
    view = load_registry(root)
    capabilities = [
        {
            "selector": capability.selector,
            "name": capability.name,
            "platform_name": capability.platform_name,
            "route": capability.route,
            "requires_auth": capability.requires_auth,
            "available": capability.available,
            "proof_status": capability.proof_status,
        }
        for capability in view.capabilities
    ]
    if as_json:
        print(
            json.dumps(
                {"capabilities": capabilities, "warnings": list(view.warnings)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if not capabilities:
        print("No registered capabilities.")
    else:
        for item in capabilities:
            availability = "ready" if item["available"] else "unavailable"
            auth = "auth" if item["requires_auth"] else "public"
            print(
                f"{item['selector']}\t{availability}\t{item['proof_status']}\t"
                f"{item['route']}\t{auth}\t{item['name']}"
            )
    for warning in view.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


def _experiments(root: Path, *, as_json: bool) -> int:
    view = discover_experiments(root)
    experiments = [item.to_dict() for item in view.experiments]
    if as_json:
        print(
            json.dumps(
                {"experiments": experiments, "warnings": list(view.warnings)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if not experiments:
        print("No collection experiments.")
    else:
        for item in view.experiments:
            observed = (
                f"{item.route}/{item.backend}"
                if item.route and item.backend
                else "-"
            )
            proof = item.latest_verified_run or "-"
            command = item.command or "-"
            print(f"{item.status}\t{observed}\t{item.name}\t{proof}\t{command}")
    for warning in view.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 0


def _run(
    root: Path,
    target: str,
    task_value: Path,
    *,
    allow_captcha: bool = False,
) -> int:
    task_path = _path(root, task_value)
    direct_candidate = _path(root, Path(target))
    selector: str | None = None
    required_fields: tuple[str, ...] | None = None
    unique_key: str | None = None
    if direct_candidate.suffix.lower() == ".py" or direct_candidate.exists():
        entrypoint = direct_candidate
    else:
        capability = find_capability(root, target)
        entrypoint = capability.entrypoint
        selector = capability.selector
        required_fields = capability.required_fields
        unique_key = capability.unique_key
    outcome = run_collector(
        root,
        entrypoint,
        task_path,
        selector=selector,
        required_fields=required_fields,
        unique_key=unique_key,
        allow_captcha=allow_captcha,
    )
    print(
        json.dumps(
            {
                "run_dir": str(outcome.run_dir),
                "selector": selector,
                "status": outcome.status,
                "completeness": outcome.completeness,
                "records": outcome.records,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if outcome.status == "completed" else 1


def _compare(
    root: Path,
    baseline_value: Path,
    current_value: Path,
    *,
    ignore_fields: Sequence[str],
    output_value: Path | None,
) -> int:
    baseline = _path(root, baseline_value)
    current = _path(root, current_value)
    report = compare_runs(
        root, baseline, current, ignore_fields=tuple(ignore_fields)
    )
    if output_value is not None:
        write_comparison(report, current, _path(root, output_value))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _register(root: Path, experiment_value: Path, proof_value: Path) -> int:
    outcome = promote_experiment(
        root, _path(root, experiment_value), _path(root, proof_value)
    )
    print(
        json.dumps(
            {"selector": outcome.selector, "target_dir": str(outcome.target_dir)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _refresh_proof(root: Path, selector: str, proof_value: Path) -> int:
    outcome = refresh_capability_proof(root, selector, _path(root, proof_value))
    print(
        json.dumps(
            {
                "selector": outcome.selector,
                "proof": str(outcome.proof_path),
                "source_run_id": outcome.source_run_id,
                "proof_status": outcome.proof_status,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _route(evidence_json: str) -> int:
    raw = sys.stdin.read() if evidence_json == "-" else evidence_json
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RoutingError("evidence must be a JSON object")
    evidence = CollectionEvidence.from_dict(payload)
    decision = decide_route(evidence)
    print(
        json.dumps(
            {"evidence": evidence.to_dict(), "decision": decision.to_dict()},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _browser_evidence(value: str) -> BrowserEvidence:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        raise WorkspaceBrowserError("browser_evidence_invalid") from None
    if not isinstance(payload, dict):
        raise WorkspaceBrowserError("browser_evidence_invalid")
    return BrowserEvidence.from_dict(payload)


def _browser(
    root: Path,
    command: str,
    *,
    candidate: str,
    evidence_json: str,
    as_json: bool,
) -> int:
    evidence = _browser_evidence(evidence_json)
    operation = (
        status_browser_candidate if command == "status" else ensure_browser_candidate
    )
    if candidate == "all":
        candidates: dict[str, object] = {}
        degraded = False
        for name in ("chrome", "cloak"):
            try:
                candidates[name] = operation(root, name)
            except WorkspaceBrowserError as error:
                degraded = True
                candidates[name] = {"status": "error", "error": error.code}
        result = {
            "status": "degraded" if degraded else "ready",
            "candidates": candidates,
        }
        if as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for name, state in candidates.items():
                print(f"{name}: {state['status']}")
        return 2 if degraded else 0

    selected = (
        select_browser_candidate(
            evidence,
            default_candidate=load_workspace_browser_configs(root).default_candidate,
        )
        if candidate == "auto" else candidate
    )
    result = operation(root, selected)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Workspace browser {result['candidate']} ready: "
            f"{result['action']}, {result['browser']}, "
            f"CDP {result['protocol_version']}, pages {result['page_targets']}."
        )
    return 0


def _doctor(root: Path, *, as_json: bool) -> int:
    result = collection_health(root)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    available = [
        name for name, state in result["packages"].items() if state["available"]
    ]
    missing = [
        name for name, state in result["packages"].items() if not state["available"]
    ]
    print(f"Available packages: {', '.join(available) or 'none'}")
    print(f"Unavailable packages: {', '.join(missing) or 'none'}")
    for name, state in result["optional_backends"].items():
        print(f"Optional backend {name}: {state['status']}")
    print(f"Workspace browser: {result['browser']['status']}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parent
    try:
        if args.command == "list":
            return _list(root, as_json=args.json)
        if args.command == "experiments":
            return _experiments(root, as_json=args.json)
        if args.command == "run":
            return _run(
                root,
                args.target,
                args.task,
                allow_captcha=args.allow_captcha,
            )
        if args.command == "compare":
            return _compare(
                root,
                args.baseline,
                args.current,
                ignore_fields=args.ignore_fields,
                output_value=args.output,
            )
        if args.command == "register":
            return _register(root, args.experiment, args.proof_run)
        if args.command == "refresh-proof":
            return _refresh_proof(root, args.selector, args.proof_run)
        if args.command == "route":
            return _route(args.evidence_json)
        if args.command == "browser":
            return _browser(
                root,
                args.browser_command,
                candidate=args.candidate,
                evidence_json=args.evidence_json,
                as_json=args.json,
            )
        if args.command == "doctor":
            return _doctor(root, as_json=args.json)
    except WorkspaceBrowserError as error:
        if getattr(args, "json", False):
            print(
                json.dumps(
                    {"status": "error", "error": error.code},
                    ensure_ascii=False,
                )
            )
        else:
            print(f"error: {error.code}", file=sys.stderr)
        return 2
    except (
        RegistryError,
        RunError,
        RunComparisonError,
        PromotionError,
        RoutingError,
        json.JSONDecodeError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    _configure_utf8_stdio()
    raise SystemExit(main())
