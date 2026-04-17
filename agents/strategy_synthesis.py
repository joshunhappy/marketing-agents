"""Agent 06 — Strategy Synthesis Agent."""

from __future__ import annotations

from agents.base_agent import AgentResult, BaseAgent


class StrategySynthesisAgent(BaseAgent):
    """
    The 'manager' agent — aggregates outputs from all other agents and
    produces strategic recommendations for the marketing team.

    Tasks:
    - Compile weekly cross-agent performance digests
    - Identify gaps and conflicts between agent outputs
    - Propose quarterly strategy adjustments
    - Maintain brand consistency across all agents
    """

    @property
    def name(self) -> str:
        return "Strategy Synthesis Agent"

    @property
    def _config_key(self) -> str:
        return "strategy_synthesis"

    def run(
        self,
        agent_results: dict[str, dict],
    ) -> AgentResult:
        """
        Synthesize all agent outputs into a strategic direction report.

        Args:
            agent_results: Dict mapping agent name → AgentResult.to_dict() output.
        """
        system_prompt = self._prompt("system")

        # 1. Compile performance digest
        digest_prompt = self._prompt("weekly_digest").format(
            agent_results=str(agent_results)
        )
        digest = self._call(system_prompt, digest_prompt)

        # 2. Gap and conflict analysis
        gap_prompt = self._prompt("gap_analysis").format(
            agent_results=str(agent_results),
            digest=digest,
        )
        gaps = self._call(system_prompt, gap_prompt)

        # 3. Strategic recommendations
        strategy_prompt = self._prompt("strategy_recommendations").format(
            digest=digest,
            gaps=gaps,
        )
        strategy = self._call(system_prompt, strategy_prompt)

        # 4. Brand consistency audit
        brand_prompt = self._prompt("brand_audit").format(
            agent_results=str(agent_results)
        )
        brand_audit = self._call(system_prompt, brand_prompt)

        summary = strategy[:600] + ("..." if len(strategy) > 600 else "")
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "weekly_digest": digest,
                "gap_analysis": gaps,
                "strategy_recommendations": strategy,
                "brand_audit": brand_audit,
            },
            summary=summary,
        )
