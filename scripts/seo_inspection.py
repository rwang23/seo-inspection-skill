#!/usr/bin/env python3
"""Reusable SEO evidence helper for Search Console and GA4."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account


SCRIPT_PATH = Path(__file__).resolve()
SKILL_DIR = SCRIPT_PATH.parent.parent
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
API_ROOT = "https://searchconsole.googleapis.com"
WEBMASTERS_ROOT = "https://searchconsole.googleapis.com/webmasters/v3"
ANALYTICS_ADMIN_ROOT = "https://analyticsadmin.googleapis.com/v1beta"
ANALYTICS_DATA_ROOT = "https://analyticsdata.googleapis.com/v1beta"

DEFAULT_LANGUAGE_CODE = "en-US"
DEFAULT_ROW_LIMIT = 1000
DOUBLE_LOCALE_RE = re.compile(r"https://[^/]+/(?:[a-z]{2})(?:/[a-z]{2})+/", re.IGNORECASE)


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        clean_key = key.strip().lstrip("\ufeff")
        values[clean_key] = value.strip().strip('"').strip("'")
    return values


def load_config() -> dict[str, str]:
    root_env = load_env_file(PROJECT_ROOT / ".env")
    skill_env = load_env_file(SKILL_DIR / ".env")
    merged = {**root_env, **skill_env}
    for key in (
        "GSC_SERVICE_ACCOUNT_PATH",
        "GOOGLE_SERVICE_ACCOUNT_PATH",
        "GSC_SITE_URL",
        "GSC_LANGUAGE_CODE",
        "GA4_PROPERTY_ID",
    ):
        if key in os.environ and os.environ[key]:
            merged[key] = os.environ[key]
    return merged


def resolve_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    skill_relative = (SKILL_DIR / candidate).resolve()
    if skill_relative.exists():
        return skill_relative
    return (PROJECT_ROOT / candidate).resolve()


def encoded(value: str) -> str:
    return quote(value, safe="")


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_json_arg(value: str | None, label: str) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON for {label}: {exc}") from exc


def parse_json_file_arg(path_value: str | None, label: str) -> Any:
    if not path_value:
        return None
    path = Path(path_value)
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {label} file {path}: {exc}") from exc


def load_urls(urls: list[str], input_file: str | None) -> list[str]:
    loaded = list(urls)
    if input_file:
        for line in Path(input_file).read_text(encoding="utf-8").splitlines():
            item = line.strip()
            if item and not item.startswith("#"):
                loaded.append(item)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in loaded:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    if not deduped:
        raise SystemExit("No URLs supplied. Use --url or --input-file.")
    return deduped


def add_global_args(parser: argparse.ArgumentParser, config: dict[str, str]) -> None:
    parser.add_argument(
        "--credentials",
        default=config.get("GSC_SERVICE_ACCOUNT_PATH") or config.get("GOOGLE_SERVICE_ACCOUNT_PATH"),
        help="Path to the Google service account JSON file.",
    )
    parser.add_argument(
        "--site-url",
        default=config.get("GSC_SITE_URL"),
        help="Search Console property, for example sc-domain:example.com.",
    )
    parser.add_argument(
        "--language-code",
        default=config.get("GSC_LANGUAGE_CODE", DEFAULT_LANGUAGE_CODE),
    )
    parser.add_argument(
        "--ga4-property-id",
        default=config.get("GA4_PROPERTY_ID"),
        help="GA4 numeric property ID, for example 346785523.",
    )
    parser.add_argument("--output", help="Write JSON results to this file. Defaults to stdout.")


def add_output_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", help="Write JSON results to this file. Defaults to stdout.")


def parse_args(config: dict[str, str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SEO API helper for Search Console and GA4.")
    add_global_args(parser, config)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sites_list = subparsers.add_parser("sites-list", help="List Search Console properties.")
    add_output_arg(sites_list)
    sites_list.set_defaults(handler=cmd_sites_list)

    sites_get = subparsers.add_parser("sites-get", help="Get one Search Console property.")
    add_output_arg(sites_get)
    sites_get.set_defaults(handler=cmd_sites_get)

    sites_add = subparsers.add_parser("sites-add", help="Add a Search Console property.")
    sites_add.add_argument("--apply", action="store_true", help="Actually perform the write.")
    add_output_arg(sites_add)
    sites_add.set_defaults(handler=cmd_sites_add)

    sites_delete = subparsers.add_parser("sites-delete", help="Delete a Search Console property.")
    sites_delete.add_argument("--apply", action="store_true", help="Actually perform the write.")
    add_output_arg(sites_delete)
    sites_delete.set_defaults(handler=cmd_sites_delete)

    sitemaps_list = subparsers.add_parser("sitemaps-list", help="List submitted sitemaps.")
    add_output_arg(sitemaps_list)
    sitemaps_list.set_defaults(handler=cmd_sitemaps_list)

    sitemaps_get = subparsers.add_parser("sitemaps-get", help="Get one sitemap.")
    sitemaps_get.add_argument("--sitemap-url", required=True)
    add_output_arg(sitemaps_get)
    sitemaps_get.set_defaults(handler=cmd_sitemaps_get)

    sitemaps_submit = subparsers.add_parser("sitemaps-submit", help="Submit a sitemap.")
    sitemaps_submit.add_argument("--sitemap-url", required=True)
    sitemaps_submit.add_argument("--apply", action="store_true", help="Actually perform the write.")
    add_output_arg(sitemaps_submit)
    sitemaps_submit.set_defaults(handler=cmd_sitemaps_submit)

    sitemaps_delete = subparsers.add_parser("sitemaps-delete", help="Delete a submitted sitemap.")
    sitemaps_delete.add_argument("--sitemap-url", required=True)
    sitemaps_delete.add_argument("--apply", action="store_true", help="Actually perform the write.")
    add_output_arg(sitemaps_delete)
    sitemaps_delete.set_defaults(handler=cmd_sitemaps_delete)

    analytics = subparsers.add_parser("searchanalytics-query", help="Query Search Analytics data.")
    analytics.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    analytics.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    analytics.add_argument("--dimensions", default="query,page", help="Comma-separated dimensions.")
    analytics.add_argument("--search-type", help="web, image, video, news, googleNews, discover.")
    analytics.add_argument("--aggregation-type", help="auto, byPage, byProperty, byNewsShowcasePanel.")
    analytics.add_argument("--data-state", help="final or all.")
    analytics.add_argument("--row-limit", type=int, default=DEFAULT_ROW_LIMIT)
    analytics.add_argument("--start-row", type=int, default=0)
    analytics.add_argument(
        "--dimension-filter-groups",
        help="Raw JSON for dimensionFilterGroups.",
    )
    add_output_arg(analytics)
    analytics.set_defaults(handler=cmd_searchanalytics_query)

    inspect = subparsers.add_parser("inspect", help="Inspect one or more URLs.")
    inspect.add_argument("--url", action="append", default=[], help="URL to inspect. Repeatable.")
    inspect.add_argument("--input-file", help="File containing one URL per line.")
    add_output_arg(inspect)
    inspect.set_defaults(handler=cmd_inspect)

    ga4_accounts = subparsers.add_parser(
        "ga4-account-summaries",
        help="List GA4 accounts and properties visible to the service account.",
    )
    add_output_arg(ga4_accounts)
    ga4_accounts.set_defaults(handler=cmd_ga4_account_summaries)

    ga4_metadata = subparsers.add_parser(
        "ga4-metadata",
        help="List GA4 dimensions and metrics for the configured property.",
    )
    add_output_arg(ga4_metadata)
    ga4_metadata.set_defaults(handler=cmd_ga4_metadata)

    ga4_report = subparsers.add_parser("ga4-report", help="Run a generic GA4 Data API report.")
    ga4_report.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ga4_report.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ga4_report.add_argument("--dimensions", default="pagePath", help="Comma-separated GA4 dimensions.")
    ga4_report.add_argument("--metrics", default="sessions,activeUsers,screenPageViews,engagementRate,conversions,totalRevenue", help="Comma-separated GA4 metrics.")
    ga4_report.add_argument("--dimension-filter", help="Raw JSON for dimensionFilter.")
    ga4_report.add_argument("--metric-filter", help="Raw JSON for metricFilter.")
    ga4_report.add_argument("--order-bys", help="Raw JSON for orderBys.")
    ga4_report.add_argument("--limit", type=int, default=DEFAULT_ROW_LIMIT)
    ga4_report.add_argument("--offset", type=int, default=0)
    ga4_report.add_argument("--keep-empty-rows", action="store_true")
    add_output_arg(ga4_report)
    ga4_report.set_defaults(handler=cmd_ga4_report)

    ga4_batch_report = subparsers.add_parser(
        "ga4-batch-report",
        help="Run multiple GA4 reports in one Data API request.",
    )
    ga4_batch_report.add_argument(
        "--requests-json",
        help="Raw JSON array for the reports field. Each report is a RunReportRequest without property.",
    )
    ga4_batch_report.add_argument(
        "--requests-file",
        help="JSON file containing either an array of report requests or an object with a reports array.",
    )
    add_output_arg(ga4_batch_report)
    ga4_batch_report.set_defaults(handler=cmd_ga4_batch_report)

    ga4_pivot_report = subparsers.add_parser(
        "ga4-pivot-report",
        help="Run a GA4 pivot report using a raw request body.",
    )
    ga4_pivot_report.add_argument("--body-json", help="Raw JSON request body for runPivotReport.")
    ga4_pivot_report.add_argument("--body-file", help="JSON file request body for runPivotReport.")
    add_output_arg(ga4_pivot_report)
    ga4_pivot_report.set_defaults(handler=cmd_ga4_pivot_report)

    ga4_batch_pivot_report = subparsers.add_parser(
        "ga4-batch-pivot-report",
        help="Run multiple GA4 pivot reports in one Data API request.",
    )
    ga4_batch_pivot_report.add_argument(
        "--requests-json",
        help="Raw JSON array for the requests field. Each request is a RunPivotReportRequest without property.",
    )
    ga4_batch_pivot_report.add_argument(
        "--requests-file",
        help="JSON file containing either an array of pivot requests or an object with a requests array.",
    )
    add_output_arg(ga4_batch_pivot_report)
    ga4_batch_pivot_report.set_defaults(handler=cmd_ga4_batch_pivot_report)

    ga4_check_compat = subparsers.add_parser(
        "ga4-check-compatibility",
        help="Check whether GA4 dimensions and metrics are compatible.",
    )
    ga4_check_compat.add_argument("--dimensions", required=True, help="Comma-separated GA4 dimensions.")
    ga4_check_compat.add_argument("--metrics", required=True, help="Comma-separated GA4 metrics.")
    ga4_check_compat.add_argument(
        "--compatibility-filter",
        help="Raw JSON compatibilityFilter, for example {\"compatibility\":\"COMPATIBLE\"}.",
    )
    add_output_arg(ga4_check_compat)
    ga4_check_compat.set_defaults(handler=cmd_ga4_check_compatibility)

    ga4_product_pages = subparsers.add_parser(
        "ga4-product-pages",
        help="Run a GA4 report for product-page paths, optionally aggregating by product handle.",
    )
    ga4_product_pages.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ga4_product_pages.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ga4_product_pages.add_argument("--path-contains", default="/products/")
    ga4_product_pages.add_argument("--limit", type=int, default=10000)
    ga4_product_pages.add_argument("--aggregate-by-handle", action="store_true")
    add_output_arg(ga4_product_pages)
    ga4_product_pages.set_defaults(handler=cmd_ga4_product_pages)

    ga4_landing_pages = subparsers.add_parser(
        "ga4-landing-pages",
        help="Preset GA4 landing-page performance report.",
    )
    ga4_landing_pages.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ga4_landing_pages.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ga4_landing_pages.add_argument("--limit", type=int, default=1000)
    add_output_arg(ga4_landing_pages)
    ga4_landing_pages.set_defaults(handler=cmd_ga4_landing_pages)

    ga4_channels = subparsers.add_parser("ga4-channels", help="Preset GA4 traffic channel report.")
    ga4_channels.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ga4_channels.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ga4_channels.add_argument("--dimension", default="sessionDefaultChannelGroup")
    ga4_channels.add_argument("--limit", type=int, default=1000)
    add_output_arg(ga4_channels)
    ga4_channels.set_defaults(handler=cmd_ga4_channels)

    ga4_geo = subparsers.add_parser("ga4-geo", help="Preset GA4 country or region report.")
    ga4_geo.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ga4_geo.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ga4_geo.add_argument("--dimension", default="country", choices=["country", "region", "city"])
    ga4_geo.add_argument("--limit", type=int, default=1000)
    add_output_arg(ga4_geo)
    ga4_geo.set_defaults(handler=cmd_ga4_geo)

    ga4_devices = subparsers.add_parser("ga4-devices", help="Preset GA4 device/browser report.")
    ga4_devices.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ga4_devices.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ga4_devices.add_argument("--dimension", default="deviceCategory", choices=["deviceCategory", "browser", "operatingSystem"])
    ga4_devices.add_argument("--limit", type=int, default=1000)
    add_output_arg(ga4_devices)
    ga4_devices.set_defaults(handler=cmd_ga4_devices)

    ga4_events = subparsers.add_parser("ga4-events", help="Preset GA4 event performance report.")
    ga4_events.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ga4_events.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ga4_events.add_argument("--limit", type=int, default=1000)
    add_output_arg(ga4_events)
    ga4_events.set_defaults(handler=cmd_ga4_events)

    ga4_ecommerce = subparsers.add_parser(
        "ga4-ecommerce-items",
        help="Preset GA4 ecommerce item performance report.",
    )
    ga4_ecommerce.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ga4_ecommerce.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ga4_ecommerce.add_argument("--limit", type=int, default=1000)
    add_output_arg(ga4_ecommerce)
    ga4_ecommerce.set_defaults(handler=cmd_ga4_ecommerce_items)

    ga4_timeseries = subparsers.add_parser("ga4-timeseries", help="Preset GA4 date trend report.")
    ga4_timeseries.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    ga4_timeseries.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    ga4_timeseries.add_argument("--dimension", default="date", choices=["date", "week", "month"])
    ga4_timeseries.add_argument("--metrics", default="sessions,activeUsers,conversions,totalRevenue")
    ga4_timeseries.add_argument("--limit", type=int, default=5000)
    add_output_arg(ga4_timeseries)
    ga4_timeseries.set_defaults(handler=cmd_ga4_timeseries)

    ga4_realtime = subparsers.add_parser("ga4-realtime-report", help="Run a GA4 realtime report.")
    ga4_realtime.add_argument("--dimensions", default="unifiedScreenName")
    ga4_realtime.add_argument("--metrics", default="activeUsers")
    ga4_realtime.add_argument("--dimension-filter", help="Raw JSON for dimensionFilter.")
    ga4_realtime.add_argument("--metric-filter", help="Raw JSON for metricFilter.")
    ga4_realtime.add_argument("--limit", type=int, default=100)
    add_output_arg(ga4_realtime)
    ga4_realtime.set_defaults(handler=cmd_ga4_realtime_report)

    args = parser.parse_args()
    if not args.credentials:
        raise SystemExit("Missing credentials path. Set GSC_SERVICE_ACCOUNT_PATH, GOOGLE_SERVICE_ACCOUNT_PATH, or use --credentials.")
    return args


def build_session(credentials_path: Path) -> AuthorizedSession:
    creds = service_account.Credentials.from_service_account_file(
        str(credentials_path),
        scopes=[
            "https://www.googleapis.com/auth/webmasters",
            "https://www.googleapis.com/auth/analytics.readonly",
        ],
    )
    return AuthorizedSession(creds)


def require_site_url(args: argparse.Namespace) -> str:
    if not args.site_url:
        raise SystemExit("Missing Search Console property. Set GSC_SITE_URL or use --site-url.")
    return args.site_url


def require_ga4_property_id(args: argparse.Namespace) -> str:
    if not args.ga4_property_id:
        raise SystemExit("Missing GA4 property ID. Set GA4_PROPERTY_ID or use --ga4-property-id.")
    return str(args.ga4_property_id).removeprefix("properties/")


def ga4_field_list(value: str, field_name: str) -> list[dict[str, str]]:
    return [{field_name: item} for item in parse_csv(value)]


def ga4_numeric(value: str) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number


def extract_product_handle(page_path: str) -> str | None:
    match = re.search(r"/(?:[a-z]{2}(?:-[a-z]{2})?/)?products/([^/?#]+)", page_path, re.I)
    return match.group(1) if match else None


def write_output(payload: dict[str, Any], output_path: str | None) -> None:
    text = json.dumps(payload, ensure_ascii=True, indent=2)
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"Wrote output to {path}")
    else:
        print(text)


def response_json_or_empty(response: Any) -> dict[str, Any]:
    if not response.content:
        return {}
    return response.json()


def guard_write(args: argparse.Namespace, action: str) -> dict[str, Any] | None:
    if getattr(args, "apply", False):
        return None
    return {
        "dry_run": True,
        "action": action,
        "message": "This is a write operation. Re-run with --apply to execute it.",
    }


def cmd_sites_list(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    response = session.get(f"{WEBMASTERS_ROOT}/sites")
    response.raise_for_status()
    return {"command": args.command, "result": response_json_or_empty(response)}


def cmd_sites_get(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    site_url = require_site_url(args)
    response = session.get(f"{WEBMASTERS_ROOT}/sites/{encoded(site_url)}")
    response.raise_for_status()
    return {"command": args.command, "site_url": site_url, "result": response_json_or_empty(response)}


def cmd_sites_add(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    site_url = require_site_url(args)
    dry_run = guard_write(args, f"add site {site_url}")
    if dry_run:
        return dry_run
    response = session.put(f"{WEBMASTERS_ROOT}/sites/{encoded(site_url)}")
    response.raise_for_status()
    return {"command": args.command, "site_url": site_url, "result": response_json_or_empty(response)}


def cmd_sites_delete(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    site_url = require_site_url(args)
    dry_run = guard_write(args, f"delete site {site_url}")
    if dry_run:
        return dry_run
    response = session.delete(f"{WEBMASTERS_ROOT}/sites/{encoded(site_url)}")
    response.raise_for_status()
    return {"command": args.command, "site_url": site_url, "result": response_json_or_empty(response)}


def cmd_sitemaps_list(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    site_url = require_site_url(args)
    response = session.get(f"{WEBMASTERS_ROOT}/sites/{encoded(site_url)}/sitemaps")
    response.raise_for_status()
    return {"command": args.command, "site_url": site_url, "result": response_json_or_empty(response)}


def cmd_sitemaps_get(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    site_url = require_site_url(args)
    response = session.get(
        f"{WEBMASTERS_ROOT}/sites/{encoded(site_url)}/sitemaps/{encoded(args.sitemap_url)}"
    )
    response.raise_for_status()
    return {
        "command": args.command,
        "site_url": site_url,
        "sitemap_url": args.sitemap_url,
        "result": response_json_or_empty(response),
    }


def cmd_sitemaps_submit(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    site_url = require_site_url(args)
    dry_run = guard_write(args, f"submit sitemap {args.sitemap_url}")
    if dry_run:
        return dry_run
    response = session.put(
        f"{WEBMASTERS_ROOT}/sites/{encoded(site_url)}/sitemaps/{encoded(args.sitemap_url)}"
    )
    response.raise_for_status()
    return {
        "command": args.command,
        "site_url": site_url,
        "sitemap_url": args.sitemap_url,
        "result": response_json_or_empty(response),
    }


def cmd_sitemaps_delete(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    site_url = require_site_url(args)
    dry_run = guard_write(args, f"delete sitemap {args.sitemap_url}")
    if dry_run:
        return dry_run
    response = session.delete(
        f"{WEBMASTERS_ROOT}/sites/{encoded(site_url)}/sitemaps/{encoded(args.sitemap_url)}"
    )
    response.raise_for_status()
    return {
        "command": args.command,
        "site_url": site_url,
        "sitemap_url": args.sitemap_url,
        "result": response_json_or_empty(response),
    }


def cmd_searchanalytics_query(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    site_url = require_site_url(args)
    body: dict[str, Any] = {
        "startDate": args.start_date,
        "endDate": args.end_date,
        "dimensions": parse_csv(args.dimensions),
        "rowLimit": args.row_limit,
        "startRow": args.start_row,
    }
    if args.search_type:
        body["searchType"] = args.search_type
    if args.aggregation_type:
        body["aggregationType"] = args.aggregation_type
    if args.data_state:
        body["dataState"] = args.data_state
    dimension_filter_groups = parse_json_arg(
        args.dimension_filter_groups, "dimension-filter-groups"
    )
    if dimension_filter_groups is not None:
        body["dimensionFilterGroups"] = dimension_filter_groups

    response = session.post(
        f"{WEBMASTERS_ROOT}/sites/{encoded(site_url)}/searchAnalytics/query",
        json=body,
    )
    response.raise_for_status()
    return {"command": args.command, "site_url": site_url, "request": body, "result": response.json()}


def inspect_url(
    session: AuthorizedSession, site_url: str, inspection_url: str, language_code: str
) -> dict[str, Any]:
    payload = {
        "inspectionUrl": inspection_url,
        "siteUrl": site_url,
        "languageCode": language_code,
    }
    response = session.post(f"{API_ROOT}/v1/urlInspection/index:inspect", json=payload)
    response.raise_for_status()
    return response.json()


def classify_url(url: str, status: dict[str, Any]) -> tuple[str, str]:
    coverage = status.get("coverageState", "")
    robots = status.get("robotsTxtState", "")
    fetch = status.get("pageFetchState", "")
    referring = status.get("referringUrls", [])

    if robots == "DISALLOWED" or "Blocked by robots.txt" in coverage:
        if any(token in url for token in ("/web-pixels", "/sandbox/", "/wpm@", "/cdn/wpm/")):
            return (
                "shopify_internal_robots_block",
                "Internal platform pixel or sandbox URL. Usually expected to be disallowed by robots rules.",
            )
        return (
            "robots_blocked_other",
            "Blocked by robots.txt but not matched to the common internal pixel or sandbox URL pattern.",
        )

    if fetch == "NOT_FOUND" or "Not found (404)" in coverage:
        hostname = ""
        if "://" in url:
            hostname = url.split("://", 1)[1].split("/", 1)[0]
        if hostname and f"/{hostname}/" in url:
            return (
                "historical_malformed_domain_repeat_404",
                "Malformed URL contains the hostname inside the path. Often historical bad discovery or concatenation output.",
            )
        if DOUBLE_LOCALE_RE.search(url):
            return (
                "historical_malformed_multilang_404",
                "Malformed URL contains repeated locale segments. Often caused by historical locale-path concatenation bugs.",
            )
        if referring:
            return (
                "not_found_with_referring_source",
                "404 with at least one referring URL. Inspect the referring source before deciding whether the issue is still live.",
            )
        return (
            "not_found_without_referrer",
            "404 with no referring URL returned by the Inspection API.",
        )

    return ("needs_manual_review", "Inspection result does not match the main heuristics.")


def extract_summary(inspection_payload: dict[str, Any], inspected_url: str) -> dict[str, Any]:
    result = inspection_payload.get("inspectionResult", {})
    status = result.get("indexStatusResult", {})
    classification, rationale = classify_url(inspected_url, status)
    return {
        "url": inspected_url,
        "classification": classification,
        "classification_rationale": rationale,
        "verdict": status.get("verdict"),
        "coverageState": status.get("coverageState"),
        "robotsTxtState": status.get("robotsTxtState"),
        "indexingState": status.get("indexingState"),
        "pageFetchState": status.get("pageFetchState"),
        "lastCrawlTime": status.get("lastCrawlTime"),
        "referringUrls": status.get("referringUrls", []),
        "inspectionResultLink": result.get("inspectionResultLink"),
        "raw": inspection_payload,
    }


def cmd_inspect(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    site_url = require_site_url(args)
    urls = load_urls(args.url, args.input_file)
    inspected: list[dict[str, Any]] = []
    for item in urls:
        payload = inspect_url(session, site_url, item, args.language_code)
        inspected.append(extract_summary(payload, item))
    return {
        "command": args.command,
        "site_url": site_url,
        "inspected_count": len(inspected),
        "results": inspected,
    }


def cmd_ga4_account_summaries(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    response = session.get(f"{ANALYTICS_ADMIN_ROOT}/accountSummaries")
    response.raise_for_status()
    return {"command": args.command, "result": response_json_or_empty(response)}


def cmd_ga4_metadata(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    response = session.get(f"{ANALYTICS_DATA_ROOT}/properties/{property_id}/metadata")
    response.raise_for_status()
    return {
        "command": args.command,
        "ga4_property_id": property_id,
        "result": response_json_or_empty(response),
    }


def build_ga4_report_body(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {
        "dateRanges": [{"startDate": args.start_date, "endDate": args.end_date}],
        "dimensions": ga4_field_list(args.dimensions, "name"),
        "metrics": ga4_field_list(args.metrics, "name"),
        "limit": args.limit,
        "offset": args.offset,
    }
    if getattr(args, "keep_empty_rows", False):
        body["keepEmptyRows"] = True
    dimension_filter = parse_json_arg(getattr(args, "dimension_filter", None), "dimension-filter")
    if dimension_filter is not None:
        body["dimensionFilter"] = dimension_filter
    metric_filter = parse_json_arg(getattr(args, "metric_filter", None), "metric-filter")
    if metric_filter is not None:
        body["metricFilter"] = metric_filter
    order_bys = parse_json_arg(getattr(args, "order_bys", None), "order-bys")
    if order_bys is not None:
        body["orderBys"] = order_bys
    return body


def run_ga4_report(session: AuthorizedSession, property_id: str, body: dict[str, Any]) -> dict[str, Any]:
    response = session.post(
        f"{ANALYTICS_DATA_ROOT}/properties/{property_id}:runReport",
        json=body,
    )
    response.raise_for_status()
    return response.json()


def run_ga4_method(
    session: AuthorizedSession, property_id: str, method: str, body: dict[str, Any]
) -> dict[str, Any]:
    response = session.post(
        f"{ANALYTICS_DATA_ROOT}/properties/{property_id}:{method}",
        json=body,
    )
    response.raise_for_status()
    return response_json_or_empty(response)


def cmd_ga4_report(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body = build_ga4_report_body(args)
    return {
        "command": args.command,
        "ga4_property_id": property_id,
        "request": body,
        "result": run_ga4_report(session, property_id, body),
    }


def load_ga4_requests(args: argparse.Namespace, label: str) -> list[dict[str, Any]]:
    raw = parse_json_arg(getattr(args, "requests_json", None), f"{label}-json")
    from_file = parse_json_file_arg(getattr(args, "requests_file", None), f"{label}-file")
    payload = raw if raw is not None else from_file
    if payload is None:
        raise SystemExit(f"Missing {label}. Use --requests-json or --requests-file.")
    if isinstance(payload, dict):
        payload = payload.get("requests") or payload.get("reports")
    if not isinstance(payload, list):
        raise SystemExit(f"{label} must be a JSON array or an object with requests/reports.")
    return payload


def cmd_ga4_batch_report(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    requests_payload = load_ga4_requests(args, "GA4 batch report requests")
    body = {"requests": requests_payload}
    return {
        "command": args.command,
        "ga4_property_id": property_id,
        "request": body,
        "result": run_ga4_method(session, property_id, "batchRunReports", body),
    }


def load_body_arg(args: argparse.Namespace, label: str) -> dict[str, Any]:
    raw = parse_json_arg(getattr(args, "body_json", None), f"{label}-json")
    from_file = parse_json_file_arg(getattr(args, "body_file", None), f"{label}-file")
    body = raw if raw is not None else from_file
    if not isinstance(body, dict):
        raise SystemExit(f"Missing or invalid {label}. Use --body-json or --body-file with a JSON object.")
    return body


def cmd_ga4_pivot_report(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body = load_body_arg(args, "GA4 pivot report body")
    return {
        "command": args.command,
        "ga4_property_id": property_id,
        "request": body,
        "result": run_ga4_method(session, property_id, "runPivotReport", body),
    }


def cmd_ga4_batch_pivot_report(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    requests_payload = load_ga4_requests(args, "GA4 batch pivot report requests")
    body = {"requests": requests_payload}
    return {
        "command": args.command,
        "ga4_property_id": property_id,
        "request": body,
        "result": run_ga4_method(session, property_id, "batchRunPivotReports", body),
    }


def cmd_ga4_check_compatibility(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body: dict[str, Any] = {
        "dimensions": ga4_field_list(args.dimensions, "name"),
        "metrics": ga4_field_list(args.metrics, "name"),
    }
    compatibility_filter = parse_json_arg(args.compatibility_filter, "compatibility-filter")
    if compatibility_filter is not None:
        body["compatibilityFilter"] = compatibility_filter
    return {
        "command": args.command,
        "ga4_property_id": property_id,
        "request": body,
        "result": run_ga4_method(session, property_id, "checkCompatibility", body),
    }


def ga4_preset_payload(
    command: str,
    property_id: str,
    body: dict[str, Any],
    session: AuthorizedSession,
) -> dict[str, Any]:
    return {
        "command": command,
        "ga4_property_id": property_id,
        "request": body,
        "result": run_ga4_report(session, property_id, body),
    }


def ga4_standard_body(
    args: argparse.Namespace,
    dimensions: list[str],
    metrics: list[str],
    order_metric: str = "sessions",
) -> dict[str, Any]:
    return {
        "dateRanges": [{"startDate": args.start_date, "endDate": args.end_date}],
        "dimensions": [{"name": item} for item in dimensions],
        "metrics": [{"name": item} for item in metrics],
        "orderBys": [{"metric": {"metricName": order_metric}, "desc": True}],
        "limit": args.limit,
    }


def cmd_ga4_landing_pages(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body = ga4_standard_body(
        args,
        ["landingPagePlusQueryString"],
        ["sessions", "activeUsers", "screenPageViews", "engagementRate", "conversions", "totalRevenue"],
    )
    return ga4_preset_payload(args.command, property_id, body, session)


def cmd_ga4_channels(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body = ga4_standard_body(
        args,
        [args.dimension],
        ["sessions", "activeUsers", "engagementRate", "conversions", "totalRevenue"],
    )
    return ga4_preset_payload(args.command, property_id, body, session)


def cmd_ga4_geo(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body = ga4_standard_body(
        args,
        [args.dimension],
        ["sessions", "activeUsers", "engagementRate", "conversions", "totalRevenue"],
    )
    return ga4_preset_payload(args.command, property_id, body, session)


def cmd_ga4_devices(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body = ga4_standard_body(
        args,
        [args.dimension],
        ["sessions", "activeUsers", "engagementRate", "conversions", "totalRevenue"],
    )
    return ga4_preset_payload(args.command, property_id, body, session)


def cmd_ga4_events(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body = ga4_standard_body(
        args,
        ["eventName"],
        ["eventCount", "activeUsers", "conversions", "totalRevenue"],
        order_metric="eventCount",
    )
    return ga4_preset_payload(args.command, property_id, body, session)


def cmd_ga4_ecommerce_items(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body = ga4_standard_body(
        args,
        ["itemName", "itemId"],
        ["itemsViewed", "itemsAddedToCart", "itemsPurchased", "itemRevenue"],
        order_metric="itemsViewed",
    )
    return ga4_preset_payload(args.command, property_id, body, session)


def cmd_ga4_timeseries(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body = ga4_standard_body(
        args,
        [args.dimension],
        parse_csv(args.metrics),
        order_metric=parse_csv(args.metrics)[0],
    )
    body["orderBys"] = [{"dimension": {"dimensionName": args.dimension}}]
    return ga4_preset_payload(args.command, property_id, body, session)


def aggregate_product_page_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    aggregated: dict[str, dict[str, float]] = {}
    for row in rows:
        page_path = row["dimensionValues"][0]["value"]
        handle = extract_product_handle(page_path)
        if not handle:
            continue
        metric_values = [ga4_numeric(item["value"]) for item in row.get("metricValues", [])]
        sessions, active_users, page_views, engagement_rate, conversions, total_revenue = metric_values
        item = aggregated.setdefault(
            handle,
            {
                "sessions": 0,
                "activeUsers": 0,
                "screenPageViews": 0,
                "engagementRateNumerator": 0,
                "conversions": 0,
                "totalRevenue": 0,
            },
        )
        item["sessions"] += sessions
        item["activeUsers"] += active_users
        item["screenPageViews"] += page_views
        item["engagementRateNumerator"] += engagement_rate * sessions
        item["conversions"] += conversions
        item["totalRevenue"] += total_revenue
    for item in aggregated.values():
        sessions = item["sessions"]
        item["engagementRate"] = item["engagementRateNumerator"] / sessions if sessions else 0
        del item["engagementRateNumerator"]
    return aggregated


def cmd_ga4_product_pages(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body = {
        "dateRanges": [{"startDate": args.start_date, "endDate": args.end_date}],
        "dimensions": [{"name": "pagePath"}],
        "metrics": [
            {"name": "sessions"},
            {"name": "activeUsers"},
            {"name": "screenPageViews"},
            {"name": "engagementRate"},
            {"name": "conversions"},
            {"name": "totalRevenue"},
        ],
        "dimensionFilter": {
            "filter": {
                "fieldName": "pagePath",
                "stringFilter": {"matchType": "CONTAINS", "value": args.path_contains},
            }
        },
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
        "limit": args.limit,
    }
    result = run_ga4_report(session, property_id, body)
    payload: dict[str, Any] = {
        "command": args.command,
        "ga4_property_id": property_id,
        "request": body,
        "result": result,
    }
    if args.aggregate_by_handle:
        payload["aggregated_by_handle"] = aggregate_product_page_rows(result.get("rows", []))
    return payload


def cmd_ga4_realtime_report(session: AuthorizedSession, args: argparse.Namespace) -> dict[str, Any]:
    property_id = require_ga4_property_id(args)
    body: dict[str, Any] = {
        "dimensions": ga4_field_list(args.dimensions, "name"),
        "metrics": ga4_field_list(args.metrics, "name"),
        "limit": args.limit,
    }
    dimension_filter = parse_json_arg(args.dimension_filter, "dimension-filter")
    if dimension_filter is not None:
        body["dimensionFilter"] = dimension_filter
    metric_filter = parse_json_arg(args.metric_filter, "metric-filter")
    if metric_filter is not None:
        body["metricFilter"] = metric_filter
    response = session.post(
        f"{ANALYTICS_DATA_ROOT}/properties/{property_id}:runRealtimeReport",
        json=body,
    )
    response.raise_for_status()
    return {
        "command": args.command,
        "ga4_property_id": property_id,
        "request": body,
        "result": response_json_or_empty(response),
    }


def main() -> None:
    config = load_config()
    args = parse_args(config)
    credentials_path = resolve_path(args.credentials)
    session = build_session(credentials_path)
    payload = args.handler(session, args)
    payload.setdefault("credentials", str(credentials_path))
    payload.setdefault(
        "config_sources",
        {"skill_env": str(SKILL_DIR / ".env"), "root_env": str(PROJECT_ROOT / ".env")},
    )
    write_output(payload, args.output)


if __name__ == "__main__":
    main()
