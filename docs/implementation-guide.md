# Implementation guide

How to adopt this loop for your own agent system.

## 1. Replace the stubs, keep the loop

The loop (sampler -> diagnoser -> reflect -> synthesize ->
benchmark -> store) does not care what the target agents are.
Replace `tuning/agents.py` with adapters over your real agents:
each adapter must expose the same three decisions the stubs do
(route, QA verdict, publish verdict) as pure functions of
(case, config). Keep configs plain data (thresholds, blocked
sets, modes) so the synthesizer can rewrite them and the store
can version them.

## 2. Bring a real golden set

Replace `tuning/labels.py` with labels collected from your own
labelers under a written guide (see `knowledge/labeling-guide.md`
for the shape of such a guide: objective criteria, worked
examples, and the bar for each decision). Keep the cut
coverage check: a golden set that covers one geography, one
dish type, or one quality tier will tune you toward that slice
and away from the rest.

## 3. Feed real run logs

The sampler reads flat JSON records with the sibling schema
keys (`run_id, route, published_variant, ...`). If your
pipeline logs nested traces, flatten one record per run first:
the sampler's join key is `run_id` -> golden case id, and its
segment keys are optional `geo`/`device` extras.

## 4. Set the guardrail before the first tuning run

`GUARDRAIL_RECALL` in `tuning/benchmark.py` is 0.90 for the
demo. Pick yours from the cost of the failure you fear most:
a bad item approved (recall guardrail) vs a good item
reworked (precision cost). The gate ships only when recall,
accuracy, regressions, and published-bad all pass.

## 5. Operate it

- Sample at a fixed cadence; alert when the mismatch rate
  crosses your threshold, not on every single mismatch.
- Read the tuning log, not the dashboard, when a ship looks
  wrong: every step is append-only and replayable.
- Roll back first, investigate second. Rollback is one call
  and restores exact prior behavior; a bad ship costs more
  the longer it runs.
- Never ship a candidate the gate blocked by hand-editing the
  store. If the gate is wrong, fix the gate (and its tests),
  not the version history.
