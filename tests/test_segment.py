"""Segment-sliced tuning tests."""

from tuning.agents import BASELINE, evaluate_case
from tuning.benchmark import benchmark, segment_metrics
from tuning.diagnoser import OutcomeRecord, diagnose
from tuning.labels import build_golden_set
from tuning.runner import run_production
from tuning.sampler import find_mismatches
from tuning.synthesize import synthesize
from tuning.reflect import SystemicIssue


def tuned_config():
    issues = [
        SystemicIssue("router", "skipped_bad", 8, ("c1",), ""),
        SystemicIssue("publish", "published_bad", 11, ("c2",), ""),
    ]
    return synthesize(synthesize(BASELINE, issues), issues)


def test_worst_segment_is_sushi_under_baseline():
    cases = build_golden_set()
    metrics = segment_metrics(BASELINE, cases)
    dish_recalls = {
        value: m["recall"]
        for (dim, value), m in metrics.items() if dim == "dish_type"
    }
    worst = min(dish_recalls, key=dish_recalls.get)
    assert worst == "sushi"
    assert dish_recalls["sushi"] == 0.5


def test_segment_improves_without_global_degradation():
    cases = build_golden_set()
    before = segment_metrics(BASELINE, cases)
    after = segment_metrics(tuned_config(), cases)
    assert after[("dish_type", "sushi")]["recall"] == 1.0
    assert after[("dish_type", "sushi")]["recall"] > \
        before[("dish_type", "sushi")]["recall"]
    base = benchmark(BASELINE, cases)
    cand = benchmark(tuned_config(), cases)
    assert cand.recall >= base.recall
    assert cand.case_accuracy >= base.case_accuracy


def test_demo_outcomes_flag_sushi_conversion_drop():
    cases = build_golden_set()
    outcomes = [
        OutcomeRecord(
            case.case_id, case.geo, case.device, case.dish_type,
            evaluate_case(case, BASELINE).passed,
            evaluate_case(case, BASELINE).passed)
        for case in cases
    ]
    records = run_production(cases, BASELINE)
    mismatches, _ = find_mismatches(records, cases)
    diagnosis = diagnose(mismatches, [], outcomes, cases, BASELINE)
    flagged = {(d, v) for d, v, _, _ in diagnosis.segment_flags}
    assert ("dish_type", "sushi") in flagged


def test_segment_metrics_cover_every_dimension():
    cases = build_golden_set()
    metrics = segment_metrics(BASELINE, cases)
    dims = {d for d, _ in metrics}
    assert dims == {"geo", "device", "dish_type"}
