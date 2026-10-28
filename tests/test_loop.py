"""End-to-end loop tests: the demo's real numbers, locked in."""

from tuning.demo import run_demo


def test_demo_ships_on_round_two():
    numbers = run_demo()
    assert len(numbers["rounds"]) == 2
    assert numbers["rounds"][0]["ship"] is False
    assert numbers["rounds"][1]["ship"] is True
    assert numbers["shipped_version"] == 2


def test_demo_baseline_and_shipped_metrics():
    numbers = run_demo()
    assert numbers["baseline"]["recall"] == 0.667
    assert numbers["baseline"]["case_accuracy"] == 0.472
    assert numbers["baseline"]["published_bad"] == 5
    assert numbers["shipped"]["recall"] == 1.0
    assert numbers["shipped"]["case_accuracy"] == 1.0
    assert numbers["shipped"]["published_bad"] == 0


def test_demo_round_one_blocks_only_on_recall():
    numbers = run_demo()
    reasons = numbers["rounds"][0]["reasons"]
    assert reasons == ["recall 0.875 below guardrail 0.9"]


def test_demo_diagnosis_targets_both_broken_agents():
    numbers = run_demo()
    assert numbers["diagnosis_targets"] == ["publish", "router"]


def test_demo_segment_sushi_improves():
    numbers = run_demo()
    assert numbers["segment_sushi_recall_before"] == 0.5
    assert numbers["segment_sushi_recall_after"] == 1.0


def test_demo_rollback_restores_baseline_exactly():
    numbers = run_demo()
    assert numbers["rollback_version"] == 1
    assert numbers["rollback_recall"] == 0.667
    assert numbers["rollback_matches_baseline"] is True


def test_demo_runner_bad_counts_flip_with_version():
    numbers = run_demo()
    assert numbers["runner_shipped_published_bad"] == 0
    assert numbers["runner_rolled_published_bad"] == 5


def test_demo_log_covers_ship_block_and_rollback():
    numbers = run_demo()
    steps = numbers["log_steps"]
    assert "ship" in steps
    assert "block" in steps
    assert "rollback" in steps
    assert "segment_tuning" in steps
    assert numbers["log_entries"] == len(steps)
