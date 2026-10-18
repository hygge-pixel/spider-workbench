from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from spider_core.experiments import discover_experiments


class ExperimentDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "experiments").mkdir()
        (self.root / "platforms").mkdir()
        (self.root / "runs").mkdir()
        self.write_json(
            self.root / "platforms" / "registry.json",
            {"schema_version": 1, "platforms": []},
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def create_experiment(
        self,
        name: str,
        *,
        task_name: str | None = "task.json",
        capability: dict[str, object] | None = None,
    ) -> Path:
        directory = self.root / "experiments" / name
        directory.mkdir()
        collector = directory / "collector.py"
        collector.write_text("# collector\n", encoding="utf-8")
        if task_name is not None:
            self.write_json(
                directory / task_name,
                {
                    "query": {"token": "sensitive-value"},
                    "completion": {"mode": "sample", "min_records": 1},
                    "validation": {"required_fields": ["id"]},
                },
            )
        if capability is not None:
            self.write_json(directory / "capability.json", capability)
        return collector

    def add_run(
        self,
        name: str,
        collector: Path,
        *,
        status: str = "completed",
        validation_passed: bool = True,
        records: int = 2,
        completeness: str = "partial",
        route: str = "http",
        backend: str = "requests",
    ) -> Path:
        run = self.root / "runs" / name
        run.mkdir()
        self.write_json(
            run / "run.json",
            {
                "entrypoint": str(collector.resolve()),
                "collector_sha256": hashlib.sha256(collector.read_bytes()).hexdigest(),
                "status": status,
                "records": records,
                "completeness": completeness,
            },
        )
        self.write_json(
            run / "validation.json",
            {
                "passed": validation_passed,
                "errors": [] if validation_passed else ["failed"],
            },
        )
        self.write_json(
            run / "collector_result.json",
            {"route": route, "backend": backend, "source_exhausted": False},
        )
        return run

    def test_changed_collector_does_not_inherit_old_verified_run(self) -> None:
        collector = self.create_experiment("changed_items")
        self.add_run("20260816T120000Z_success", collector)
        collector.write_text("# changed collector\n", encoding="utf-8")

        view = discover_experiments(self.root)

        item = view.experiments[0]
        self.assertEqual(item.status, "unverified")
        self.assertIsNone(item.latest_verified_run)
        self.assertTrue(
            any("collector_sha256 does not match" in warning for warning in view.warnings)
        )

    def test_run_without_collector_hash_is_not_verified(self) -> None:
        collector = self.create_experiment("legacy_items")
        run = self.add_run("20260816T120000Z_success", collector)
        payload = json.loads((run / "run.json").read_text(encoding="utf-8"))
        del payload["collector_sha256"]
        self.write_json(run / "run.json", payload)

        view = discover_experiments(self.root)

        self.assertEqual(view.experiments[0].status, "unverified")
        self.assertTrue(
            any("collector_sha256 is invalid" in warning for warning in view.warnings)
        )

    def test_invalid_run_warnings_are_bounded_to_the_newest_matching_run(self) -> None:
        collector = self.create_experiment("noisy_items")
        for index in range(3):
            self.add_run(
                f"20260816T12000{index}Z_failed",
                collector,
                status="failed",
                validation_passed=False,
                records=0,
            )

        view = discover_experiments(self.root)

        warnings = [
            warning for warning in view.warnings if warning.startswith("noisy_items:")
        ]
        self.assertEqual(len(warnings), 1)
        self.assertIn("20260816T120002Z_failed", warnings[0])

    def test_verified_unregistered_uses_only_small_machine_evidence(self) -> None:
        collector = self.create_experiment("live_items")
        run = self.add_run("20260816T120000Z_success", collector)
        (run / "normalized.jsonl").write_text(
            '{"id":"1","token":"sensitive-value"}\n', encoding="utf-8"
        )
        raw = run / "raw"
        raw.mkdir()
        (raw / "page.json").write_text(
            '{"authorization":"sensitive-value"}', encoding="utf-8"
        )

        view = discover_experiments(self.root)

        self.assertEqual(len(view.experiments), 1)
        item = view.experiments[0]
        self.assertEqual(item.name, "live_items")
        self.assertEqual(item.status, "verified_unregistered")
        self.assertEqual(item.collector, "experiments/live_items/collector.py")
        self.assertEqual(item.task, "experiments/live_items/task.json")
        self.assertIsNone(item.selector)
        self.assertEqual(
            item.latest_verified_run, "runs/20260816T120000Z_success"
        )
        self.assertEqual(item.records, 2)
        self.assertEqual(item.completeness, "partial")
        self.assertEqual(item.route, "http")
        self.assertEqual(item.backend, "requests")
        self.assertEqual(
            item.command,
            "py -3.11 spider.py run experiments/live_items/collector.py "
            "--task experiments/live_items/task.json",
        )
        self.assertNotIn("sensitive-value", json.dumps(item.to_dict()))

    def test_classifies_all_lifecycle_states_in_lexical_order(self) -> None:
        self.create_experiment("a_example", task_name="task.example.json")
        registered_experiment = self.create_experiment(
            "b_registered",
            task_name="task.example.json",
            capability={
                "platform_id": "demo",
                "id": "items",
            },
        )
        self.add_run(
            "20260816T120000Z_registered_failure",
            registered_experiment,
            status="failed",
            validation_passed=False,
            records=0,
        )
        self.create_experiment("c_unverified")
        verified = self.create_experiment("d_verified")
        self.add_run("20260816T120000Z_verified", verified)
        registered_collector = (
            self.root / "platforms" / "demo" / "items" / "collector.py"
        )
        registered_collector.parent.mkdir(parents=True)
        registered_collector.write_text("# registered\n", encoding="utf-8")
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
                                "required_fields": ["id"],
                                "proof_run": None,
                            }
                        ],
                    }
                ],
            },
        )

        view = discover_experiments(self.root)

        self.assertEqual(
            [item.name for item in view.experiments],
            ["a_example", "b_registered", "c_unverified", "d_verified"],
        )
        self.assertEqual(
            [item.status for item in view.experiments],
            ["example", "registered_source", "unverified", "verified_unregistered"],
        )
        registered = view.experiments[1]
        self.assertEqual(registered.selector, "demo/items")
        self.assertIsNone(registered.command)
        self.assertFalse(
            any("b_registered:" in warning for warning in view.warnings)
        )

    def test_newer_failure_does_not_hide_older_success_and_missing_task_warns(
        self,
    ) -> None:
        collector = self.create_experiment("stable_items")
        self.add_run("20260816T110000Z_success", collector)
        self.add_run(
            "20260816T120000Z_failed",
            collector,
            status="failed",
            validation_passed=False,
            records=0,
        )
        self.create_experiment("without_task", task_name=None)

        view = discover_experiments(self.root)

        stable = next(item for item in view.experiments if item.name == "stable_items")
        missing = next(item for item in view.experiments if item.name == "without_task")
        self.assertEqual(
            stable.latest_verified_run, "runs/20260816T110000Z_success"
        )
        self.assertEqual(stable.status, "verified_unregistered")
        self.assertEqual(missing.status, "example")
        self.assertIsNone(missing.task)
        self.assertIsNone(missing.command)
        self.assertTrue(
            any("20260816T120000Z_failed" in warning for warning in view.warnings)
        )
        self.assertTrue(any("without_task" in warning for warning in view.warnings))

    def test_broken_capability_is_local_warning(self) -> None:
        broken = self.create_experiment("broken_capability")
        (broken.parent / "capability.json").write_text("[]", encoding="utf-8")
        self.create_experiment("healthy")

        view = discover_experiments(self.root)

        self.assertEqual(
            [item.name for item in view.experiments],
            ["broken_capability", "healthy"],
        )
        self.assertTrue(
            any("broken_capability" in warning for warning in view.warnings)
        )

    def test_missing_directories_are_empty(self) -> None:
        empty = Path(self.temporary.name) / "empty"
        empty.mkdir()
        (empty / "platforms").mkdir()
        self.write_json(
            empty / "platforms" / "registry.json",
            {"schema_version": 1, "platforms": []},
        )

        view = discover_experiments(empty)

        self.assertEqual(view.experiments, ())
        self.assertEqual(view.warnings, ())


if __name__ == "__main__":
    unittest.main()
