"""Config-driven tuning loops for a multi-agent system.

Keeps a set of agents aligned as production data drifts, without a
human in the loop for the loop itself: golden labels are the source
of truth, production runs are sampled at a cadence, a diagnoser
localizes which agent(s) need tuning across several feedback-loop
types, a reflect/synthesize pair proposes a new config, and a
benchmark gate ships it only if guardrail metrics pass. Configs are
versioned and rollback restores prior behavior exactly.

Everything here runs offline on synthetic fixture data. No real
agents, models, photos, or user data are involved.
"""

__version__ = "0.1.0"
