# Security policy

This is a synthetic, offline portfolio project: no real
agents, models, photos, keys, network calls, or user data.
There is nothing deployed and nothing to breach.

If you find a security issue in the code itself (for example,
a gate that can be bypassed, or a real-company name leaking
into the repo), please report it by opening an issue on this
repo. Do not include any personal data in the report.

The brand guard (`scripts/brand_check.py`) stores real-company
names only as SHA-256 hashes, never in plain text.
