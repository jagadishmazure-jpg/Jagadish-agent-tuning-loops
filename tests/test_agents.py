"""Tunable target agent tests."""

import pytest

from tuning.agents import (
    BASELINE,
    AgentConfig,
    PublishConfig,
    QAConfig,
    RouterConfig,
    evaluate_case,
    publish,
    published_bad,
    qa_gate,
    route,
)
from tuning.labels import GoldenCase


def make_case(**overrides):
    params = {
        "case_id": "c1",
        "dish": "d",
        "merchant": "m",
        "geo": "us-midwest",
        "device": "ios",
        "dish_type": "burger",
        "quality_tier": "high",
        "sharpness": 0.9,
        "composition": 0.9,
        "color": 0.9,
        "plating": 0.9,
        "expected_route": "skip",
        "expected_publish": "original",
    }
    params.update(overrides)
    return GoldenCase(**params)


def test_router_skips_when_all_scores_clear_the_bar():
    assert route(make_case(), RouterConfig()) == "skip"


def test_router_enhances_when_one_score_falls_below():
    assert route(make_case(sharpness=0.5), RouterConfig()) == "enhance"


def test_router_score_exactly_at_bar_skips():
    # Boundary: enhance is strictly below the bar.
    assert route(make_case(sharpness=0.7), RouterConfig()) == "skip"
    assert route(make_case(sharpness=0.69), RouterConfig()) == "enhance"


def test_router_enhances_on_unrealistic_plating_despite_scores():
    assert route(
        make_case(plating_realistic=False), RouterConfig()) == "enhance"


def test_router_negative_threshold_is_rejected():
    with pytest.raises(ValueError):
        RouterConfig(thresholds={
            "sharpness": -0.1, "composition": 0.7, "color": 0.7,
            "plating": 0.7})


def test_router_missing_criterion_is_rejected():
    with pytest.raises(ValueError):
        RouterConfig(thresholds={"sharpness": 0.7})


def test_qa_blocks_configured_classes_only():
    case = make_case(generic_fallback=True, incoherent=True)
    result = qa_gate(case, QAConfig())
    assert result.passed is True  # neither class blocked by default
    assert result.failure_classes == ()
    blocked = qa_gate(
        case, QAConfig(blocked_classes=frozenset({"generic"})))
    assert blocked.passed is False
    assert blocked.failure_classes == ("generic",)


def test_qa_score_floor_fails_low_candidates():
    case = make_case(candidate_sharpness=0.5)
    result = qa_gate(case, QAConfig(score_floor=0.6))
    assert result.passed is False
    assert "low_quality" in result.failure_classes


def test_publish_standard_publishes_enhanced_when_qa_passes():
    case = make_case()
    assert publish(case, qa_gate(case, QAConfig()), PublishConfig()) \
        == "enhanced"


def test_publish_strict_withholds_when_any_flag_present():
    case = make_case(generic_fallback=True)
    qa = qa_gate(case, QAConfig())
    assert publish(case, qa, PublishConfig(mode="strict")) == "original"
    assert publish(case, qa, PublishConfig(mode="standard")) == "enhanced"


def test_publish_policy_flag_publishes_nothing():
    case = make_case(policy_flag=True)
    assert publish(
        case, qa_gate(case, QAConfig()), PublishConfig()) == "none"


def test_publish_bad_mode_is_rejected():
    with pytest.raises(ValueError):
        PublishConfig(mode="whenever")


def test_evaluate_case_passes_when_both_decisions_match():
    result = evaluate_case(make_case(), BASELINE)
    assert result.passed is True
    # High scores route skip, so the original is what publishes.
    assert result.published_variant == "original"


def test_evaluate_case_passes_on_correct_enhance():
    result = evaluate_case(
        make_case(sharpness=0.5, expected_route="enhance",
                  expected_publish="enhanced"), BASELINE)
    # Baseline bar 0.70: 0.5 enhances, candidate 0.70 passes floor
    # 0.60, no flags -> enhanced. Both match.
    assert result.passed is True


def test_published_bad_flags_enhanced_publishes_with_failure_classes():
    case = make_case(
        sharpness=0.5, generic_fallback=True, expected_route="enhance",
        expected_publish="enhanced")
    result = evaluate_case(case, BASELINE)
    assert result.published_variant == "enhanced"
    assert published_bad(case, result) is True


def test_skipped_case_never_counts_as_published_bad():
    case = make_case(generic_fallback=True, expected_route="skip")
    result = evaluate_case(case, BASELINE)
    assert result.published_variant == "original"
    assert published_bad(case, result) is False
