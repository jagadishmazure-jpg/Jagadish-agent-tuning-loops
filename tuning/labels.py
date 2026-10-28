"""Golden label set: the source of truth for every tuning decision.

Labels are fixture data, NOT collected human labels. Each case was
assigned by applying the written labeling guide (see
``knowledge/labeling-guide.md``): the guide states the bar, the
fixture code applies it, and the test suite checks a hand-picked
sample of cases against the guide literally. The honest statement
is: these labels stand in for a human-labeled golden set, so the
loop machinery -- sampling, diagnosis, tuning, gating -- can be
proven offline. They are not a quality claim about any real system.

A case is one marketplace item: quality scores, candidate flags,
segment cuts, and the expected decisions. The gold bar and gold QA
rule below ARE the labeling guide in code form.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Labeling guide, in code form (see knowledge/labeling-guide.md).
GOLD_ROUTER_BAR = 0.80
GOLD_QA_FLOOR = 0.70
GOLD_QA_BLOCKED = frozenset(
    {"added", "removed", "generic", "incoherent", "count_unknown"}
)
FAILURE_CLASSES = ("added", "removed", "generic", "incoherent", "count_unknown")

GEOS = ("us-midwest", "us-west", "eu-west")
DEVICES = ("ios", "android", "web")
DISH_TYPES = ("burger", "sushi", "curry", "dessert")
QUALITY_TIERS = ("low", "mid", "high")


def _score(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {value!r}")
    value = float(value)
    if math.isnan(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1, got {value!r}")
    return value


@dataclass(frozen=True)
class GoldenCase:
    """One labeled item: what the agents SHOULD have decided.

    ``scores`` are the item's quality scores (sharpness, composition,
    color, plating). ``candidate_scores`` are the post-edit scores the
    QA gate judges. ``expected_route`` / ``expected_publish`` are the
    labels; ``geo`` / ``device`` / ``dish_type`` are the segment cuts.
    """

    case_id: str
    dish: str
    merchant: str
    geo: str
    device: str
    dish_type: str
    quality_tier: str
    sharpness: float
    composition: float
    color: float
    plating: float
    plating_realistic: bool = True
    count_verified: bool = True
    candidate_sharpness: float = 1.0
    candidate_composition: float = 1.0
    candidate_color: float = 1.0
    candidate_plating: float = 1.0
    added_objects: bool = False
    removed_objects: bool = False
    generic_fallback: bool = False
    incoherent: bool = False
    count_known: bool = True
    policy_flag: bool = False
    expected_route: str = "skip"
    expected_publish: str = "original"

    def __post_init__(self):
        for name in ("sharpness", "composition", "color", "plating",
                     "candidate_sharpness", "candidate_composition",
                     "candidate_color", "candidate_plating"):
            object.__setattr__(self, name, _score(getattr(self, name), name))
        if self.expected_route not in ("enhance", "skip"):
            raise ValueError(f"bad expected_route: {self.expected_route!r}")
        if self.expected_publish not in ("enhanced", "original", "none"):
            raise ValueError(
                f"bad expected_publish: {self.expected_publish!r}")
        if self.geo not in GEOS:
            raise ValueError(f"unknown geo cut: {self.geo!r}")
        if self.dish_type not in DISH_TYPES:
            raise ValueError(f"unknown dish cut: {self.dish_type!r}")
        if self.quality_tier not in QUALITY_TIERS:
            raise ValueError(f"unknown tier cut: {self.quality_tier!r}")

    @property
    def scores(self):
        return {
            "sharpness": self.sharpness,
            "composition": self.composition,
            "color": self.color,
            "plating": self.plating,
        }

    @property
    def candidate_scores(self):
        return {
            "sharpness": self.candidate_sharpness,
            "composition": self.candidate_composition,
            "color": self.candidate_color,
            "plating": self.candidate_plating,
        }

    @property
    def failure_flags(self):
        """Failure classes present in this item's edited candidate."""
        flags = []
        if self.added_objects:
            flags.append("added")
        if self.removed_objects:
            flags.append("removed")
        if self.generic_fallback:
            flags.append("generic")
        if self.incoherent:
            flags.append("incoherent")
        if not self.count_known:
            flags.append("count_unknown")
        return tuple(flags)

    def guide_route(self):
        """Route the labeling guide itself assigns (bar 0.80)."""
        if not self.plating_realistic:
            return "enhance"
        if min(self.scores.values()) < GOLD_ROUTER_BAR:
            return "enhance"
        return "skip"

    def guide_publish(self):
        """Publish outcome the labeling guide itself assigns."""
        if self.policy_flag:
            return "none"
        if self.expected_route == "skip":
            return "original"
        blocked = [f for f in self.failure_flags if f in GOLD_QA_BLOCKED]
        low = any(
            v < GOLD_QA_FLOOR
            for v in (
                self.candidate_sharpness,
                self.candidate_composition,
                self.candidate_color,
                self.candidate_plating,
            )
        )
        if blocked or low:
            return "original"
        return "enhanced"


def _tier_scores(tier, dish_type, index):
    """Deterministic scores per tier.

    Mid-tier sushi sits just ABOVE the miscalibrated baseline bar
    (0.70) but BELOW the guide bar (0.80): the underperforming
    segment the tuning loop must find and fix.
    """
    base = {"low": 0.45, "mid": 0.70, "high": 0.90}[tier]
    if tier == "mid" and dish_type == "sushi":
        base = 0.74
    elif tier == "mid":
        base = 0.68
    jitter = (index % 5) * 0.01
    return {
        "sharpness": round(min(1.0, base + jitter), 3),
        "composition": round(min(1.0, base + 0.02 + jitter), 3),
        "color": round(min(1.0, base + 0.01 + jitter), 3),
        "plating": round(min(1.0, base + 0.03 + jitter), 3),
    }


def build_golden_set():
    """36 cases: 3 geos x 4 dish types x 3 quality tiers.

    Expected decisions follow the labeling guide. A few cases carry
    candidate failure flags and policy flags so the QA and publish
    agents have something real to get wrong.
    """
    cases = []
    index = 0
    for geo in GEOS:
        for dish_type in DISH_TYPES:
            for tier in QUALITY_TIERS:
                scores = _tier_scores(tier, dish_type, index)
                candidate = {
                    k: round(min(1.0, v + 0.20), 3)
                    for k, v in scores.items()
                }
                case = GoldenCase(
                    case_id=f"case-{index:02d}",
                    dish=f"{dish_type}-{tier}-{geo}",
                    merchant=f"merchant-{index % 6:02d}",
                    geo=geo,
                    device=DEVICES[(index // 4) % len(DEVICES)],
                    dish_type=dish_type,
                    quality_tier=tier,
                    sharpness=scores["sharpness"],
                    composition=scores["composition"],
                    color=scores["color"],
                    plating=scores["plating"],
                    plating_realistic=not (index % 13 == 0 and tier == "low"),
                    count_verified=True,
                    candidate_sharpness=candidate["sharpness"],
                    candidate_composition=candidate["composition"],
                    candidate_color=candidate["color"],
                    candidate_plating=candidate["plating"],
                    added_objects=(index % 17 == 0),
                    removed_objects=(index % 19 == 0),
                    generic_fallback=(index % 7 == 0),
                    incoherent=(index % 9 == 0),
                    count_known=not (index % 11 == 0),
                    policy_flag=(index == 23),
                    expected_route="skip",
                    expected_publish="original",
                )
                # Labels follow the guide; assign them after construction
                # so the guide rule is the single source of truth.
                object.__setattr__(
                    case, "expected_route", case.guide_route())
                object.__setattr__(
                    case, "expected_publish", case.guide_publish())
                cases.append(case)
                index += 1
    return cases


def cuts_covered(cases):
    """Check the set is representative across every cut dimension."""
    return {
        "geos": sorted({c.geo for c in cases}) == sorted(GEOS),
        "dish_types": sorted({c.dish_type for c in cases}) == sorted(DISH_TYPES),
        "quality_tiers": sorted({c.quality_tier for c in cases})
        == sorted(QUALITY_TIERS),
        "devices": sorted({c.device for c in cases}) == sorted(DEVICES),
        "routes": sorted({c.expected_route for c in cases})
        == ["enhance", "skip"],
        "publishes": sorted({c.expected_publish for c in cases})
        == ["enhanced", "none", "original"],
    }
