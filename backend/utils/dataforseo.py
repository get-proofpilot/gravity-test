"""
DataForSEO client — competitor research and keyword intelligence for ProofPilot audits.

Core functions (live, pay-per-result ~$0.002 each):
  SERP:
    get_local_pack()             — top N Google Maps / Local Pack results
    get_organic_serp()           — top N organic Google SERP results
    research_competitors()       — both in parallel, combined results
  Keywords Data:
    get_keyword_search_volumes() — Google Ads monthly volume, CPC, competition
  DataForSEO Labs:
    get_domain_ranked_keywords() — keywords a domain currently ranks for + volumes
    get_bulk_keyword_difficulty() — keyword difficulty scores (0-100)
  Competitor profiles:
    get_competitor_sa_profiles() — SA organic/backlink data for competitor domains

Required env vars:
    DATAFORSEO_LOGIN      your DataForSEO account email
    DATAFORSEO_PASSWORD   your DataForSEO account password

Pricing: ~$0.002 per live SERP request, ~$0.0005 for Keywords Data / DFS Labs
Sign up at https://dataforseo.com — add $20 credit, will last months.

Location name format examples:
    "Chandler,Arizona,United States"
    "Phoenix,Arizona,United States"
    "Queen Creek,Arizona,United States"
    "Los Angeles,California,United States"

Full DataForSEO API capability map (see CLAUDE.md for agent architecture):
  - SERP API:          Maps, Organic, News, Images, Shopping, Local Services
  - Keywords Data API: Google Ads volumes, CPC, competition; Bing keywords
  - DataForSEO Labs:   Ranked keywords, competitor gaps, bulk difficulty, tech lookup
  - Business Data API: Google My Business profiles, reviews, Q&A, Maps search
  - On-Page API:       Technical crawl (120+ metrics), Core Web Vitals, page audit
  - Content Analysis:  Sentiment, brand mentions, keyword context, backlink anchors
  - Domain Analytics:  Tech stack (Whois, DNS), similar domains
  - Backlinks API:     Full backlink profile, referring domains, anchors
  - App Data API:      App Store / Play Store rankings and reviews
  - Merchant API:      Google Shopping, Amazon listings
  - Trends API:        Google Trends, keyword trends over time
  - Appendix:          Locations, languages, categories lookups
"""

import os
import asyncio
import base64
import httpx
from urllib.parse import urlparse
from typing import Optional

from utils.searchatlas import sa_call

DFS_BASE = "https://api.dataforseo.com/v3"


# ── Auth ─────────────────────────────────────────────────────────────────────

def _auth_header() -> str:
    login = os.environ.get("DATAFORSEO_LOGIN", "")
    password = os.environ.get("DATAFORSEO_PASSWORD", "")
    if not login or not password:
        raise ValueError(
            "DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD env vars are required. "
            "Sign up at dataforseo.com and set these in your Railway environment."
        )
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return f"Basic {token}"


def _domain_from_url(url: str) -> str:
    """Extract bare domain from any URL string."""
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    return urlparse(url).netloc.replace("www.", "").strip("/")


# ── Core HTTP call ────────────────────────────────────────────────────────────

async def _dfs_post(endpoint: str, payload: list[dict]) -> dict:
    """
    Make a single DataForSEO API call.
    Raises ValueError on API-level errors, httpx.HTTPError on transport errors.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{DFS_BASE}/{endpoint}",
            headers={
                "Authorization": _auth_header(),
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    # DataForSEO wraps everything in a status code — 20000 = success
    if data.get("status_code", 20000) != 20000:
        raise ValueError(
            f"DataForSEO error {data['status_code']}: {data.get('status_message', 'Unknown')}"
        )

    try:
        task = data["tasks"][0]
        if task.get("status_code", 20000) != 20000:
            raise ValueError(
                f"DataForSEO task error {task['status_code']}: {task.get('status_message', '')}"
            )
    except (KeyError, IndexError):
        raise ValueError("Unexpected DataForSEO response structure")

    return data


# ── Google Maps / Local Pack ──────────────────────────────────────────────────

async def get_local_pack(
    keyword: str,
    location_name: str,
    num_results: int = 5,
) -> list[dict]:
    """
    Get top N Google Maps / Local Pack results.

    Args:
        keyword:       Search query, e.g. "electrician chandler az"
        location_name: DataForSEO location, e.g. "Chandler,Arizona,United States"
        num_results:   How many businesses to return

    Returns:
        List of competitor dicts: rank, name, rating, reviews, website,
        domain, categories, address, phone, place_id
    """
    data = await _dfs_post("serp/google/maps/live/advanced", [{
        "keyword": keyword,
        "location_name": location_name,
        "language_name": "English",
        "depth": 20,  # fetch extra to account for ads being filtered out
    }])

    try:
        items = data["tasks"][0]["result"][0]["items"] or []
    except (KeyError, IndexError, TypeError):
        return []

    results = []
    for item in items:
        # Only grab organic map listings, skip paid ads
        if item.get("type") != "maps_element":
            continue

        url = item.get("url") or item.get("contact_url") or ""
        domain = _domain_from_url(url)
        rating_obj = item.get("rating") or {}

        results.append({
            "rank": len(results) + 1,
            "name": item.get("title", ""),
            "rating": rating_obj.get("value"),
            "reviews": rating_obj.get("votes_count"),
            "website": url,
            "domain": domain,
            "categories": item.get("category") or "",
            "address": item.get("address", ""),
            "phone": item.get("phone", ""),
            "place_id": item.get("place_id", ""),
        })

        if len(results) >= num_results:
            break

    return results


# ── Organic SERP ──────────────────────────────────────────────────────────────

async def get_organic_serp(
    keyword: str,
    location_name: str,
    num_results: int = 10,
) -> list[dict]:
    """
    Get top N organic Google SERP results.

    Returns:
        List of dicts: rank, title, url, domain, description
    """
    data = await _dfs_post("serp/google/organic/live/advanced", [{
        "keyword": keyword,
        "location_name": location_name,
        "language_name": "English",
        "depth": 10,
    }])

    try:
        items = data["tasks"][0]["result"][0]["items"] or []
    except (KeyError, IndexError, TypeError):
        return []

    results = []
    for item in items:
        if item.get("type") != "organic":
            continue

        url = item.get("url", "")
        domain = _domain_from_url(url)

        results.append({
            "rank": item.get("rank_group", len(results) + 1),
            "title": item.get("title", ""),
            "url": url,
            "domain": domain,
            "description": item.get("description", ""),
        })

        if len(results) >= num_results:
            break

    return results


# ── Keywords Data API — search volumes + CPC ─────────────────────────────────

async def get_keyword_search_volumes(
    keywords: list[str],
    location_name: str,
) -> list[dict]:
    """
    Get Google Ads monthly search volume, CPC, and competition data.

    Args:
        keywords:      List of keywords to look up (max 700 per call)
        location_name: DataForSEO location, e.g. "Chandler,Arizona,United States"

    Returns:
        List of dicts: keyword, search_volume, cpc, competition_level
    """
    if not keywords:
        return []

    data = await _dfs_post("keywords_data/google_ads/search_volume/live", [{
        "keywords": keywords[:700],
        "location_name": location_name,
        "language_name": "English",
    }])

    try:
        items = data["tasks"][0]["result"] or []
    except (KeyError, IndexError, TypeError):
        return []

    results = []
    for item in items:
        if not item:
            continue
        results.append({
            "keyword":           item.get("keyword", ""),
            "search_volume":     item.get("search_volume") or 0,
            "cpc":               item.get("cpc"),
            "competition":       item.get("competition"),
            "competition_level": item.get("competition_level", ""),
        })

    return sorted(results, key=lambda x: x.get("search_volume") or 0, reverse=True)


# ── DataForSEO Labs — domain ranked keywords ──────────────────────────────────

async def get_domain_ranked_keywords(
    domain: str,
    location_name: str,
    limit: int = 20,
) -> list[dict]:
    """
    Get keywords a domain currently ranks for via DataForSEO Labs.
    Complements Search Atlas organic keywords with independent volume data.

    Returns:
        List of dicts: keyword, rank, search_volume, traffic_estimate, url
    """
    data = await _dfs_post("dataforseo_labs/google/ranked_keywords/live", [{
        "target": domain,
        "location_name": location_name,
        "language_name": "English",
        "limit": limit,
        "order_by": ["etv,desc"],
    }])

    try:
        items = data["tasks"][0]["result"][0]["items"] or []
    except (KeyError, IndexError, TypeError):
        return []

    results = []
    for item in items:
        kd       = item.get("keyword_data") or {}
        ki       = kd.get("keyword_info") or {}
        se_item  = (item.get("ranked_serp_element") or {}).get("serp_item") or {}
        results.append({
            "keyword":          kd.get("keyword", ""),
            "rank":             se_item.get("rank_group"),
            "search_volume":    ki.get("search_volume") or 0,
            "traffic_estimate": round(item.get("etv") or 0, 1),
            "url":              se_item.get("url", ""),
        })

    return results


# ── DataForSEO Labs — bulk keyword difficulty ─────────────────────────────────

async def get_bulk_keyword_difficulty(
    keywords: list[str],
    location_name: str,
) -> list[dict]:
    """
    Get keyword difficulty scores (0-100) for a list of keywords.
    Higher score = harder to rank. Use for prioritizing keyword targets.

    Returns:
        List of dicts: keyword, keyword_difficulty (0-100)
    """
    if not keywords:
        return []

    data = await _dfs_post("dataforseo_labs/google/bulk_keyword_difficulty/live", [{
        "keywords": keywords[:1000],
        "location_name": location_name,
        "language_name": "English",
    }])

    try:
        items = data["tasks"][0]["result"][0]["items"] or []
    except (KeyError, IndexError, TypeError):
        return []

    return [
        {
            "keyword":            item.get("keyword", ""),
            "keyword_difficulty": item.get("keyword_difficulty"),
        }
        for item in items if item
    ]


# ── Combined competitor research ──────────────────────────────────────────────

async def research_competitors(
    keyword: str,
    location_name: str,
    maps_count: int = 5,
    organic_count: int = 5,
) -> dict:
    """
    Run Maps + organic SERP research in parallel for a keyword + location.

    Returns:
        {
            "maps":        [top N Google Maps competitors],
            "organic":     [top N organic Google competitors],
            "all_domains": [deduplicated competitor domains for SA lookup],
            "keyword":     the keyword that was searched,
            "location":    the location that was searched,
        }
    """
    maps_result, organic_result = await asyncio.gather(
        get_local_pack(keyword, location_name, maps_count),
        get_organic_serp(keyword, location_name, organic_count),
        return_exceptions=True,
    )

    if isinstance(maps_result, Exception):
        maps_result = []
    if isinstance(organic_result, Exception):
        organic_result = []

    # Deduplicate domains across both lists for Search Atlas lookups
    seen: set[str] = set()
    all_domains: list[str] = []
    for item in (maps_result + organic_result):
        d = item.get("domain", "").strip().lower()
        if d and d not in seen:
            seen.add(d)
            all_domains.append(d)

    return {
        "maps": maps_result,
        "organic": organic_result,
        "all_domains": all_domains[:8],  # cap at 8 to keep SA calls manageable
        "keyword": keyword,
        "location": location_name,
    }


# ── Search Atlas profiles for each competitor ─────────────────────────────────

async def get_competitor_sa_profile(domain: str) -> dict[str, str]:
    """
    Pull Search Atlas organic keyword + backlink summary for one competitor domain.
    Falls back gracefully if the domain has no SA data.
    """
    async def safe(label: str, coro) -> tuple[str, str]:
        try:
            return label, await coro
        except Exception as e:
            return label, f"Data unavailable: {e}"

    tasks = [
        safe("keywords", sa_call(
            "Site_Explorer_Organic_Tool", "get_organic_keywords",
            {"project_identifier": domain, "page_size": 5, "ordering": "-traffic"},
        )),
        safe("backlinks", sa_call(
            "Site_Explorer_Backlinks_Tool", "get_site_referring_domains",
            {"project_identifier": domain, "page_size": 5, "ordering": "-domain_rating"},
        )),
    ]

    results = await asyncio.gather(*tasks)
    return {"domain": domain, **dict(results)}


async def get_competitor_sa_profiles(domains: list[str]) -> list[dict]:
    """
    Pull SA data for a list of competitor domains in parallel.
    Returns list of profile dicts ordered by input list.
    """
    if not domains:
        return []

    profiles = await asyncio.gather(
        *[get_competitor_sa_profile(d) for d in domains],
        return_exceptions=True,
    )

    results = []
    for domain, profile in zip(domains, profiles):
        if isinstance(profile, Exception):
            results.append({"domain": domain, "keywords": "Data unavailable", "backlinks": "Data unavailable"})
        else:
            results.append(profile)

    return results


# ── Formatting helpers for Claude prompts ────────────────────────────────────

def format_maps_competitors(results: list[dict]) -> str:
    """Format Google Maps results as readable text for Claude."""
    if not results:
        return "No Google Maps / Local Pack results found for this keyword."

    lines = [f"Top {len(results)} Google Maps (Local Pack) Competitors:\n"]
    for r in results:
        if r.get("rating") and r.get("reviews"):
            rating_str = f"{r['rating']}★  ({r['reviews']:,} reviews)"
        else:
            rating_str = "No rating data"

        lines += [
            f"#{r['rank']}: {r['name']}",
            f"  Rating:   {rating_str}",
            f"  Website:  {r['domain'] or 'No website listed'}",
            f"  Category: {r['categories'] or 'N/A'}",
            f"  Address:  {r['address'] or 'N/A'}",
        ]
        if r.get("phone"):
            lines.append(f"  Phone:    {r['phone']}")
        lines.append("")

    return "\n".join(lines)


def format_organic_competitors(results: list[dict]) -> str:
    """Format organic SERP results as readable text for Claude."""
    if not results:
        return "No organic SERP results found."

    lines = [f"Top {len(results)} Organic Google Results:\n"]
    for r in results:
        snippet = (r.get("description") or "")[:140]
        lines += [
            f"#{r['rank']}: {r['title']}",
            f"  URL: {r['url']}",
        ]
        if snippet:
            lines.append(f"  Snippet: {snippet}...")
        lines.append("")

    return "\n".join(lines)


def format_competitor_profiles(profiles: list[dict]) -> str:
    """Format SA competitor profiles as a comparison block for Claude."""
    if not profiles:
        return "No competitor Search Atlas data available."

    lines = ["Search Atlas Competitor Profiles (keywords + backlink domains):\n"]
    for p in profiles:
        lines.append(f"--- {p['domain']} ---")
        kw = p.get("keywords", "")
        bl = p.get("backlinks", "")
        # Keep it tight — just the first meaningful line from each
        kw_preview = (kw.split("\n")[0] if kw else "No data")[:200]
        bl_preview = (bl.split("\n")[0] if bl else "No data")[:200]
        lines.append(f"  Keywords:  {kw_preview}")
        lines.append(f"  Backlinks: {bl_preview}")
        lines.append("")

    return "\n".join(lines)


def format_full_competitor_section(
    keyword: str,
    maps: list[dict],
    organic: list[dict],
    sa_profiles: Optional[list[dict]] = None,
) -> str:
    """
    Build the full competitor research block that gets injected into Claude's prompt.
    Combines Maps results + organic results + SA profiles into one coherent section.
    """
    sections = [
        f"## COMPETITOR RESEARCH — \"{keyword}\"\n",
        format_maps_competitors(maps),
        format_organic_competitors(organic),
    ]

    if sa_profiles:
        sections.append(format_competitor_profiles(sa_profiles))

    return "\n".join(sections)


def format_keyword_volumes(data: list[dict]) -> str:
    """Format keyword search volume data for Claude prompt injection."""
    if not data:
        return "No keyword volume data available."

    lines = ["Keyword Search Volume Data (Google Ads):\n"]
    for kw in data:
        vol   = kw.get("search_volume") or 0
        cpc   = kw.get("cpc")
        comp  = kw.get("competition_level", "")
        parts = [f"  \"{kw['keyword']}\": {vol:,}/mo"]
        if cpc:
            parts.append(f"CPC ${float(cpc):.2f}")
        if comp:
            parts.append(f"{comp} competition")
        lines.append("  ".join(parts))

    return "\n".join(lines)


def format_domain_ranked_keywords(data: list[dict]) -> str:
    """Format DataForSEO Labs ranked keyword data for Claude prompt."""
    if not data:
        return "No ranked keyword data available from DataForSEO Labs."

    lines = ["Domain Ranked Keywords — DataForSEO Labs (independent data source):\n"]
    for kw in data[:20]:
        vol     = kw.get("search_volume") or 0
        rank    = kw.get("rank", "?")
        traffic = kw.get("traffic_estimate") or 0
        lines.append(
            f"  #{rank}: \"{kw['keyword']}\" — {vol:,}/mo search vol, ~{traffic:.0f} est. monthly visits"
        )

    return "\n".join(lines)


def format_keyword_difficulty(data: list[dict]) -> str:
    """Format keyword difficulty scores for Claude prompt."""
    if not data:
        return "No keyword difficulty data available."

    lines = ["Keyword Difficulty Scores (0-100, higher = harder):\n"]
    for kw in sorted(data, key=lambda x: x.get("keyword_difficulty") or 0):
        kd = kw.get("keyword_difficulty")
        if kd is None:
            continue
        level = "Easy" if kd < 30 else "Medium" if kd < 60 else "Hard"
        lines.append(f"  \"{kw['keyword']}\": {kd}/100 ({level})")

    return "\n".join(lines)


# ── Business Data API — Google Business Profile competitor profiles ────────────

async def get_competitor_gmb_profiles(
    competitor_names: list[str],
    location_name: str,
) -> list[dict]:
    """
    Fetch GBP profiles for competitor businesses by name + location.
    Uses business_data/google/my_business_search/live

    Returns list of dicts with: name, rating, reviews_count, categories,
    address, phone, website, work_hours, attributes (like 'women_led',
    'lgbtq_friendly', etc.), photos_count
    """
    if not competitor_names:
        return []

    # Limit to first 3 to keep costs low
    names_to_fetch = competitor_names[:3]

    try:
        payload = [
            {
                "keyword": name,
                "location_name": location_name,
                "language_name": "English",
            }
            for name in names_to_fetch
        ]

        data = await _dfs_post(
            "business_data/google/my_business_search/live", payload
        )

        tasks = data.get("tasks") or []
        results = []

        for task in tasks:
            try:
                items = task["result"][0]["items"] or []
            except (KeyError, IndexError, TypeError):
                continue

            if not items:
                continue

            # Take the first match for each business name query
            item = items[0]
            rating_obj = item.get("rating") or {}
            attrs = item.get("attributes") or {}

            results.append({
                "name":          item.get("title", ""),
                "rating":        rating_obj.get("value"),
                "reviews_count": rating_obj.get("votes_count"),
                "categories":    item.get("category", ""),
                "address":       item.get("address", ""),
                "phone":         item.get("phone", ""),
                "website":       item.get("url", ""),
                "work_hours":    item.get("work_hours"),
                "attributes":    attrs,
                "photos_count":  item.get("main_image") and 1 or 0,
            })

        return results

    except Exception:
        return []


def format_competitor_gmb_profiles(data: list[dict]) -> str:
    """Format GBP competitor profile data for Claude prompt injection."""
    if not data:
        return "No GBP competitor profile data available."

    lines = ["Competitor Google Business Profile (GBP) Data:\n"]

    for profile in data:
        name = profile.get("name") or "Unknown Business"
        rating = profile.get("rating")
        reviews = profile.get("reviews_count")
        categories = profile.get("categories") or "N/A"
        address = profile.get("address") or "N/A"
        phone = profile.get("phone") or "N/A"
        website = profile.get("website") or "N/A"
        work_hours = profile.get("work_hours")
        attributes = profile.get("attributes") or {}

        if rating and reviews:
            rating_str = f"{rating}★ ({reviews:,} reviews)"
        elif rating:
            rating_str = f"{rating}★"
        else:
            rating_str = "No rating"

        lines.append(f"--- {name} ---")
        lines.append(f"  Rating:     {rating_str}")
        lines.append(f"  Category:   {categories}")
        lines.append(f"  Address:    {address}")
        lines.append(f"  Phone:      {phone}")
        lines.append(f"  Website:    {website}")

        if work_hours:
            # Flatten work_hours dict to a readable string if it's a dict
            if isinstance(work_hours, dict):
                hours_parts = []
                for day, hours in work_hours.items():
                    hours_parts.append(f"{day}: {hours}")
                lines.append(f"  Hours:      {', '.join(hours_parts[:3])}{'...' if len(hours_parts) > 3 else ''}")
            else:
                lines.append(f"  Hours:      {str(work_hours)[:120]}")

        if attributes:
            # Surface notable GBP attributes (e.g. women_led, lgbtq_friendly, 24hr)
            attr_flags = [k for k, v in attributes.items() if v is True]
            if attr_flags:
                lines.append(f"  Attributes: {', '.join(attr_flags)}")

        lines.append("")

    return "\n".join(lines)



# ── State abbreviation mapping ────────────────────────────────────────────────

STATE_ABBREVS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


def build_location_name(city_state: str) -> str:
    """
    Convert 'Chandler, AZ' → 'Chandler,Arizona,United States'
    for DataForSEO location_name parameter.
    """
    parts = [p.strip() for p in city_state.split(",")]
    if len(parts) < 2:
        return f"{city_state},United States"

    city = parts[0]
    state_raw = parts[1].strip().upper()
    state_full = STATE_ABBREVS.get(state_raw, parts[1].strip())

    return f"{city},{state_full},United States"


# ── Location research for programmatic content ───────────────────────────────

async def get_location_research(
    service: str,
    city_state: str,
) -> dict:
    """
    Run parallel research for a single location — SERP competitors, Maps
    competitors, and keyword search volumes. Used by the programmatic content
    agent to inject real market data into each page.

    Args:
        service:    e.g. "electrician", "plumbing repair"
        city_state: e.g. "Mesa, AZ"

    Returns:
        Dict with keys: organic, maps, volumes, keyword, location
        Empty dict on failure (graceful fallback).
    """
    try:
        location_name = build_location_name(city_state)
        city = city_state.split(",")[0].strip()
        keyword = f"{service} {city}"

        seeds = build_service_keyword_seeds(service, city, 5)

        organic, maps, volumes = await asyncio.gather(
            get_organic_serp(keyword, location_name, 3),
            get_local_pack(keyword, location_name, 3),
            get_keyword_search_volumes(seeds, location_name),
            return_exceptions=True,
        )

        if isinstance(organic, Exception):
            organic = []
        if isinstance(maps, Exception):
            maps = []
        if isinstance(volumes, Exception):
            volumes = []

        return {
            "organic": organic,
            "maps": maps,
            "volumes": volumes,
            "keyword": keyword,
            "location": city_state,
        }
    except Exception:
        return {}


def format_location_research(research: dict, city: str) -> str:
    """Format location research data for Claude prompt injection."""
    if not research:
        return f"No research data available for {city} — use your knowledge of the area to write genuinely local content."

    sections = [f"## LOCAL MARKET RESEARCH — {city}\n"]

    maps = research.get("maps", [])
    organic = research.get("organic", [])
    volumes = research.get("volumes", [])

    if maps:
        sections.append(format_maps_competitors(maps))

    if organic:
        sections.append(format_organic_competitors(organic))

    if volumes:
        sections.append(format_keyword_volumes(volumes))

    if not any([maps, organic, volumes]):
        sections.append(f"No DataForSEO data available for {city} — use your knowledge of the area.")

    return "\n\n".join(sections)


def build_service_keyword_seeds(service: str, city: str, count: int = 10) -> list[str]:
    """
    Build a seed keyword list for a service + city combination.
    Used to look up search volumes for prospect audits and keyword gap analysis.

    Args:
        service: e.g. "plumber", "electrician", "HVAC technician"
        city:    e.g. "Chandler", "Gilbert", "Phoenix"
        count:   max keywords to generate (default 10)

    Returns:
        List of keyword strings ready for get_keyword_search_volumes()
    """
    s = service.lower().strip()
    c = city.lower().strip()

    seeds = [
        f"{s} {c}",
        f"best {s} {c}",
        f"emergency {s} {c}",
        f"{s} near me",
        f"local {s} {c}",
        f"{s} company {c}",
        f"affordable {s} {c}",
        f"licensed {s} {c}",
        f"24 hour {s} {c}",
        f"{s} service {c}",
    ]

    return seeds[:count]
