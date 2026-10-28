# Feedback loops

Three loop types feed the diagnoser. Each is described here
in the form the code consumes it.

## 1. Drift loop (labels vs production)

- **Input:** sampled production run records + golden labels.
- **Signal:** mismatches, grouped by (agent, pattern).
- **Cadence:** every sampling run (the demo samples the full
  batch; production would sample every Nth record).
- **Failure mode it catches:** gradual drift -- a router bar
  that fit last quarter's photos but not this quarter's.
- **Trust level:** high, when labels are fresh. Stale labels
  invert the loop: it tunes toward yesterday's truth.

## 2. Dogfooding loop (internal testing)

- **Input:** thumbs up/down + free-form text from merchants,
  design, and product teams, each optionally hinting an agent.
- **Signal:** down-signals with an agent hint localize that
  agent directly; up-signals never create a tuning target.
- **Failure mode it catches:** experience problems labels
  miss -- a photo that is technically fine but off-brand, or
  a policy edge the rubric never stated.
- **Trust level:** medium. A hint localizes, but a wrong
  target is harmless: its candidate still faces the benchmark
  gate, and a candidate that does not improve golden metrics
  does not ship.

## 3. Production outcome loop (conversion by segment)

- **Input:** per-item outcomes (added to cart, order
  completed) sliced by geo, device, and dish type.
- **Signal:** a segment trailing the global rate by more
  than 0.10 is flagged.
- **Failure mode it catches:** segment-specific decay --
  one dish type or geography degrading while global metrics
  look healthy.
- **Trust level:** low alone, high in triangulation. A
  conversion flag is attributed to an agent only when that
  segment's cases also mismatch on that agent.

## What the diagnoser does with all three

It does not average them. It localizes: each loop type votes
for agents (mismatches directly, dogfooding by hint,
conversion by segment attribution), and the union of voted
agents becomes the tuning target set. Then it replays flagged
examples -- good and bad -- so the diagnosis cites current
behavior, not stale reports.
