# seo-inspection

[中文文档](README.zh-CN.md)

Reusable SEO evidence skill for Google Search Console and GA4. Use it before SEO code, metadata, robots, sitemap, canonical, hreflang, content, or product-page prioritization changes.

## What This Skill Provides

- Search Console URL Inspection, Search Analytics, Sites, and Sitemaps commands.
- GA4 Admin discovery and GA4 Data API reports.
- Product-page GA4 aggregation by Shopify handle.
- Preset reports for landing pages, channels, countries, devices, events, ecommerce items, and time series.
- Advanced GA4 wrappers for batch reports, pivot reports, compatibility checks, and realtime reports.
- Guardrails for write operations: Search Console site/sitemap writes require `--apply`.

## Directory Layout

```text
seo-inspection/
├── SKILL.md
├── README.md
├── README.zh-CN.md
├── .env.example
├── requirements.txt
├── references/
│   └── ga4-recipes.md
├── samples/
└── scripts/
    └── seo_inspection.py
```

## Install

From the skill directory:

```powershell
python -m pip install -r requirements.txt
```

Required packages:

- `google-auth`
- `requests`

## Configuration

The helper reads config from:

1. `./.env` inside this skill directory
2. project-root `.env`

Skill-local `.env` takes precedence. Environment variables override both files.

Copy `.env.example` to `.env` and set:

```env
GSC_SERVICE_ACCOUNT_PATH=credential/google-service-account.json
GOOGLE_SERVICE_ACCOUNT_PATH=credential/google-service-account.json
GSC_SITE_URL=sc-domain:example.com
GSC_LANGUAGE_CODE=en-US
GA4_PROPERTY_ID=123456789
```

Notes:

- `GSC_SERVICE_ACCOUNT_PATH` is the primary credential key.
- `GOOGLE_SERVICE_ACCOUNT_PATH` is an optional alias when the same credential is used for both GSC and GA4.
- `GSC_SITE_URL` accepts values such as `sc-domain:example.com` or URL-prefix properties.
- `GA4_PROPERTY_ID` is the numeric GA4 property ID, not the `G-...` measurement ID.
- Do not commit real `.env` files or service account JSON files.

## Google Access Setup

1. Create or reuse a Google service account.
2. Add the service account email to the Search Console property.
3. Add the same service account email to the GA4 property with viewer/read access.
4. Put the JSON key path in `.env`.
5. Run `ga4-account-summaries` to confirm property access.

## Command Reference

Run help:

```powershell
python scripts/seo_inspection.py --help
python scripts/seo_inspection.py ga4-report --help
```

### Search Console

```powershell
python scripts/seo_inspection.py sites-list --output temp/gsc-sites.json
python scripts/seo_inspection.py sites-get --output temp/gsc-site.json
python scripts/seo_inspection.py sitemaps-list --output temp/gsc-sitemaps.json
python scripts/seo_inspection.py sitemaps-get --sitemap-url "https://example.com/sitemap.xml" --output temp/gsc-sitemap.json
```

Write operations are dry-run by default:

```powershell
python scripts/seo_inspection.py sitemaps-submit --sitemap-url "https://example.com/sitemap.xml"
python scripts/seo_inspection.py sitemaps-submit --sitemap-url "https://example.com/sitemap.xml" --apply
```

URL Inspection:

```powershell
python scripts/seo_inspection.py inspect `
  --url "https://example.com/products/example" `
  --output temp/url-inspection.json
```

Search Analytics:

```powershell
python scripts/seo_inspection.py searchanalytics-query `
  --start-date 2026-01-01 `
  --end-date 2026-01-31 `
  --dimensions query,page `
  --row-limit 1000 `
  --output temp/gsc-searchanalytics.json
```

### GA4 Discovery

```powershell
python scripts/seo_inspection.py ga4-account-summaries --output temp/ga4-account-summaries.json
python scripts/seo_inspection.py ga4-metadata --output temp/ga4-metadata.json
python scripts/seo_inspection.py ga4-check-compatibility `
  --dimensions pagePath,sessionDefaultChannelGroup `
  --metrics sessions,totalRevenue `
  --output temp/ga4-compatibility.json
```

### GA4 Presets

```powershell
python scripts/seo_inspection.py ga4-product-pages --start-date 2026-01-17 --end-date 2026-04-16 --aggregate-by-handle --output temp/ga4-product-pages.json
python scripts/seo_inspection.py ga4-landing-pages --start-date 2026-01-17 --end-date 2026-04-16 --output temp/ga4-landing-pages.json
python scripts/seo_inspection.py ga4-channels --start-date 2026-01-17 --end-date 2026-04-16 --output temp/ga4-channels.json
python scripts/seo_inspection.py ga4-geo --start-date 2026-01-17 --end-date 2026-04-16 --dimension country --output temp/ga4-countries.json
python scripts/seo_inspection.py ga4-devices --start-date 2026-01-17 --end-date 2026-04-16 --dimension deviceCategory --output temp/ga4-devices.json
python scripts/seo_inspection.py ga4-events --start-date 2026-01-17 --end-date 2026-04-16 --output temp/ga4-events.json
python scripts/seo_inspection.py ga4-ecommerce-items --start-date 2026-01-17 --end-date 2026-04-16 --output temp/ga4-items.json
python scripts/seo_inspection.py ga4-timeseries --start-date 2026-01-17 --end-date 2026-04-16 --output temp/ga4-timeseries.json
```

### GA4 Generic And Advanced Reports

Generic report:

```powershell
python scripts/seo_inspection.py ga4-report `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --dimensions pagePath,sessionDefaultChannelGroup `
  --metrics sessions,engagementRate,conversions,totalRevenue `
  --output temp/ga4-custom.json
```

Batch and pivot reports should use JSON files to avoid shell escaping issues:

```powershell
python scripts/seo_inspection.py ga4-batch-report --requests-file temp/ga4-batch-requests.json --output temp/ga4-batch.json
python scripts/seo_inspection.py ga4-pivot-report --body-file temp/ga4-pivot-body.json --output temp/ga4-pivot.json
python scripts/seo_inspection.py ga4-batch-pivot-report --requests-file temp/ga4-batch-pivot-requests.json --output temp/ga4-batch-pivot.json
```

Realtime report:

```powershell
python scripts/seo_inspection.py ga4-realtime-report `
  --dimensions unifiedScreenName `
  --metrics activeUsers `
  --output temp/ga4-realtime.json
```

More examples: `references/ga4-recipes.md`.

## Recommended SEO Workflow

1. Use Search Console for search demand, query language, indexing, crawl, sitemap, and robots evidence.
2. Use GA4 for page demand, engagement, conversion quality, revenue, channel mix, device behavior, and market behavior.
3. Combine both before prioritizing metadata, GEO/AEO copy, product content, or technical SEO changes.
4. Store raw API output under `temp/` and cite the file in reports.

## Output Shape

Every command returns JSON with:

- `command`
- request metadata such as `site_url` or `ga4_property_id`
- `request` when applicable
- `result`
- `credentials`
- `config_sources`

`inspect` additionally returns normalized classification fields.

## Verification

From the project root:

```powershell
python -m py_compile .codex/skills/seo-inspection/scripts/seo_inspection.py
python .codex/skills/seo-inspection/scripts/seo_inspection.py sites-list --output temp/seo-inspection-gsc-test.json
python .codex/skills/seo-inspection/scripts/seo_inspection.py ga4-account-summaries --output temp/seo-inspection-ga4-test.json
python .codex/skills/seo-inspection/scripts/seo_inspection.py ga4-product-pages --start-date 2026-04-01 --end-date 2026-04-16 --limit 2 --aggregate-by-handle --output temp/seo-inspection-ga4-product-test.json
```

Validate the skill:

```powershell
python C:/Users/desre/.codex/skills/.system/skill-creator/scripts/quick_validate.py .codex/skills/seo-inspection
```

## Publish Checklist

- `SKILL.md` has valid frontmatter with `name: seo-inspection`.
- `scripts/seo_inspection.py` compiles and at least one GSC plus one GA4 command succeeds.
- `.env.example` includes all required keys but no real credentials.
- Real `.env`, `credential/`, `temp/`, outputs, and `__pycache__/` are ignored.
- README examples use relative paths that work from the skill directory.
- `references/ga4-recipes.md` is included for GA4 examples.

## Official References

- Search Console API: https://developers.google.com/webmaster-tools/v1/api_reference_index
- URL Inspection API: https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
- Search Analytics query: https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- Analytics Admin API account summaries: https://developers.google.com/analytics/devguides/config/admin/v1/rest/v1alpha/accountSummaries/list
- Analytics Data API overview: https://developers.google.com/analytics/devguides/reporting/data/v1
- Analytics Data API REST: https://developers.google.com/analytics/devguides/reporting/data/v1/rest
- Analytics Data API realtime: https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/runRealtimeReport
