# ADR-001: Stub agents instead of the sibling pipeline

## Context

The sibling repo (visual-content-agents) already implements a
full pipeline: describe, route, edit loop, QA gate, publish QA.
The tuning loop needs target agents to tune, and the obvious
move is to import the sibling's agents and tune them.

## Decision

Use small deterministic stub agents that mirror the siblings'
decision logic (rubric routing, QA gating, publish gating) but
are fully controlled by config dicts.

## Rationale

- **Tuning needs a config surface.** The sibling's agents have
  fixed rules; there is nothing for a synthesizer to rewrite.
  Stubs make thresholds, blocked classes, and modes explicit
  parameters, which is what makes synthesize/benchmark/store
  testable.
- **Independence.** This repo must run, test, and demo alone,
  without a sibling checkout. A hard dependency would couple
  two repos' test suites and break the one-writer-per-repo
  rule.
- **Compatibility where it matters.** The contract with the
  sibling is the run-log schema, not its code: this repo reads
  sibling-format records unchanged, and its simulated records
  carry the same keys.

## Consequences

- The loop proves machinery, not sibling improvement. The
  README and limitations doc say so.
- An adopter replaces the stubs with adapters (see
  `docs/implementation-guide.md`); the loop code does not
  change.
