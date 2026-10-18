#!/usr/bin/env python3
"""Build a validated dependency graph from bounded evidence records."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _bounded_input import InputError, emit_json, read_json, redact


def build_graph(document: object) -> dict[str, object]:
    if not isinstance(document, dict) or not isinstance(document.get("evidence"), list):
        raise ValueError("invalid_evidence_document")
    nodes: list[dict[str, object]] = []
    seen: set[str] = set()
    raw_records = document["evidence"]
    for record in raw_records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise ValueError("invalid_evidence_record")
        identifier = record["id"].strip()
        if not identifier or identifier in seen:
            raise ValueError("duplicate_or_blank_evidence_id")
        seen.add(identifier)
        dependencies = record.get("depends_on", [])
        if not isinstance(dependencies, list) or any(
            not isinstance(item, str) or not item for item in dependencies
        ):
            raise ValueError("invalid_evidence_dependencies")
        nodes.append(
            {
                "id": identifier,
                "kind": record.get("kind", "unknown"),
                "status": record.get("status", "observed"),
                "depends_on": sorted(set(dependencies)),
            }
        )
    unknown = sorted(
        dependency
        for node in nodes
        for dependency in node["depends_on"]
        if dependency not in seen
    )
    if unknown:
        raise ValueError("unknown_dependency:" + ",".join(unknown))
    edges = sorted(
        (
            {"from": dependency, "to": str(node["id"])}
            for node in nodes
            for dependency in node["depends_on"]
        ),
        key=lambda edge: (edge["from"], edge["to"]),
    )
    return {"nodes": sorted(nodes, key=lambda node: str(node["id"])), "edges": edges}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        graph = build_graph(redact(read_json(args.input)))
    except (InputError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    emit_json(graph)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
