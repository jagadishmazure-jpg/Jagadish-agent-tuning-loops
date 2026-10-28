"""Drift sampler: read production run logs, compare against gold.

Input records use the sibling pipeline's flat run-log schema
(see the sibling repo's ``pipeline.run_pipeline``): one flat JSON
object per run with keys ``run_id, merchant, dish, route, tier,
tier_cost_usd, count_unverified, iterations, qa_pass_iteration,
qa_passed, coverage_hit, pairwise_verdict, publish_decision,
published_variant, qa_reasons, publish_reasons, failure_classes``.
This module reads exactly those keys. Segment keys ``geo`` and
``device`` are optional extras: when a record carries them they are
used for slicing, and when it does not the segment is "unknown".
Nothing else about the record shape is assumed, so real sibling
logs and this repo's simulated logs are interchangeable inputs.

A run record joins to its golden case through ``run_id``:
sibling run ids are ``run-<case_id>``. Records with no matching
golden case are counted as unmatched, never as mismatches.
"""

from __future__ import annotations

from dataclasses import dataclass

# Keys the sampler reads from a sibling-schema run record.
REQUIRED_KEYS = (
    "run_id",
    "route",
    "published_variant",
)


@dataclass(frozen=True)
class Mismatch:
    """One agent decision that disagrees with the golden label."""

    case_id: str
    agent: str  # "router" or "publish"
    expected: str
    actual: str
    geo: str
    device: str
    dish_type: str
    run_id: str

    @property
    def pattern(self):
        """Coarse failure pattern used by reflect to find systems."""
        if self.agent == "router":
            if self.expected == "enhance" and self.actual == "skip":
                return "skipped_bad"
            return "enhanced_good"
        if self.expected == "enhanced" and self.actual != "enhanced":
            return "withheld_good"
        if self.expected != "enhanced" and self.actual == "enhanced":
            return "published_bad"
        return "publish_mismatch"


def sample_records(records, cadence: int):
    """Sample production runs at a regular cadence: records 0,
    cadence, 2*cadence, ... Deterministic; cadence 1 takes all."""
    if not isinstance(cadence, int) or cadence < 1:
        raise ValueError(f"cadence must be a positive int, got {cadence!r}")
    return [r for i, r in enumerate(records) if i % cadence == 0]


def sample_by_segment(records, per_segment: int):
    """Take up to ``per_segment`` records per (geo, dish) segment,
    preserving order. Guarantees small segments are represented."""
    if per_segment < 1:
        raise ValueError("per_segment must be >= 1")
    counts = {}
    out = []
    for record in records:
        key = (record.get("geo", "unknown"), record.get("dish", "unknown"))
        if counts.get(key, 0) < per_segment:
            counts[key] = counts.get(key, 0) + 1
            out.append(record)
    return out


def find_mismatches(records, golden_cases):
    """Compare sampled records against golden labels.

    Returns (mismatches, unmatched_count). A record missing a
    required key is unmatched, not a mismatch: the sampler never
    invents a disagreement from malformed input.
    """
    by_id = {c.case_id: c for c in golden_cases}
    mismatches = []
    unmatched = 0
    for record in records:
        if any(k not in record for k in REQUIRED_KEYS):
            unmatched += 1
            continue
        run_id = record["run_id"]
        case_id = run_id[4:] if run_id.startswith("run-") else run_id
        case = by_id.get(case_id)
        if case is None:
            unmatched += 1
            continue
        geo = record.get("geo", "unknown")
        device = record.get("device", "unknown")
        route_ok = record["route"] == case.expected_route
        if not route_ok:
            mismatches.append(
                Mismatch(
                    case_id=case_id,
                    agent="router",
                    expected=case.expected_route,
                    actual=record["route"],
                    geo=geo,
                    device=device,
                    dish_type=case.dish_type,
                    run_id=run_id,
                )
            )
        # A publish mismatch is only counted when the route was
        # right. When the router skipped a case, the publish
        # outcome (original) is downstream of that skip, not an
        # independent publish failure: counting it would double
        # count one error and misdirect tuning at the QA gate.
        if route_ok and record["published_variant"] != case.expected_publish:
            mismatches.append(
                Mismatch(
                    case_id=case_id,
                    agent="publish",
                    expected=case.expected_publish,
                    actual=record["published_variant"],
                    geo=geo,
                    device=device,
                    dish_type=case.dish_type,
                    run_id=run_id,
                )
            )
    return mismatches, unmatched
