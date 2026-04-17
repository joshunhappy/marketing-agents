"""Content Platform Integration — Mailchimp, WordPress/Webflow, Buffer."""

from __future__ import annotations

import os

from integrations.base_integration import BaseIntegration


class ContentIntegration(BaseIntegration):
    """
    Publishes content assets to email, blog, and social platforms.
    All write operations require approval gate (set dry_run=False + human approval).
    """

    def health_check(self) -> bool:
        return bool(os.environ.get("MAILCHIMP_API_KEY"))

    def create_email_campaign(self, subject: str, body_html: str, list_id: str | None = None) -> str | None:
        """Create a draft email campaign in Mailchimp. Returns campaign ID."""
        list_id = list_id or os.environ.get("MAILCHIMP_LIST_ID", "")
        if not self._guard(f"Create Mailchimp draft: '{subject}' to list {list_id}"):
            return None
        # TODO: implement real Mailchimp API call
        return None

    def create_blog_draft(self, title: str, content_md: str, tags: list[str] | None = None) -> str | None:
        """Create a blog post draft in WordPress/Webflow. Returns post ID."""
        if not self._guard(f"Create blog draft: '{title}'"):
            return None
        # TODO: implement real WordPress REST API or Webflow CMS API call
        return None

    def schedule_social_post(self, platform: str, text: str, scheduled_at: str) -> bool:
        """Schedule a social media post via Buffer."""
        if not self._guard(f"Schedule {platform} post for {scheduled_at}"):
            return False
        # TODO: implement real Buffer API call
        return True
