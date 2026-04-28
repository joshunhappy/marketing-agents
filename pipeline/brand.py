"""Active-brand resolution and brand directory helpers.

Each brand lives under `brands/<slug>/` with its own `.env`, `brand_voice.yaml`,
`icp.yaml`, and `integrations.yaml`. The "active brand" is resolved in this
order:

  1. `BRAND` environment variable        (per-invocation override)
  2. `.active-brand` file at project root (persistent default)
  3. The single brand under `brands/`     (auto-pick if only one exists)
  4. Raises BrandNotConfigured            (caller should prompt setup)

A shared `.env` at the project root is still loaded first (e.g. for an
Anthropic key billed across all brands); brand-specific `.env` values override
shared values for the active brand.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
BRANDS_ROOT = ROOT / "brands"
ACTIVE_BRAND_FILE = ROOT / ".active-brand"
TEMPLATES_DIR = ROOT / "config" / "templates"

BRAND_FILES = ("brand_voice.yaml", "icp.yaml", "integrations.yaml")


class BrandNotConfigured(RuntimeError):
    """No active brand could be resolved."""


def slugify(name: str) -> str:
    """Lowercase + alphanumeric-only. 'America Voice' → 'americavoice'."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def list_brands() -> list[str]:
    """Sorted list of brand slugs that exist under brands/."""
    if not BRANDS_ROOT.exists():
        return []
    return sorted(p.name for p in BRANDS_ROOT.iterdir() if p.is_dir() and not p.name.startswith("."))


def active_brand(allow_missing: bool = False) -> str:
    """Resolve the active brand slug. See module docstring for resolution order."""
    import os

    env_brand = os.environ.get("BRAND", "").strip()
    if env_brand:
        return env_brand

    if ACTIVE_BRAND_FILE.exists():
        slug = ACTIVE_BRAND_FILE.read_text().strip()
        if slug:
            return slug

    brands = list_brands()
    if len(brands) == 1:
        return brands[0]

    if allow_missing:
        return ""

    if not brands:
        raise BrandNotConfigured(
            "No brand configured. Run `marketing-agents brand new <slug>` or "
            "`marketing-agents setup` to create one."
        )
    raise BrandNotConfigured(
        f"Multiple brands available ({', '.join(brands)}) and none selected. "
        "Run `marketing-agents brand use <slug>` or set BRAND=<slug>."
    )


def brand_dir(slug: str | None = None) -> Path:
    """Return Path to brands/<slug>/ (no creation). Resolves active brand if slug omitted."""
    return BRANDS_ROOT / (slug or active_brand())


def brand_file(name: str, slug: str | None = None) -> Path:
    """Return Path to a file inside the active (or named) brand directory."""
    return brand_dir(slug) / name


def set_active_brand(slug: str) -> None:
    """Persist the given slug as the active brand."""
    if not (BRANDS_ROOT / slug).is_dir():
        raise BrandNotConfigured(f"Brand '{slug}' does not exist under brands/.")
    ACTIVE_BRAND_FILE.write_text(slug + "\n")


def init_brand(slug: str, *, set_active: bool = True) -> Path:
    """Create brands/<slug>/ from templates. Returns the brand directory path."""
    slug = slugify(slug)
    if not slug:
        raise ValueError("Brand slug must contain at least one alphanumeric character.")

    target = BRANDS_ROOT / slug
    target.mkdir(parents=True, exist_ok=True)

    # Copy YAML templates if missing.
    for name in BRAND_FILES:
        src = TEMPLATES_DIR / name
        dst = target / name
        if dst.exists():
            continue
        if not src.exists():
            raise FileNotFoundError(f"Template missing: {src}")
        shutil.copy(src, dst)

    # Seed .env from .env.example if missing.
    env_template = ROOT / ".env.example"
    env_target = target / ".env"
    if not env_target.exists() and env_template.exists():
        shutil.copy(env_template, env_target)

    if set_active:
        set_active_brand(slug)

    return target


def load_brand_env() -> str | None:
    """Load shared .env then the active brand's .env (overrides). Returns the active slug."""
    load_dotenv(ROOT / ".env", override=False)
    try:
        slug = active_brand()
    except BrandNotConfigured:
        return None
    brand_env = brand_dir(slug) / ".env"
    if brand_env.exists():
        load_dotenv(brand_env, override=True)
    return slug
