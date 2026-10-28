"""Diagnoser: one component over MANY feedback-loop types.

Production systems do not have one feedback channel; they have
several, and each lies in its own way. The diagnoser ingests all
three loop types this repo models, weighs them together, and
localizes WHICH agent(s) need tuning -- one agent, or several:

1. Drift mismatches: sampled production runs vs golden labels.
2. Dogfooding signals: thumbs up/down plus free-form feedback
   from merchants, design, and product teams.
3. Production outcomes: conversion (add-to-cart, order completion)
   sliced by segment (geo, device, dish type).

It replays flagged examples -- good and bad -- through the current
config before any config change, so a diagnosis is evidence, not a
hunch. A segment whose conversion trails the global rate by more
than the drop threshold is flagged, and is attributed to an agent
only when that segment's cases also mismatch on that agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from .agents import evaluate_case

CONVERSION_DROP_THRESHOLD = 0.10
SOURCES = ("merchant", "design", "product")


@dataclass(frozen=True)
class DogfoodSignal:
    case_id: str
    source: str  # merchant | design | product
    sentiment: str  # "up" | "down"
    text: str = ""
    agent_hint: str = ""  # "router" | "qa" | "publish" | ""

    def __post_init__(self):
        if self.source not in SOURCES:
            raise ValueError(f"unknown dogfood source: {self.source!r}")
        if self.sentiment not in ("up", "down"):
            raise ValueError(f"bad sentiment: {self.sentiment!r}")
        if self.agent_hint not in ("", "router", "qa", "publish"):
            raise ValueError(f"bad agent hint: {self.agent_hint!r}")


@dataclass(frozen=True)
class OutcomeRecord:
    case_id: str
    geo: str
    device: str
    dish_type: str
    added_to_cart: bool
    order_completed: bool


@dataclass(frozen=True)
class Diagnosis:
    targets: tuple  # agent names, sorted, empty when nothing to tune
    evidence: dict  # agent -> {"mismatches": n, "dogfood_down": n}
    segment_flags: tuple  # (dimension, value, rate, global_rate)
    replayed: tuple  # case_ids replayed (good and bad)
    replay_results: tuple  # CaseResult per replayed case


def segment_conversion(outcomes):
    """Order-completion rate per segment dimension value."""
    totals = {}
    completed = {}
    for outcome in outcomes:
        for dimension, value in (
            ("geo", outcome.geo),
            ("device", outcome.device),
            ("dish_type", outcome.dish_type),
        ):
            key = (dimension, value)
            totals[key] = totals.get(key, 0) + 1
            completed[key] = completed.get(key, 0) + int(
                outcome.order_completed)
    return {
        key: round(completed[key] / totals[key], 3) for key in totals
    }


def replay(case_ids, config, golden_cases):
    """Re-run the current config on flagged examples, good and bad,
    and return the fresh results. Nothing is tuned from a replay
    alone; it exists so the diagnosis cites current behavior."""
    by_id = {c.case_id: c for c in golden_cases}
    results = []
    for case_id in case_ids:
        case = by_id.get(case_id)
        if case is not None:
            results.append(evaluate_case(case, config))
    return results


def diagnose(mismatches, dogfood, outcomes, golden_cases, config):
    """Localize tuning targets across all three loop types."""
    evidence = {}
    for mismatch in mismatches:
        slot = evidence.setdefault(
            mismatch.agent, {"mismatches": 0, "dogfood_down": 0})
        slot["mismatches"] += 1
    for signal in dogfood:
        if signal.sentiment == "down" and signal.agent_hint:
            slot = evidence.setdefault(
                signal.agent_hint, {"mismatches": 0, "dogfood_down": 0})
            slot["dogfood_down"] += 1
    rates = segment_conversion(outcomes)
    global_rate = (
        round(
            sum(1 for o in outcomes if o.order_completed) / len(outcomes), 3
        )
        if outcomes
        else 0.0
    )
    segment_flags = []
    for (dimension, value), rate in sorted(rates.items()):
        if global_rate - rate > CONVERSION_DROP_THRESHOLD:
            segment_flags.append((dimension, value, rate, global_rate))
    # Attribute a flagged segment to an agent only when that
    # segment's cases also mismatch on that agent.
    flagged_values = {value for _, value, _, _ in segment_flags}
    for mismatch in mismatches:
        segment_values = {mismatch.geo, mismatch.device, mismatch.dish_type}
        if segment_values & flagged_values:
            evidence.setdefault(
                mismatch.agent, {"mismatches": 0, "dogfood_down": 0})
    targets = tuple(sorted(evidence))
    flagged_ids = sorted(
        {m.case_id for m in mismatches}
        | {s.case_id for s in dogfood if s.sentiment == "down"}
    )
    # Replay flagged examples plus an equal number of clean ones,
    # so the diagnosis shows both sides.
    clean_ids = sorted(
        c.case_id for c in golden_cases if c.case_id not in flagged_ids
    )
    replay_ids = tuple(flagged_ids + clean_ids[: len(flagged_ids)])
    replay_results = tuple(replay(replay_ids, config, golden_cases))
    return Diagnosis(
        targets=targets,
        evidence=evidence,
        segment_flags=tuple(segment_flags),
        replayed=replay_ids,
        replay_results=replay_results,
    )
