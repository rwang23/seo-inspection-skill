#!/usr/bin/env python3
"""Reusable Google Search Console API helper."""

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
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_config() -> dict[str, str]:
    root_env = load_env_file(PROJECT_ROOT / ".env")
    skill_env = load_env_file(SKILL_DIR / ".env")
    merged = {**root_env, **skill_env}
    for key in ("GSC_SERVICE_ACCOUNT_PATH", "GSC_SITE_URL", "GSC_LANGUAGE_CODE"):
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
        default=config.get("GSC_SERVICE_ACCOUNT_PATH"),
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
    parser.add_argument("--output", help="Write JSON results to this file. Defaults to stdout.")


def add_output_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", help="Write JSON results to this file. Defaults to stdout.")


def parse_args(config: dict[str, str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Google Search Console API helper.")
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

    args = parser.parse_args()
    if not args.credentials:
        raise SystemExit("Missing credentials path. Set GSC_SERVICE_ACCOUNT_PATH or use --credentials.")
    return args


def build_session(credentials_path: Path) -> AuthorizedSession:
    creds = service_account.Credentials.from_service_account_file(
        str(credentials_path),
        scopes=["https://www.googleapis.com/auth/webmasters"],
    )
    return AuthorizedSession(creds)


def require_site_url(args: argparse.Namespace) -> str:
    if not args.site_url:
        raise SystemExit("Missing Search Console property. Set GSC_SITE_URL or use --site-url.")
    return args.site_url


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
