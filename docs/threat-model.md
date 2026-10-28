# Threat model

This repo runs offline on fixture data, so there is no user
data to breach and nothing deployed. The threats that matter
are to the integrity of the loop itself -- the ways a tuning
system can be made to ship harm while reporting improvement.

## STRIDE sketch

- **Spoofing:** a forged run record (wrong `run_id`) joins to
  the wrong golden case and manufactures mismatches. Mitigation:
  the sampler counts unmatched records separately and never
  treats a malformed record as a mismatch; in production, sign
  run records at emission (Planned).
- **Tampering:** editing the tuning log to hide a bad ship.
  Mitigation: append-only API with no delete/edit/truncate;
  hash-chaining the log is Planned (the sibling repos use it
  for audit ledgers).
- **Repudiation:** a ship with no record of who approved what.
  Mitigation: every step (sample, mismatch, diagnosis,
  candidate, benchmark, ship/block, rollback) is logged with
  its payload; the store refuses registration without a
  passing ship decision.
- **Information disclosure:** golden labels or run records
  leaking merchant or customer data. Mitigation: all data here
  is synthetic; in production, redact before logging (the
  sibling trace repo demonstrates redact-before-store).
- **Denial of service:** a flood of mismatches triggering
  endless tuning rounds. Mitigation: the loop caps at three
  rounds per invocation and synthesizes nothing from unknown
  patterns.
- **Elevation of privilege:** hand-editing the store to ship a
  blocked candidate. Mitigation: `register()` enforces the
  gate in code, not in documentation; the test suite covers
  the absent, reject, and bypass paths.

## OWASP LLM Top 10 (where relevant)

- **LLM09 (overreliance / misinformation):** the loop trusts
  golden labels absolutely. If the labels are wrong, tuning
  converges on wrong behavior. Mitigation: the labeling guide
  is written, versioned, and checked for cut coverage; label
  audits are a Planned operational practice.
- **LLM10 (unbounded consumption):** tuning rounds and
  production sampling are both capped (three rounds; cadence
  sampling), so a pathological batch cannot loop forever.

## Out of scope

Real-model prompt injection, data exfiltration through model
outputs, and multi-tenant isolation are not modeled here: the
agents are stubs with no model calls. They belong to the
adopter's agent layer, not to this loop.
