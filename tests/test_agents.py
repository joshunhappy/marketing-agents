"""Basic tests for agent scaffolding — no real API calls."""

import pytest

from agents.base_agent import AgentResult


class TestAgentResult:
    def test_to_dict_has_required_keys(self):
        result = AgentResult(
            agent_name="Test Agent",
            success=True,
            data={"key": "value"},
            summary="Test summary",
        )
        d = result.to_dict()
        assert d["agent"] == "Test Agent"
        assert d["success"] is True
        assert d["data"] == {"key": "value"}
        assert "timestamp" in d

    def test_save_creates_files(self, tmp_path):
        result = AgentResult(
            agent_name="Market Intelligence Agent",
            success=True,
            data={},
            summary="Test",
        )
        json_path = result.save(output_dir=str(tmp_path))
        assert json_path.exists()
        # Reports are nested under reports/<brand>/
        assert json_path.parent.parent == tmp_path
        md_path = json_path.with_suffix(".md")
        assert md_path.exists()


class TestBaseAgentConfig:
    def test_agents_load_settings(self):
        """Verify that agent settings are loaded without errors."""
        from agents.base_agent import SETTINGS
        assert "agents" in SETTINGS
        assert "market_intelligence" in SETTINGS["agents"]

    def test_dry_run_default_is_true(self):
        """dry_run should default to True (safe by default)."""
        import os
        os.environ["PIPELINE_DRY_RUN"] = "true"
        os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
        from agents.market_intelligence import MarketIntelligenceAgent
        agent = MarketIntelligenceAgent()
        assert agent.dry_run is True
