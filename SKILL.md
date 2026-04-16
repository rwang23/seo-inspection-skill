---
name: gsc-inspection
description: Use this skill whenever the user mentions Google Search Console, GSC, URL Inspection, indexing coverage, crawl status, referring URLs, or robots.txt blocking. Use it before changing SEO code whenever the question can be answered with Search Console evidence. This skill is especially useful for sorting historical malformed URLs from still-live crawl sources and for identifying internal platform URLs that are expected to be blocked.
---

# GSC Inspection

Inspect exact URLs with Search Console before changing canonical, hreflang, sitemap, internal links, or robots rules.

## Included files

- `scripts/gsc_inspection.py`: helper CLI for URL Inspection
- `.env.example`: config template
- `README.md`: setup and publishing notes

## Configuration

This skill supports two config locations:

1. `./.env` inside this skill directory
2. project-root `.env`

Skill-local `.env` overrides project-root `.env`.

Expected keys:

- `GSC_SERVICE_ACCOUNT_PATH`
- `GSC_SITE_URL`
- `GSC_LANGUAGE_CODE` (optional, defaults to `en-US`)

Do not hardcode private site settings into this file. Keep them in `.env`.

## When to use

- The user shows GSC examples and asks whether they are historical or still active.
- The user asks about `Not found (404)` coverage issues.
- The user asks about `Blocked by robots.txt`.
- The user asks which page is referring Google toward a bad URL.
- The user wants API-backed proof before SEO changes.
- The user asks why a URL is not indexed, crawled, or eligible for validation.
- The user asks whether a redirect, canonical, or hreflang cleanup actually changed Google's view.
- The user asks to triage a group of Search Console examples into action/no-action buckets.

## Standard workflow

1. Run the inspection script against the exact user-provided URLs.
2. Read `coverageState`, `robotsTxtState`, `pageFetchState`, `lastCrawlTime`, and `referringUrls`.
3. Compare the inspection result with the current live site output.
4. Classify the result before proposing any fix.

## Common use cases

- Historical malformed locale path investigation
- Repeated-domain path investigation
- Search result URL and `SearchAction` referral investigation
- Shopify internal pixel or sandbox URL review
- Batch review of newly surfaced GSC examples
- Post-migration 404 cleanup
- Parameter URL and faceted navigation triage
- Soft 404 versus hard 404 comparison
- Redirect validation after URL structure changes
- Canonical mismatch investigation
- Hreflang or localized path validation
- Robots block validation for admin, checkout, search, or platform-generated URLs
- Referring source analysis before editing templates or navigation
- Property access checks with `sites-list` and `sites-get`
- Submitted sitemap inventory and sitemap status checks
- Search Analytics performance pulls by query, page, country, device, date, or appearance

## Commands

Single URL:

```powershell
python scripts/gsc_inspection.py inspect `
  --url "https://example.com/path" `
  --output temp/gsc-inspection-run.json
```

Batch input:

```powershell
python scripts/gsc_inspection.py inspect `
  --input-file temp/gsc-urls.txt `
  --output temp/gsc-inspection-run.json
```

Override config explicitly:

```powershell
python scripts/gsc_inspection.py inspect `
  --credentials credential/google-service-account.json `
  --site-url "sc-domain:example.com" `
  --url "https://example.com/path" `
  --output temp/gsc-inspection-run.json
```

Other useful commands:

```powershell
python scripts/gsc_inspection.py sites-list --output temp/gsc-sites.json
python scripts/gsc_inspection.py sitemaps-list --output temp/gsc-sitemaps.json
python scripts/gsc_inspection.py searchanalytics-query --start-date 2026-01-01 --end-date 2026-01-31 --dimensions query,page --output temp/gsc-searchanalytics.json
```

Write commands such as `sites-add`, `sites-delete`, `sitemaps-submit`, and `sitemaps-delete` require `--apply`.

## Interpretation rules

- If the result is `Blocked by robots.txt` and the URL path includes internal platform markers like `/web-pixels`, `/sandbox/`, `/wpm@`, or `/cdn/wpm/`, classify it as expected internal robots blocking unless live evidence shows otherwise.
- If the result is `Not found (404)` and the path contains the hostname again inside the path, classify it as malformed repeated-domain discovery unless a live source is reproduced.
- If the result is `Not found (404)` and the path contains repeated locale segments, classify it as malformed multilingual discovery unless the current site still emits it.
- If `referringUrls` is present, inspect the referring page live before concluding the issue is purely historical.
- If the result is a redirect or canonical-related state, compare Google's selected canonical or final URL with the live page before editing canonical tags.
- If the result mentions crawl allowed but indexing excluded, do not change `robots.txt` first; inspect content quality, canonical, duplicate state, and live response.
- If the URL has tracking or faceted parameters, decide whether the parameterized URL should exist, canonicalize, redirect, or remain excluded.

## Playbooks

### Validate a reported 404

1. Inspect the exact URL from GSC.
2. Check `lastCrawlTime` and `referringUrls`.
3. Fetch the referring page if one exists.
4. Classify as historical if the current live site no longer emits the URL.

### Validate a robots block

1. Inspect the exact URL.
2. Confirm `robotsTxtState` and `pageFetchState`.
3. Compare the path with intentional robots rules.
4. Treat internal platform or admin endpoints as expected blocks unless the URL should be indexed.

### Check canonical or duplicate issues

1. Inspect the URL and read canonical-related fields from the raw output.
2. Fetch the live page and compare `<link rel="canonical">`.
3. Inspect the canonical target if needed.
4. Recommend changes only when live tags and GSC evidence disagree with the desired indexable URL.

### Triage a batch of examples

1. Put one URL per line in an input file.
2. Run `scripts/gsc_inspection.py --input-file`.
3. Group results by `classification`.
4. Investigate only groups that have live referring sources or unexpected robots/indexing states.

## Response shape

Prefer this structure:

1. Conclusion
2. Search Console evidence
3. Live-site evidence
4. Recommendation

Do not skip the evidence step.
