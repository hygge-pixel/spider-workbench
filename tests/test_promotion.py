from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from spider_core.promotion import (
    PromotionError,
    promote_experiment,
    refresh_capability_proof,
)
from spider_core.registry import load_registry


class PromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "platforms").mkdir()
        (self.root / "experiments").mkdir()
        (self.root / "runs").mkdir()
        self.write_json(
            self.root / "platforms" / "registry.json",
            {"schema_version": 1, "platforms": []},
        )
        self.experiment = self.root / "experiments" / "demo_items"
        self.experiment.mkdir()
        self.collector = self.experiment / "collector.py"
        self.collector.write_text("# proven collector\n", encoding="utf-8")
        self.write_json(
            self.experiment / "capability.json",
            {
                "platform_id": "demo",
                "platform_name": "Demo",
                "id": "items",
                "name": "Items",
                "route": "http",
                "requires_auth": False,
                "unique_key": "id",
                "required_fields": ["id", "title"],
            },
        )
        self.write_json(
            self.experiment / "task.example.json",
            {
                "query": {"category": "books"},
                "completion": {"mode": "sample", "min_records": 1},
                "validation": {"unique_key": "id", "required_fields": ["id", "title"]},
            },
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def proof_run(
        self,
        *,
        status: str = "completed",
        passed: bool = True,
        entrypoint: Path | None = None,
        run_overrides: dict[str, object] | None = None,
        collector_result_overrides: dict[str, object] | None = None,
    ) -> Path:
        proof = self.root / "runs" / "proof_run"
        proof.mkdir(exist_ok=True)
        run_payload: dict[str, object] = {
            "schema_version": 1,
            "run_id": "20260816T000000Z_proof",
            "selector": None,
            "status": status,
            "entrypoint": str(entrypoint or self.collector.resolve()),
            "collector_sha256": hashlib.sha256(self.collector.read_bytes()).hexdigest(),
            "completeness": "complete",
            "records": 1,
            "completed_at": "2026-08-16T00:00:01Z",
        }
        if run_overrides:
            run_payload.update(run_overrides)
        self.write_json(
            proof / "run.json",
            run_payload,
        )
        collector_result: dict[str, object] = {
            "source_exhausted": True,
            "route": "http",
            "backend": "requests",
            "records": 1,
        }
        if collector_result_overrides:
            collector_result.update(collector_result_overrides)
        self.write_json(proof / "collector_result.json", collector_result)
        self.write_json(
            proof / "validation.json",
            {
                "passed": passed,
                "required_fields": ["id", "title"],
                "unique_key": "id",
                "errors": [],
            },
        )
        return proof

    def test_rejects_run_that_is_not_completed_and_validated(self) -> None:
        proof = self.proof_run(status="partial")

        with self.assertRaisesRegex(PromotionError, "completed"):
            promote_experiment(self.root, self.experiment, proof)

        self.assertFalse((self.root / "platforms" / "demo").exists())
        self.assertEqual(load_registry(self.root).capabilities, ())

    def test_promotes_proven_collector_and_updates_registry(self) -> None:
        proof = self.proof_run()

        outcome = promote_experiment(self.root, self.experiment, proof)

        self.assertEqual(outcome.selector, "demo/items")
        self.assertEqual(
            (outcome.target_dir / "collector.py").read_text(encoding="utf-8"),
            "# proven collector\n",
        )
        self.assertTrue((outcome.target_dir / "task.example.json").is_file())
        proof_snapshot = json.loads(
            (outcome.target_dir / "proof.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            proof_snapshot,
            {
                "schema_version": 1,
                "selector": "demo/items",
                "source_run_id": "20260816T000000Z_proof",
                "verified_at": "2026-08-16T00:00:01Z",
                "status": "completed",
                "completeness": "complete",
                "records": 1,
                "collector_sha256": hashlib.sha256(
                    self.collector.read_bytes()
                ).hexdigest(),
                "validation": {
                    "passed": True,
                    "unique_key": "id",
                    "required_fields": ["id", "title"],
                    "errors_count": 0,
                },
                "observed": {
                    "route": "http",
                    "backend": "requests",
                    "source_exhausted": True,
                },
            },
        )
        self.assertNotIn(str(self.root), json.dumps(proof_snapshot))
        capability = load_registry(self.root).capabilities[0]
        self.assertEqual(capability.selector, "demo/items")
        self.assertTrue(capability.available)
        registry = json.loads(
            (self.root / "platforms" / "registry.json").read_text(encoding="utf-8")
        )
        registered = registry["platforms"][0]["capabilities"][0]
        self.assertEqual(
            registered["proof"], "platforms/demo/items/proof.json"
        )
        self.assertNotIn("proof_run", registered)
        self.assertEqual(registered["verification_ttl_days"], 30)

    def test_promotion_carries_configured_verification_ttl(self) -> None:
        metadata_path = self.experiment / "capability.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["verification_ttl_days"] = 45
        self.write_json(metadata_path, metadata)

        outcome = promote_experiment(self.root, self.experiment, self.proof_run())

        installed_metadata = json.loads(
            (outcome.target_dir / "capability.json").read_text(encoding="utf-8")
        )
        registry = json.loads(
            (self.root / "platforms" / "registry.json").read_text(encoding="utf-8")
        )
        registered = registry["platforms"][0]["capabilities"][0]
        self.assertEqual(installed_metadata["verification_ttl_days"], 45)
        self.assertEqual(registered["verification_ttl_days"], 45)

    def test_rejects_duplicate_selector_without_mutation(self) -> None:
        proof = self.proof_run()
        promote_experiment(self.root, self.experiment, proof)
        registry_before = (self.root / "platforms" / "registry.json").read_bytes()

        with self.assertRaisesRegex(PromotionError, "already registered"):
            promote_experiment(self.root, self.experiment, proof)

        self.assertEqual(
            (self.root / "platforms" / "registry.json").read_bytes(), registry_before
        )

    def test_rejects_experiment_outside_workspace(self) -> None:
        outside = Path(self.temporary.name).parent / "outside_experiment"

        with self.assertRaisesRegex(PromotionError, "experiments"):
            promote_experiment(self.root, outside, self.proof_run())

    def test_rejects_proof_from_a_different_collector(self) -> None:
        proof = self.proof_run(entrypoint=self.root / "other.py")

        with self.assertRaisesRegex(PromotionError, "different collector"):
            promote_experiment(self.root, self.experiment, proof)

    def test_rejects_proof_without_collector_hash(self) -> None:
        proof = self.proof_run()
        run_path = proof / "run.json"
        run_payload = json.loads(run_path.read_text(encoding="utf-8"))
        del run_payload["collector_sha256"]
        self.write_json(run_path, run_payload)

        with self.assertRaisesRegex(PromotionError, "collector_sha256"):
            promote_experiment(self.root, self.experiment, proof)

    def test_rejects_proof_with_mismatching_collector_hash(self) -> None:
        proof = self.proof_run(run_overrides={"collector_sha256": "0" * 64})

        with self.assertRaisesRegex(PromotionError, "collector_sha256"):
            promote_experiment(self.root, self.experiment, proof)

    def test_rejects_registered_run_for_experiment_promotion(self) -> None:
        proof = self.proof_run(run_overrides={"selector": "demo/items"})

        with self.assertRaisesRegex(PromotionError, "selector"):
            promote_experiment(self.root, self.experiment, proof)

    def test_rejects_invalid_identifier_before_creating_platform_directory(self) -> None:
        metadata_path = self.experiment / "capability.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["platform_id"] = "../escape"
        self.write_json(metadata_path, metadata)

        with self.assertRaisesRegex(PromotionError, "platform_id"):
            promote_experiment(self.root, self.experiment, self.proof_run())

        self.assertFalse((self.root / "escape").exists())

    def test_rejects_secret_bearing_example_task(self) -> None:
        task_path = self.experiment / "task.example.json"
        task = json.loads(task_path.read_text(encoding="utf-8"))
        task["query"]["access_token"] = "secret"
        self.write_json(task_path, task)

        with self.assertRaisesRegex(PromotionError, "secret-like key"):
            promote_experiment(self.root, self.experiment, self.proof_run())

    def test_rejects_secret_bearing_capability_metadata(self) -> None:
        metadata_path = self.experiment / "capability.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["proxy_password"] = "do-not-copy"
        self.write_json(metadata_path, metadata)

        with self.assertRaisesRegex(PromotionError, "capability metadata.*secret-like key"):
            promote_experiment(self.root, self.experiment, self.proof_run())

    def test_rejects_incomplete_portable_proof_fields_without_mutation(self) -> None:
        cases = [
            ({"run_id": ""}, None, "run_id"),
            ({"completed_at": ""}, None, "completed_at"),
            ({"records": 0}, None, "records"),
            ({"completeness": ""}, None, "completeness"),
            (None, {"route": ""}, "route"),
            (None, {"backend": ""}, "backend"),
            (None, {"source_exhausted": "yes"}, "source_exhausted"),
        ]
        registry_before = (self.root / "platforms" / "registry.json").read_bytes()

        for run_overrides, collector_overrides, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                PromotionError, message
            ):
                promote_experiment(
                    self.root,
                    self.experiment,
                    self.proof_run(
                        run_overrides=run_overrides,
                        collector_result_overrides=collector_overrides,
                    ),
                )
            self.assertFalse((self.root / "platforms" / "demo").exists())
            self.assertEqual(
                (self.root / "platforms" / "registry.json").read_bytes(),
                registry_before,
            )

    def test_rejects_proof_with_validation_errors_without_mutation(self) -> None:
        proof = self.proof_run()
        validation_path = proof / "validation.json"
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        validation["errors"] = ["inconsistent passed report"]
        self.write_json(validation_path, validation)
        registry_before = (self.root / "platforms" / "registry.json").read_bytes()

        with self.assertRaisesRegex(PromotionError, "validation errors"):
            promote_experiment(self.root, self.experiment, proof)

        self.assertFalse((self.root / "platforms" / "demo").exists())
        self.assertEqual(
            (self.root / "platforms" / "registry.json").read_bytes(),
            registry_before,
        )


class ProofRefreshTests(unittest.TestCase):
    write_json = staticmethod(PromotionTests.write_json)
    proof_run = PromotionTests.proof_run

    def setUp(self) -> None:
        PromotionTests.setUp(self)
        promoted = promote_experiment(self.root, self.experiment, self.proof_run())
        self.target_dir = promoted.target_dir
        self.registered_collector = self.target_dir / "collector.py"
        self.proof_path = self.target_dir / "proof.json"
        self.proof_path.write_text('{"stale":true}\n', encoding="utf-8")
        self.registered_run = self.root / "runs" / "registered_run"
        self.registered_run.mkdir()
        self.write_json(
            self.registered_run / "run.json",
            {
                "schema_version": 1,
                "run_id": "20260817T000000Z_registered",
                "selector": "demo/items",
                "status": "completed",
                "entrypoint": str(self.registered_collector.resolve()),
                "collector_sha256": hashlib.sha256(
                    self.registered_collector.read_bytes()
                ).hexdigest(),
                "completeness": "complete",
                "records": 1,
                "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            },
        )
        self.write_json(
            self.registered_run / "validation.json",
            {
                "passed": True,
                "required_fields": ["id", "title"],
                "unique_key": "id",
                "errors": [],
            },
        )
        self.write_json(
            self.registered_run / "collector_result.json",
            {
                "source_exhausted": True,
                "route": "http",
                "backend": "requests",
            },
        )

    def tearDown(self) -> None:
        PromotionTests.tearDown(self)

    def test_refresh_replaces_only_portable_proof(self) -> None:
        registry_before = (self.root / "platforms" / "registry.json").read_bytes()
        collector_before = self.registered_collector.read_bytes()
        capability_before = (self.target_dir / "capability.json").read_bytes()

        outcome = refresh_capability_proof(
            self.root, "demo/items", self.registered_run
        )

        self.assertEqual(outcome.selector, "demo/items")
        self.assertEqual(outcome.proof_path, self.proof_path.resolve())
        self.assertEqual(outcome.source_run_id, "20260817T000000Z_registered")
        self.assertEqual(outcome.proof_status, "verified")
        proof = json.loads(self.proof_path.read_text(encoding="utf-8"))
        self.assertEqual(proof["source_run_id"], outcome.source_run_id)
        self.assertEqual(
            proof["collector_sha256"],
            hashlib.sha256(self.registered_collector.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            (self.root / "platforms" / "registry.json").read_bytes(), registry_before
        )
        self.assertEqual(self.registered_collector.read_bytes(), collector_before)
        self.assertEqual(
            (self.target_dir / "capability.json").read_bytes(), capability_before
        )

    def test_refresh_rejects_contract_mismatches(self) -> None:
        cases = [
            ("selector", {"selector": "other/items"}, None),
            ("different collector", {"entrypoint": str(self.root / "other.py")}, None),
            ("collector_sha256", {"collector_sha256": "0" * 64}, None),
            ("completed", {"status": "partial"}, None),
            ("unique_key", None, {"unique_key": "other"}),
            ("required_fields", None, {"required_fields": ["id"]}),
            ("passed", None, {"passed": False}),
        ]
        original_proof = self.proof_path.read_bytes()
        for message, run_overrides, validation_overrides in cases:
            run_path = self.registered_run / "run.json"
            validation_path = self.registered_run / "validation.json"
            original_run = json.loads(run_path.read_text(encoding="utf-8"))
            original_validation = json.loads(
                validation_path.read_text(encoding="utf-8")
            )
            changed_run = dict(original_run)
            changed_validation = dict(original_validation)
            if run_overrides:
                changed_run.update(run_overrides)
            if validation_overrides:
                changed_validation.update(validation_overrides)
            self.write_json(run_path, changed_run)
            self.write_json(validation_path, changed_validation)
            with self.subTest(message=message), self.assertRaisesRegex(
                PromotionError, message
            ):
                refresh_capability_proof(
                    self.root, "demo/items", self.registered_run
                )
            self.assertEqual(self.proof_path.read_bytes(), original_proof)
            self.write_json(run_path, original_run)
            self.write_json(validation_path, original_validation)

    def test_refresh_rejects_run_outside_workspace_runs(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()

        with self.assertRaisesRegex(PromotionError, "runs"):
            refresh_capability_proof(self.root, "demo/items", outside)

    def test_refresh_rejects_expired_run_without_replacing_proof(self) -> None:
        run_path = self.registered_run / "run.json"
        run_payload = json.loads(run_path.read_text(encoding="utf-8"))
        run_payload["completed_at"] = "2020-01-01T00:00:00Z"
        self.write_json(run_path, run_payload)
        proof_before = self.proof_path.read_bytes()

        with self.assertRaisesRegex(PromotionError, "verification TTL"):
            refresh_capability_proof(self.root, "demo/items", self.registered_run)

        self.assertEqual(self.proof_path.read_bytes(), proof_before)


if __name__ == "__main__":
    unittest.main()
