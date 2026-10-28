"""Synthesize agent: rewrite a target config from reflect feedback.

The rules are small, deterministic, and direction-checked:

- skipped_bad (bad items approved as-is): the router bar is too
  low, so RAISE thresholds by one step. Raising the bar routes
  more items to enhancement, which is the safe direction for a
  recall guardrail.
- enhanced_good (good items sent for enhancement): the bar is too
  high, so LOWER thresholds by one step (wasted compute, and a
  degradation risk on already-good photos).
- published_bad (a bad candidate published): the QA gate is too
  lax, so BLOCK the failure class behind the pattern and raise the
  score floor by one step.
- withheld_good (a good candidate held back): the QA gate is too
  strict, so UNBLOCK the class and lower the floor by one step.

Thresholds clamp to [0.30, 0.95]; the floor clamps to [0.30, 0.95].
An unknown pattern leaves the config unchanged: the synthesizer
never invents a change it cannot justify from an issue.
"""

from __future__ import annotations

from .agents import STEP, THRESHOLD_CAP, THRESHOLD_FLOOR, AgentConfig

# published_bad mismatches do not carry the class in the record, so
# the synthesizer blocks the lax classes: the ones the baseline
# leaves unblocked. The caller passes the exact class set when it
# knows it; the default covers the QA gap the demo exhibits.
DEFAULT_LAX_CLASSES = ("generic", "incoherent", "count_unknown")


def _clamp(value):
    return round(max(THRESHOLD_FLOOR, min(THRESHOLD_CAP, value)), 3)


def synthesize(config: AgentConfig, issues, lax_classes=DEFAULT_LAX_CLASSES):
    """Return a candidate config adjusted for every issue."""
    router_thresholds = dict(config.router.thresholds)
    qa_blocked = set(config.qa.blocked_classes)
    qa_floor = config.qa.score_floor
    changed = False
    for issue in issues:
        if issue.agent == "router" and issue.pattern == "skipped_bad":
            for key in router_thresholds:
                router_thresholds[key] = _clamp(
                    router_thresholds[key] + STEP)
            changed = True
        elif issue.agent == "router" and issue.pattern == "enhanced_good":
            for key in router_thresholds:
                router_thresholds[key] = _clamp(
                    router_thresholds[key] - STEP)
            changed = True
        elif issue.agent == "publish" and issue.pattern == "published_bad":
            qa_blocked.update(lax_classes)
            qa_floor = _clamp(qa_floor + STEP)
            changed = True
        elif issue.agent == "publish" and issue.pattern == "withheld_good":
            qa_blocked.difference_update(lax_classes)
            qa_floor = _clamp(qa_floor - STEP)
            changed = True
        # QA-agent issues map to the same gate the publish agent
        # enforces; unknown patterns are ignored on purpose.
        elif issue.agent == "qa" and issue.pattern == "published_bad":
            qa_blocked.update(lax_classes)
            qa_floor = _clamp(qa_floor + STEP)
            changed = True
        elif issue.agent == "qa" and issue.pattern == "withheld_good":
            qa_blocked.difference_update(lax_classes)
            qa_floor = _clamp(qa_floor - STEP)
            changed = True
    if not changed:
        return config
    return AgentConfig(
        name=f"{config.name}+tuned",
        router=config.router.with_thresholds(**router_thresholds),
        qa=config.qa.with_blocked(qa_blocked, floor=qa_floor),
        publish=config.publish,
    )
