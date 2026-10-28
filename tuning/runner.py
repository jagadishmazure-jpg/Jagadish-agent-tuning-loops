"""Simulated production runner: picks up the newest config.

The runner executes the target agents over a batch of cases and
emits one flat JSON record per run in the sibling pipeline's
schema -- the exact keys ``pipeline.run_pipeline`` produces --
plus optional ``geo`` and ``device`` segment keys. The sibling
schema is the contract: a real sibling log can be fed to the
sampler unchanged, and these simulated records can be fed to
any tool that reads sibling logs.

Tier pricing mirrors the sibling's illustrative fake tiers:
enhanced runs cost the standard tier; skipped runs cost nothing.
"""

from __future__ import annotations

from .agents import evaluate_case

TIER_COST_USD = 0.08


def run_production(cases, config):
    """Run cases through the current config; return flat records."""
    records = []
    for case in cases:
        result = evaluate_case(case, config)
        if result.route == "skip":
            record = {
                "run_id": f"run-{case.case_id}",
                "merchant": case.merchant,
                "dish": case.dish,
                "route": "skip",
                "tier": "",
                "tier_cost_usd": 0.0,
                "count_unverified": not case.count_verified,
                "iterations": 0,
                "qa_pass_iteration": None,
                "qa_passed": False,
                "coverage_hit": False,
                "pairwise_verdict": "",
                "publish_decision": (
                    "reject" if result.published_variant == "none"
                    else "publish"
                ),
                "published_variant": result.published_variant,
                "qa_reasons": [],
                "publish_reasons": [],
                "failure_classes": list(case.failure_flags),
            }
        else:
            qa_passed = result.qa_passed
            record = {
                "run_id": f"run-{case.case_id}",
                "merchant": case.merchant,
                "dish": case.dish,
                "route": "enhance",
                "tier": "standard",
                "tier_cost_usd": TIER_COST_USD,
                "count_unverified": not case.count_verified,
                "iterations": 1,
                "qa_pass_iteration": 1 if qa_passed else None,
                "qa_passed": qa_passed,
                "coverage_hit": not qa_passed,
                "pairwise_verdict": (
                    "better" if result.published_variant == "enhanced" else ""
                ),
                "publish_decision": (
                    "reject" if result.published_variant == "none"
                    else "publish"
                ),
                "published_variant": result.published_variant,
                "qa_reasons": list(result.qa_failure_classes),
                "publish_reasons": [],
                "failure_classes": list(case.failure_flags),
            }
        record["geo"] = case.geo
        record["device"] = case.device
        records.append(record)
    return records
