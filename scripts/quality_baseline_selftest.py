#!/usr/bin/env python3
"""Adversarial self-test for the B00 quality-authority validator."""

from __future__ import annotations

import copy

import quality_baseline as quality


def authorities():
    return (
        quality.read_json(quality.CAPABILITIES_PATH),
        quality.read_json(quality.SCORECARD_PATH),
        quality.read_json(quality.POLICY_PATH),
        quality.read_json(quality.BATCHES_PATH),
    )


def expect_failure(capabilities, scorecard, policy, batches, required_messages):
    try:
        quality.validate_authorities(capabilities, scorecard, policy, batches)
    except quality.ValidationError as exc:
        text = str(exc)
        missing = [message for message in required_messages if message not in text]
        if missing:
            raise AssertionError(f"validation failed, but required diagnostics were absent: {missing}\n{text}") from exc
    else:
        raise AssertionError("invalid authority mutation unexpectedly passed validation")


def main() -> int:
    capabilities, scorecard, policy, batches = authorities()
    quality.validate_authorities(capabilities, scorecard, policy, batches)

    stable = copy.deepcopy(capabilities)
    row = next(item for item in stable["capabilities"] if item["id"] == "tools.ai")
    row["lifecycle"] = "stable"
    row["implementation"] = "real"
    row["known_gaps"] = []
    expect_failure(
        stable,
        scorecard,
        policy,
        batches,
        [
            "stable capability requires tests.qualification=release_qualified",
            "stable capability requires mapped integration test evidence",
            "stable capability requires mapped end_to_end test evidence",
            "stable capability requires at least one verified platform",
            "stable capability requires requirements.audit_status=complete",
            "stable network-capable capability requires release-qualified privacy disclosure",
            "stable tool/API capability requires release-qualified per-interface evidence",
        ],
    )

    fake_stable = copy.deepcopy(capabilities)
    row = next(item for item in fake_stable["capabilities"] if item["id"] == "integrations.demo_connectors")
    row["lifecycle"] = "stable"
    row["known_gaps"] = []
    expect_failure(
        fake_stable,
        scorecard,
        policy,
        batches,
        ["stable capability must have implementation=real"],
    )

    broken_closure = copy.deepcopy(batches)
    broken_closure["batches"][0]["closure_evidence"] = "quality/evidence/B00/missing.json"
    expect_failure(
        capabilities,
        scorecard,
        policy,
        broken_closure,
        ["closure_evidence does not exist"],
    )

    print("quality baseline self-test passed: current authorities plus 3 adversarial mutations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
