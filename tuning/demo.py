"""End-to-end demo: one full tuning loop, start to finish.

Baseline config (router bar 0.70, QA floor 0.60, two blocked
classes) runs a production batch over the golden set. The sampler
finds its disagreements with the labels, the diagnoser localizes
targets across drift, dogfooding, and conversion signals, reflect
separates systemic issues from noise, synthesize proposes a
candidate, and the benchmark gate ships or blocks it. A blocked
candidate becomes the next round's current config; the loop runs
at most three rounds. Afterwards the shipped config is validated
per segment, and rollback is proven by restoring the baseline
config and re-benchmarking it.

All numbers printed here come from real runs of this code.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from .agents import BASELINE, evaluate_case
from .benchmark import benchmark, segment_metrics, ship_decision
from .diagnoser import OutcomeRecord, diagnose, DogfoodSignal
from .labels import build_golden_set
from .log import TuningLog
from .reflect import reflect
from .runner import run_production
from .sampler import find_mismatches, sample_records
from .store import ConfigStore
from .synthesize import synthesize

MAX_ROUNDS = 3


def _dogfood_signals():
    """Three dogfooding signals: two downs that corroborate the
    drift evidence, one up that must not create a target."""
    return [
        DogfoodSignal(
            case_id="case-16",
            source="merchant",
            sentiment="down",
            text="bad photo stayed on the menu",
            agent_hint="router",
        ),
        DogfoodSignal(
            case_id="case-27",
            source="design",
            sentiment="down",
            text="edited photo hides the dish",
            agent_hint="publish",
        ),
        DogfoodSignal(
            case_id="case-05",
            source="product",
            sentiment="up",
            text="good photo, left alone",
            agent_hint="",
        ),
    ]


def run_demo(log_path=None):
    """Run the full loop; return every number the README quotes."""
    cases = build_golden_set()
    store = ConfigStore(BASELINE)
    baseline_result = benchmark(BASELINE, cases)
    log = TuningLog(
        log_path or Path(tempfile.mkdtemp()) / "tuning-log.jsonl")

    current = BASELINE
    records = run_production(cases, current)
    sampled = sample_records(records, cadence=1)
    log.append("sample", {"sampled": len(sampled), "total": len(records)})
    mismatches, unmatched = find_mismatches(sampled, cases)
    log.append(
        "mismatch",
        {"mismatches": len(mismatches), "unmatched": unmatched})
    outcomes = [
        OutcomeRecord(
            case_id=case.case_id,
            geo=case.geo,
            device=case.device,
            dish_type=case.dish_type,
            added_to_cart=evaluate_case(case, BASELINE).passed,
            order_completed=evaluate_case(case, BASELINE).passed,
        )
        for case in cases
    ]
    diagnosis = diagnose(
        mismatches, _dogfood_signals(), outcomes, cases, current)
    log.append(
        "diagnosis",
        {
            "targets": list(diagnosis.targets),
            "segment_flags": [
                [d, v, r, g] for d, v, r, g in diagnosis.segment_flags
            ],
            "replayed": len(diagnosis.replayed),
        },
    )
    issues, noise = reflect(mismatches)
    first_mismatches = len(mismatches)
    first_issues = len(issues)
    first_noise = noise

    rounds = []
    shipped = None
    shipped_result = None
    shipped_version = None
    for round_no in range(1, MAX_ROUNDS + 1):
        candidate = synthesize(current, issues)
        if candidate is current or candidate == current:
            rounds.append({"round": round_no, "no_change": True})
            break
        candidate_result = benchmark(candidate, cases)
        decision = ship_decision(candidate_result, baseline_result)
        log.append("candidate", candidate.describe())
        log.append(
            "benchmark",
            {
                "config": candidate.name,
                "recall": candidate_result.recall,
                "case_accuracy": candidate_result.case_accuracy,
                "published_bad": candidate_result.published_bad,
            },
        )
        rounds.append(
            {
                "round": round_no,
                "thresholds": dict(candidate.router.thresholds),
                "qa_floor": candidate.qa.score_floor,
                "qa_blocked": sorted(candidate.qa.blocked_classes),
                "recall": candidate_result.recall,
                "case_accuracy": candidate_result.case_accuracy,
                "published_bad": candidate_result.published_bad,
                "ship": decision.ship,
                "reasons": list(decision.reasons),
            }
        )
        if decision.ship:
            shipped_version = store.register(candidate, decision)
            log.append("ship", {"version": shipped_version})
            shipped = candidate
            shipped_result = candidate_result
            break
        log.append("block", {"reasons": list(decision.reasons)})
        current = candidate
        records = run_production(cases, current)
        sampled = sample_records(records, cadence=1)
        mismatches, unmatched = find_mismatches(sampled, cases)
        issues, noise = reflect(mismatches)

    # Segment validation: the shipped config must improve the worst
    # segment without degrading the global metrics.
    seg_before = segment_metrics(BASELINE, cases)
    seg_after = segment_metrics(shipped, cases) if shipped else {}
    sushi_before = seg_before.get(("dish_type", "sushi"), {})
    sushi_after = seg_after.get(("dish_type", "sushi"), {})
    log.append(
        "segment_tuning",
        {
            "segment": ["dish_type", "sushi"],
            "recall_before": sushi_before.get("recall"),
            "recall_after": sushi_after.get("recall"),
            "global_recall_before": baseline_result.recall,
            "global_recall_after": shipped_result.recall if shipped else None,
        },
    )

    # Rollback proof: restoring the previous version restores its
    # exact benchmark behavior.
    rolled = store.rollback()
    rolled_result = benchmark(rolled, cases)
    log.append("rollback", {"version": store.current_version()})
    shipped_records = run_production(cases, shipped) if shipped else []
    rolled_records = run_production(cases, rolled)
    shipped_bad = sum(
        1
        for r in shipped_records
        if r["published_variant"] == "enhanced" and r["failure_classes"]
    )
    rolled_bad = sum(
        1
        for r in rolled_records
        if r["published_variant"] == "enhanced" and r["failure_classes"]
    )

    return {
        "golden_size": len(cases),
        "baseline": {
            "recall": baseline_result.recall,
            "precision": baseline_result.precision,
            "case_accuracy": baseline_result.case_accuracy,
            "published_bad": baseline_result.published_bad,
        },
        "round1_mismatches": first_mismatches,
        "round1_issues": first_issues,
        "round1_noise": first_noise,
        "diagnosis_targets": list(diagnosis.targets),
        "segment_flags": [
            [d, v, r, g] for d, v, r, g in diagnosis.segment_flags
        ],
        "rounds": rounds,
        "shipped_version": shipped_version,
        "shipped": (
            {
                "recall": shipped_result.recall,
                "case_accuracy": shipped_result.case_accuracy,
                "published_bad": shipped_result.published_bad,
            }
            if shipped_result
            else None
        ),
        "segment_sushi_recall_before": sushi_before.get("recall"),
        "segment_sushi_recall_after": sushi_after.get("recall"),
        "rollback_version": store.current_version(),
        "rollback_recall": rolled_result.recall,
        "rollback_matches_baseline": (
            rolled_result.recall == baseline_result.recall
            and rolled_result.case_accuracy == baseline_result.case_accuracy
        ),
        "runner_shipped_published_bad": shipped_bad,
        "runner_rolled_published_bad": rolled_bad,
        "log_entries": len(log.read_all()),
        "log_steps": [e["step"] for e in log.read_all()],
    }


def print_demo(numbers):
    """Print the demo numbers in a stable, quotable form."""
    print(f"golden cases: {numbers['golden_size']}")
    base = numbers["baseline"]
    print(
        f"baseline: recall {base['recall']}, precision "
        f"{base['precision']}, case accuracy {base['case_accuracy']}, "
        f"published_bad {base['published_bad']}"
    )
    print(f"diagnosis targets: {numbers['diagnosis_targets']}")
    print(f"segment flags: {numbers['segment_flags']}")
    for round_info in numbers["rounds"]:
        if round_info.get("no_change"):
            print(f"round {round_info['round']}: no change proposed")
            continue
        print(
            f"round {round_info['round']}: thresholds "
            f"{round_info['thresholds']}, floor {round_info['qa_floor']}, "
            f"blocked {round_info['qa_blocked']} -> recall "
            f"{round_info['recall']}, accuracy "
            f"{round_info['case_accuracy']}, published_bad "
            f"{round_info['published_bad']}, ship={round_info['ship']} "
            f"({'; '.join(round_info['reasons'])})"
        )
    shipped = numbers["shipped"]
    print(
        f"shipped v{numbers['shipped_version']}: recall "
        f"{shipped['recall']}, accuracy {shipped['case_accuracy']}, "
        f"published_bad {shipped['published_bad']}"
    )
    print(
        f"segment sushi recall: {numbers['segment_sushi_recall_before']} "
        f"-> {numbers['segment_sushi_recall_after']}"
    )
    print(
        f"rollback to v{numbers['rollback_version']}: recall "
        f"{numbers['rollback_recall']}, matches baseline: "
        f"{numbers['rollback_matches_baseline']}"
    )
    print(
        f"runner published_bad: shipped "
        f"{numbers['runner_shipped_published_bad']}, rolled "
        f"{numbers['runner_rolled_published_bad']}"
    )
    print(f"tuning log entries: {numbers['log_entries']}")
