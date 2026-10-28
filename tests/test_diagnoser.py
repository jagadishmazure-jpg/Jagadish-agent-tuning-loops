"""Diagnoser tests: many loop types, one localization."""

from tuning.agents import BASELINE, evaluate_case
from tuning.diagnoser import (
    DogfoodSignal,
    OutcomeRecord,
    diagnose,
    replay,
    segment_conversion,
)
from tuning.labels import build_golden_set
from tuning.sampler import Mismatch


def mismatch(case_id, agent, expected, actual, geo="us-west",
             device="ios", dish_type="sushi"):
    return Mismatch(
        case_id=case_id, agent=agent, expected=expected, actual=actual,
        geo=geo, device=device, dish_type=dish_type, run_id=f"run-{case_id}")


def test_drift_only_localizes_the_router():
    cases = build_golden_set()
    diagnosis = diagnose(
        [mismatch("case-04", "router", "enhance", "skip")],
        [], [], cases, BASELINE)
    assert diagnosis.targets == ("router",)
    assert diagnosis.evidence["router"]["mismatches"] == 1


def test_dogfood_down_with_hint_localizes_that_agent():
    cases = build_golden_set()
    signal = DogfoodSignal(
        case_id="case-27", source="design", sentiment="down",
        text="hides the dish", agent_hint="publish")
    diagnosis = diagnose([], [signal], [], cases, BASELINE)
    assert diagnosis.targets == ("publish",)
    assert diagnosis.evidence["publish"]["dogfood_down"] == 1


def test_dogfood_up_creates_no_target():
    cases = build_golden_set()
    signal = DogfoodSignal(
        case_id="case-05", source="product", sentiment="up", text="good")
    diagnosis = diagnose([], [signal], [], cases, BASELINE)
    assert diagnosis.targets == ()


def test_empty_evidence_means_no_targets():
    cases = build_golden_set()
    diagnosis = diagnose([], [], [], cases, BASELINE)
    assert diagnosis.targets == ()
    assert diagnosis.segment_flags == ()


def test_bad_dogfood_source_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        DogfoodSignal(
            case_id="c", source="stranger", sentiment="down")


def test_segment_conversion_math():
    outcomes = [
        OutcomeRecord(f"c{i}", "us-west", "ios", "sushi", True, True)
        for i in range(3)
    ] + [
        OutcomeRecord(f"d{i}", "us-west", "ios", "sushi", True, False)
        for i in range(3)
    ]
    rates = segment_conversion(outcomes)
    assert rates[("dish_type", "sushi")] == 0.5
    assert rates[("geo", "us-west")] == 0.5


def test_conversion_drop_flags_the_segment():
    cases = build_golden_set()
    outcomes = []
    for case in cases:
        # Sushi converts at 0.333 while the rest convert at 1.0:
        # a clear drop the diagnoser must flag.
        completed = case.dish_type != "sushi"
        outcomes.append(OutcomeRecord(
            case.case_id, case.geo, case.device, case.dish_type,
            completed, completed))
    diagnosis = diagnose([], [], outcomes, cases, BASELINE)
    flagged = {(d, v) for d, v, _, _ in diagnosis.segment_flags}
    assert ("dish_type", "sushi") in flagged


def test_replay_covers_flagged_and_clean_cases():
    cases = build_golden_set()
    results = replay(["case-04", "case-05"], BASELINE, cases)
    assert [r.case_id for r in results] == ["case-04", "case-05"]
    assert all(hasattr(r, "passed") for r in results)


def test_replay_ignores_unknown_case_ids():
    cases = build_golden_set()
    assert replay(["nope"], BASELINE, cases) == []


def test_diagnosis_replays_flagged_plus_clean():
    cases = build_golden_set()
    diagnosis = diagnose(
        [mismatch("case-04", "router", "enhance", "skip")],
        [], [], cases, BASELINE)
    assert "case-04" in diagnosis.replayed
    # Equal number of clean cases replayed alongside.
    assert len(diagnosis.replayed) == 2
    assert len(diagnosis.replay_results) == 2
