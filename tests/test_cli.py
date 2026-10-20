from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

import spider
from spider_core.experiments import Experiment, ExperimentView


SOURCE_ROOT = Path(__file__).resolve().parents[1]

COLLECTOR = r'''
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--task", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()
task = json.loads(args.task.read_text(encoding="utf-8"))
rows = task["query"]["rows"]
args.output_dir.mkdir(parents=True, exist_ok=True)
with (args.output_dir / "normalized.jsonl").open("w", encoding="utf-8") as handle:
    for row in rows:
        handle.write(json.dumps(row) + "\n")
(args.output_dir / "collector_result.json").write_text(
    json.dumps({"source_exhausted": True, "route": "local", "backend": "python"}),
    encoding="utf-8",
)
'''


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        shutil.copy2(SOURCE_ROOT / "spider.py", self.root / "spider.py")
        shutil.copytree(SOURCE_ROOT / "spider_core", self.root / "spider_core")
        (self.root / "platforms").mkdir()
        (self.root / "experiments").mkdir()
        (self.root / "runs").mkdir()
        self.write_json(
            self.root / "platforms" / "registry.json",
            {"schema_version": 1, "platforms": []},
        )
        self.write_json(self.root / "config/workspace_browser.json", {
            "schema_version": 2, "default_candidate": "chrome",
            "candidates": {name: {
                "executable": str(self.root / name / "browser.exe"),
                "user_data_dir": str(self.root / "tmp" / name),
                "cdp_url": f"http://127.0.0.1:{port}",
                "startup_timeout_seconds": 10, "launch_args": [], "environment": {},
            } for name, port in (("chrome", 9222),)}
        })

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.root / "spider.py"), *arguments],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

    def create_experiment(self) -> tuple[Path, Path]:
        experiment = self.root / "experiments" / "demo_items"
        experiment.mkdir()
        (experiment / "collector.py").write_text(
            textwrap.dedent(COLLECTOR), encoding="utf-8"
        )
        task = {
            "query": {"rows": [{"id": "1", "title": "one"}]},
            "completion": {"mode": "all", "expected_total": 1},
            "validation": {"unique_key": "id", "required_fields": ["id", "title"]},
        }
        task_path = experiment / "task.example.json"
        self.write_json(task_path, task)
        self.write_json(
            experiment / "capability.json",
            {
                "platform_id": "demo",
                "platform_name": "Demo",
                "id": "items",
                "name": "Items",
                "route": "local",
                "requires_auth": False,
                "unique_key": "id",
                "required_fields": ["id", "title"],
            },
        )
        return experiment, task_path

    def create_comparison_runs(self) -> tuple[Path, Path]:
        def make_run(name: str, rows: list[dict[str, object]]) -> Path:
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

        baseline = make_run(
            "baseline", [{"id": "1", "title": "one", "price": 10}]
        )
        current = make_run(
            "current", [{"id": "1", "title": "one", "price": 11}]
        )
        return baseline, current

    def invoke_main(self, arguments: list[str]):
        stdout = io.StringIO()
        stderr = io.StringIO()
        pool = spider.load_workspace_browser_configs(self.root)
        with (contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr),
              mock.patch.object(spider, "load_workspace_browser_configs", return_value=pool)):
            code = spider.main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_list_json_returns_empty_registry(self) -> None:
        result = self.run_cli("list", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["capabilities"], [])

    def test_list_json_forces_utf8_even_when_parent_requests_cp936(self) -> None:
        collector = self.root / "platforms" / "douban" / "top250" / "collector.py"
        collector.parent.mkdir(parents=True)
        collector.write_text("", encoding="utf-8")
        self.write_json(
            self.root / "platforms" / "registry.json",
            {
                "schema_version": 1,
                "platforms": [
                    {
                        "id": "demo",
                        "name": "豆瓣",
                        "capabilities": [
                            {
                                "id": "top250",
                                "name": "豆瓣电影 Top250",
                                "entrypoint": "platforms/douban/top250/collector.py",
                                "route": "html",
                                "requires_auth": False,
                                "unique_key": "movie_id",
                                "required_fields": ["movie_id"],
                                "proof_run": None,
                            }
                        ],
                    }
                ],
            },
        )
        environment = dict(os.environ)
        environment["PYTHONIOENCODING"] = "cp936"

        result = subprocess.run(
            [sys.executable, str(self.root / "spider.py"), "list", "--json"],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("\ufffd", result.stdout)
        capability = json.loads(result.stdout)["capabilities"][0]
        self.assertEqual(capability["platform_name"], "豆瓣")
        self.assertEqual(capability["name"], "豆瓣电影 Top250")
        self.assertEqual(capability["proof_status"], "missing")

        text_result = self.run_cli("list")
        self.assertEqual(text_result.returncode, 0, text_result.stderr)
        self.assertIn("\tmissing\t", text_result.stdout)

    def test_direct_path_run_outputs_machine_readable_outcome(self) -> None:
        experiment, task_path = self.create_experiment()

        result = self.run_cli(
            "run",
            str(experiment / "collector.py"),
            "--task",
            str(task_path),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["completeness"], "complete")
        self.assertTrue(Path(payload["run_dir"]).is_dir())

    def test_captcha_run_requires_one_time_cli_permission(self) -> None:
        experiment, task_path = self.create_experiment()
        task = json.loads(task_path.read_text(encoding="utf-8"))
        task["routing_evidence"] = {
            "captcha_present": True,
            "authorized_captcha_research": True,
        }
        self.write_json(task_path, task)

        paused = self.run_cli(
            "run",
            str(experiment / "collector.py"),
            "--task",
            str(task_path),
        )

        self.assertEqual(paused.returncode, 2)
        self.assertIn("captcha_user_instruction_required", paused.stderr)
        run_dirs = list((self.root / "runs").iterdir())
        self.assertEqual(len(run_dirs), 1)
        paused_run = json.loads(
            (run_dirs[0] / "run.json").read_text(encoding="utf-8")
        )
        self.assertEqual(paused_run["status"], "paused")
        self.assertFalse(paused_run["captcha_permission_granted"])

        allowed = self.run_cli(
            "run",
            str(experiment / "collector.py"),
            "--task",
            str(task_path),
            "--allow-captcha",
        )

        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertEqual(json.loads(allowed.stdout)["status"], "completed")

    def test_compare_emits_machine_readable_aggregate(self) -> None:
        baseline, current = self.create_comparison_runs()

        result = self.run_cli("compare", str(baseline), str(current))

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(1, payload["shared_unique_ids"])
        self.assertEqual(1, payload["changed_fields_on_shared_ids"]["price"])
        self.assertFalse((current / "historical_diff.json").exists())

    def test_compare_writes_only_explicit_current_run_output(self) -> None:
        baseline, current = self.create_comparison_runs()
        output = current / "diff.json"

        result = self.run_cli(
            "compare",
            str(baseline),
            str(current),
            "--ignore-field",
            "price",
            "--output",
            str(output),
        )

        self.assertEqual(0, result.returncode, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload, json.loads(output.read_text(encoding="utf-8")))
        self.assertNotIn("price", payload["changed_fields_on_shared_ids"])

        failed = self.run_cli("compare", str(baseline), str(self.root))
        self.assertEqual(2, failed.returncode)
        self.assertNotIn("Traceback", failed.stderr)

    def test_registered_selector_run_uses_registry_validation_contract(self) -> None:
        experiment, task_path = self.create_experiment()
        collector_target = self.root / "platforms" / "demo" / "items" / "collector.py"
        collector_target.parent.mkdir(parents=True)
        shutil.copy2(experiment / "collector.py", collector_target)
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
                                "proof_run": None,
                            }
                        ],
                    }
                ],
            },
        )

        result = self.run_cli("run", "demo/items", "--task", str(task_path))

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["selector"], "demo/items")

    def test_register_promotes_a_direct_successful_run(self) -> None:
        experiment, task_path = self.create_experiment()
        run_result = self.run_cli(
            "run", str(experiment / "collector.py"), "--task", str(task_path)
        )
        proof_run = json.loads(run_result.stdout)["run_dir"]

        result = self.run_cli("register", str(experiment), "--proof-run", proof_run)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["selector"], "demo/items")
        listed = json.loads(self.run_cli("list", "--json").stdout)
        self.assertEqual(listed["capabilities"][0]["selector"], "demo/items")

    def test_registered_and_direct_runs_enforce_stricter_task_fields(self) -> None:
        experiment, task_path = self.create_experiment()
        initial = self.run_cli("run", str(experiment / "collector.py"), "--task", str(task_path))
        self.assertEqual(initial.returncode, 0, initial.stderr)
        registered = self.run_cli("register", str(experiment), "--proof-run", json.loads(initial.stdout)["run_dir"])
        self.assertEqual(registered.returncode, 0, registered.stderr)
        task = json.loads(task_path.read_text("utf-8"))
        task["validation"]["required_fields"].append("author")
        self.write_json(task_path, task)
        for target in (str(experiment / "collector.py"), "demo/items"):
            with self.subTest(target=target):
                result = self.run_cli("run", target, "--task", str(task_path))
                self.assertEqual(result.returncode, 1, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "failed")
                validation = json.loads((Path(payload["run_dir"]) / "validation.json").read_text("utf-8"))
                self.assertIn("author", validation["required_fields"])

    def test_refresh_proof_emits_verified_machine_readable_result(self) -> None:
        experiment, task_path = self.create_experiment()
        direct_run = json.loads(
            self.run_cli(
                "run", str(experiment / "collector.py"), "--task", str(task_path)
            ).stdout
        )["run_dir"]
        registered = self.run_cli(
            "register", str(experiment), "--proof-run", direct_run
        )
        self.assertEqual(registered.returncode, 0, registered.stderr)
        registered_run_result = self.run_cli(
            "run", "demo/items", "--task", str(task_path)
        )
        self.assertEqual(
            registered_run_result.returncode, 0, registered_run_result.stderr
        )
        registered_run = json.loads(registered_run_result.stdout)["run_dir"]

        result = self.run_cli(
            "refresh-proof", "demo/items", "--proof-run", registered_run
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["selector"], "demo/items")
        self.assertEqual(payload["proof_status"], "verified")
        self.assertEqual(
            payload["source_run_id"],
            json.loads(
                (Path(registered_run) / "run.json").read_text(encoding="utf-8")
            )["run_id"],
        )
        self.assertTrue(Path(payload["proof"]).is_file())

        failed = self.run_cli(
            "refresh-proof", "demo/items", "--proof-run", str(self.root)
        )
        self.assertEqual(failed.returncode, 2)
        self.assertNotIn("Traceback", failed.stderr)

    def test_experiments_json_keeps_unregistered_state_separate(self) -> None:
        experiment, example_task = self.create_experiment()
        task_path = experiment / "task.json"
        shutil.copy2(example_task, task_path)
        run_result = self.run_cli(
            "run", str(experiment / "collector.py"), "--task", str(task_path)
        )
        self.assertEqual(run_result.returncode, 0, run_result.stderr)

        result = self.run_cli("experiments", "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["experiments"]), 1)
        item = payload["experiments"][0]
        self.assertEqual(item["name"], "demo_items")
        self.assertEqual(item["status"], "verified_unregistered")
        self.assertEqual(item["route"], "local")
        self.assertEqual(item["backend"], "python")
        self.assertEqual(item["records"], 1)
        self.assertEqual(payload["warnings"], [])
        listed = json.loads(self.run_cli("list", "--json").stdout)
        self.assertEqual(listed["capabilities"], [])

    def test_experiments_text_and_empty_output(self) -> None:
        empty = self.run_cli("experiments")

        self.assertEqual(empty.returncode, 0, empty.stderr)
        self.assertEqual(empty.stdout.strip(), "No collection experiments.")

        self.create_experiment()
        populated = self.run_cli("experiments")

        self.assertEqual(populated.returncode, 0, populated.stderr)
        self.assertIn("example\t-\tdemo_items\t-\t", populated.stdout)
        self.assertIn(
            "py -3.11 spider.py run experiments/demo_items/collector.py "
            "--task experiments/demo_items/task.example.json",
            populated.stdout,
        )

    def test_experiments_renderer_only_discovers_read_only_state(self) -> None:
        view = ExperimentView(
            experiments=(
                Experiment(
                    name="demo",
                    status="verified_unregistered",
                    collector="experiments/demo/collector.py",
                    task="experiments/demo/task.json",
                    selector=None,
                    latest_verified_run="runs/proof",
                    records=1,
                    completeness="sample",
                    route="local",
                    backend="python",
                    command=(
                        "py -3.11 spider.py run experiments/demo/collector.py "
                        "--task experiments/demo/task.json"
                    ),
                ),
            ),
            warnings=(),
        )
        with (
            mock.patch.object(spider, "discover_experiments", return_value=view) as discover,
            mock.patch.object(spider, "run_collector") as runner,
            mock.patch.object(spider, "ensure_workspace_browser") as browser,
            mock.patch.object(spider, "promote_experiment") as promotion,
            mock.patch.object(spider, "collection_health") as health,
        ):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = spider._experiments(self.root, as_json=True)

        self.assertEqual(code, 0, stderr.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["experiments"][0]["name"], "demo")
        discover.assert_called_once_with(self.root)
        runner.assert_not_called()
        browser.assert_not_called()
        promotion.assert_not_called()
        health.assert_not_called()

    def test_user_contract_error_has_no_traceback(self) -> None:
        task_path = self.root / "task.json"
        self.write_json(task_path, {"query": {}})

        result = self.run_cli("run", "missing/items", "--task", str(task_path))

        self.assertEqual(result.returncode, 2)
        self.assertIn("not registered", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_route_returns_machine_readable_decision(self) -> None:
        code, stdout, stderr = self.invoke_main(
            ["route", "--evidence-json", '{"stable_api":true}']
        )

        self.assertEqual(code, 0, stderr)
        payload = json.loads(stdout)
        self.assertEqual(payload["decision"]["route"], "http")
        self.assertEqual(payload["decision"]["backend"], "requests")
        self.assertTrue(payload["evidence"]["stable_api"])

    def test_browser_status_and_ensure_return_safe_json(self) -> None:
        status = {
            "status": "ready",
            "candidate": "chrome",
            "action": "available",
            "cdp_url": "http://127.0.0.1:9222",
            "browser": "Chrome/151.0.7922.137",
            "protocol_version": "1.3",
            "page_targets": 1,
        }
        ensured = {**status, "action": "reused"}
        with (
            mock.patch.object(spider, "status_browser_candidate", return_value=status),
            mock.patch.object(spider, "ensure_browser_candidate", return_value=ensured),
        ):
            status_code, status_stdout, _ = self.invoke_main(
                ["browser", "status", "--json"]
            )
            ensure_code, ensure_stdout, _ = self.invoke_main(
                ["browser", "ensure", "--json"]
            )

        self.assertEqual(status_code, 0)
        self.assertEqual(ensure_code, 0)
        self.assertEqual(json.loads(status_stdout), status)
        self.assertEqual(json.loads(ensure_stdout), ensured)

    def test_browser_auto_selects_chrome_from_reverse_evidence(self) -> None:
        result = {
            "status": "ready",
            "candidate": "chrome",
            "action": "reused",
            "cdp_url": "http://127.0.0.1:9222",
            "browser": "Chrome/142.0.7444.175",
            "protocol_version": "1.3",
            "page_targets": 1,
        }
        with mock.patch.object(
            spider,
            "ensure_browser_candidate",
            return_value=result,
        ) as ensure_candidate:
            code, stdout, stderr = self.invoke_main(
                [
                    "browser",
                    "ensure",
                    "--candidate",
                    "auto",
                    "--evidence-json",
                    '{"anti_debugger_pressure":true}',
                    "--json",
                ]
            )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout)["candidate"], "chrome")
        ensure_candidate.assert_called_once_with(SOURCE_ROOT, "chrome")

    def test_browser_auto_defaults_to_chrome_and_rejects_invalid_evidence(self) -> None:
        result = {
            "status": "ready",
            "candidate": "chrome",
            "action": "available",
            "cdp_url": "http://127.0.0.1:9222",
            "browser": "Chrome/151.0.7922.137",
            "protocol_version": "1.3",
            "page_targets": 1,
        }
        with mock.patch.object(
            spider,
            "status_browser_candidate",
            return_value=result,
        ) as status_candidate:
            code, stdout, stderr = self.invoke_main(
                ["browser", "status", "--candidate", "auto", "--json"]
            )
        self.assertEqual(code, 0, stderr)
        status_candidate.assert_called_once_with(SOURCE_ROOT, "chrome")

        code, stdout, stderr = self.invoke_main(
            [
                "browser",
                "status",
                "--candidate",
                "auto",
                "--evidence-json",
                '{"fingerprint_pressure":1}',
                "--json",
            ]
        )
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(stdout),
            {"status": "error", "error": "browser_evidence_invalid"},
        )
        self.assertEqual(stderr, "")

    def test_browser_all_aggregates_supported_candidates(self) -> None:
        def status(_: Path, candidate: str):
            return {
                "status": "ready",
                "candidate": candidate,
                "action": "available",
                "cdp_url": "http://127.0.0.1:9222",
                "browser": "Chrome/test",
                "protocol_version": "1.3",
                "page_targets": 1,
            }

        with mock.patch.object(spider, "status_browser_candidate", side_effect=status):
            code, stdout, stderr = self.invoke_main(
                ["browser", "status", "--candidate", "all", "--json"]
            )

        payload = json.loads(stdout)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(set(payload["candidates"]), {"chrome"})

    def test_browser_json_error_is_machine_readable(self) -> None:
        with mock.patch.object(
            spider,
            "status_browser_candidate",
            side_effect=spider.WorkspaceBrowserError("browser_unavailable"),
        ):
            code, stdout, stderr = self.invoke_main(
                ["browser", "status", "--json"]
            )

        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(stdout),
            {"status": "error", "error": "browser_unavailable"},
        )
        self.assertEqual(stderr, "")

    def test_doctor_returns_machine_readable_health_without_mutation(self) -> None:
        expected = {
            "packages": {"requests": {"available": True}},
            "optional_backends": {
                "scrapling": {
                    "status": "unavailable",
                },
                "camoufox": {
                    "status": "unavailable",
                },
            },
            "skills": {"web-collection-router": {"canonical": True, "discoverable": True}},
            "browser": {"status": "unavailable", "error": "browser_unavailable"},
        }
        with mock.patch.object(spider, "collection_health", return_value=expected):
            code, stdout, stderr = self.invoke_main(["doctor", "--json"])
            text_code, text_stdout, text_stderr = self.invoke_main(["doctor"])

        self.assertEqual(code, 0, stderr)
        self.assertEqual(json.loads(stdout), expected)
        self.assertEqual(text_code, 0, text_stderr)
        self.assertIn("scrapling: unavailable", text_stdout)
        self.assertIn("camoufox: unavailable", text_stdout)


if __name__ == "__main__":
    unittest.main()
