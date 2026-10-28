"""Production runner tests: sibling-schema output, newest config."""

from tuning.agents import BASELINE
from tuning.labels import build_golden_set
from tuning.runner import run_production
from tuning.store import ConfigStore

# Exact flat keys the sibling pipeline's run_pipeline produces.
SIBLING_KEYS = {
    "run_id", "merchant", "dish", "route", "tier", "tier_cost_usd",
    "count_unverified", "iterations", "qa_pass_iteration", "qa_passed",
    "coverage_hit", "pairwise_verdict", "publish_decision",
    "published_variant", "qa_reasons", "publish_reasons",
    "failure_classes",
}


def test_records_carry_every_sibling_schema_key():
    records = run_production(build_golden_set()[:3], BASELINE)
    for record in records:
        assert SIBLING_KEYS <= set(record), SIBLING_KEYS - set(record)


def test_records_carry_segment_keys_as_superset():
    records = run_production(build_golden_set()[:3], BASELINE)
    for record in records:
        assert "geo" in record and "device" in record


def test_run_id_joins_back_to_golden_case_id():
    cases = build_golden_set()
    records = run_production(cases, BASELINE)
    assert records[0]["run_id"] == f"run-{cases[0].case_id}"


def test_skipped_record_has_no_edit_cost_or_iterations():
    cases = [c for c in build_golden_set() if c.quality_tier == "high"]
    records = run_production(cases[:1], BASELINE)
    assert records[0]["route"] == "skip"
    assert records[0]["tier_cost_usd"] == 0.0
    assert records[0]["iterations"] == 0


def test_failed_qa_marks_a_coverage_hit():
    cases = build_golden_set()
    low = [c for c in cases if c.quality_tier == "low"][0]
    # A stricter config forces the QA failure the baseline passes.
    from tuning.agents import AgentConfig, QAConfig
    strict = AgentConfig(
        name="strict",
        qa=QAConfig(blocked_classes=frozenset({"added"}),
                    score_floor=0.99))
    records = run_production([low], strict)
    assert records[0]["coverage_hit"] is True
    assert records[0]["qa_passed"] is False


def test_runner_picks_up_the_newest_registered_version():
    from tuning.benchmark import benchmark, ship_decision
    from tuning.reflect import SystemicIssue
    from tuning.synthesize import synthesize
    cases = build_golden_set()
    store = ConfigStore(BASELINE)
    issues = [
        SystemicIssue("router", "skipped_bad", 8, ("c1",), ""),
        SystemicIssue("publish", "published_bad", 11, ("c2",), ""),
    ]
    cand = synthesize(synthesize(BASELINE, issues), issues)
    base = benchmark(BASELINE, cases)
    store.register(cand, ship_decision(benchmark(cand, cases), base))
    records = run_production(cases, store.current())
    bad = sum(
        1 for r in records
        if r["published_variant"] == "enhanced" and r["failure_classes"])
    assert bad == 0
