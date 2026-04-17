"""Agent 02 — Content Creation Agent."""

from __future__ import annotations

from agents.base_agent import AgentResult, BaseAgent


class ContentCreationAgent(BaseAgent):
    """
    Produces on-brand content at scale — blog posts, ad copy,
    email sequences, social posts, and landing pages.

    Tasks:
    - Draft SEO-optimized blog articles from briefs
    - Write A/B variants for ads and headlines
    - Generate personalized email nurture sequences
    - Adapt content across formats and channels
    """

    @property
    def name(self) -> str:
        return "Content Creation Agent"

    @property
    def _config_key(self) -> str:
        return "content_creation"

    def run(
        self,
        brief: str,
        formats: list[str] | None = None,
        persona_id: str | None = None,
        intelligence_briefing: str | None = None,
    ) -> AgentResult:
        """
        Generate content assets from a brief.

        Args:
            brief: Content brief describing topic, goal, keywords, and CTA.
            formats: Subset of [blog, email_sequence, ad_copy, social_post, landing_page].
                     Defaults to all formats in settings.
            persona_id: Target persona from config/brand_voice.yaml.
            intelligence_briefing: Optional Market Intelligence output to inform content.
        """
        allowed = self.settings["agents"]["content_creation"]["output_formats"]
        formats = formats or allowed

        system_prompt = self._prompt("system")
        outputs: dict[str, str] = {}

        context = ""
        if intelligence_briefing:
            context = f"\n\n## Market Intelligence Context\n{intelligence_briefing}"
        if persona_id:
            context += f"\n\n## Target Persona\n{persona_id}"

        for fmt in formats:
            if fmt not in allowed:
                continue
            user_msg = self._prompt(fmt).format(brief=brief, context=context)
            outputs[fmt] = self._call(system_prompt, user_msg)

        summary = f"Generated {len(outputs)} content asset(s): {', '.join(outputs.keys())}"
        return AgentResult(
            agent_name=self.name,
            success=True,
            data=outputs,
            summary=summary,
        )
