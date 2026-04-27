"""Base class shared by all marketing agents."""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anthropic
import yaml
from rich.console import Console

console = Console()


def _load_settings() -> dict:
    path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


SETTINGS = _load_settings()


class AgentResult:
    """Structured output returned by every agent run."""

    def __init__(self, agent_name: str, success: bool, data: dict[str, Any], summary: str):
        self.agent_name = agent_name
        self.success = success
        self.data = data
        self.summary = summary
        self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict:
        return {
            "agent": self.agent_name,
            "success": self.success,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "data": self.data,
        }

    def save(self, output_dir: str = "reports") -> Path:
        """Persist the result to disk as JSON and Markdown."""
        out = Path(output_dir)
        out.mkdir(exist_ok=True)
        slug = self.agent_name.replace(" ", "_").lower()
        date = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        # JSON
        json_path = out / f"{slug}_{date}.json"
        json_path.write_text(json.dumps(self.to_dict(), indent=2))

        # Markdown summary
        md_path = out / f"{slug}_{date}.md"
        md_path.write_text(f"# {self.agent_name} — {self.timestamp}\n\n{self.summary}\n")

        return json_path


class BaseAgent(ABC):
    """
    All marketing agents extend this class.

    Subclasses must implement:
      - `name` property
      - `model_tier` property  (primary | secondary | fast)
      - `run(**kwargs) -> AgentResult`
    """

    def __init__(self, dry_run: bool | None = None):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.settings = SETTINGS
        self.dry_run = dry_run if dry_run is not None else self._env_dry_run()
        self._agent_cfg = SETTINGS.get("agents", {}).get(self._config_key, {})
        self.require_approval = self._agent_cfg.get("require_approval", True)

    # ── Subclass contract ─────────────────────────────────────────────────────

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name, e.g. 'Market Intelligence Agent'."""

    @property
    def _config_key(self) -> str:
        """Key in settings.yaml → agents section. Override if it differs from the slug."""
        return self.name.lower().replace(" agent", "").replace(" ", "_")

    @abstractmethod
    def run(self, **kwargs) -> AgentResult:
        """Execute the agent's primary task and return a structured result."""

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _model(self) -> str:
        tier = self._agent_cfg.get("model_tier", "secondary")
        anthropic_cfg = self.settings.get("anthropic", {})
        mapping = {
            "primary": anthropic_cfg.get("model_primary", "claude-opus-4-6"),
            "secondary": anthropic_cfg.get("model_secondary", "claude-sonnet-4-6"),
            "fast": anthropic_cfg.get("model_fast", "claude-haiku-4-5-20251001"),
        }
        return mapping.get(tier, "claude-sonnet-4-6")

    def _prompt(self, name: str) -> str:
        """Load a prompt template from prompts/<agent_config_key>/<name>.md"""
        path = (
            Path(__file__).parent.parent
            / "prompts"
            / self._config_key
            / f"{name}.md"
        )
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text()

    def _call(self, system: str, user: str, max_tokens: int | None = None, _retries: int = 4) -> str:
        """Single-turn Claude API call with exponential backoff on rate limits."""
        max_tokens = max_tokens or self.settings.get("anthropic", {}).get("max_tokens", 4096)
        for attempt in range(_retries):
            try:
                message = self.client.messages.create(
                    model=self._model(),
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return message.content[0].text
            except anthropic.RateLimitError as e:
                if attempt == _retries - 1:
                    raise
                wait = 60 * (attempt + 1)  # 60s, 120s, 180s
                console.print(f"[yellow]Rate limit hit — waiting {wait}s (attempt {attempt + 1}/{_retries - 1})...[/yellow]")
                time.sleep(wait)
        raise RuntimeError("Unreachable")

    def _gate(self, action_description: str) -> bool:
        """
        Human-in-the-loop approval gate.
        Returns True if the action should proceed, False to skip.
        In dry_run mode, always returns False (read-only).
        """
        if self.dry_run:
            console.print(f"[yellow]DRY RUN — skipped:[/yellow] {action_description}")
            return False
        if self.require_approval:
            console.print(f"\n[bold cyan]Approval required:[/bold cyan] {action_description}")
            answer = input("Proceed? [y/N] ").strip().lower()
            return answer == "y"
        return True

    @staticmethod
    def _env_dry_run() -> bool:
        return os.environ.get("PIPELINE_DRY_RUN", "true").lower() in ("1", "true", "yes")
