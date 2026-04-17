"""Agent 04 — Campaign Optimization Agent."""

from __future__ import annotations

from agents.base_agent import AgentResult, BaseAgent


class CampaignOptimizationAgent(BaseAgent):
    """
    Monitors live campaign performance, identifies underperforming assets,
    and recommends or executes optimizations.

    Tasks:
    - Analyze ad performance and flag poor performers
    - Recommend bid adjustments and audience tweaks
    - Generate weekly campaign performance reports
    - Surface CRO (conversion rate optimization) opportunities
    """

    @property
    def name(self) -> str:
        return "Campaign Optimization Agent"

    @property
    def _config_key(self) -> str:
        return "campaign_optimization"

    def run(
        self,
        campaign_data: dict,
    ) -> AgentResult:
        """
        Analyze campaign performance and produce optimization recommendations.

        Args:
            campaign_data: Dict containing campaigns, ad sets, and performance
                           metrics (impressions, clicks, CTR, CPC, conversions, ROAS).
        """
        system_prompt = self._prompt("system")

        # 1. Analyze performance
        analysis_prompt = self._prompt("analyze_performance").format(
            campaign_data=str(campaign_data)
        )
        analysis = self._call(system_prompt, analysis_prompt)

        # 2. Generate recommendations
        rec_prompt = self._prompt("recommendations").format(analysis=analysis)
        recommendations = self._call(system_prompt, rec_prompt)

        # 3. Weekly report
        report_prompt = self._prompt("weekly_report").format(
            campaign_data=str(campaign_data),
            analysis=analysis,
            recommendations=recommendations,
        )
        report = self._call(system_prompt, report_prompt)

        # Gate any actual changes to ad platforms
        self._gate("Apply recommended bid adjustments to ad platforms")

        summary = f"Campaign analysis complete. {recommendations[:200]}..."
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "analysis": analysis,
                "recommendations": recommendations,
                "weekly_report": report,
            },
            summary=summary,
        )
