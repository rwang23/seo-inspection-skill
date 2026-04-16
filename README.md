# gsc-inspection

[中文文档](README.zh-CN.md)

Reusable Google Search Console URL Inspection skill for debugging indexing, crawl, and `robots.txt` issues with evidence from the Search Console API instead of guesswork.

## What this skill includes

- `SKILL.md`: trigger guidance and workflow rules for the agent
- `scripts/gsc_inspection.py`: helper CLI for URL Inspection and basic classification
- `.env.example`: configuration template for credentials and Search Console property

## Configuration

This skill can read configuration from either location:

1. `./.env` inside the skill directory
2. project-root `.env`

If both exist, the skill-local `.env` wins.

Required keys:

```env
GSC_SERVICE_ACCOUNT_PATH=credential/google-service-account.json
GSC_SITE_URL=sc-domain:example.com
```

Optional key:

```env
GSC_LANGUAGE_CODE=en-US
```

For this workspace, a local `.env` can live beside this README. Do not commit it. Commit `.env.example` only.

## Credential setup

1. Place your Google service account JSON somewhere accessible in the repo, for example:

```text
credential/google-service-account.json
```

2. Add that service account email to your Search Console property with permission to inspect URLs.
3. Set `GSC_SERVICE_ACCOUNT_PATH` and `GSC_SITE_URL` in either supported `.env` file.

## Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## API coverage

This helper covers the main public Search Console API surfaces:

- `sites-list`, `sites-get`, `sites-add`, `sites-delete`
- `sitemaps-list`, `sitemaps-get`, `sitemaps-submit`, `sitemaps-delete`
- `searchanalytics-query`
- `inspect`

Write operations require `--apply`; without it the command returns a dry-run payload.

Official references:

- Search Console API reference: https://developers.google.com/webmaster-tools/v1/api_reference_index
- URL Inspection API: https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
- Search Analytics query: https://developers.google.com/webmaster-tools/v1/searchanalytics/query

## Usage

From the skill directory:

```powershell
python scripts/gsc_inspection.py inspect `
  --url "https://example.com/missing-page" `
  --output temp/gsc-inspection-run.json
```

Inspect multiple URLs from a file:

```powershell
python scripts/gsc_inspection.py inspect `
  --input-file temp/gsc-urls.txt `
  --output temp/gsc-inspection-run.json
```

List properties:

```powershell
python scripts/gsc_inspection.py sites-list `
  --output temp/gsc-sites.json
```

List submitted sitemaps:

```powershell
python scripts/gsc_inspection.py sitemaps-list `
  --output temp/gsc-sitemaps.json
```

Get one sitemap:

```powershell
python scripts/gsc_inspection.py sitemaps-get `
  --sitemap-url "https://example.com/sitemap.xml" `
  --output temp/gsc-sitemap.json
```

Submit a sitemap:

```powershell
python scripts/gsc_inspection.py sitemaps-submit `
  --sitemap-url "https://example.com/sitemap.xml" `
  --apply `
  --output temp/gsc-sitemap-submit.json
```

Query Search Analytics:

```powershell
python scripts/gsc_inspection.py searchanalytics-query `
  --start-date 2026-01-01 `
  --end-date 2026-01-31 `
  --dimensions query,page `
  --row-limit 1000 `
  --output temp/gsc-searchanalytics.json
```

Filter Search Analytics by page:

```powershell
python scripts/gsc_inspection.py searchanalytics-query `
  --start-date 2026-01-01 `
  --end-date 2026-01-31 `
  --dimensions query,page `
  --dimension-filter-groups '[{"filters":[{"dimension":"page","operator":"contains","expression":"/products/"}]}]' `
  --output temp/gsc-searchanalytics-products.json
```

Try the bundled sample shape without running the API:

```text
samples/urls.txt
samples/inspection-output.example.json
samples/searchanalytics-output.example.json
samples/sitemaps-output.example.json
```

The sample files are sanitized and use `example.com`; replace them with URLs from your own verified Search Console property before running the script.

## Common use cases

- Confirm whether a GSC `Not found (404)` URL is still being emitted or is only historical.
- Verify whether a URL is `Blocked by robots.txt` because of an intentional internal rule.
- Check `referringUrls` from URL Inspection before changing canonical, hreflang, or robots rules.
- Separate Shopify internal crawl targets from real storefront crawl problems.
- Build a batch evidence file before doing SEO cleanup work.
- Validate whether a redirect cleanup has been recognized by Google.
- Compare soft 404 and hard 404 examples before deciding whether content or routing needs work.
- Review parameterized URLs from filters, sorting, recommendations, ads, or tracking campaigns.
- Confirm whether a canonical mismatch is a live template issue or stale Google state.
- Audit localized URL examples after hreflang or market routing changes.
- Separate sitemap-discovered URLs from internally linked URLs using `referringUrls` evidence.

## Practical playbooks

### 404 cleanup after a migration

Use when GSC reports many `Not found (404)` URLs after a redesign, platform migration, or URL structure change.

1. Export representative examples from GSC.
2. Put one URL per line in an input file.
3. Run the script with `--input-file`.
4. Group by `classification`.
5. For URLs with `referringUrls`, fetch those referring pages live before creating redirects.
6. For URLs with no live source and old crawl dates, treat them as historical unless they have backlinks or traffic value.

### Robots block triage

Use when GSC reports `Blocked by robots.txt`.

1. Inspect examples with the script.
2. Confirm `robotsTxtState` is `DISALLOWED`.
3. Compare the path with intended internal exclusions such as admin, checkout, search, or platform-generated endpoints.
4. Change `robots.txt` only when the blocked URL should be indexable.

### Parameter URL review

Use for URLs containing tracking, sorting, filtering, search, recommendation, or session parameters.

1. Inspect the exact parameterized URL.
2. Check whether Google found a `referringUrls` source.
3. Decide whether the URL should be canonicalized, redirected, blocked, noindexed, or left alone.
4. Avoid broad `robots.txt` blocks until you confirm the parameter class is not needed for crawling important products or content.

### Canonical mismatch investigation

Use when GSC says Google chose a different canonical or the page is a duplicate.

1. Inspect the reported URL and its intended canonical target.
2. Fetch the live HTML and compare canonical tags.
3. Check whether internal links point to the canonical or duplicate URL.
4. Fix templates or links only if current live evidence still points Google at the wrong URL.

### Hreflang and localized URL validation

Use after changing language routes, markets, or hreflang output.

1. Inspect malformed localized examples and expected localized versions.
2. Check for repeated language prefixes or mixed locale paths.
3. Inspect referring URLs and live alternate links.
4. Treat old malformed examples as historical if current pages no longer emit them.

### Sitemap validation

Use when GSC examples appear to come from a sitemap.

1. Inspect the URL.
2. Check whether it has `referringUrls`.
3. Fetch the sitemap or sitemap index separately.
4. If the sitemap no longer lists the URL, treat repeated crawls as stale discovery.

### Bulk validation before closing a GSC issue

Use before telling a user that validation is ready.

1. Build a sample set across every issue pattern.
2. Run the script and save JSON output.
3. Verify at least one example per pattern with live fetches.
4. Report exact evidence, crawl dates, and residual risk.

## Output

The script writes JSON with:

- Search Console property access confirmation
- inspection result per URL
- normalized summary fields
- classification and rationale

Main classifications:

- `historical_malformed_domain_repeat_404`
- `historical_malformed_multilang_404`
- `shopify_internal_robots_block`
- `robots_blocked_other`
- `not_found_with_referring_source`
- `not_found_without_referrer`
- `needs_manual_review`

## Publishability notes

This skill is intentionally generic:

- no site-specific property is hardcoded in `SKILL.md`
- no credentials path is hardcoded in documentation beyond the example placeholder
- configuration is externalized into `.env`

Before sharing, verify:

1. `.env` is not committed
2. sample outputs do not contain private URLs you do not want to share
3. your target environment has `google-auth` installed

## Standalone GitHub repo workflow

This directory is designed to become the root of a standalone GitHub repository.

Recommended steps:

```powershell
Copy-Item -Recurse .claude/skills/gsc-inspection ../gsc-inspection
Set-Location ../gsc-inspection
git init
git add SKILL.md README.md .env.example .gitignore scripts samples
git commit -m "feat: publish gsc inspection skill"
```

Then create a GitHub repository and push this folder. Keep `.env`, credential files, temp outputs, and real inspection exports out of git.

## Current limitations

- The script covers public Search Console API endpoints, but not every Search Console UI report has an API equivalent.
- Classification is heuristic. It helps triage, but it does not replace inspecting live sources.
- The helper does not currently fetch live HTML by itself. Pair it with browser or HTTP checks when a referring source needs confirmation.
- Search Console UI reports that do not have a public API endpoint cannot be fetched directly by this skill.

## Good next upgrades

- Add optional live-fetch verification for referring URLs.
- Add CSV input and CSV summary export.
- Add richer platform-specific classifiers beyond the current internal pixel and sandbox patterns.
- Add sitemap fetch and URL membership checks.
- Add a report generator that turns JSON outputs into Markdown issue summaries.
