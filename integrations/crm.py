"""CRM Integration — HubSpot / Salesforce."""

from __future__ import annotations

import os

import httpx

from integrations.base_integration import BaseIntegration


class CRMIntegration(BaseIntegration):
    """
    Reads leads and customers from HubSpot (default) or Salesforce.
    Writes enriched data and engagement records back.

    Set HUBSPOT_API_KEY in .env to use HubSpot.
    Set SALESFORCE_* vars to switch to Salesforce.
    """

    def __init__(self, provider: str = "hubspot", dry_run: bool | None = None):
        super().__init__(dry_run=dry_run)
        self.provider = provider
        self._base_url = "https://api.hubapi.com" if provider == "hubspot" else None
        self._api_key = os.environ.get("HUBSPOT_API_KEY", "")

    def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            resp = httpx.get(
                f"{self._base_url}/crm/v3/objects/contacts",
                headers={"Authorization": f"Bearer {self._api_key}"},
                params={"limit": 1},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def get_leads(self, limit: int = 100) -> list[dict]:
        """Fetch recent contacts from CRM as lead dicts."""
        # TODO: implement real HubSpot / Salesforce API call
        # Returns stubbed data until API keys are configured
        return []

    def get_customers(self, health_score_below: int | None = None) -> list[dict]:
        """Fetch customer accounts, optionally filtered by health score."""
        # TODO: implement real CRM call
        return []

    def update_lead_score(self, lead_id: str, score: int, notes: str) -> bool:
        """Write lead score back to CRM."""
        if not self._guard(f"Update lead {lead_id} score to {score} in {self.provider}"):
            return False
        # TODO: implement real CRM write
        return True

    def log_outreach(self, lead_id: str, subject: str, body: str) -> bool:
        """Log drafted outreach email to CRM activity timeline."""
        if not self._guard(f"Log outreach to lead {lead_id} in {self.provider}"):
            return False
        # TODO: implement real CRM write
        return True
