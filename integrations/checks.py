"""Integration health-check probes.

Each entry in HEALTH_PROBES maps an integration slug (matching the keys in
brands/<slug>/integrations.yaml) to a function that returns a CheckResult.
A probe should be cheap (one auth-checked API call) and never write.

Add probes incrementally as you wire each integration up. Slugs without a
probe registered here report `state="skipped"` so the table still shows
them as untested rather than failing.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class CheckResult:
    slug: str
    ok: bool
    state: str  # "ok" | "missing_key" | "failed" | "skipped"
    detail: str
    latency_ms: int | None = None


def _missing(slug: str, env_key: str) -> CheckResult:
    return CheckResult(
        slug=slug, ok=False, state="missing_key", detail=f"{env_key} not set in env"
    )


def _failed(slug: str, detail: str, latency_ms: int | None = None) -> CheckResult:
    return CheckResult(slug=slug, ok=False, state="failed", detail=detail, latency_ms=latency_ms)


def _ok(slug: str, detail: str, latency_ms: int) -> CheckResult:
    return CheckResult(slug=slug, ok=True, state="ok", detail=detail, latency_ms=latency_ms)


# ── Probes ──────────────────────────────────────────────────────────────────


def probe_anthropic(cfg: dict) -> CheckResult:
    """List one model. Cheapest auth-checked call on the Anthropic API."""
    slug = "anthropic"
    api_key = os.environ.get(cfg.get("env_key") or "ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-ant-..."):
        return _missing(slug, cfg.get("env_key") or "ANTHROPIC_API_KEY")
    try:
        import anthropic  # local import keeps startup cheap
    except ImportError:
        return _failed(slug, "anthropic SDK not installed")
    client = anthropic.Anthropic(api_key=api_key)
    t0 = time.perf_counter()
    try:
        models = client.models.list(limit=1)
    except anthropic.AuthenticationError as e:
        return _failed(slug, f"401 Unauthorized: {e.message[:300] if hasattr(e, 'message') else str(e)[:300]}")
    except anthropic.APIError as e:
        return _failed(slug, f"API error: {str(e)[:300]}")
    except Exception as e:
        return _failed(slug, f"{type(e).__name__}: {str(e)[:300]}")
    latency = int((time.perf_counter() - t0) * 1000)
    first = models.data[0].id if models.data else "no models returned"
    return _ok(slug, f"models.list ok (first: {first})", latency)


def probe_meta_ads(cfg: dict) -> CheckResult:
    """GET /v19.0/act_<account_id> — verifies token + account access in one call."""
    slug = "meta_ads"
    env_key = cfg.get("env_key") or "META_ADS_ACCESS_TOKEN"
    account_env = cfg.get("env_account_id") or "META_ADS_ACCOUNT_ID"
    token = os.environ.get(env_key, "").strip()
    account = os.environ.get(account_env, "").strip()
    if not token:
        return _missing(slug, env_key)
    if not account:
        return _missing(slug, account_env)
    # Account ID may be passed with or without the act_ prefix.
    act_id = account if account.startswith("act_") else f"act_{account}"
    try:
        import httpx
    except ImportError:
        return _failed(slug, "httpx not installed")
    t0 = time.perf_counter()
    try:
        resp = httpx.get(
            f"https://graph.facebook.com/v19.0/{act_id}",
            params={"fields": "id,name,account_status", "access_token": token},
            timeout=5.0,
        )
    except httpx.HTTPError as e:
        return _failed(slug, f"{type(e).__name__}: {str(e)[:300]}")
    latency = int((time.perf_counter() - t0) * 1000)
    if resp.status_code == 200:
        body = resp.json()
        return _ok(slug, f"{body.get('id')} ('{body.get('name', '?')}')", latency)
    # Surface Meta's own error message — it tells you exactly what's wrong.
    try:
        err = resp.json().get("error", {})
        msg = err.get("message", resp.text[:300])
    except ValueError:
        msg = resp.text[:300]
    return _failed(slug, f"HTTP {resp.status_code}: {msg[:300]}", latency)


def probe_hubspot(cfg: dict) -> CheckResult:
    """GET /crm/v3/objects/contacts?limit=1 — auth-checked, no writes."""
    slug = "crm_salesforce_hubspot"
    env_key = cfg.get("env_key") or "HUBSPOT_API_KEY"
    api_key = os.environ.get(env_key, "").strip()
    if not api_key:
        return _missing(slug, env_key)
    try:
        import httpx
    except ImportError:
        return _failed(slug, "httpx not installed")
    t0 = time.perf_counter()
    try:
        resp = httpx.get(
            "https://api.hubapi.com/crm/v3/objects/contacts",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"limit": 1},
            timeout=5.0,
        )
    except httpx.HTTPError as e:
        return _failed(slug, f"{type(e).__name__}: {str(e)[:300]}")
    latency = int((time.perf_counter() - t0) * 1000)
    if resp.status_code == 200:
        return _ok(slug, "HTTP 200, contacts.list ok", latency)
    return _failed(slug, f"HTTP {resp.status_code}: {resp.text[:300]}", latency)


# ── Registry ────────────────────────────────────────────────────────────────


HEALTH_PROBES: dict[str, Callable[[dict], CheckResult]] = {
    "anthropic": probe_anthropic,
    "crm_salesforce_hubspot": probe_hubspot,
    "meta_ads": probe_meta_ads,
}


def run_check(slug: str, cfg: dict) -> CheckResult:
    """Run a single probe by slug. Returns 'skipped' if no probe is registered."""
    probe = HEALTH_PROBES.get(slug)
    if probe is None:
        return CheckResult(
            slug=slug,
            ok=False,
            state="skipped",
            detail="no probe implemented yet",
        )
    return probe(cfg)


def run_all_checks(integrations_data: dict) -> list[CheckResult]:
    """Run probes for every integration in the YAML, in order."""
    items = (integrations_data or {}).get("integrations", {}) or {}
    results = []
    for slug, cfg in items.items():
        results.append(run_check(slug, cfg or {}))
    return results
