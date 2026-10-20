from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from spider_core.registry import RegistryError, find_capability, load_registry, write_registry


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_NOW = datetime(2026, 8, 17, tzinfo=timezone.utc)


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "platforms").mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_registry(self, platforms: list[dict[str, object]]) -> None:
        payload = {"schema_version": 1, "platforms": platforms}
        (self.root / "platforms" / "registry.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def valid_capability(self, **overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": "items",
            "name": "Items",
            "entrypoint": "platforms/demo/items/collector.py",
            "route": "http",
            "requires_auth": False,
            "unique_key": "id",
            "required_fields": ["id", "title"],
            "proof_run": "runs/proof",
        }
        payload.update(overrides)
        return payload

    def platform(self, capabilities: list[dict[str, object]]) -> dict[str, object]:
        return {"id": "demo", "name": "Demo", "capabilities": capabilities}

    def collector(self) -> Path:
        collector = self.root / "platforms" / "demo" / "items" / "collector.py"
        collector.parent.mkdir(parents=True, exist_ok=True)
        collector.write_text("# collector\n", encoding="utf-8")
        return collector

    def write_proof(
        self,
        collector: Path,
        *,
        overrides: dict[str, object] | None = None,
    ) -> Path:
        proof = {
            "schema_version": 1,
            "selector": "demo/items",
            "source_run_id": "proof-run",
            "verified_at": "2026-08-16T00:00:00Z",
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
                "route": "http",
                "backend": "requests",
                "source_exhausted": True,
            },
        }
        if overrides:
            proof.update(overrides)
        path = collector.parent / "proof.json"
        self.write_json(path, proof)
        return path

    @staticmethod
    def write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_valid_capability_is_loaded_while_malformed_sibling_is_skipped(self) -> None:
        collector = self.root / "platforms" / "demo" / "items" / "collector.py"
        collector.parent.mkdir(parents=True)
        collector.write_text("# collector\n", encoding="utf-8")
        malformed = self.valid_capability(name="Missing id")
        malformed.pop("id")
        self.write_registry([self.platform([self.valid_capability(), malformed])])

        view = load_registry(self.root, now=FIXTURE_NOW)

        self.assertEqual([item.selector for item in view.capabilities], ["demo/items"])
        self.assertTrue(view.capabilities[0].available)
        self.assertTrue(any("capability 2" in warning for warning in view.warnings))

    def test_missing_entrypoint_marks_only_that_capability_unavailable(self) -> None:
        self.write_registry([self.platform([self.valid_capability()])])

        view = load_registry(self.root, now=FIXTURE_NOW)

        self.assertEqual(len(view.capabilities), 1)
        self.assertFalse(view.capabilities[0].available)
        self.assertTrue(any("entrypoint is missing" in warning for warning in view.warnings))

    def test_missing_proof_run_is_warning_but_does_not_disable_collector(self) -> None:
        collector = self.root / "platforms" / "demo" / "items" / "collector.py"
        collector.parent.mkdir(parents=True)
        collector.write_text("# collector\n", encoding="utf-8")
        self.write_registry([self.platform([self.valid_capability()])])

        view = load_registry(self.root, now=FIXTURE_NOW)

        self.assertTrue(view.capabilities[0].available)
        self.assertTrue(any("proof run is missing" in warning for warning in view.warnings))

    def test_valid_portable_proof_is_verified(self) -> None:
        collector = self.collector()
        self.write_proof(collector)
        capability = self.valid_capability(
            proof="platforms/demo/items/proof.json"
        )
        capability.pop("proof_run")
        self.write_registry([self.platform([capability])])

        view = load_registry(self.root, now=FIXTURE_NOW)

        self.assertEqual(view.capabilities[0].proof_status, "verified")
        self.assertEqual(
            view.capabilities[0].proof_text,
            "platforms/demo/items/proof.json",
        )
        self.assertFalse(any("proof" in warning for warning in view.warnings))

    def test_unreadable_proof_is_local_and_healthy_capability_still_runs(self) -> None:
        from spider_core.runner import run_collector
        broken = self.collector()
        bad_proof = broken.parent / 'proof.json'
        bad_proof.write_bytes(b'\xff\xfe{broken proof}')
        healthy = self.root / 'platforms/demo/healthy/collector.py'
        healthy.parent.mkdir(parents=True)
        healthy.write_text('''import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--task');p.add_argument('--output-dir');a=p.parse_args()
out=Path(a.output_dir)
(out/'normalized.jsonl').write_text(json.dumps({'id':'1','title':'healthy'})+'\\n',encoding='utf-8')
(out/'collector_result.json').write_text(json.dumps({'route':'http','backend':'python','source_exhausted':True}),encoding='utf-8')
''', encoding='utf-8')
        good_proof = self.write_proof(healthy, overrides={'selector': 'demo/healthy',
            'verified_at': datetime.now(timezone.utc).isoformat()})
        bad = self.valid_capability(proof='platforms/demo/items/proof.json')
        good = self.valid_capability(id='healthy', entrypoint='platforms/demo/healthy/collector.py',
                                     proof='platforms/demo/healthy/proof.json')
        bad.pop('proof_run'); good.pop('proof_run')
        self.write_registry([self.platform([bad, good])])
        evidence = {path: path.read_bytes() for path in
                    (bad_proof, good_proof, self.root / 'platforms/registry.json')}
        view = load_registry(self.root)
        self.assertEqual([item.proof_status for item in view.capabilities], ['stale', 'verified'])
        self.assertTrue(all(item.available for item in view.capabilities))
        self.assertTrue(any('demo/items' in warning and 'unreadable' in warning and 'UTF-8' in warning
                            for warning in view.warnings), view.warnings)
        capability = find_capability(self.root, 'demo/healthy')
        task = self.root / 'task.json'
        self.write_json(task, {'completion': {'mode': 'all', 'expected_total': 1},
                               'validation': {'unique_key': 'id', 'required_fields': ['id', 'title']}})
        self.assertEqual(run_collector(self.root, capability.entrypoint, task,
                                      selector=capability.selector).status, 'completed')
        self.assertEqual(evidence, {path: path.read_bytes() for path in evidence})

    def test_changed_collector_makes_portable_proof_stale(self) -> None:
        collector = self.collector()
        self.write_proof(collector)
        collector.write_text("# changed collector\n", encoding="utf-8")
        capability = self.valid_capability(
            proof="platforms/demo/items/proof.json"
        )
        capability.pop("proof_run")
        self.write_registry([self.platform([capability])])

        view = load_registry(self.root, now=FIXTURE_NOW)

        self.assertTrue(view.capabilities[0].available)
        self.assertEqual(view.capabilities[0].proof_status, "stale")
        self.assertTrue(any("collector hash" in warning for warning in view.warnings))

    def test_expired_portable_proof_is_stale_but_collector_remains_available(self) -> None:
        collector = self.collector()
        self.write_proof(collector)
        capability = self.valid_capability(
            proof="platforms/demo/items/proof.json",
            verification_ttl_days=7,
        )
        capability.pop("proof_run")
        self.write_registry([self.platform([capability])])

        view = load_registry(
            self.root,
            now=datetime(2026, 8, 24, tzinfo=timezone.utc),
        )

        self.assertTrue(view.capabilities[0].available)
        self.assertEqual(view.capabilities[0].verification_ttl_days, 7)
        self.assertEqual(view.capabilities[0].proof_status, "stale")
        self.assertTrue(any("proof has expired" in warning for warning in view.warnings))

    def test_verification_ttl_defaults_to_thirty_days(self) -> None:
        collector = self.collector()
        self.write_proof(collector)
        capability = self.valid_capability(proof="platforms/demo/items/proof.json")
        capability.pop("proof_run")
        self.write_registry([self.platform([capability])])

        view = load_registry(
            self.root,
            now=datetime(2026, 8, 17, tzinfo=timezone.utc),
        )

        self.assertEqual(view.capabilities[0].verification_ttl_days, 30)
        self.assertEqual(view.capabilities[0].proof_status, "verified")

    def test_portable_proof_rejects_fields_outside_the_safe_schema(self) -> None:
        collector = self.collector()
        self.write_proof(collector, overrides={"access_token": "must-not-be-here"})
        capability = self.valid_capability(
            proof="platforms/demo/items/proof.json"
        )
        capability.pop("proof_run")
        self.write_registry([self.platform([capability])])

        view = load_registry(self.root, now=FIXTURE_NOW)

        self.assertEqual(view.capabilities[0].proof_status, "stale")
        self.assertTrue(any("schema" in warning for warning in view.warnings))

    def test_missing_or_malformed_portable_proof_is_reported(self) -> None:
        collector = self.collector()
        capability = self.valid_capability(
            proof="platforms/demo/items/proof.json"
        )
        capability.pop("proof_run")
        self.write_registry([self.platform([capability])])

        missing = load_registry(self.root, now=FIXTURE_NOW)

        self.assertEqual(missing.capabilities[0].proof_status, "missing")
        self.assertTrue(any("proof is missing" in warning for warning in missing.warnings))

        (collector.parent / "proof.json").write_text("[]", encoding="utf-8")
        malformed = load_registry(self.root, now=FIXTURE_NOW)

        self.assertEqual(malformed.capabilities[0].proof_status, "stale")
        self.assertTrue(any("proof is invalid" in warning for warning in malformed.warnings))

    def test_legacy_and_absent_proof_states_remain_distinct(self) -> None:
        self.collector()
        (self.root / "runs" / "proof").mkdir(parents=True)
        self.write_registry([self.platform([self.valid_capability()])])

        legacy = load_registry(self.root, now=FIXTURE_NOW)

        self.assertEqual(legacy.capabilities[0].proof_status, "legacy")

        capability = self.valid_capability()
        capability.pop("proof_run")
        self.write_registry([self.platform([capability])])
        missing = load_registry(self.root, now=FIXTURE_NOW)

        self.assertEqual(missing.capabilities[0].proof_status, "missing")
        self.assertTrue(any("proof evidence is missing" in warning for warning in missing.warnings))

    def test_find_capability_reports_focused_selector_errors(self) -> None:
        self.write_registry([self.platform([])])

        with self.assertRaisesRegex(RegistryError, "expected platform/capability"):
            find_capability(self.root, "demo")
        with self.assertRaisesRegex(RegistryError, "not registered: demo/items"):
            find_capability(self.root, "demo/items")

    def test_malformed_top_level_document_is_a_registry_error(self) -> None:
        (self.root / "platforms" / "registry.json").write_text("[]", encoding="utf-8")

        with self.assertRaisesRegex(RegistryError, "top-level JSON object"):
            load_registry(self.root, now=FIXTURE_NOW)

    def test_write_registry_replaces_the_document(self) -> None:
        self.write_registry([])
        replacement = {"schema_version": 1, "platforms": [self.platform([])]}

        write_registry(self.root, replacement)

        saved = json.loads(
            (self.root / "platforms" / "registry.json").read_text(encoding="utf-8")
        )
        self.assertEqual(saved, replacement)
        self.assertFalse((self.root / "platforms" / "registry.json.tmp").exists())




if __name__ == "__main__":
    unittest.main()
