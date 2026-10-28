"""Benchmark gate tests: ship only on proof."""

from tuning.agents import BASELINE, AgentConfig, PublishConfig, QAConfig
from tuning.benchmark import (
    GUARDRAIL_RECALL,
    benchmark,
    segment_metrics,
    ship_decision,
)
from tuning.labels import build_golden_set
from tuning.synthesize import synthesize
from tuning.reflect import SystemicIssue


def tuned_config():
    issues = [
        SystemicIssue("router", "skipped_bad", 8, ("c1",), ""),
        SystemicIssue("publish", "published_bad", 11, ("c2",), ""),
    ]
    once = synthesize(BASELINE, issues)
    return synthesize(once, issues)


def test_baseline_metrics_match_the_real_demo():
    result = benchmark(BASELINE, build_golden_set())
    assert result.cases == 36
    assert result.recall == 0.667
    assert result.precision == 1.0
    assert result.case_accuracy == 0.472
    assert result.published_bad == 5


def test_tuned_config_ships_against_baseline():
    cases = build_golden_set()
    base = benchmark(BASELINE, cases)
    cand = benchmark(tuned_config(), cases)
    decision = ship_decision(cand, base)
    assert decision.ship is True
    assert decision.regressions == ()
    assert cand.recall == 1.0
    assert cand.case_accuracy == 1.0
    assert cand.published_bad == 0


def test_recall_below_guardrail_blocks():
    cases = build_golden_set()
    base = benchmark(BASELINE, cases)
    decision = ship_decision(base, base)
    assert decision.ship is False
    assert any("recall" in r for r in decision.reasons)


def test_regression_blocks_even_when_aggregates_improve():
    cases = build_golden_set()
    base = benchmark(BASELINE, cases)
    # A config that fixes the router but breaks publish strictness
    # on clean high cases: strict mode withholds flagged-free
    # photos? No -- strict only withholds flagged ones. Instead,
    # break one baseline-passing case directly: raise the router
    # bar so a high case flips to enhance.
    from tuning.agents import RouterConfig
    breaking = AgentConfig(
        name="breaking",
        router=RouterConfig(thresholds={
            "sharpness": 0.99, "composition": 0.99, "color": 0.99,
            "plating": 0.99}),
        qa=BASELINE.qa, publish=BASELINE.publish)
    cand = benchmark(breaking, cases)
    decision = ship_decision(cand, base)
    assert decision.ship is False
    assert decision.regressions, "expected named regressions"
    assert any("regressions" in r for r in decision.reasons)


def test_published_bad_blocks():
    cases = build_golden_set()
    base = benchmark(BASELINE, cases)
    # Baseline itself has published_bad > 0, so it blocks itself.
    decision = ship_decision(base, base)
    assert any("published_bad" in r for r in decision.reasons)


def test_guardrail_constant_is_0_90():
    assert GUARDRAIL_RECALL == 0.90


def test_segment_metrics_slice_by_dish_type():
    cases = build_golden_set()
    metrics = segment_metrics(BASELINE, cases)
    sushi = metrics[("dish_type", "sushi")]
    assert sushi["cases"] == 9
    assert sushi["recall"] == 0.5
    tuned = segment_metrics(tuned_config(), cases)
    assert tuned[("dish_type", "sushi")]["recall"] == 1.0


def test_segment_tuning_does_not_degrade_global_metrics():
    cases = build_golden_set()
    base = benchmark(BASELINE, cases)
    cand = benchmark(tuned_config(), cases)
    assert cand.recall >= base.recall
    assert cand.case_accuracy >= base.case_accuracy
