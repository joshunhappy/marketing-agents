"""Agent 03 — Lead Generation Agent."""

from __future__ import annotations

from agents.base_agent import AgentResult, BaseAgent


class LeadGenerationAgent(BaseAgent):
    """
    Identifies and qualifies high-intent prospects, crafts personalized
    outreach, and maintains pipeline health.

    Tasks:
    - Score and prioritize inbound leads by ICP fit
    - Draft hyper-personalized cold outreach emails
    - Follow-up sequences based on engagement signals
    - Enrich CRM records with research data
    """

    @property
    def name(self) -> str:
        return "Lead Generation Agent"

    @property
    def _config_key(self) -> str:
        return "lead_generation"

    def run(
        self,
        leads: list[dict],
        content_assets: dict | None = None,
    ) -> AgentResult:
        """
        Score leads and draft personalized outreach.

        Args:
            leads: List of lead dicts with fields like name, company, title,
                   industry, website, recent_activity, etc.
            content_assets: Output from ContentCreationAgent to reference in outreach.
        """
        system_prompt = self._prompt("system")
        daily_limit = self._agent_cfg.get("outreach_daily_limit", 50)
        leads = leads[:daily_limit]

        scored: list[dict] = []
        outreach_drafts: list[dict] = []

        # 1. Score each lead
        for lead in leads:
            score_prompt = self._prompt("score_lead").format(
                lead=str(lead),
            )
            score_response = self._call(system_prompt, score_prompt, max_tokens=512)
            scored.append({"lead": lead, "scoring": score_response})

        # 2. Draft outreach for qualified leads (score text contains "QUALIFIED")
        qualified = [s for s in scored if "QUALIFIED" in s["scoring"].upper()]

        asset_context = ""
        if content_assets:
            asset_context = f"\n\nAvailable content assets to reference:\n{list(content_assets.keys())}"

        for item in qualified:
            outreach_prompt = self._prompt("draft_outreach").format(
                lead=str(item["lead"]),
                scoring=item["scoring"],
                asset_context=asset_context,
            )
            draft = self._call(system_prompt, outreach_prompt)
            outreach_drafts.append({"lead": item["lead"].get("name", "Unknown"), "draft": draft})

            # Gate: require approval before any outreach is marked for sending
            self._gate(f"Send outreach to {item['lead'].get('name', 'Unknown')} at {item['lead'].get('company', '')}")

        summary = (
            f"Processed {len(leads)} leads. "
            f"Qualified: {len(qualified)}. "
            f"Outreach drafts created: {len(outreach_drafts)}."
        )
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={"scored_leads": scored, "outreach_drafts": outreach_drafts},
            summary=summary,
        )
