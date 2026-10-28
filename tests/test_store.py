"""Config store tests: gates fail closed, rollback is exact."""

import pytest

from tuning.agents import BASELINE
from tuning.benchmark import benchmark, ship_decision
from tuning.labels import build_golden_set
from tuning.store import ConfigStore
from tuning.synthesize import synthesize
from tuning.reflect import SystemicIssue


def passing_decision():
    cases = build_golden_set()
    base = benchmark(BASELINE, cases)
    issues = [
        SystemicIssue("router", "skipped_bad", 8, ("c1",), ""),
        SystemicIssue("publish", "published_bad", 11, ("c2",), ""),
    ]
    cand = synthesize(synthesize(BASELINE, issues), issues)
    return cand, ship_decision(benchmark(cand, cases), base)


def test_register_requires_a_ship_decision():
    store = ConfigStore(BASELINE)
    with pytest.raises(ValueError, match="no benchmark"):
        store.register(BASELINE, None)


def test_register_refuses_a_failed_candidate():
    store = ConfigStore(BASELINE)
    cases = build_golden_set()
    base = benchmark(BASELINE, cases)
    decision = ship_decision(base, base)
    assert decision.ship is False
    with pytest.raises(ValueError, match="failed the benchmark gate"):
        store.register(BASELINE, decision)


def test_register_increments_version_and_moves_current():
    store = ConfigStore(BASELINE)
    cand, decision = passing_decision()
    version = store.register(cand, decision)
    assert version == 2
    assert store.current_version() == 2
    assert store.current() is cand
    assert store.history() == (1, 2)


def test_rollback_restores_previous_version_exactly():
    store = ConfigStore(BASELINE)
    cand, decision = passing_decision()
    store.register(cand, decision)
    rolled = store.rollback()
    assert rolled is BASELINE
    assert store.current_version() == 1
    cases = build_golden_set()
    assert benchmark(rolled, cases).recall == \
        benchmark(BASELINE, cases).recall
    assert benchmark(rolled, cases).case_accuracy == \
        benchmark(BASELINE, cases).case_accuracy


def test_rollback_with_one_version_is_refused():
    store = ConfigStore(BASELINE)
    with pytest.raises(ValueError, match="no previous version"):
        store.rollback()


def test_current_starts_at_baseline():
    store = ConfigStore(BASELINE)
    assert store.current() is BASELINE
    assert store.current_version() == 1
