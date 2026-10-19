from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from spider_core.evidence_safety import scrub_run_evidence


class EvidenceSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.temporary.name) / "runs" / "current"
        self.run_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_scrubs_structured_and_text_dynamic_secrets(self) -> None:
        secret = "dynamic-secret-123"
        structured = {
            "access_token": secret,
            "nested": {"Cookie": f"session={secret}"},
            "has_dynamic_token": True,
            "token_count": 3,
            "request_url": f"https://example.test/items?page=2&token={secret}#trace",
        }
        (self.run_dir / "raw").mkdir()
        (self.run_dir / "raw" / "page.json").write_text(
            json.dumps(structured), encoding="utf-8"
        )
        (self.run_dir / "events.jsonl").write_text(
            json.dumps({"authorization": f"Bearer {secret}"}) + "\n"
            + json.dumps({"url": f"https://example.test/api?w_rid={secret}"})
            + "\n",
            encoding="utf-8",
        )
        (self.run_dir / "stdout.log").write_text(
            f"Authorization: Bearer {secret}\n"
            f"Cookie: sid={secret}\n"
            f"proxy=http://user:{secret}@127.0.0.1:8080\n"
            f"url=https://example.test/data?signature={secret}#debug\n",
            encoding="utf-8",
        )

        report = scrub_run_evidence(self.run_dir)

        self.assertEqual(
            set(report),
            {
                "passed",
                "files_scanned",
                "session_files_excluded",
                "redactions",
                "violations",
            },
        )
        self.assertTrue(report["passed"])
        self.assertEqual(report["files_scanned"], 3)
        self.assertGreaterEqual(report["redactions"], 7)
        self.assertEqual(report["violations"], [])
        saved = json.loads(
            (self.run_dir / "raw" / "page.json").read_text(encoding="utf-8")
        )
        self.assertEqual(saved["access_token"], "<redacted>")
        self.assertEqual(saved["nested"]["Cookie"], "<redacted>")
        self.assertTrue(saved["has_dynamic_token"])
        self.assertEqual(saved["token_count"], 3)
        self.assertEqual(saved["request_url"], "https://example.test/items")
        all_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in self.run_dir.rglob("*")
            if path.is_file()
        )
        self.assertNotIn(secret, all_text)
        self.assertIn("Authorization: <redacted>", all_text)
        self.assertIn("Cookie: <redacted>", all_text)
        self.assertIn("http://<redacted>@127.0.0.1:8080", all_text)
        self.assertIn("https://example.test/data", all_text)

    def test_ignores_binary_and_files_outside_run(self) -> None:
        outside = self.run_dir.parent / "outside.log"
        outside.write_text("Authorization: Bearer keep", encoding="utf-8")
        binary = self.run_dir / "page.png"
        binary.write_bytes(b"Authorization: Bearer keep")

        report = scrub_run_evidence(self.run_dir)

        self.assertEqual(report["files_scanned"], 0)
        self.assertEqual(outside.read_text(encoding="utf-8"), "Authorization: Bearer keep")
        self.assertEqual(binary.read_bytes(), b"Authorization: Bearer keep")

    def test_preserves_exact_cookie_cache_but_scrubs_other_json(self) -> None:
        secret = "session-secret-value"
        (self.run_dir / "cookies.json").write_text(
            json.dumps({"Cookie": f"sid={secret}"}), encoding="utf-8"
        )
        (self.run_dir / "raw").mkdir()
        (self.run_dir / "raw" / "response.json").write_text(
            json.dumps({"Cookie": f"sid={secret}"}), encoding="utf-8"
        )

        report = scrub_run_evidence(self.run_dir)

        self.assertEqual(report["session_files_excluded"], 1)
        self.assertEqual(report["files_scanned"], 1)
        self.assertIn(
            secret,
            (self.run_dir / "cookies.json").read_text(encoding="utf-8"),
        )
        self.assertNotIn(
            secret,
            (self.run_dir / "raw" / "response.json").read_text(encoding="utf-8"),
        )

    def test_similarly_named_cookie_json_is_still_scrubbed(self) -> None:
        secret = "backup-session-secret"
        path = self.run_dir / "cookies-backup.json"
        path.write_text(json.dumps({"Cookie": secret}), encoding="utf-8")

        report = scrub_run_evidence(self.run_dir)

        self.assertEqual(report["session_files_excluded"], 0)
        self.assertNotIn(secret, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
