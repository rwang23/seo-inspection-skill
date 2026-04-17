---
name: seo-inspection
description: Use when working with SEO evidence from Google Search Console or GA4, including GSC URL Inspection, indexing coverage, crawl status, referring URLs, robots.txt blocking, sitemap status, Search Analytics queries, GA4 product-page sessions, engagement, conversions, revenue, ecommerce funnels, landing pages, channels, countries, devices, realtime users, or when deciding SEO priorities from search plus analytics data.
---

# SEO Inspection

Use this skill to gather API-backed SEO evidence before changing SEO code, content priorities, robots rules, sitemap submissions, canonical tags, metadata, or product-page optimization plans.

## Included Files

- `scripts/seo_inspection.py`: helper CLI for Search Console and GA4 Admin/Data APIs
- `references/ga4-recipes.md`: GA4 report presets, advanced reports, and interpretation notes
- `.env.example`: config template
- `requirements.txt`: Python package requirements

## Configuration

Config can live in this skill directory `.env` or the project-root `.env`. Skill-local `.env` wins.

Required for GSC commands:

- `GSC_SERVICE_ACCOUNT_PATH`
- `GSC_SITE_URL`
- `GSC_LANGUAGE_CODE` optional, defaults to `en-US`

Required for GA4 commands:

- `GSC_SERVICE_ACCOUNT_PATH` or `GOOGLE_SERVICE_ACCOUNT_PATH`
- `GA4_PROPERTY_ID`

For this project, use `GA4_PROPERTY_ID=346785523` for `Viva Essence` unless the user explicitly asks for a different property.

## Standard Workflow

1. Pull Search Console evidence first for indexing, crawl, sitemap, robots, query, and page visibility questions.
2. Pull GA4 evidence when the decision depends on on-page demand, engagement, ecommerce quality, conversions, revenue, landing paths, country/device/channel behavior, or prioritizing which SEO work matters most.
3. Compare GSC search demand with GA4 engagement/conversion evidence before recommending metadata or content changes.
4. Preserve raw JSON outputs under `temp/` or another task-specific path when the result supports a report.
5. Treat Search Console write operations as guarded actions: `sites-add`, `sites-delete`, `sitemaps-submit`, and `sitemaps-delete` require `--apply`.

## Commands

Search Console:

```powershell
python .codex/skills/seo-inspection/scripts/seo_inspection.py inspect `
  --url "https://example.com/path" `
  --output temp/seo-inspection-url.json

python .codex/skills/seo-inspection/scripts/seo_inspection.py searchanalytics-query `
  --start-date 2026-01-01 `
  --end-date 2026-01-31 `
  --dimensions query,page `
  --output temp/gsc-searchanalytics.json

python .codex/skills/seo-inspection/scripts/seo_inspection.py sites-list --output temp/gsc-sites.json
python .codex/skills/seo-inspection/scripts/seo_inspection.py sitemaps-list --output temp/gsc-sitemaps.json
```

GA4 discovery:

```powershell
python .codex/skills/seo-inspection/scripts/seo_inspection.py ga4-account-summaries `
  --output temp/ga4-account-summaries.json

python .codex/skills/seo-inspection/scripts/seo_inspection.py ga4-metadata `
  --output temp/ga4-metadata.json
```

GA4 reports:

```powershell
python .codex/skills/seo-inspection/scripts/seo_inspection.py ga4-product-pages `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --aggregate-by-handle `
  --output temp/ga4-product-pages.json

python .codex/skills/seo-inspection/scripts/seo_inspection.py ga4-report `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --dimensions sessionDefaultChannelGroup `
  --metrics sessions,conversions,totalRevenue `
  --order-bys '[{"metric":{"metricName":"sessions"},"desc":true}]' `
  --output temp/ga4-channels.json

python .codex/skills/seo-inspection/scripts/seo_inspection.py ga4-realtime-report `
  --dimensions unifiedScreenName `
  --metrics activeUsers `
  --output temp/ga4-realtime.json
```

## GA4 Analysis Patterns

- For detailed GA4 examples, read `references/ga4-recipes.md` when the task involves report design, ecommerce analysis, landing pages, channels, countries, devices, events, batch reports, pivots, or compatibility checks.
- Product prioritization: use `ga4-product-pages --aggregate-by-handle` with GSC `query,page` data to rank pages by search demand plus sessions, engagement rate, conversions, and revenue.
- Landing page analysis: use `ga4-report --dimensions landingPagePlusQueryString --metrics sessions,engagementRate,conversions,totalRevenue`.
- Channel analysis: use `sessionDefaultChannelGroup` or `firstUserDefaultChannelGroup`.
- Country/device analysis: use `country`, `region`, `deviceCategory`, or `browser`.
- Ecommerce analysis: use dimensions such as `itemName`, `itemId`, `itemCategory`, and metrics such as `itemsViewed`, `itemsAddedToCart`, `itemsPurchased`, `itemRevenue` when available in metadata.
- Funnel checks: query event dimensions and metrics around `page_view`, `view_item`, `add_to_cart`, `begin_checkout`, and `purchase`.
- Realtime checks: use `ga4-realtime-report` for current active users, top pages, and current traffic context; do not use realtime as a historical performance substitute.
- Advanced stable endpoints: use `ga4-batch-report`, `ga4-pivot-report`, `ga4-batch-pivot-report`, and `ga4-check-compatibility` for multi-report, pivot, and field compatibility needs.
- Early preview endpoints such as funnel reports and audience exports are intentionally not wrapped by default; check official Google docs before adding them for a task.

## Interpretation Rules

- GSC tells you how Google searchers find or fail to find the page; GA4 tells you what visitors did after landing.
- High GSC impressions + low CTR: metadata, title, rich result, and query alignment are likely candidates.
- High GSC clicks + weak GA4 engagement: page intent mismatch, UX, offer, or content quality may matter more than metadata.
- High GA4 sessions + weak GSC evidence: traffic may be paid, social, direct, email, or app-driven; inspect channel and landing dimensions before treating it as an SEO opportunity.
- GA4 `conversions` / key events are property-defined; confirm the event meaning before treating them as purchases.
- GA4 page-attributed revenue can be zero even when conversions exist, depending on attribution, event setup, or ecommerce implementation.
- If a GA4 product path has locales such as `/ja/products/...`, aggregate by handle before comparing with Shopify product handles.

## URL Inspection Rules

- If `Blocked by robots.txt` includes `/web-pixels`, `/sandbox/`, `/wpm@`, or `/cdn/wpm/`, classify it as expected internal robots blocking unless live evidence shows otherwise.
- If `Not found (404)` contains the hostname inside the path, classify it as malformed repeated-domain discovery unless a live source is reproduced.
- If `Not found (404)` contains repeated locale segments, classify it as malformed multilingual discovery unless the current site still emits it.
- If `referringUrls` is present, inspect the referring page live before deciding it is historical.

## Response Shape

Prefer:

1. Conclusion
2. GSC evidence
3. GA4 evidence when relevant
4. Live-site evidence
5. Recommendation
