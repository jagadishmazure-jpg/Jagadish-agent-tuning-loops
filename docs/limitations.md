# Limitations and known failures

What this repo does not do, stated plainly so the demo numbers
are never mistaken for production claims.

## Fake by design

- **Stub agents.** Router, QA gate, and publish decisions are
  threshold rules over fixture scores, not model calls. The
  loop's mechanics are real; the agents' behavior is not
  evidence about any real system.
- **Fixture labels, not human labels.** Golden cases were
  labeled by applying a written guide in code. No labelers
  were involved, no inter-rater agreement was measured, and
  label noise -- the thing reflect is built to filter -- is
  only simulated by construction (singletons are noise by
  definition here).
- **Derived conversion outcomes.** Demo outcomes come from
  baseline pass/fail, not observed purchases. Segment flags
  in the demo show the flagging mechanism working, not real
  segment performance.

## Known misses (visible as behavior, not hidden)

- **Floor-boundary publishes.** A candidate scoring exactly at
  the QA floor passes (the floor is a strict `<` check). The
  demo's shipped config reaches gold behavior, but a future
  floor change could reintroduce boundary publishes; the
  published-bad metric is the backstop, not the floor.
- **Global config, segment validation.** Segment tuning is
  diagnosed and validated per segment, but the shipped config
  applies everywhere. A fix that helps sushi and hurts curry
  would be caught by the global accuracy gate, but a fix
  that helps sushi and is merely neutral elsewhere ships
  without per-segment overrides (Planned).
- **Synthesizer scope.** Threshold steps and blocked-class
  edits only. It cannot add a rubric criterion, rewrite a
  prompt, or split a segment's policy. Unknown patterns leave
  the config unchanged by design -- which means a genuinely
  new failure mode stalls the loop until a human extends the
  synthesizer.

## Not built

- Per-segment config overrides; prompt-rewriting synthesis;
  live-model adapters; hash-chained tuning log; signed run
  records; any deployment. See the Built vs planned table in
  the README.
