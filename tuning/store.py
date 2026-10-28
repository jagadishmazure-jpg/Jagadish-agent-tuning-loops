"""Versioned config store: ship only through the benchmark gate,
and roll back exactly.

Rules, enforced here (not just documented):
- register() requires a BenchmarkResult that passed its ship
  decision. No result, or a failing result, is REFUSED -- the
  absent path and the reject path both fail closed.
- rollback() requires a previous version; with only one version
  it is REFUSED.
- rollback restores the previous version object itself, so behavior
  on the golden set is identical by construction -- and the test
  suite proves it by re-benchmarking.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoredVersion:
    version: int
    config: object
    benchmark: object


class ConfigStore:
    """Append-only version history with a movable current pointer."""

    def __init__(self, initial_config, initial_benchmark=None):
        self._versions = [
            StoredVersion(
                version=1, config=initial_config, benchmark=initial_benchmark
            )
        ]
        self._current = 1

    def current(self):
        return self._by_version(self._current).config

    def current_version(self):
        return self._current

    def history(self):
        return tuple(v.version for v in self._versions)

    def _by_version(self, version):
        for stored in self._versions:
            if stored.version == version:
                return stored
        raise ValueError(f"no such version: {version}")

    def register(self, config, ship_decision):
        """Register a candidate as a new version. Refuses anything
        that did not pass the benchmark gate."""
        if ship_decision is None:
            raise ValueError(
                "refused: no benchmark ship decision supplied")
        if not ship_decision.ship:
            raise ValueError(
                "refused: candidate failed the benchmark gate: "
                + "; ".join(ship_decision.reasons)
            )
        version = self._versions[-1].version + 1
        self._versions.append(
            StoredVersion(version=version, config=config, benchmark=None))
        self._current = version
        return version

    def rollback(self):
        """Move current back one version. Refused when there is no
        previous version to return to."""
        if self._current <= 1:
            raise ValueError("refused: no previous version to roll back to")
        self._current -= 1
        return self._by_version(self._current).config
