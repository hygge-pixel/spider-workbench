from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from spider_core.run_comparison import (
    RunComparisonError,
    compare_runs,
    write_comparison,
)


class RunComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "runs").mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def write_json(path: Path, payload: object) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def make_run(self, name: str, rows: list[dict[str, object]]) -> Path:
        run_dir = self.root / "runs" / name
        run_dir.mkdir()
        self.write_json(
            run_dir / "run.json",
            {
                "run_id": name,
                "selector": None,
                "entrypoint": str(self.root / "experiments/demo/collector.py"),
                "status": "completed",
            },
        )
        self.write_json(
            run_dir / "validation.json",
            {"passed": True, "unique_key": "id", "errors": []},
        )
        with (run_dir / "normalized.jsonl").open(
            "w", encoding="utf-8", newline=""
        ) as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        return run_dir

    def test_compares_aggregate_drift_without_values(self) -> None:
        baseline = self.make_run(
            "baseline",
            [
                {
                    "id": "1",
                    "title": "one",
                    "price": 10,
                    "collected_at": "before",
                },
                {"id": "2", "title": "two", "price": 20},
                {"id": "3", "title": "old only", "price": 30},
            ],
        )
        current = self.make_run(
            "current",
            [
                {
                    "id": "1",
                    "title": "one",
                    "price": 11,
                    "collected_at": "after",
                },
                {"id": "2", "title": "two", "price": 20},
                {"id": "4", "title": "new only", "price": 40},
            ],
        )

        report = compare_runs(self.root, baseline, current)

        self.assertEqual(2, report["shared_unique_ids"])
        self.assertEqual(1, report["baseline_only_unique_ids"])
        self.assertEqual(1, report["current_only_unique_ids"])
        self.assertEqual(
            {"price": 1, "title": 0}, report["changed_fields_on_shared_ids"]
        )
        self.assertNotIn("collected_at", report["changed_fields_on_shared_ids"])
        self.assertNotIn("shared_ids", report)
        self.assertNotIn("old only", json.dumps(report))

    def test_additional_ignored_fields_are_applied(self) -> None:
        baseline = self.make_run(
            "baseline", [{"id": "1", "title": "one", "price": 10}]
        )
        current = self.make_run(
            "current", [{"id": "1", "title": "one", "price": 11}]
        )

        report = compare_runs(
            self.root, baseline, current, ignore_fields=("price",)
        )

        self.assertEqual({"title": 0}, report["changed_fields_on_shared_ids"])
        self.assertEqual(["collected_at", "price"], report["ignored_fields"])

    def test_rejects_failed_unvalidated_and_mismatched_runs(self) -> None:
        baseline = self.make_run("baseline", [{"id": "1", "title": "one"}])
        current = self.make_run("current", [{"id": "1", "title": "one"}])

        run_payload = json.loads((current / "run.json").read_text(encoding="utf-8"))
        run_payload["status"] = "failed"
        self.write_json(current / "run.json", run_payload)
        with self.assertRaisesRegex(RunComparisonError, "completed"):
            compare_runs(self.root, baseline, current)

        run_payload["status"] = "completed"
        self.write_json(current / "run.json", run_payload)
        validation = json.loads(
            (current / "validation.json").read_text(encoding="utf-8")
        )
        validation["passed"] = False
        self.write_json(current / "validation.json", validation)
        with self.assertRaisesRegex(RunComparisonError, "passed validation"):
            compare_runs(self.root, baseline, current)

        validation["passed"] = True
        validation["unique_key"] = "other_id"
        self.write_json(current / "validation.json", validation)
        with self.assertRaisesRegex(RunComparisonError, "same nonblank unique key"):
            compare_runs(self.root, baseline, current)

    def test_rejects_selector_and_collector_mismatch(self) -> None:
        baseline = self.make_run("baseline", [{"id": "1", "title": "one"}])
        current = self.make_run("current", [{"id": "1", "title": "one"}])
        baseline_meta = json.loads(
            (baseline / "run.json").read_text(encoding="utf-8")
        )
        current_meta = json.loads((current / "run.json").read_text(encoding="utf-8"))
        baseline_meta["selector"] = "demo/items"
        current_meta["selector"] = "other/items"
        self.write_json(baseline / "run.json", baseline_meta)
        self.write_json(current / "run.json", current_meta)
        with self.assertRaisesRegex(RunComparisonError, "same selector"):
            compare_runs(self.root, baseline, current)

        baseline_meta["selector"] = None
        current_meta["selector"] = None
        current_meta["entrypoint"] = str(self.root / "experiments/other/collector.py")
        self.write_json(baseline / "run.json", baseline_meta)
        self.write_json(current / "run.json", current_meta)
        with self.assertRaisesRegex(RunComparisonError, "same collector"):
            compare_runs(self.root, baseline, current)

    def test_verified_portable_proof_links_pre_and_post_registration_runs(self) -> None:
        baseline = self.make_run("baseline", [{"id": "1", "title": "one"}])
        current = self.make_run("current", [{"id": "1", "title": "one"}])
        collector = self.root / "platforms" / "demo" / "items" / "collector.py"
        collector.parent.mkdir(parents=True)
        collector.write_text("# registered collector\n", encoding="utf-8")
        current_meta = json.loads((current / "run.json").read_text(encoding="utf-8"))
        current_meta["selector"] = "demo/items"
        current_meta["entrypoint"] = str(collector)
        self.write_json(current / "run.json", current_meta)
        proof = collector.parent / "proof.json"
        self.write_json(
            proof,
            {
                "schema_version": 1,
                "selector": "demo/items",
                "source_run_id": "baseline",
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "status": "completed",
                "completeness": "complete",
                "records": 1,
                "collector_sha256": hashlib.sha256(collector.read_bytes()).hexdigest(),
                "validation": {
                    "passed": True,
                    "unique_key": "id",
                    "required_fields": ["id", "title"],
                    "errors_count": 0,
                },
                "observed": {
                    "route": "local",
                    "backend": "python",
                    "source_exhausted": True,
                },
            },
        )
        self.write_json(
            self.root / "platforms" / "registry.json",
            {
                "schema_version": 1,
                "platforms": [
                    {
                        "id": "demo",
                        "name": "Demo",
                        "capabilities": [
                            {
                                "id": "items",
                                "name": "Items",
                                "entrypoint": "platforms/demo/items/collector.py",
                                "route": "local",
                                "requires_auth": False,
                                "unique_key": "id",
                                "required_fields": ["id", "title"],
                                "proof": "platforms/demo/items/proof.json",
                            }
                        ],
                    }
                ],
            },
        )

        report = compare_runs(self.root, baseline, current)

        self.assertEqual("demo/items", report["selector"])
        proof_payload = json.loads(proof.read_text(encoding="utf-8"))
        proof_payload["source_run_id"] = "different-run"
        self.write_json(proof, proof_payload)
        with self.assertRaisesRegex(RunComparisonError, "same selector or proof lineage"):
            compare_runs(self.root, baseline, current)

    def test_rejects_invalid_normalized_rows_and_outside_paths(self) -> None:
        baseline = self.make_run("baseline", [{"id": "1", "title": "one"}])
        current = self.make_run("current", [{"id": "1", "title": "one"}])

        (current / "normalized.jsonl").write_text(
            '{"id":""}\n', encoding="utf-8"
        )
        with self.assertRaisesRegex(RunComparisonError, "blank unique key"):
            compare_runs(self.root, baseline, current)

        (current / "normalized.jsonl").write_text(
            '{"id":"1"}\n{"id":"1"}\n', encoding="utf-8"
        )
        with self.assertRaisesRegex(RunComparisonError, "duplicate unique key"):
            compare_runs(self.root, baseline, current)

        (current / "normalized.jsonl").write_text("{bad\n", encoding="utf-8")
        with self.assertRaisesRegex(RunComparisonError, "line 1 is invalid"):
            compare_runs(self.root, baseline, current)

        outside = self.root / "outside"
        outside.mkdir()
        with self.assertRaisesRegex(RunComparisonError, "workspace runs"):
            compare_runs(self.root, baseline, outside)

    def test_writes_only_a_new_json_file_inside_current_run(self) -> None:
        baseline = self.make_run("baseline", [{"id": "1", "title": "one"}])
        current = self.make_run("current", [{"id": "1", "title": "one"}])
        report = compare_runs(self.root, baseline, current)
        output = current / "historical_diff.json"

        write_comparison(report, current, output)

        self.assertEqual(report, json.loads(output.read_text(encoding="utf-8")))
        with self.assertRaisesRegex(RunComparisonError, "already exists"):
            write_comparison(report, current, output)
        with self.assertRaisesRegex(RunComparisonError, "current run"):
            write_comparison(report, current, self.root / "outside.json")
        with self.assertRaisesRegex(RunComparisonError, "current run"):
            write_comparison(report, current, current / "report.txt")


if __name__ == "__main__":
    unittest.main()
