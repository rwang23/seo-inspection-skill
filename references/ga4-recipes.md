# GA4 Recipes for SEO Inspection

Use these recipes when a task needs analytics evidence beyond Search Console.

## Stable Data API Commands

The helper wraps stable GA4 Data API v1beta methods:

- `ga4-report` -> `runReport`
- `ga4-batch-report` -> `batchRunReports`
- `ga4-pivot-report` -> `runPivotReport`
- `ga4-batch-pivot-report` -> `batchRunPivotReports`
- `ga4-check-compatibility` -> `checkCompatibility`
- `ga4-metadata` -> `getMetadata`
- `ga4-realtime-report` -> `runRealtimeReport`

Early preview methods such as funnel reports and audience exports are not wrapped by default. Use official docs before adding them.

## Common Presets

### Product Pages

```powershell
python scripts/seo_inspection.py ga4-product-pages `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --aggregate-by-handle `
  --output temp/ga4-product-pages.json
```

Use with GSC `query,page` data to prioritize metadata, content, and product-page SEO work.

### Landing Pages

```powershell
python scripts/seo_inspection.py ga4-landing-pages `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --limit 1000 `
  --output temp/ga4-landing-pages.json
```

Use for entry-page efficiency: sessions, users, views, engagement rate, conversions, and revenue.

### Channels

```powershell
python scripts/seo_inspection.py ga4-channels `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --dimension sessionDefaultChannelGroup `
  --output temp/ga4-channels.json
```

Use to separate organic search opportunities from paid, social, direct, email, and referral traffic.

### Countries / Regions / Cities

```powershell
python scripts/seo_inspection.py ga4-geo `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --dimension country `
  --output temp/ga4-countries.json
```

Use for market prioritization, localization, hreflang validation support, and international SEO planning.

### Devices / Browsers

```powershell
python scripts/seo_inspection.py ga4-devices `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --dimension deviceCategory `
  --output temp/ga4-devices.json
```

Use when SEO performance appears device-specific or Core Web Vitals differ by device class.

### Events

```powershell
python scripts/seo_inspection.py ga4-events `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --output temp/ga4-events.json
```

Use to understand event volume, key events, and whether conversions are configured in a useful way.

### Ecommerce Items

```powershell
python scripts/seo_inspection.py ga4-ecommerce-items `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --output temp/ga4-items.json
```

Use for item-level merchandising and product demand. If item metrics return empty, inspect GA4 ecommerce implementation before trusting revenue conclusions.

### Time Series

```powershell
python scripts/seo_inspection.py ga4-timeseries `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --dimension date `
  --metrics sessions,activeUsers,conversions,totalRevenue `
  --output temp/ga4-timeseries.json
```

Use for before/after checks and post-deployment trend monitoring.

## Generic Reports

Use `ga4-report` when a preset is too narrow:

```powershell
python scripts/seo_inspection.py ga4-report `
  --start-date 2026-01-17 `
  --end-date 2026-04-16 `
  --dimensions pagePath,sessionDefaultChannelGroup `
  --metrics sessions,engagementRate,conversions,totalRevenue `
  --dimension-filter '{"filter":{"fieldName":"pagePath","stringFilter":{"matchType":"CONTAINS","value":"/products/"}}}' `
  --output temp/ga4-product-channel.json
```

Prefer `--body-file` / `--requests-file` for complex JSON to avoid shell escaping problems.

## Compatibility Check

Before combining unfamiliar fields:

```powershell
python scripts/seo_inspection.py ga4-check-compatibility `
  --dimensions pagePath,sessionDefaultChannelGroup `
  --metrics sessions,totalRevenue `
  --output temp/ga4-compatibility.json
```

If compatibility fails, run `ga4-metadata` and choose a valid field set.

## Batch Reports

Create `temp/ga4-batch-requests.json`:

```json
[
  {
    "dateRanges": [{"startDate": "2026-01-17", "endDate": "2026-04-16"}],
    "dimensions": [{"name": "date"}],
    "metrics": [{"name": "sessions"}],
    "limit": 1000
  },
  {
    "dateRanges": [{"startDate": "2026-01-17", "endDate": "2026-04-16"}],
    "dimensions": [{"name": "sessionDefaultChannelGroup"}],
    "metrics": [{"name": "sessions"}],
    "limit": 1000
  }
]
```

Run:

```powershell
python scripts/seo_inspection.py ga4-batch-report `
  --requests-file temp/ga4-batch-requests.json `
  --output temp/ga4-batch.json
```

## Interpretation Notes

- `conversions` are GA4 key events; confirm which events are marked as key events before treating them as purchases.
- `totalRevenue` depends on ecommerce event quality and attribution. Zero revenue with non-zero conversions can be normal for non-purchase key events.
- Product handle aggregation merges localized product paths such as `/ja/products/example-handle` with `/products/example-handle`.
- Realtime data covers recent activity only; use it for smoke checks, not historical decisions.
- Search Console and GA4 use different attribution and sampling/processing models. Do not expect their clicks and sessions to match exactly.
