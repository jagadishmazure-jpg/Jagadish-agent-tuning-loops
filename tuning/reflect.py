"""Reflect agent: turn raw mismatches into systemic issues.

A single mismatch is noise until proven otherwise: one bad photo,
one odd label, one transient glitch. Reflect groups mismatches by
(agent, pattern) and, within that, by segment, and only promotes a
group to a systemic issue when it recurs -- the same failure, in
more than one case. Singleton patterns are reported as noise and
never reach the synthesizer. Every issue carries its evidence:
counts and the case ids behind them.
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_SYSTEMIC_COUNT = 2


@dataclass(frozen=True)
class SystemicIssue:
    agent: str
    pattern: str
    count: int
    case_ids: tuple
    segment_hint: str  # "geo:<v>" / "dish_type:<v>" / "" when mixed

    def describe(self):
        hint = f" [{self.segment_hint}]" if self.segment_hint else ""
        return (
            f"{self.agent}/{self.pattern} x{self.count}{hint}: "
            f"{', '.join(self.case_ids)}"
        )


def reflect(mismatches, min_count=MIN_SYSTEMIC_COUNT):
    """Group mismatches; return (issues, noise_count).

    A group is (agent, pattern). Its segment hint is set only when
    every case in the group shares one geo or one dish type --
    otherwise the issue is global, not segment-shaped.
    """
    groups = {}
    for mismatch in mismatches:
        key = (mismatch.agent, mismatch.pattern)
        groups.setdefault(key, []).append(mismatch)
    issues = []
    noise = 0
    for (agent, pattern), members in sorted(groups.items()):
        if len(members) < min_count:
            noise += len(members)
            continue
        geos = {m.geo for m in members}
        dishes = {m.dish_type for m in members}
        if len(geos) == 1:
            hint = f"geo:{next(iter(geos))}"
        elif len(dishes) == 1:
            hint = f"dish_type:{next(iter(dishes))}"
        else:
            hint = ""
        issues.append(
            SystemicIssue(
                agent=agent,
                pattern=pattern,
                count=len(members),
                case_ids=tuple(sorted(m.case_id for m in members)),
                segment_hint=hint,
            )
        )
    return issues, noise
