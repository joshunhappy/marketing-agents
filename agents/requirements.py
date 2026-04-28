"""Per-agent integration and configuration requirements.

Single source of truth for what each agent needs to run. Used by:
  - The orchestrator, to skip agents whose requirements aren't met (live mode)
  - The setup wizard's readiness check, to tell the user which agents can run

Each agent maps to:
  requires_any:    integration slugs (from config/integrations.yaml). The agent
                   needs ≥1 of these marked status: connected. Empty list means
                   the agent can run with no external integrations (it relies on
                   Claude + the inputs it's given).
  optional:        integration slugs the agent uses if connected, ignores if not.
  requires_config: config files (without extension) under config/ that must not
                   contain template placeholders. Empty list means the agent
                   doesn't read any branded copy/persona files.
"""

from __future__ import annotations

AGENT_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "market_intelligence": {
        "requires_any": [],
        "optional": ["seo_tool", "google_search_console", "app_store_reviews", "social_scheduler"],
        "requires_config": ["icp"],
    },
    "content_creation": {
        "requires_any": [],
        "optional": ["cms", "email_platform", "design_tool", "notion"],
        "requires_config": ["brand_voice"],
    },
    "lead_generation": {
        "requires_any": ["crm", "apollo"],
        "optional": ["linkedin_sales_nav", "outreach_salesloft"],
        "requires_config": ["icp", "brand_voice"],
    },
    "campaign_optimization": {
        "requires_any": ["google_ads", "meta_ads"],
        "optional": ["google_analytics_4", "product_analytics", "bi_tool"],
        "requires_config": [],
    },
    "customer_engagement": {
        "requires_any": ["email_platform", "crm"],
        "optional": ["customer_data_warehouse", "social_scheduler", "slack"],
        "requires_config": ["brand_voice"],
    },
    "strategy_synthesis": {
        "requires_any": [],
        "optional": ["bi_tool", "slack", "notion"],
        "requires_config": [],
    },
}


def connected_integrations(integrations_data: dict) -> set[str]:
    """Return the set of integration slugs whose status is 'connected'."""
    items = (integrations_data or {}).get("integrations", {}) or {}
    return {k for k, v in items.items() if (v or {}).get("status") == "connected"}


def agent_runnability(
    agent_slug: str,
    connected: set[str],
    filled_configs: set[str],
) -> dict:
    """Compute whether a single agent has its requirements met.

    Returns:
        {
          "can_run": bool,
          "missing_required_any": [slug, ...]  — only set when can_run is False
                                                 due to integrations
          "missing_required_configs": [name, ...]
          "missing_optional": [slug, ...]
        }
    """
    req = AGENT_REQUIREMENTS.get(agent_slug)
    if req is None:
        return {
            "can_run": False,
            "missing_required_any": [],
            "missing_required_configs": [],
            "missing_optional": [],
            "unknown_agent": True,
        }

    required_any = req["requires_any"]
    required_configs = req["requires_config"]
    optional = req["optional"]

    has_required_integration = (
        not required_any or any(slug in connected for slug in required_any)
    )
    missing_configs = [c for c in required_configs if c not in filled_configs]
    missing_optional = [s for s in optional if s not in connected]

    can_run = has_required_integration and not missing_configs

    return {
        "can_run": can_run,
        "missing_required_any": [] if has_required_integration else required_any,
        "missing_required_configs": missing_configs,
        "missing_optional": missing_optional,
    }
