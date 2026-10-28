"""Benchmark gate: a candidate ships ONLY if it proves itself
against the golden set.

Metrics, all computed on the golden set:
- router recall on the "needs enhancement" class -- THE guardrail.
  A bad item approved as-is is the failure to minimize.
- router precision and accuracy.
- case accuracy: fraction of cases where route AND publish both
  match the label.
- published_bad: enhanced publishes whose candidate actually
  carries a failure class. Must be zero.
- regressions: cases that passed under the baseline config and
  fail under the candidate. Any regression BLOCKS the candidate,
  and the diff names the cases.

Ship rule: recall >= guardrail AND case accuracy >= baseline
AND no regressions AND published_bad == 0. Anything else blocks
with reasons. The gate never ships on a promise.
"""

from __future__ import annotations

from dataclasses import dataclass

from .agents import evaluate_case, published_bad

GUARDRAIL_RECALL = 0.90


@dataclass(frozen=True)
class BenchmarkResult:
    config_name: str
    cases: int
    precision: float
    recall: float
    router_accuracy: float
    case_accuracy: float
    published_bad: int
    passed_case_ids: tuple
    failed_case_ids: tuple


def _rate(numerator, denominator):
    return round(numerator / denominator, 3) if denominator else 0.0


def benchmark(config, cases):
    """Run a config over the golden set and score it."""
    results = [evaluate_case(c, config) for c in cases]
    by_id = {c.case_id: c for c in cases}
    tp = fp = fn = tn = 0
    passed = []
    failed = []
    bad = 0
    for result in results:
        case = by_id[result.case_id]
        needs = case.expected_route == "enhance"
        routed = result.route == "enhance"
        if needs and routed:
            tp += 1
        elif needs and not routed:
            fn += 1
        elif not needs and routed:
            fp += 1
        else:
            tn += 1
        if result.passed:
            passed.append(result.case_id)
        else:
            failed.append(result.case_id)
        if published_bad(case, result):
            bad += 1
    return BenchmarkResult(
        config_name=config.name,
        cases=len(cases),
        precision=_rate(tp, tp + fp),
        recall=_rate(tp, tp + fn),
        router_accuracy=_rate(tp + tn, len(cases)),
        case_accuracy=_rate(len(passed), len(cases)),
        published_bad=bad,
        passed_case_ids=tuple(sorted(passed)),
        failed_case_ids=tuple(sorted(failed)),
    )


@dataclass(frozen=True)
class ShipDecision:
    ship: bool
    reasons: tuple
    regressions: tuple  # case_ids passing under baseline, failing now


def ship_decision(candidate: BenchmarkResult, baseline: BenchmarkResult):
    """Decide ship vs block. A regression blocks even when every
    aggregate metric improves: aggregates hide single-case harm."""
    regressions = tuple(
        sorted(set(baseline.passed_case_ids) - set(candidate.passed_case_ids))
    )
    reasons = []
    if candidate.recall < GUARDRAIL_RECALL:
        reasons.append(
            f"recall {candidate.recall} below guardrail {GUARDRAIL_RECALL}")
    if candidate.case_accuracy < baseline.case_accuracy:
        reasons.append(
            f"case accuracy {candidate.case_accuracy} below baseline "
            f"{baseline.case_accuracy}")
    if regressions:
        reasons.append(f"regressions: {', '.join(regressions)}")
    if candidate.published_bad > 0:
        reasons.append(f"published_bad {candidate.published_bad} > 0")
    ship = not reasons
    if ship:
        reasons = ["all guardrails pass"]
    return ShipDecision(
        ship=ship,
        reasons=tuple(reasons),
        regressions=regressions,
    )


def segment_metrics(config, cases):
    """Benchmark metrics sliced by segment dimension value."""
    out = {}
    for dimension in ("geo", "device", "dish_type"):
        groups = {}
        for case in cases:
            groups.setdefault(getattr(case, dimension), []).append(case)
        for value, members in sorted(groups.items()):
            result = benchmark(config, members)
            out[(dimension, value)] = {
                "cases": result.cases,
                "recall": result.recall,
                "case_accuracy": result.case_accuracy,
                "published_bad": result.published_bad,
            }
    return out
