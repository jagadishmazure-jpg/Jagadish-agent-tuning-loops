"""Golden label set tests."""

import pytest

from tuning.labels import (
    GOLD_QA_BLOCKED,
    GOLD_ROUTER_BAR,
    build_golden_set,
    cuts_covered,
    GoldenCase,
)


def base_case(**overrides):
    params = {
        "case_id": "case-x",
        "dish": "dish-x",
        "merchant": "merchant-00",
        "geo": "us-midwest",
        "device": "ios",
        "dish_type": "burger",
        "quality_tier": "high",
        "sharpness": 0.95,
        "composition": 0.95,
        "color": 0.95,
        "plating": 0.95,
        "expected_route": "skip",
        "expected_publish": "original",
    }
    params.update(overrides)
    return GoldenCase(**params)


def test_golden_set_has_36_cases():
    assert len(build_golden_set()) == 36


def test_golden_set_covers_every_cut():
    covered = cuts_covered(build_golden_set())
    assert all(covered.values()), covered


def test_every_label_matches_the_written_guide():
    for case in build_golden_set():
        assert case.expected_route == case.guide_route(), case.case_id
        assert case.expected_publish == case.guide_publish(), case.case_id


def test_hand_picked_case_00_is_fully_flagged():
    case = build_golden_set()[0]
    assert case.expected_route == "enhance"
    assert case.expected_publish == "original"
    assert set(case.failure_flags) == set(GOLD_QA_BLOCKED)


def test_hand_picked_policy_case_publishes_nothing():
    cases = {c.case_id: c for c in build_golden_set()}
    assert cases["case-23"].policy_flag is True
    assert cases["case-23"].expected_publish == "none"


def test_hand_picked_high_case_is_skipped_and_kept():
    cases = {c.case_id: c for c in build_golden_set()}
    high = cases["case-05"]
    assert high.quality_tier == "high"
    assert high.expected_route == "skip"
    assert high.expected_publish == "original"


def test_guide_bar_is_0_80():
    assert GOLD_ROUTER_BAR == 0.80


def test_score_out_of_range_is_rejected():
    with pytest.raises(ValueError):
        base_case(sharpness=1.5)


def test_nan_score_is_rejected():
    with pytest.raises(ValueError):
        base_case(color=float("nan"))


def test_unknown_route_is_rejected():
    with pytest.raises(ValueError):
        base_case(expected_route="maybe")


def test_unknown_geo_cut_is_rejected():
    with pytest.raises(ValueError):
        base_case(geo="mars")


def test_failure_flags_list_every_present_class():
    case = base_case(
        added_objects=True, generic_fallback=True, count_known=False)
    assert case.failure_flags == ("added", "generic", "count_unknown")
