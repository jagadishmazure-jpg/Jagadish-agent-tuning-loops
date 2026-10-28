"""Tunable target agents: small deterministic stand-ins for the
agents a tuning loop would keep sharp.

These are NOT the sibling pipeline's agents. They mirror the
decision logic (rubric routing, QA gating, publish gating) in a
form whose behavior is fully controlled by a config dict, so the
reflect/synthesize loop has something real to adjust and the
benchmark gate has something real to measure. Each agent is a pure
function of (case, config): same inputs, same outputs, every time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CRITERIA = ("sharpness", "composition", "color", "plating")
STEP = 0.05
THRESHOLD_FLOOR = 0.30
THRESHOLD_CAP = 0.95


def _check_threshold(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {value!r}")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1, got {value!r}")
    return value


@dataclass(frozen=True)
class RouterConfig:
    """Rubric thresholds: enhance when any score falls below its bar."""

    thresholds: dict = field(
        default_factory=lambda: {
            "sharpness": 0.70,
            "composition": 0.70,
            "color": 0.70,
            "plating": 0.70,
        }
    )
    plating_realistic_required: bool = True

    def __post_init__(self):
        clean = {}
        for key in CRITERIA:
            if key not in self.thresholds:
                raise ValueError(f"router threshold missing: {key}")
            clean[key] = _check_threshold(self.thresholds[key], key)
        object.__setattr__(self, "thresholds", clean)

    def with_thresholds(self, **updates):
        merged = dict(self.thresholds)
        merged.update(updates)
        return RouterConfig(
            thresholds=merged,
            plating_realistic_required=self.plating_realistic_required,
        )


@dataclass(frozen=True)
class QAConfig:
    """Which candidate failure classes block, and the score floor."""

    blocked_classes: frozenset = frozenset({"added", "removed"})
    score_floor: float = 0.60

    def __post_init__(self):
        object.__setattr__(
            self, "blocked_classes", frozenset(self.blocked_classes))
        object.__setattr__(
            self, "score_floor", _check_threshold(self.score_floor, "floor"))

    def with_blocked(self, classes, floor=None):
        return QAConfig(
            blocked_classes=frozenset(classes),
            score_floor=self.score_floor if floor is None else floor,
        )


@dataclass(frozen=True)
class PublishConfig:
    """Standard publishes unless a policy flag is set; strict also
    requires zero failure classes in the candidate."""

    mode: str = "standard"

    def __post_init__(self):
        if self.mode not in ("standard", "strict"):
            raise ValueError(f"bad publish mode: {self.mode!r}")


@dataclass(frozen=True)
class AgentConfig:
    """One version of the whole target system."""

    name: str
    router: RouterConfig = field(default_factory=RouterConfig)
    qa: QAConfig = field(default_factory=QAConfig)
    publish: PublishConfig = field(default_factory=PublishConfig)

    def describe(self):
        return {
            "name": self.name,
            "router_thresholds": dict(self.router.thresholds),
            "qa_blocked": sorted(self.qa.blocked_classes),
            "qa_floor": self.qa.score_floor,
            "publish_mode": self.publish.mode,
        }


BASELINE = AgentConfig(name="baseline")


@dataclass(frozen=True)
class QAResult:
    passed: bool
    failure_classes: tuple
    reasons: tuple


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    route: str
    qa_passed: bool
    qa_failure_classes: tuple
    published_variant: str
    passed: bool  # route AND publish both match the label


def route(case, config: RouterConfig) -> str:
    """Enhance when any rubric score falls below its bar, or when
    plating is unrealistic and that check is required."""
    if config.plating_realistic_required and not case.plating_realistic:
        return "enhance"
    for key in CRITERIA:
        if case.scores[key] < config.thresholds[key]:
            return "enhance"
    return "skip"


def qa_gate(case, config: QAConfig) -> QAResult:
    """Judge the edited candidate: blocked failure classes and the
    score floor both fail it. Unblocked classes are reported but
    do not fail -- that gap is exactly what the tuning loop finds."""
    classes = []
    reasons = []
    for cls in case.failure_flags:
        if cls in config.blocked_classes:
            classes.append(cls)
            reasons.append(f"candidate has blocked class: {cls}")
        else:
            reasons.append(f"candidate has unblocked class: {cls}")
    for key in CRITERIA:
        if case.candidate_scores[key] < config.score_floor:
            classes.append("low_quality")
            reasons.append(f"candidate {key} below floor")
            break
    classes = tuple(sorted(set(classes)))
    return QAResult(
        passed=not classes, failure_classes=classes, reasons=tuple(reasons))


def publish(case, qa: QAResult, config: PublishConfig) -> str:
    """Publish the enhanced photo only if QA passed (and, in strict
    mode, the candidate carries no failure class at all). A failed
    candidate falls back to the original; a policy flag publishes
    nothing."""
    if case.policy_flag:
        return "none"
    if not qa.passed:
        return "original"
    if config.mode == "strict" and case.failure_flags:
        return "original"
    return "enhanced"


def evaluate_case(case, config: AgentConfig) -> CaseResult:
    """Run all three agents on one labeled case."""
    predicted_route = route(case, config.router)
    qa = qa_gate(case, config.qa)
    if predicted_route == "skip":
        # Skipped items are never edited: the original goes to
        # publish QA, which here means the policy check only.
        variant = "none" if case.policy_flag else "original"
        qa_for_record = QAResult(True, (), ())
    else:
        variant = publish(case, qa, config.publish)
        qa_for_record = qa
    passed = (
        predicted_route == case.expected_route
        and variant == case.expected_publish
    )
    return CaseResult(
        case_id=case.case_id,
        route=predicted_route,
        qa_passed=qa_for_record.passed,
        qa_failure_classes=qa_for_record.failure_classes,
        published_variant=variant,
        passed=passed,
    )


def published_bad(case, result: CaseResult) -> bool:
    """An enhanced publish whose candidate actually carries a
    failure class: the bad outcome the loop must drive to zero."""
    return result.published_variant == "enhanced" and bool(case.failure_flags)
