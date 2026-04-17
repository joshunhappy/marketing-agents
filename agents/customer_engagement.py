"""Agent 05 — Customer Engagement Agent."""

from __future__ import annotations

from agents.base_agent import AgentResult, BaseAgent


class CustomerEngagementAgent(BaseAgent):
    """
    Manages post-sale communication, drives upsell opportunities,
    and keeps customers engaged with relevant content.

    Tasks:
    - Trigger personalized onboarding email sequences
    - Identify upsell and cross-sell opportunities
    - Monitor and respond to social media mentions
    - Flag churn-risk accounts for human review
    """

    @property
    def name(self) -> str:
        return "Customer Engagement Agent"

    @property
    def _config_key(self) -> str:
        return "customer_engagement"

    def run(
        self,
        customers: list[dict],
        social_mentions: list[dict] | None = None,
    ) -> AgentResult:
        """
        Run the customer engagement cycle.

        Args:
            customers: List of customer dicts with usage data, plan, tenure, health score.
            social_mentions: List of {platform, text, author, sentiment} dicts.
        """
        system_prompt = self._prompt("system")
        churn_alerts: list[dict] = []
        upsell_opportunities: list[dict] = []
        onboarding_sequences: list[dict] = []
        social_responses: list[dict] = []

        # 1. Analyze each customer
        for customer in customers:
            analysis_prompt = self._prompt("customer_analysis").format(
                customer=str(customer)
            )
            analysis = self._call(system_prompt, analysis_prompt, max_tokens=768)

            analysis_upper = analysis.upper()

            if "CHURN RISK" in analysis_upper:
                churn_alerts.append({"customer": customer.get("name"), "analysis": analysis})

            if "UPSELL" in analysis_upper:
                upsell_prompt = self._prompt("upsell_opportunity").format(
                    customer=str(customer), analysis=analysis
                )
                upsell_draft = self._call(system_prompt, upsell_prompt)
                upsell_opportunities.append({
                    "customer": customer.get("name"),
                    "draft": upsell_draft,
                })
                self._gate(f"Send upsell email to {customer.get('name')}")

            if customer.get("days_since_signup", 99) < 14:
                onboard_prompt = self._prompt("onboarding_sequence").format(
                    customer=str(customer)
                )
                onboarding_sequences.append({
                    "customer": customer.get("name"),
                    "sequence": self._call(system_prompt, onboard_prompt),
                })

        # 2. Social media responses
        for mention in (social_mentions or []):
            response_prompt = self._prompt("social_response").format(mention=str(mention))
            draft = self._call(system_prompt, response_prompt, max_tokens=512)
            social_responses.append({"mention": mention, "draft_response": draft})
            self._gate(f"Post response to @{mention.get('author')} on {mention.get('platform')}")

        churn_alert_channel = self._agent_cfg.get("churn_risk_alert_channel")
        if churn_alerts and churn_alert_channel == "slack":
            self._gate(f"Send {len(churn_alerts)} churn-risk alert(s) to Slack")

        summary = (
            f"Processed {len(customers)} customers. "
            f"Churn risks: {len(churn_alerts)}. "
            f"Upsell opportunities: {len(upsell_opportunities)}. "
            f"Social responses drafted: {len(social_responses)}."
        )
        return AgentResult(
            agent_name=self.name,
            success=True,
            data={
                "churn_alerts": churn_alerts,
                "upsell_opportunities": upsell_opportunities,
                "onboarding_sequences": onboarding_sequences,
                "social_responses": social_responses,
            },
            summary=summary,
        )
