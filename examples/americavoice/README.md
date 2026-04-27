# America Voice — Reference Implementation

A fully populated configuration of the Marketing Agents fleet for **America Voice**, a 16+ year-old B2C fintech/telecom service that lets US and Canada migrants send mobile top-ups, gift cards, and international recharges to family in 100+ countries.

This directory is kept as a realistic, end-to-end reference. The top-level `config/` files are generic templates — this folder shows what a complete, populated fleet looks like for a real business.

## What's here

| File | Mirrors | Purpose |
|---|---|---|
| `brand_voice.yaml` | `config/brand_voice.yaml` | Warm/clear/reliable/empowering voice pillars, bilingual (EN/ES) guidance, glossary, prohibited words, do/don't examples |
| `icp.yaml` | `config/icp.yaml` | B2C persona ("The Migrant Provider") + secondary reseller persona, behavioral signals, lead scoring weights |
| `integrations.yaml` | `config/integrations.yaml` | Data source registry from the Phase 1 audit — includes America Voice App Backend, MoneyGram dealer data, and the full status/auth/access matrix for 22 integrations |
| `input.json` | `examples/input.json` | Realistic pipeline input: Mexico/Guatemala campaigns, Spanish-speaking customers, Haitian leads, dealer-channel signups |

## Using this reference

To run the pipeline against this configuration instead of the generic templates:

```bash
# Point the agents at these configs (one-off)
cp examples/americavoice/brand_voice.yaml config/brand_voice.yaml
cp examples/americavoice/icp.yaml         config/icp.yaml
cp examples/americavoice/integrations.yaml config/integrations.yaml

# Run the pipeline with the realistic input
marketing-agents run --input examples/americavoice/input.json
```

Or read these files directly to see what a fully populated config looks like before filling out your own.
