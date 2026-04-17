"""Agent 01 — Market Intelligence Agent."""

from __future__ import annotations

from agents.base_agent import AgentResult, BaseAgent


class MarketIntelligenceAgent(BaseAgent):
    """
    Continuously monitors competitors, market trends, and customer signals
    to surface actionable intelligence for the marketing team.

    Tasks:
    - Scrape and summarize competitor campaigns
    - Track industry news and flag relevant trends
    - Analyze customer review data for pain points
    - Produce weekly intelligence briefings
    """

    @property
    def name(self) -> str:
        return "Market Intelligence Agent"

    @property
    def _config_key(self) -> str:
        return "market_intelligence"

    def run(
        self,
        competitor_urls: list[str] | None = None,
        industry_topics: list[str] | None = None,
        customer_reviews: list[str] | None = None,
    ) -> AgentResult:
        """
        Run the market intelligence cycle.

        Args:
            competitor_urls: Landing pages / blog URLs to analyze.
            industry_topics: Industry keywords / topics to monitor.
            customer_reviews: Raw review text (from G2, Capterra, etc.) to analyze.
        """
        system_prompt = self._prompt("system")

        sections: dict = {}

        # 1. Competitor analysis
        if competitor_urls:
            user_msg = self._prompt("competitor_analysis").format(
                urls="\n".join(f"- {u}" for u in competitor_urls)
            )
            sections["competitor_analysis"] = self._call(system_prompt, user_msg)
        else:
            sections["competitor_analysis"] = "No competitor URLs provided for this run."

        # 2. Trend monitoring
        if industry_topics:
            user_msg = self._prompt("trend_monitoring").format(
                topics="\n".join(f"- {t}" for t in industry_topics)
            )
            sections["trend_monitoring"] = self._call(system_prompt, user_msg)
        else:
            sections["trend_monitoring"] = "No industry topics provided for this run."

        # 3. Customer review analysis
        if customer_reviews:
            user_msg = self._prompt("review_analysis").format(
                reviews="\n\n---\n\n".join(customer_reviews)
            )
            sections["review_analysis"] = self._call(system_prompt, user_msg)
        else:
            sections["review_analysis"] = "No customer reviews provided for this run."

        # 4. Compile intelligence briefing
        briefing_prompt = self._prompt("compile_briefing").format(
            competitor_analysis=sections["competitor_analysis"],
            trend_monitoring=sections["trend_monitoring"],
            review_analysis=sections["review_analysis"],
        )
        briefing = self._call(system_prompt, briefing_prompt)
        sections["weekly_briefing"] = briefing

        summary = briefing[:500] + ("..." if len(briefing) > 500 else "")
        return AgentResult(
            agent_name=self.name,
            success=True,
            data=sections,
            summary=summary,
        )
