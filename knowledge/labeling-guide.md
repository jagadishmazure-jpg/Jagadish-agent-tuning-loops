# Labeling guide

The written guide the golden set follows. In a production
system, this document is what labelers are trained on; here
it is what the fixture code implements, so the loop can be
proven offline. The honest statement: these labels stand in
for human labels. No labelers were involved.

## Objective: remove subjectivity

Labelers must not answer "is this a good photo?" They answer
the checklist below. Every question has a yes/no answer from
observable facts, so two labelers labeling the same item
should agree, and disagreement is itself a signal (the guide
is ambiguous, not the labeler).

## Routing decision: enhance or skip

Enhance the item when ANY of these hold; otherwise skip it
(keep the original):

1. Any quality score (sharpness, composition, color,
   plating) is below **0.80**.
2. Plating is unrealistic (the dish as plated could not
   plausibly be served this way), regardless of scores.

Rationale for the bar: the router's guardrail is recall on
the "needs enhancement" class. A bad item skipped stays on
the menu; a good item enhanced costs compute. The bar errs
toward enhancement.

## QA decision: does the edited candidate pass?

The candidate FAILS when ANY of these hold:

1. It adds an object not in the original (faithfulness).
2. It removes an object from the original (completeness).
3. It falls back to generic plating/style (brand and
   diversity loss).
4. It is incoherent or physically implausible (objects
   overlapping impossibly, plates covering food).
5. The item count cannot be verified from the photo
   (never guess a count).
6. Any candidate quality score is below **0.70**.

## Publish decision: what goes on the menu

- QA passed and no policy flag: publish the **enhanced**
  photo.
- QA failed and no policy flag: publish the **original**
  photo (a coverage hit for enhancement, not a blank menu).
- Policy flag set: publish **nothing**, regardless of QA.

## Representativeness

The golden set must cover every cut: geography (us-midwest,
us-west, eu-west), device (ios, android, web), dish type
(burger, sushi, curry, dessert), and quality tier (low, mid,
high). A set missing a cut cannot detect drift in that cut,
and tuning on it will silently favor the covered cuts.
`cuts_covered()` in `tuning/labels.py` enforces this.

## What the guide deliberately does not say

It does not say what "looks appetizing" means, what a
"premium" photo looks like, or which merchant's style is
better. Taste judgments are not labelable; they are product
decisions, and they belong in the rubric criteria, not in
labeler discretion.
