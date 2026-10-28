# ADR-002: Global config, segment-scoped validation

## Context

Production tuning often wants per-segment behavior: one dish
type, one geography, or one device class needs different
thresholds. The alternative is one global config validated
per segment.

## Decision

Ship a global config; diagnose and validate per segment.

## Rationale

- **A global config keeps the gate honest.** One benchmark
  over the whole golden set, one regression check, one
  rollback target. Per-segment configs multiply the version
  space (segments x versions) and make rollback ambiguous:
  which segment's version rolls back?
- **Segment diagnosis still finds the problem.** The
  diagnoser flags underperforming segments and attributes
  them to agents; the benchmark reports per-segment recall
  and accuracy. A fix driven by sushi evidence must still
  pass globally, so segment wins cannot hide global harm.
- **The demo proves the property that matters:** sushi
  recall 0.5 -> 1.0 with global recall 0.667 -> 1.0 and no
  regressions. The shipped config is global; the validation
  is sliced.

## Consequences

- A segment that genuinely needs different thresholds cannot
  be served yet; per-segment overrides are Planned and will
  need their own versioning and rollback semantics.
- Segment flags from conversion alone never retune an agent:
  attribution requires corroborating mismatches on that
  agent in that segment.
