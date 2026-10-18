from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from spider_core.runner import RunError, run_collector


COLLECTOR_SOURCE = r'''
import argparse
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--task", required=True, type=Path)
parser.add_argument("--output-dir", required=True, type=Path)
args = parser.parse_args()
task = json.loads(args.task.read_text(encoding="utf-8"))
args.output_dir.mkdir(parents=True, exist_ok=True)
rows = task.get("query", {}).get("rows", [])
with (args.output_dir / "normalized.jsonl").open("w", encoding="utf-8") as handle:
    for row in rows:
        if isinstance(row, str) and row.startswith("RAW:"):
            handle.write(row.removeprefix("RAW:") + "\n")
        else:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
result = task.get("query", {}).get("collector_result")
if result is not None:
    (args.output_dir / "collector_result.json").write_text(
        json.dumps(result), encoding="utf-8"
    )
print("collector stdout")
if task.get("query", {}).get("echo_unicode"):
    print("中文标准输出")
    print("中文错误输出", file=sys.stderr)
if task.get("query", {}).get("echo_secret"):
    print(task["query"].get("api_token", ""))
    print(task["query"].get("api_token", ""), file=sys.stderr)
sys.exit(int(task.get("query", {}).get("exit_code", 0)))
'''


class RunnerTests(unittest.TestCase):
    def test_candidate_exhaustion_preserves_valid_partial_data(self) -> None:
        payload = self.task_for(
            [{"id": "1", "title": "saved"}],
            collector_result={"source_exhausted": False, "route": "http", "backend": "requests", "status": "partial"},
        )
        payload["query"]["exit_code"] = 1
        outcome = run_collector(self.root, self.collector, self.write_task(payload))
        self.assertEqual((outcome.status, outcome.completeness, outcome.records), ("partial", "partial", 1))

    def test_partial_signal_does_not_hide_invalid_rows(self) -> None:
        payload = self.task_for(
            [{"id": "1"}],
            collector_result={"source_exhausted": False, "route": "http", "backend": "requests", "status": "partial"},
        )
        payload["query"]["exit_code"] = 1
        outcome = run_collector(self.root, self.collector, self.write_task(payload))
        self.assertEqual(outcome.status, "failed")

    def test_runtime_captcha_preserves_progress_and_marks_run_paused(self) -> None:
        payload = self.task_for(
            [{"id": "1", "title": "saved"}],
            collector_result={"source_exhausted": False, "route": "http", "backend": "requests",
                              "captcha_confirmed": True, "status": "stopped"},
        )
        payload["query"]["exit_code"] = 3
        outcome = run_collector(self.root, self.collector, self.write_task(payload))
        metadata = json.loads((outcome.run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome.status, "paused")
        self.assertEqual(outcome.completeness, "partial")
        self.assertEqual(outcome.records, 1)
        self.assertEqual(metadata["stop_reason"], "captcha_user_instruction_required")
        self.assertFalse(metadata["captcha_permission_granted"])

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "runs").mkdir()
        self.collector = self.root / "collector.py"
        self.collector.write_text(textwrap.dedent(COLLECTOR_SOURCE), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_task(self, payload: dict[str, object]) -> Path:
        path = self.root / "task.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def task_for(
        self,
        rows: list[object],
        *,
        collector_result: dict[str, object] | None = None,
        completion: dict[str, object] | None = None,
    ) -> dict[str, object]:
        query: dict[str, object] = {"rows": rows}
        if collector_result is not None:
            query["collector_result"] = collector_result
        return {
            "query": query,
            "completion": completion or {"mode": "sample", "min_records": 1},
            "validation": {"unique_key": "id", "required_fields": ["id", "title"]},
        }

    def test_direct_sample_run_writes_evidence(self) -> None:
        task = self.write_task(
            {
                "query": {
                    "rows": [{"id": "1", "title": "one"}, {"id": "2", "title": "two"}],
                    "api_token": "do-not-store",
                    "nested": {"Cookie": "also-secret"},
                    "collector_result": {
                        "source_exhausted": False,
                        "route": "local",
                        "backend": "python",
                    },
                },
                "completion": {"mode": "sample", "min_records": 2},
                "validation": {"unique_key": "id", "required_fields": ["id", "title"]},
            }
        )

        outcome = run_collector(self.root, self.collector, task)

        self.assertEqual(outcome.status, "completed")
        self.assertEqual(outcome.completeness, "sample")
        self.assertEqual(outcome.records, 2)
        run_payload = json.loads((outcome.run_dir / "run.json").read_text(encoding="utf-8"))
        validation = json.loads(
            (outcome.run_dir / "validation.json").read_text(encoding="utf-8")
        )
        saved_task = json.loads((outcome.run_dir / "task.json").read_text(encoding="utf-8"))
        self.assertEqual(run_payload["status"], "completed")
        self.assertTrue(validation["passed"])
        self.assertEqual(saved_task["query"]["api_token"], "<redacted>")
        self.assertEqual(saved_task["query"]["nested"]["Cookie"], "<redacted>")
        self.assertEqual((outcome.run_dir / "stdout.log").read_text(encoding="utf-8").strip(), "collector stdout")

    def test_task_contract_rejects_unknown_top_level_fields(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "local",
                "backend": "python",
            },
        )
        task["completino"] = {"mode": "all"}

        with self.assertRaisesRegex(RunError, "task has unknown fields"):
            run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual(list((self.root / "runs").iterdir()), [])

    def test_validation_contract_rejects_unknown_fields(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "local",
                "backend": "python",
            },
        )
        task["validation"]["required_field"] = ["id"]  # type: ignore[index]

        with self.assertRaisesRegex(RunError, "task validation has unknown fields"):
            run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual(list((self.root / "runs").iterdir()), [])

    def test_run_records_collector_sha256(self) -> None:
        expected = hashlib.sha256(self.collector.read_bytes()).hexdigest()
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "local",
                "backend": "python",
            },
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        run_payload = json.loads(
            (outcome.run_dir / "run.json").read_text(encoding="utf-8")
        )
        self.assertRegex(run_payload["collector_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(run_payload["collector_sha256"], expected)

    def test_run_rejects_collector_changed_during_execution(self) -> None:
        self.collector.write_text(
            textwrap.dedent(
                r'''
                import argparse
                import json
                from pathlib import Path

                parser = argparse.ArgumentParser()
                parser.add_argument("--task", required=True, type=Path)
                parser.add_argument("--output-dir", required=True, type=Path)
                args = parser.parse_args()
                (args.output_dir / "normalized.jsonl").write_text(
                    json.dumps({"id": "1", "title": "one"}) + "\n",
                    encoding="utf-8",
                )
                (args.output_dir / "collector_result.json").write_text(
                    json.dumps({
                        "source_exhausted": True,
                        "route": "local",
                        "backend": "python",
                    }),
                    encoding="utf-8",
                )
                with Path(__file__).open("a", encoding="utf-8") as handle:
                    handle.write("\n# changed during execution\n")
                '''
            ),
            encoding="utf-8",
        )
        initial_hash = hashlib.sha256(self.collector.read_bytes()).hexdigest()
        task = self.task_for([{"id": "1", "title": "one"}])

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        run_payload = json.loads(
            (outcome.run_dir / "run.json").read_text(encoding="utf-8")
        )
        validation = json.loads(
            (outcome.run_dir / "validation.json").read_text(encoding="utf-8")
        )
        self.assertEqual(outcome.status, "failed")
        self.assertEqual(run_payload["collector_sha256"], initial_hash)
        self.assertIn("collector changed during execution", validation["errors"])

    def test_run_scrubs_dynamic_secrets_before_validation(self) -> None:
        secret = "runtime-only-secret-789"
        self.collector.write_text(
            textwrap.dedent(
                f'''
                import argparse
                import json
                from pathlib import Path

                parser = argparse.ArgumentParser()
                parser.add_argument("--task", required=True, type=Path)
                parser.add_argument("--output-dir", required=True, type=Path)
                args = parser.parse_args()
                raw = args.output_dir / "raw"
                raw.mkdir()
                (raw / "page.json").write_text(
                    json.dumps({{"access_token": "{secret}"}}), encoding="utf-8"
                )
                (args.output_dir / "normalized.jsonl").write_text(
                    json.dumps({{"id": "1", "title": "one"}}) + "\\n",
                    encoding="utf-8",
                )
                (args.output_dir / "collector_result.json").write_text(
                    json.dumps({{
                        "source_exhausted": True,
                        "route": "http",
                        "backend": "requests",
                        "dynamic_token": "{secret}",
                    }}),
                    encoding="utf-8",
                )
                print("Authorization: Bearer {secret}")
                '''
            ),
            encoding="utf-8",
        )
        task = self.task_for([{"id": "unused", "title": "unused"}])

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        validation = json.loads(
            (outcome.run_dir / "validation.json").read_text(encoding="utf-8")
        )
        self.assertEqual(outcome.status, "completed")
        self.assertTrue(validation["evidence_safety"]["passed"])
        self.assertGreater(validation["evidence_safety"]["redactions"], 0)
        all_evidence = "\n".join(
            path.read_text(encoding="utf-8")
            for path in outcome.run_dir.rglob("*")
            if path.is_file() and path.suffix in {".json", ".jsonl", ".log"}
        )
        self.assertNotIn(secret, all_evidence)
        self.assertEqual(
            validation["collector_result"]["dynamic_token"], "<redacted>"
        )

    def test_invalid_jsonl_fails_validation(self) -> None:
        task = self.task_for(
            ["RAW:{broken-json"],
            collector_result={"source_exhausted": False, "route": "local", "backend": "python"},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        validation = json.loads((outcome.run_dir / "validation.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome.status, "failed")
        self.assertFalse(validation["passed"])
        self.assertTrue(any("invalid JSON" in error for error in validation["errors"]))

    def test_non_object_row_fails_validation(self) -> None:
        task = self.task_for(
            ["RAW:[1, 2]"],
            collector_result={"source_exhausted": False, "route": "local", "backend": "python"},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        validation = json.loads((outcome.run_dir / "validation.json").read_text(encoding="utf-8"))
        self.assertTrue(any("row must be a JSON object" in error for error in validation["errors"]))

    def test_missing_fields_and_blank_unique_key_fail_validation(self) -> None:
        task = self.task_for(
            [{"id": "", "title": ""}, {"id": "2"}],
            collector_result={"source_exhausted": False, "route": "local", "backend": "python"},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        validation = json.loads((outcome.run_dir / "validation.json").read_text(encoding="utf-8"))
        self.assertFalse(validation["passed"])
        self.assertTrue(any("unique key is blank" in error for error in validation["errors"]))
        self.assertGreaterEqual(
            sum("required field is blank" in error for error in validation["errors"]), 2
        )

    def test_duplicate_unique_key_fails_validation(self) -> None:
        task = self.task_for(
            [{"id": "same", "title": "one"}, {"id": "same", "title": "two"}],
            collector_result={"source_exhausted": False, "route": "local", "backend": "python"},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        validation = json.loads((outcome.run_dir / "validation.json").read_text(encoding="utf-8"))
        self.assertTrue(any("duplicate unique key" in error for error in validation["errors"]))

    def test_missing_collector_result_fails_validation(self) -> None:
        task = self.task_for([{"id": "1", "title": "one"}])

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        validation = json.loads((outcome.run_dir / "validation.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome.status, "failed")
        self.assertTrue(any("collector_result.json is missing" in error for error in validation["errors"]))

    def test_nonzero_collector_exit_is_preserved_as_failure(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": False, "route": "local", "backend": "python"},
        )
        task["query"]["exit_code"] = 7  # type: ignore[index]

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        run_payload = json.loads((outcome.run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome.status, "failed")
        self.assertEqual(run_payload["collector_exit_code"], 7)

    def test_all_mode_is_complete_when_external_expected_total_matches(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}, {"id": "2", "title": "two"}],
            collector_result={"source_exhausted": False, "route": "http", "backend": "requests"},
            completion={"mode": "all", "expected_total": 2},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual((outcome.status, outcome.completeness), ("completed", "complete"))

    def test_all_mode_is_complete_when_collector_exhausts_source(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": True, "route": "http", "backend": "requests"},
            completion={"mode": "all"},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual((outcome.status, outcome.completeness), ("completed", "complete"))

    def test_all_mode_without_coverage_proof_stays_unknown(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": False, "route": "http", "backend": "requests"},
            completion={"mode": "all"},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        run_payload = json.loads((outcome.run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertEqual((outcome.status, outcome.completeness), ("partial", "unknown"))
        self.assertNotIn("expected_total", run_payload)

    def test_all_mode_below_expected_total_is_partial(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": False, "route": "http", "backend": "requests"},
            completion={"mode": "all", "expected_total": 2},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual((outcome.status, outcome.completeness), ("partial", "partial"))

    def test_at_least_mode_can_finish_without_claiming_full_coverage(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}, {"id": "2", "title": "two"}],
            collector_result={"source_exhausted": False, "route": "http", "backend": "requests"},
            completion={"mode": "at_least", "min_records": 2},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual((outcome.status, outcome.completeness), ("completed", "partial"))

    def test_sample_below_minimum_is_partial_and_stays_sample_labelled(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": False, "route": "http", "backend": "requests"},
            completion={"mode": "sample", "min_records": 2},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual((outcome.status, outcome.completeness), ("partial", "sample"))

    def test_completion_contract_rejects_unknown_fields(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": False,
                "route": "local",
                "backend": "python",
            },
            completion={"mode": "sample", "minimum": 1},
        )

        with self.assertRaisesRegex(RunError, "task completion has unknown fields"):
            run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual(list((self.root / "runs").iterdir()), [])

    def test_collector_result_requires_boolean_exhaustion_and_route_backend(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": "yes", "route": "", "backend": 1},
        )

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        validation = json.loads((outcome.run_dir / "validation.json").read_text(encoding="utf-8"))
        self.assertFalse(validation["passed"])
        self.assertGreaterEqual(len(validation["errors"]), 3)

    def test_known_task_secrets_are_removed_from_standard_evidence(self) -> None:
        secret = "token-value-that-must-not-persist"
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": False,
                "route": "local",
                "backend": "python",
                "access_token": secret,
                "message": f"collector saw {secret}",
            },
        )
        task["query"]["api_token"] = secret  # type: ignore[index]
        task["query"]["echo_secret"] = True  # type: ignore[index]

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        for name in (
            "task.json",
            "collector_result.json",
            "validation.json",
            "run.json",
            "stdout.log",
            "stderr.log",
            "normalized.jsonl",
        ):
            self.assertNotIn(
                secret,
                (outcome.run_dir / name).read_text(encoding="utf-8"),
                name,
            )

    def test_subprocess_logs_use_utf8_on_windows(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": False,
                "route": "local",
                "backend": "python",
            },
        )
        task["query"]["echo_unicode"] = True  # type: ignore[index]

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        self.assertIn(
            "中文标准输出",
            (outcome.run_dir / "stdout.log").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "中文错误输出",
            (outcome.run_dir / "stderr.log").read_text(encoding="utf-8"),
        )

    def test_browser_task_ensures_workspace_chrome_and_writes_diagnostic(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": False,
                "route": "browser_context",
                "backend": "chrome_cdp",
            },
        )
        task["browser"] = {"ensure": True}
        calls: list[Path] = []
        safe_result = {
            "status": "ready",
            "candidate": "chrome",
            "action": "reused",
            "cdp_url": "http://127.0.0.1:9222",
            "browser": "Chrome/151.0.7922.137",
            "protocol_version": "1.3",
            "page_targets": 1,
        }

        outcome = run_collector(
            self.root,
            self.collector,
            self.write_task(task),
            browser_ensurer=lambda workspace: calls.append(workspace) or safe_result,
        )

        self.assertEqual(calls, [self.root.resolve()])
        self.assertEqual(
            json.loads((outcome.run_dir / "browser.json").read_text(encoding="utf-8")),
            safe_result,
        )
        self.assertEqual(outcome.status, "completed")

    def test_browser_task_accepts_cloak_loopback_aliases(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": False, "route": "browser_context", "backend": "chrome_cdp"},
        )
        task["browser"] = {"ensure": True}
        task_path = self.write_task(task)
        for url in ("http://localhost:9232", "http://[::1]:9232"):
            with self.subTest(url=url):
                safe_result = {
                    "status": "ready", "candidate": "cloak", "action": "reused",
                    "cdp_url": url, "browser": "Chrome/142.0.7444.175",
                    "protocol_version": "1.3", "page_targets": 1,
                }
                outcome = run_collector(self.root, self.collector, task_path, browser_ensurer=lambda _: safe_result)
                self.assertEqual(outcome.status, "completed")
                self.assertEqual(json.loads((outcome.run_dir / "browser.json").read_text(encoding="utf-8")), safe_result)

    def test_browser_task_accepts_cloak_and_rejects_mismatched_endpoint(self) -> None:
        safe_result = {
            "status": "ready", "candidate": "cloak", "action": "reused",
            "cdp_url": "http://127.0.0.1:9232", "browser": "Chrome/142.0.7444.175",
            "protocol_version": "1.3", "page_targets": 1,
        }
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": False, "route": "browser_context", "backend": "chrome_cdp"},
        )
        task["browser"] = {"ensure": True}
        task_path = self.write_task(task)
        outcome = run_collector(self.root, self.collector, task_path, browser_ensurer=lambda _: safe_result)
        self.assertEqual(outcome.status, "completed")
        self.assertEqual(json.loads((outcome.run_dir / "browser.json").read_text(encoding="utf-8")), safe_result)
        for url in ("http://127.0.0.1:9222", "http://127.0.0.1:9333", "http://0.0.0.0:9232",
                    "http://localhost:9222", "http://user@localhost:9232", "http://localhost:9232/json"):
            with self.subTest(url=url), self.assertRaisesRegex(RunError, "invalid result"):
                run_collector(self.root, self.collector, task_path, browser_ensurer=lambda _: {**safe_result, "cdp_url": url})

    def test_plain_task_never_starts_browser(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": False,
                "route": "http",
                "backend": "requests",
            },
        )

        outcome = run_collector(
            self.root,
            self.collector,
            self.write_task(task),
            browser_ensurer=lambda _: self.fail("plain task must not ensure Chrome"),
        )

        self.assertFalse((outcome.run_dir / "browser.json").exists())

    def test_ready_protocol_session_does_not_require_browser(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": True, "route": "http", "backend": "httpx"},
        )
        task["routing_evidence"] = {
            "protocol_ready": True, "requires_login": True,
            "reuse_existing_chrome": True, "requires_interaction": True,
        }
        outcome = run_collector(
            self.root, self.collector, self.write_task(task),
            browser_ensurer=lambda _: self.fail("ready protocol must run without Chrome"),
        )
        self.assertEqual(outcome.status, "completed")
        self.assertFalse((outcome.run_dir / "browser.json").exists())
        run = json.loads((outcome.run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertFalse(run["route_preference"]["preference_applied"])
        self.assertTrue(run["route_preference"]["protocol_preference_applied"])

    def test_explicit_reconnaissance_still_ensures_browser_when_protocol_ready(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": True, "route": "http", "backend": "node_fetch"},
        )
        task["routing_evidence"] = {"protocol_ready": True, "requires_login": True}
        task["browser"] = {"ensure": True}
        calls = []
        safe_result = {
            "status": "ready", "candidate": "chrome", "action": "reused",
            "cdp_url": "http://127.0.0.1:9222", "browser": "Chrome/test",
            "protocol_version": "1.3", "page_targets": 1,
        }
        outcome = run_collector(
            self.root, self.collector, self.write_task(task),
            browser_ensurer=lambda workspace: calls.append(workspace) or safe_result,
        )
        self.assertEqual(calls, [self.root.resolve()])
        self.assertTrue((outcome.run_dir / "browser.json").is_file())
        run = json.loads((outcome.run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertTrue(run["route_preference"]["protocol_preference_applied"])

    def test_browser_fallback_reason_is_preserved_in_route_evidence(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True, "route": "browser_context", "backend": "chrome_cdp",
                "browser_fallback_reason": "detail fields require browser interaction",
            },
        )
        task["routing_evidence"] = {"stable_api": True}
        outcome = run_collector(self.root, self.collector, self.write_task(task))
        run = json.loads((outcome.run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertFalse(run["route_preference"]["protocol_preference_applied"])
        self.assertEqual(run["route_preference"]["browser_fallback_reason"],
                         "detail fields require browser interaction")

    def test_html_protocol_backend_counts_as_protocol_preference(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={"source_exhausted": True, "route": "html", "backend": "httpx"},
        )
        task["routing_evidence"] = {}
        outcome = run_collector(self.root, self.collector, self.write_task(task))
        run = json.loads((outcome.run_dir / "run.json").read_text(encoding="utf-8"))
        self.assertTrue(run["route_preference"]["protocol_preference_applied"])

    def test_session_routing_evidence_automatically_ensures_workspace_chrome(self) -> None:
        safe_result = {
            "status": "ready",
            "candidate": "chrome",
            "action": "reused",
            "cdp_url": "http://127.0.0.1:9222",
            "browser": "Chrome/test",
            "protocol_version": "1.3",
            "page_targets": 1,
        }
        for field in (
            "requires_login",
            "requires_interaction",
            "reuse_existing_chrome",
        ):
            with self.subTest(field=field):
                task = self.task_for(
                    [{"id": "1", "title": "one"}],
                    collector_result={
                        "source_exhausted": False,
                        "route": "browser_context",
                        "backend": "chrome_cdp",
                    },
                )
                task["routing_evidence"] = {field: True}
                calls: list[Path] = []

                outcome = run_collector(
                    self.root,
                    self.collector,
                    self.write_task(task),
                    browser_ensurer=lambda workspace: calls.append(workspace)
                    or safe_result,
                )

                self.assertEqual(calls, [self.root.resolve()])
                self.assertTrue((outcome.run_dir / "browser.json").is_file())

    def test_non_session_routing_evidence_never_starts_workspace_chrome(self) -> None:
        for field in ("stable_api", "requires_javascript", "has_signature"):
            with self.subTest(field=field):
                task = self.task_for(
                    [{"id": "1", "title": "one"}],
                    collector_result={
                        "source_exhausted": False,
                        "route": "local",
                        "backend": "python",
                    },
                )
                task["routing_evidence"] = {field: True}

                outcome = run_collector(
                    self.root,
                    self.collector,
                    self.write_task(task),
                    browser_ensurer=lambda _: self.fail(
                        f"{field} must not ensure workspace Chrome"
                    ),
                )

                self.assertFalse((outcome.run_dir / "browser.json").exists())

    def test_captcha_task_waits_for_user_before_browser_or_collector(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "reverse",
                "backend": "python_node_http",
            },
        )
        task["routing_evidence"] = {
            "requires_login": True,
            "captcha_present": True,
            "authorized_captcha_research": True,
        }

        with (
            patch("spider_core.runner.subprocess.run") as process,
            self.assertRaisesRegex(
                RunError,
                "captcha_user_instruction_required.*--allow-captcha",
            ),
        ):
            run_collector(
                self.root,
                self.collector,
                self.write_task(task),
                browser_ensurer=lambda _: self.fail(
                    "captcha pause must happen before browser preflight"
                ),
            )

        process.assert_not_called()
        run_dirs = list((self.root / "runs").iterdir())
        self.assertEqual(len(run_dirs), 1)
        run_dir = run_dirs[0]
        run_payload = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        saved_task = json.loads((run_dir / "task.json").read_text(encoding="utf-8"))
        route = json.loads(
            (run_dir / "route_decision.json").read_text(encoding="utf-8")
        )
        self.assertEqual(run_payload["status"], "paused")
        self.assertEqual(run_payload["stop_reason"], "captcha_user_instruction_required")
        self.assertFalse(run_payload["captcha_permission_granted"])
        self.assertFalse(route["captcha_permission_granted"])
        self.assertTrue(saved_task["routing_evidence"]["captcha_present"])
        self.assertFalse((run_dir / "browser.json").exists())
        self.assertFalse((run_dir / "normalized.jsonl").exists())

    def test_captcha_permission_applies_to_one_run_invocation(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "reverse",
                "backend": "python_node_http",
            },
        )
        task["routing_evidence"] = {
            "captcha_present": True,
            "authorized_captcha_research": True,
        }

        outcome = run_collector(
            self.root,
            self.collector,
            self.write_task(task),
            allow_captcha=True,
        )

        self.assertEqual(outcome.status, "completed")
        run_payload = json.loads(
            (outcome.run_dir / "run.json").read_text(encoding="utf-8")
        )
        route = json.loads(
            (outcome.run_dir / "route_decision.json").read_text(encoding="utf-8")
        )
        saved_task = json.loads(
            (outcome.run_dir / "task.json").read_text(encoding="utf-8")
        )
        self.assertTrue(run_payload["captcha_permission_granted"])
        self.assertTrue(route["captcha_permission_granted"])
        self.assertNotIn("allow_captcha", json.dumps(saved_task))

    def test_runner_replaces_ambient_captcha_permission_per_invocation(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "local",
                "backend": "python",
            },
        )
        observed_permissions: list[str | None] = []

        def fake_run(command: list[str], **kwargs: object):
            environment = kwargs["env"]
            assert isinstance(environment, dict)
            observed_permissions.append(environment.get("SPIDER_CAPTCHA_PERMISSION"))
            output_dir = Path(command[-1])
            (output_dir / "normalized.jsonl").write_text(
                json.dumps({"id": "1", "title": "one"}) + "\n",
                encoding="utf-8",
            )
            (output_dir / "collector_result.json").write_text(
                json.dumps(
                    {
                        "source_exhausted": True,
                        "route": "local",
                        "backend": "python",
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with (
            patch.dict(
                "os.environ",
                {"SPIDER_CAPTCHA_PERMISSION": "allow_once_v1"},
                clear=False,
            ),
            patch("spider_core.runner.subprocess.run", side_effect=fake_run),
        ):
            run_collector(self.root, self.collector, self.write_task(task))
            run_collector(
                self.root,
                self.collector,
                self.write_task(task),
                allow_captcha=True,
            )

        self.assertEqual(observed_permissions, [None, "allow_once_v1"])

    def test_false_browser_override_does_not_suppress_session_evidence(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": False,
                "route": "browser_context",
                "backend": "chrome_cdp",
            },
        )
        task["browser"] = {"ensure": False}
        task["routing_evidence"] = {"requires_login": True}
        calls: list[Path] = []

        run_collector(
            self.root,
            self.collector,
            self.write_task(task),
            browser_ensurer=lambda workspace: calls.append(workspace)
            or {
                "status": "ready",
                "candidate": "chrome",
                "action": "reused",
                "cdp_url": "http://127.0.0.1:9222",
                "browser": "Chrome/test",
                "protocol_version": "1.3",
                "page_targets": 1,
            },
        )

        self.assertEqual(calls, [self.root.resolve()])

    def test_routing_evidence_writes_decision_and_records_applied_preference(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "http",
                "backend": "requests",
            },
            completion={"mode": "all"},
        )
        task["routing_evidence"] = {"stable_api": True}

        outcome = run_collector(self.root, self.collector, self.write_task(task))

        decision = json.loads(
            (outcome.run_dir / "route_decision.json").read_text(encoding="utf-8")
        )
        validation = json.loads(
            (outcome.run_dir / "validation.json").read_text(encoding="utf-8")
        )
        run_payload = json.loads(
            (outcome.run_dir / "run.json").read_text(encoding="utf-8")
        )
        self.assertEqual(decision["schema_version"], 1)
        self.assertTrue(decision["evidence"]["stable_api"])
        self.assertEqual(decision["decision"]["route"], "http")
        self.assertEqual(decision["decision"]["backend"], "requests")
        self.assertTrue(validation["route_preference"]["preference_applied"])
        self.assertTrue(run_payload["route_preference"]["preference_applied"])

    def test_invalid_routing_evidence_fails_before_creating_run(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "http",
                "backend": "requests",
            },
        )
        task["routing_evidence"] = {"stable_api": "yes"}

        with self.assertRaisesRegex(RunError, "stable_api must be boolean"):
            run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual(list((self.root / "runs").iterdir()), [])

    def test_invalid_execution_contract_fails_before_creating_run(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "http",
                "backend": "requests",
            },
        )
        task["execution"] = {"timeout_seconds": 0}

        with self.assertRaisesRegex(
            RunError, "execution.timeout_seconds must be an integer from 1 to 86400"
        ):
            run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual(list((self.root / "runs").iterdir()), [])

    def test_invalid_execution_contract_is_not_hidden_by_captcha_pause(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "reverse",
                "backend": "python_node_http",
            },
        )
        task["routing_evidence"] = {"captcha_present": True}
        task["execution"] = {"unexpected": 1}

        with self.assertRaisesRegex(RunError, "task execution has unknown fields"):
            run_collector(self.root, self.collector, self.write_task(task))

        self.assertEqual(list((self.root / "runs").iterdir()), [])

    def test_collector_timeout_preserves_partial_evidence_and_never_completes(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": True,
                "route": "http",
                "backend": "requests",
            },
            completion={"mode": "all"},
        )
        task["execution"] = {"timeout_seconds": 2}

        def time_out(command: list[str], **kwargs: object) -> None:
            output_dir = Path(command[command.index("--output-dir") + 1])
            (output_dir / "normalized.jsonl").write_text(
                '{"id":"partial","title":"saved"}\n', encoding="utf-8"
            )
            (output_dir / "collector_result.json").write_text(
                json.dumps(
                    {
                        "source_exhausted": False,
                        "route": "http",
                        "backend": "requests",
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(kwargs["timeout"], 2)
            raise subprocess.TimeoutExpired(
                command,
                timeout=2,
                output="partial-out",
                stderr="partial-err",
            )

        with patch("spider_core.runner.subprocess.run", side_effect=time_out):
            outcome = run_collector(self.root, self.collector, self.write_task(task))

        run_payload = json.loads(
            (outcome.run_dir / "run.json").read_text(encoding="utf-8")
        )
        validation = json.loads(
            (outcome.run_dir / "validation.json").read_text(encoding="utf-8")
        )
        self.assertNotEqual(outcome.status, "completed")
        self.assertEqual(outcome.records, 1)
        self.assertIsNone(run_payload["collector_exit_code"])
        self.assertEqual(run_payload["stop_reason"], "collector_timeout")
        self.assertEqual(run_payload["execution_timeout_seconds"], 2)
        self.assertIn("collector timed out", validation["errors"])
        self.assertEqual(
            (outcome.run_dir / "stdout.log").read_text(encoding="utf-8"),
            "partial-out",
        )
        self.assertEqual(
            (outcome.run_dir / "stderr.log").read_text(encoding="utf-8"),
            "partial-err",
        )

    def test_invalid_browser_contract_fails_before_creating_run(self) -> None:
        task = self.task_for(
            [{"id": "1", "title": "one"}],
            collector_result={
                "source_exhausted": False,
                "route": "browser_context",
                "backend": "chrome_cdp",
            },
        )
        task["browser"] = {"ensure": "yes"}

        with self.assertRaisesRegex(RunError, "browser.ensure must be boolean"):
            run_collector(
                self.root,
                self.collector,
                self.write_task(task),
                browser_ensurer=lambda _: self.fail("invalid task must not ensure Chrome"),
            )

        self.assertEqual(list((self.root / "runs").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
