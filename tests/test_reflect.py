"""Reflect tests: singletons are noise, repeats are systemic."""

from tuning.reflect import reflect
from tuning.sampler import Mismatch


def mismatch(case_id, agent, pattern, geo="us-west", dish_type="sushi"):
    expected, actual = {
        "skipped_bad": ("enhance", "skip"),
        "enhanced_good": ("skip", "enhance"),
        "published_bad": ("original", "enhanced"),
        "withheld_good": ("enhanced", "original"),
    }[pattern]
    return Mismatch(
        case_id=case_id, agent=agent, expected=expected, actual=actual,
        geo=geo, device="ios", dish_type=dish_type,
        run_id=f"run-{case_id}")


def test_singleton_pattern_is_noise_not_issue():
    issues, noise = reflect([mismatch("c1", "router", "skipped_bad")])
    assert issues == []
    assert noise == 1


def test_repeated_pattern_becomes_systemic_with_evidence():
    issues, noise = reflect([
        mismatch("c1", "router", "skipped_bad"),
        mismatch("c2", "router", "skipped_bad"),
    ])
    assert len(issues) == 1
    assert issues[0].agent == "router"
    assert issues[0].pattern == "skipped_bad"
    assert issues[0].count == 2
    assert issues[0].case_ids == ("c1", "c2")
    assert noise == 0


def test_segment_hint_set_when_all_cases_share_one_geo():
    issues, _ = reflect([
        mismatch("c1", "router", "skipped_bad", geo="us-west"),
        mismatch("c2", "router", "skipped_bad", geo="us-west"),
    ])
    assert issues[0].segment_hint == "geo:us-west"


def test_segment_hint_empty_when_cases_span_segments():
    issues, _ = reflect([
        mismatch("c1", "router", "skipped_bad", geo="us-west",
                 dish_type="sushi"),
        mismatch("c2", "router", "skipped_bad", geo="eu-west",
                 dish_type="burger"),
    ])
    assert issues[0].segment_hint == ""


def test_dish_hint_when_geo_mixed_but_dish_shared():
    issues, _ = reflect([
        mismatch("c1", "router", "skipped_bad", geo="us-west",
                 dish_type="sushi"),
        mismatch("c2", "router", "skipped_bad", geo="eu-west",
                 dish_type="sushi"),
    ])
    assert issues[0].segment_hint == "dish_type:sushi"


def test_empty_mismatches_give_no_issues():
    assert reflect([]) == ([], 0)


def test_different_patterns_are_separate_groups():
    issues, noise = reflect([
        mismatch("c1", "router", "skipped_bad"),
        mismatch("c2", "router", "enhanced_good"),
    ])
    assert issues == []
    assert noise == 2


def test_issue_describe_names_agent_pattern_and_cases():
    issues, _ = reflect([
        mismatch("c1", "router", "skipped_bad"),
        mismatch("c2", "router", "skipped_bad"),
    ])
    text = issues[0].describe()
    assert "router/skipped_bad" in text
    assert "c1" in text and "c2" in text
