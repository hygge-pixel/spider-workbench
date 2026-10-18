from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from spider_core.runner import run_collector


ROOT = Path(__file__).resolve().parents[1]


class LocalExampleTests(unittest.TestCase):
    def test_browser_preflight_task_is_offline_and_explicit(self) -> None:
        task_path = (
            ROOT
            / "experiments"
            / "example_local"
            / "task.browser-preflight.json"
        )
        task = json.loads(task_path.read_text(encoding="utf-8"))

        self.assertEqual(task["browser"], {"ensure": True})
        self.assertEqual(task["completion"], {"mode": "all", "expected_total": 3})
        self.assertEqual(len(task["query"]["rows"]), 3)
        self.assertNotIn("url", task["query"])

    def test_example_runs_without_registration_or_network(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_root = Path(directory)
            (run_root / "runs").mkdir()

            outcome = run_collector(
                run_root,
                ROOT / "experiments" / "example_local" / "collector.py",
                ROOT / "experiments" / "example_local" / "task.example.json",
            )

        self.assertEqual(outcome.status, "completed")
        self.assertEqual(outcome.completeness, "complete")
        self.assertEqual(outcome.records, 3)


if __name__ == "__main__":
    unittest.main()
