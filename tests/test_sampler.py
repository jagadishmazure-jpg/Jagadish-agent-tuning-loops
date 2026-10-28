"""Drift sampler tests: sibling-schema records vs golden labels."""

import pytest

from tuning.labels import build_golden_set
from tuning.sampler import (
    find_mismatches,
    sample_by_segment,
    sample_records,
)


def record(run_id, route, published, **extra):
    base = {
        "run_id": run_id,
        "merchant": "merchant-00",
        "dish": "dish",
        "route": route,
        "tier": "standard",
        "tier_cost_usd": 0.08,
        "count_unverified": False,
        "iterations": 1,
        "qa_pass_iteration": 1,
        "qa_passed": True,
        "coverage_hit": False,
        "pairwise_verdict": "better",
        "publish_decision": "publish",
        "published_variant": published,
        "qa_reasons": [],
        "publish_reasons": [],
        "failure_classes": [],
    }
    base.update(extra)
    return base


def test_cadence_sampling_takes_every_nth_record():
    records = [record(f"run-c{i}", "skip", "original") for i in range(6)]
    sampled = sample_records(records, cadence=2)
    assert [r["run_id"] for r in sampled] == ["run-c0", "run-c2", "run-c4"]


def test_cadence_one_takes_all():
    records = [record(f"run-c{i}", "skip", "original") for i in range(3)]
    assert len(sample_records(records, cadence=1)) == 3


def test_bad_cadence_is_rejected():
    with pytest.raises(ValueError):
        sample_records([], cadence=0)


def test_router_mismatch_is_detected():
    cases = build_golden_set()
    low = [c for c in cases if c.quality_tier == "low"][0]
    rec = record(f"run-{low.case_id}", "skip", "original")
    mismatches, unmatched = find_mismatches([rec], cases)
    assert unmatched == 0
    assert len(mismatches) == 1
    assert mismatches[0].agent == "router"
    assert mismatches[0].pattern == "skipped_bad"


def test_publish_mismatch_is_detected_when_route_is_right():
    cases = build_golden_set()
    low = [c for c in cases if c.quality_tier == "low"][0]
    rec = record(f"run-{low.case_id}", "enhance", "enhanced")
    mismatches, _ = find_mismatches([rec], cases)
    publish = [m for m in mismatches if m.agent == "publish"]
    assert len(publish) == 1
    assert publish[0].pattern == "published_bad"


def test_publish_mismatch_suppressed_when_route_is_wrong():
    # A skipped bad item's publish outcome (original) is downstream
    # of the router error, not an independent publish failure.
    cases = build_golden_set()
    low = [c for c in cases if c.quality_tier == "low"][0]
    rec = record(f"run-{low.case_id}", "skip", "original")
    mismatches, _ = find_mismatches([rec], cases)
    assert [m.agent for m in mismatches] == ["router"]


def test_unknown_run_id_is_unmatched_not_mismatch():
    cases = build_golden_set()
    rec = record("run-nope", "skip", "original")
    mismatches, unmatched = find_mismatches([rec], cases)
    assert mismatches == []
    assert unmatched == 1


def test_record_missing_required_key_is_unmatched():
    cases = build_golden_set()
    rec = {"run_id": "run-case-00"}
    mismatches, unmatched = find_mismatches([rec], cases)
    assert mismatches == []
    assert unmatched == 1


def test_missing_segment_keys_default_to_unknown():
    cases = build_golden_set()
    low = [c for c in cases if c.quality_tier == "low"][0]
    rec = record(f"run-{low.case_id}", "skip", "original")
    mismatches, _ = find_mismatches([rec], cases)
    assert mismatches[0].geo == "unknown"
    assert mismatches[0].device == "unknown"


def test_segment_keys_are_carried_into_mismatches():
    cases = build_golden_set()
    low = [c for c in cases if c.quality_tier == "low"][0]
    rec = record(
        f"run-{low.case_id}", "skip", "original",
        geo="us-west", device="ios")
    mismatches, _ = find_mismatches([rec], cases)
    assert mismatches[0].geo == "us-west"
    assert mismatches[0].device == "ios"


def test_sample_by_segment_caps_each_segment():
    records = [
        record(f"run-a{i}", "skip", "original", geo="us-west", dish="x")
        for i in range(5)
    ] + [
        record(f"run-b{i}", "skip", "original", geo="eu-west", dish="y")
        for i in range(2)
    ]
    sampled = sample_by_segment(records, per_segment=2)
    assert len(sampled) == 4
