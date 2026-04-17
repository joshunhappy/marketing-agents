"""Shared base for all external platform integrations."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class BaseIntegration(ABC):
    """
    All integrations extend this class.
    In dry_run mode, all write operations are no-ops that print what would happen.
    """

    def __init__(self, dry_run: bool | None = None):
        self.dry_run = dry_run if dry_run is not None else self._env_dry_run()

    def _guard(self, description: str) -> bool:
        """Return True if the write operation should proceed."""
        if self.dry_run:
            print(f"[DRY RUN] Would: {description}")
            return False
        return True

    @staticmethod
    def _env_dry_run() -> bool:
        return os.environ.get("PIPELINE_DRY_RUN", "true").lower() in ("1", "true", "yes")

    @abstractmethod
    def health_check(self) -> bool:
        """Verify the integration credentials and connection are working."""
