"""Synthesize tests: every adjustment goes the safe direction."""

from tuning.agents import BASELINE
from tuning.reflect import SystemicIssue
from tuning.synthesize import synthesize


def issue(agent, pattern, count=2):
    return SystemicIssue(
        agent=agent, pattern=pattern, count=count,
        case_ids=("c1", "c2"), segment_hint="")


def test_skipped_bad_raises_all_router_thresholds():
    candidate = synthesize(BASELINE, [issue("router", "skipped_bad")])
    assert candidate.router.thresholds == {
        "sharpness": 0.75, "composition": 0.75, "color": 0.75,
        "plating": 0.75}


def test_enhanced_good_lowers_all_router_thresholds():
    candidate = synthesize(BASELINE, [issue("router", "enhanced_good")])
    assert candidate.router.thresholds["sharpness"] == 0.65


def test_thresholds_clamp_at_cap_and_floor():
    from tuning.agents import AgentConfig, RouterConfig
    high = AgentConfig(
        name="high",
        router=RouterConfig(thresholds={
            "sharpness": 0.95, "composition": 0.95, "color": 0.95,
            "plating": 0.95}))
    candidate = synthesize(high, [issue("router", "skipped_bad")])
    assert candidate.router.thresholds["sharpness"] == 0.95
    low = AgentConfig(
        name="low",
        router=RouterConfig(thresholds={
            "sharpness": 0.30, "composition": 0.30, "color": 0.30,
            "plating": 0.30}))
    candidate = synthesize(low, [issue("router", "enhanced_good")])
    assert candidate.router.thresholds["sharpness"] == 0.30


def test_published_bad_blocks_lax_classes_and_raises_floor():
    candidate = synthesize(BASELINE, [issue("publish", "published_bad")])
    assert "generic" in candidate.qa.blocked_classes
    assert "incoherent" in candidate.qa.blocked_classes
    assert "count_unknown" in candidate.qa.blocked_classes
    assert candidate.qa.score_floor == 0.65


def test_withheld_good_unblocks_and_lowers_floor():
    from tuning.agents import QAConfig, AgentConfig
    strict = AgentConfig(
        name="strict",
        qa=QAConfig(
            blocked_classes=frozenset(
                {"added", "removed", "generic", "incoherent",
                 "count_unknown"}),
            score_floor=0.70))
    candidate = synthesize(strict, [issue("publish", "withheld_good")])
    assert "generic" not in candidate.qa.blocked_classes
    assert candidate.qa.score_floor == 0.65


def test_qa_published_bad_matches_publish_published_bad():
    a = synthesize(BASELINE, [issue("qa", "published_bad")])
    b = synthesize(BASELINE, [issue("publish", "published_bad")])
    assert a.qa.blocked_classes == b.qa.blocked_classes
    assert a.qa.score_floor == b.qa.score_floor


def test_unknown_pattern_leaves_config_unchanged():
    candidate = synthesize(BASELINE, [issue("router", "mystery")])
    assert candidate is BASELINE


def test_empty_issues_leave_config_unchanged():
    assert synthesize(BASELINE, []) is BASELINE
