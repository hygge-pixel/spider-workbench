from __future__ import annotations

import unittest

from spider_core.routing import CollectionEvidence, RoutingError, decide_route


class CollectionRoutingTests(unittest.TestCase):
    def assert_decision(
        self,
        evidence: CollectionEvidence,
        *,
        route: str,
        backend: str | None,
        executable: bool,
    ) -> None:
        decision = decide_route(evidence)
        self.assertEqual(decision.route, route)
        self.assertEqual(decision.backend, backend)
        self.assertEqual(decision.executable, executable)

    def test_stable_api_uses_requests(self) -> None:
        self.assert_decision(
            CollectionEvidence(stable_api=True),
            route="http",
            backend="requests",
            executable=True,
        )

    def test_static_html_defaults_to_requests(self) -> None:
        decision = decide_route(CollectionEvidence())

        self.assertEqual((decision.route, decision.backend), ("html", "requests"))
        self.assertEqual(decision.reason_codes, ("static_html_default",))

    def test_document_collection_uses_crawl4ai(self) -> None:
        self.assert_decision(
            CollectionEvidence(document_collection=True),
            route="html",
            backend="crawl4ai",
            executable=False,
        )

    def test_javascript_requires_protocol_investigation_before_browser_batch(self) -> None:
        self.assert_decision(
            CollectionEvidence(requires_javascript=True),
            route="browser",
            backend="scrapling_dynamic",
            executable=False,
        )

    def test_stable_api_takes_priority_over_login_and_rendering(self) -> None:
        self.assert_decision(
            CollectionEvidence(stable_api=True, requires_login=True, requires_javascript=True),
            route="http", backend="requests", executable=True,
        )

    def test_verified_protocol_replay_takes_priority_over_site_complexity(self) -> None:
        decision = decide_route(CollectionEvidence(
            protocol_ready=True, has_signature=True, has_dynamic_token=True,
            has_waf_state=True, requires_login=True, requires_interaction=True,
            requires_javascript=True, fingerprint_pressure=True,
        ))
        self.assertEqual((decision.route, decision.backend), ("http", "requests"))
        self.assertTrue(decision.executable)
        self.assertIn("protocol_ready", decision.reason_codes)

    def test_unresolved_signature_still_requires_reverse_despite_stable_api(self) -> None:
        decision = decide_route(CollectionEvidence(stable_api=True, has_signature=True))
        self.assertEqual(decision.route, "reverse")
        self.assertFalse(decision.executable)

    def test_browser_batch_requires_protocol_inability_evidence(self) -> None:
        decision = decide_route(CollectionEvidence(
            requires_javascript=True, protocol_unavailable=True,
        ))
        self.assertEqual((decision.route, decision.backend), ("browser", "scrapling_dynamic"))
        self.assertTrue(decision.executable)
        self.assertIn("protocol_unavailable", decision.reason_codes)

    def test_browser_bound_api_uses_browser_only_after_protocol_failure(self) -> None:
        decision = decide_route(CollectionEvidence(stable_api=True, protocol_unavailable=True))
        self.assertEqual((decision.route, decision.backend), ("browser_context", "chrome_cdp"))

    def test_protocol_readiness_and_inability_are_mutually_exclusive(self) -> None:
        with self.assertRaisesRegex(RoutingError, "mutually exclusive"):
            CollectionEvidence(protocol_ready=True, protocol_unavailable=True)

    def test_protocol_ready_does_not_override_captcha_pause(self) -> None:
        decision = decide_route(CollectionEvidence(protocol_ready=True, captcha_present=True))
        self.assertEqual(decision.reason_codes, ("captcha_user_instruction_required",))
        self.assertFalse(decision.executable)

    def test_resilient_html_uses_scrapling_static(self) -> None:
        self.assert_decision(
            CollectionEvidence(requires_resilient_html=True),
            route="html",
            backend="scrapling_static",
            executable=True,
        )

    def test_login_uses_workspace_chrome(self) -> None:
        decision = decide_route(CollectionEvidence(requires_login=True))

        self.assertEqual(
            (decision.route, decision.backend, decision.executable),
            ("browser_context", "chrome_cdp", False),
        )
        self.assertEqual(decision.next_skill, "playwright-cli")

    def test_existing_chrome_has_specific_reason(self) -> None:
        decision = decide_route(CollectionEvidence(reuse_existing_chrome=True))

        self.assertEqual(decision.backend, "chrome_cdp")
        self.assertEqual(decision.reason_codes, ("reuse_existing_chrome",))

    def test_signature_hands_off_to_reverse_workflow(self) -> None:
        decision = decide_route(
            CollectionEvidence(has_signature=True, has_dynamic_token=True)
        )

        self.assertEqual((decision.route, decision.backend), ("reverse", None))
        self.assertFalse(decision.executable)
        self.assertEqual(
            decision.reason_codes, ("has_signature", "has_dynamic_token")
        )
        self.assertEqual(decision.next_skill, "web-reverse-workflow")

    def test_captcha_requires_user_instruction_without_automatic_handoff(self) -> None:
        decision = decide_route(CollectionEvidence(captcha_present=True))

        self.assertEqual(decision.route, "reverse")
        self.assertFalse(decision.executable)
        self.assertEqual(
            decision.reason_codes, ("captcha_user_instruction_required",)
        )
        self.assertIsNone(decision.backend)
        self.assertIsNone(decision.next_skill)
        self.assertTrue(any("wait for user instruction" in item for item in decision.warnings))

    def test_authorized_captcha_research_still_requires_per_run_instruction(self) -> None:
        decision = decide_route(
            CollectionEvidence(
                captcha_present=True,
                authorized_captcha_research=True,
            )
        )

        self.assertIsNone(decision.next_skill)
        self.assertEqual(
            decision.reason_codes, ("captcha_user_instruction_required",)
        )
        self.assertTrue(any("--allow-captcha" in item for item in decision.warnings))

    def test_fingerprint_pressure_requires_authorization(self) -> None:
        decision = decide_route(CollectionEvidence(fingerprint_pressure=True))

        self.assertEqual((decision.route, decision.backend), ("stealth", None))
        self.assertFalse(decision.executable)
        self.assertEqual(decision.reason_codes, ("stealth_not_authorized",))

    def test_authorized_fingerprint_pressure_uses_scrapling(self) -> None:
        self.assert_decision(
            CollectionEvidence(
                fingerprint_pressure=True,
                allow_stealth=True,
                protocol_unavailable=True,
            ),
            route="stealth",
            backend="scrapling_stealth",
            executable=True,
        )

    def test_camoufox_requires_prior_scrapling_failure_and_authorization(self) -> None:
        decision = decide_route(
            CollectionEvidence(
                fingerprint_pressure=True,
                allow_stealth=True,
                protocol_unavailable=True,
                scrapling_stealth_failed=True,
                allow_experimental_camoufox=True,
            )
        )

        self.assertEqual((decision.route, decision.backend), ("stealth", "camoufox"))
        self.assertTrue(decision.executable)

    def test_fingerprint_pressure_alone_does_not_authorize_browser_collection(self) -> None:
        decision = decide_route(CollectionEvidence(fingerprint_pressure=True, allow_stealth=True))
        self.assertFalse(decision.executable)
        self.assertEqual(decision.next_skill, "web-reverse-workflow")

    def test_unknown_evidence_is_rejected(self) -> None:
        with self.assertRaisesRegex(RoutingError, "unknown evidence fields"):
            CollectionEvidence.from_dict({"stable_api": True, "magic": True})

    def test_non_boolean_evidence_is_rejected(self) -> None:
        with self.assertRaisesRegex(RoutingError, "stable_api must be boolean"):
            CollectionEvidence.from_dict({"stable_api": 1})

    def test_captcha_authorization_requires_captcha_evidence(self) -> None:
        with self.assertRaisesRegex(RoutingError, "requires captcha evidence"):
            CollectionEvidence(authorized_captcha_research=True)

    def test_scrapling_failure_requires_fingerprint_evidence(self) -> None:
        with self.assertRaisesRegex(RoutingError, "requires fingerprint pressure"):
            CollectionEvidence(scrapling_stealth_failed=True)


if __name__ == "__main__":
    unittest.main()
