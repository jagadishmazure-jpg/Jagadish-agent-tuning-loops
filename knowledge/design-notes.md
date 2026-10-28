# Design notes

Distilled from the production pattern this repo implements, in
our own words.

## The loop, in one paragraph

A shipped agent system is a moving target: the data it sees
next month is not the data it was tuned on. The defense is a
loop, not a launch: keep a golden set that states what good
looks like, sample what production actually did, compare the
two, figure out which agent broke, propose a small config
change, and let a benchmark -- not a person in a hurry --
decide whether it ships. Version everything, so any ship can
be undone exactly.

## Why recall is the guardrail

Every routing decision has two failure directions, and they
rarely cost the same. Approving a bad item puts it in front
of customers; reworking a good item costs compute. When the
costs are asymmetric, the guardrail belongs on the expensive
direction. The demo's round-1 block exists to prove the gate
means it: an improvement on every aggregate still does not
ship when the guardrail fails.

## Why the diagnoser spans loop types

No single feedback channel is trustworthy alone. Drift
labels are precise but arrive late. Dogfooding is fast but
noisy and self-selected. Conversion is real but confounded
by everything else in the product. The diagnoser's job is
triangulation: a segment drop plus matching mismatches on
one agent is evidence; either alone is a lead.

## Why reflect exists between data and synthesis

Raw mismatches contain noise: one-off label errors, transient
glitches, edge cases that will never recur. Tuning on noise
thrashes the config -- each round chases the last round's
outlier. Reflect's only job is to refuse that: a pattern must
recur before it earns a config change.

## Why the synthesizer is boring on purpose

A synthesizer that can rewrite anything can reward-hack:
improve the metric, worsen the product. Threshold steps and
blocked-class edits are auditable, reversible, and small
enough that the benchmark gate can judge them. Ambition
belongs in the gate's metrics, not in the size of the edit.

## Why the log is append-only

A tuning system that can rewrite its own history cannot be
debugged. Every sample, mismatch, diagnosis, candidate,
benchmark, ship, block, and rollback is one JSON line, in
order, forever. The log is how a future engineer answers
"why did this config ship?" without trusting anyone's memory.
