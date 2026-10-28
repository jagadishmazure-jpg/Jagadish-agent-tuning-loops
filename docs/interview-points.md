# Interview points

Sixty-second versions of the ideas in this repo.

## "How do you keep agents good after launch?"

Most teams evaluate once, before launch, and then watch the
system decay. This repo closes the loop: golden labels are the
source of truth, production runs are sampled against them, a
diagnoser localizes which agent broke, a reflect/synthesize
pair proposes a config fix, and a benchmark gate ships it only
if recall holds, nothing regresses, and nothing bad publishes.
Configs are versioned with rollback, so a bad ship is one call
from undone.

## "Why recall as the guardrail?"

Because the failure modes are asymmetric. A bad item approved
stays customer-visible; a good item sent for rework costs
compute and time. The demo's round 1 improved every aggregate
except recall (0.875 vs a 0.90 bar) and the gate blocked it.
That block is the feature: aggregates hide single-case harm,
and the guardrail is what stops a near-miss from shipping.

## "Why one diagnoser for many feedback types?"

Drift labels, dogfooding thumbs, and conversion numbers each
lie differently. Labels are precise but slow; thumbs are fast
but noisy; conversion is real but confounded. The diagnoser
combines them and attributes a segment drop to an agent only
when that segment's cases also mismatch on that agent -- so a
conversion dip alone never retunes an innocent agent.

## "Why not just let the model rewrite its own prompts?"

Because an unconstrained self-editing loop is how you get
reward hacking: a change that improves the metric and worsens
the product. Here the synthesizer makes small, direction-
checked edits (threshold steps, blocked classes), every
candidate faces the golden set, regressions block with a diff,
and rollback is exact. The loop is closed, not unleashed.

## "What is honestly fake here?"

The agents are stubs and the labels are fixtures, not human
labels. The repo proves the machinery -- sampling, diagnosis,
tuning, gating, versioning -- not that any real agent improves
by these amounts. Saying so up front is what makes the numbers
trustworthy: every figure comes from a real run of the code.
