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
            "cpc":              ki.get("cpc"),
            "url":              se_item.get("url", ""),
        })

    # Sort by search volume descending (DFS Labs doesn't support order_by on this endpoint)
    results.sort(key=lambda x: (x.get("search_volume") or 0), reverse=True)
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


# ── DataForSEO Labs — domain rank overview ────────────────────────────────────

async def get_domain_rank_overview(
    domain: str,
    location_name: str,
) -> dict:
    """
    Get summary organic stats for a domain: estimated traffic, traffic value, keyword count.
    Uses dataforseo_labs/google/domain_rank_overview/live.

    Returns:
        dict: domain, keywords, etv (est. monthly traffic), etv_cost (traffic value $)
    """
    try:
        data = await _dfs_post("dataforseo_labs/google/domain_rank_overview/live", [{
            "target": domain,
            "location_name": location_name,
            "language_name": "English",
        }])

        try:
            items = data["tasks"][0]["result"][0]["items"] or []
        except (KeyError, IndexError, TypeError):
            return {"domain": domain, "keywords": 0, "etv": 0, "etv_cost": 0}

        if not items:
            return {"domain": domain, "keywords": 0, "etv": 0, "etv_cost": 0}

        item = items[0]
        metrics = item.get("metrics") or {}
        organic = metrics.get("organic") or {}

        return {
            "domain":    domain,
            "keywords":  organic.get("count", 0) or 0,
            "etv":       round(organic.get("etv", 0) or 0, 0),
            "etv_cost":  round(organic.get("estimated_paid_traffic_cost", 0) or 0, 0),
        }
    except Exception:
        return {"domain": domain, "keywords": 0, "etv": 0, "etv_cost": 0}


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


# ══════════════════════════════════════════════════════════════════════════════
# BACKLINKS API
# ══════════════════════════════════════════════════════════════════════════════

async def get_backlink_summary(domain: str) -> dict:
    """
    Get high-level backlink stats for a domain.
    Endpoint: backlinks/summary/live

    Returns:
        dict with: total_backlinks, referring_domains, referring_ips,
        broken_backlinks, referring_domains_nofollow, rank
    """
    try:
        data = await _dfs_post("backlinks/summary/live", [{
            "target": domain,
            "internal_list_limit": 0,
            "backlinks_status_type": "all",
        }])

        try:
            items = data["tasks"][0]["result"] or []
        except (KeyError, IndexError, TypeError):
            return {"domain": domain}

        if not items:
            return {"domain": domain}

        item = items[0]
        return {
            "domain":                    domain,
            "total_backlinks":           item.get("total_backlinks", 0),
            "referring_domains":         item.get("referring_domains", 0),
            "referring_ips":             item.get("referring_ips", 0),
            "broken_backlinks":          item.get("broken_backlinks", 0),
            "referring_domains_nofollow": item.get("referring_domains_nofollow", 0),
            "rank":                      item.get("rank", 0),
            "backlinks_spam_score":      item.get("backlinks_spam_score", 0),
        }
    except Exception:
        return {"domain": domain}


async def get_referring_domains(
    domain: str,
    limit: int = 20,
) -> list[dict]:
    """
    Get top referring domains linking to a target domain.
    Endpoint: backlinks/referring_domains/live

    Returns:
        List of dicts: domain, backlinks_count, rank, is_broken, first_seen
    """
    try:
        data = await _dfs_post("backlinks/referring_domains/live", [{
            "target": domain,
            "limit": limit,
            "order_by": ["rank,desc"],
            "backlinks_status_type": "live",
        }])

        try:
            items = data["tasks"][0]["result"][0]["items"] or []
        except (KeyError, IndexError, TypeError):
            return []

        return [
            {
                "domain":          item.get("domain", ""),
                "backlinks_count": item.get("backlinks", 0),
                "rank":            item.get("rank", 0),
                "is_broken":       item.get("broken_backlinks", 0) > 0,
                "first_seen":      item.get("first_seen"),
            }
            for item in items if item
        ]
    except Exception:
        return []


async def get_backlink_anchors(
    domain: str,
    limit: int = 20,
) -> list[dict]:
    """
    Get anchor text distribution for backlinks pointing to a domain.
    Endpoint: backlinks/anchors/live

    Returns:
        List of dicts: anchor, backlinks_count, referring_domains, first_seen
    """
    try:
        data = await _dfs_post("backlinks/anchors/live", [{
            "target": domain,
            "limit": limit,
            "order_by": ["backlinks,desc"],
            "backlinks_status_type": "live",
        }])

        try:
            items = data["tasks"][0]["result"][0]["items"] or []
        except (KeyError, IndexError, TypeError):
            return []

        return [
            {
                "anchor":            item.get("anchor", ""),
                "backlinks_count":   item.get("backlinks", 0),
                "referring_domains": item.get("referring_domains", 0),
                "first_seen":        item.get("first_seen"),
            }
            for item in items if item
        ]
    except Exception:
        return []


async def get_backlink_competitors(
    domain: str,
    limit: int = 10,
) -> list[dict]:
    """
    Find domains that compete for the same backlink sources.
    Endpoint: dataforseo_labs/google/competitors_domain/live

    Returns:
        List of dicts: domain, avg_position, keywords_count, etv, intersections
    """
    try:
        data = await _dfs_post("dataforseo_labs/google/competitors_domain/live", [{
            "target": domain,
            "limit": limit,
            "language_name": "English",
            "location_name": "United States",
        }])

        try:
            items = data["tasks"][0]["result"][0]["items"] or []
        except (KeyError, IndexError, TypeError):
            return []

        return [
            {
                "domain":         item.get("domain", ""),
                "avg_position":   round(item.get("avg_position", 0) or 0, 1),
                "keywords_count": item.get("se_keywords", 0),
                "etv":            round(item.get("etv", 0) or 0, 0),
                "intersections":  item.get("intersections", 0),
            }
            for item in items if item
        ]
    except Exception:
        return []


async def get_full_backlink_profile(domain: str) -> dict:
    """
    Run all backlink research in parallel — summary, referring domains,
    anchors, and competitors.

    Returns:
        Dict with keys: summary, referring_domains, anchors, competitors
    """
    summary, ref_domains, anchors, competitors = await asyncio.gather(
        get_backlink_summary(domain),
        get_referring_domains(domain, 20),
        get_backlink_anchors(domain, 20),
        get_backlink_competitors(domain, 10),
        return_exceptions=True,
    )

    if isinstance(summary, Exception):
        summary = {"domain": domain}
    if isinstance(ref_domains, Exception):
        ref_domains = []
    if isinstance(anchors, Exception):
        anchors = []
    if isinstance(competitors, Exception):
        competitors = []

    return {
        "summary": summary,
        "referring_domains": ref_domains,
        "anchors": anchors,
        "competitors": competitors,
    }


def format_backlink_summary(data: dict) -> str:
    """Format backlink summary stats for Claude prompt."""
    if not data or not data.get("total_backlinks"):
        return "No backlink data available for this domain."

    return (
        f"Backlink Profile Summary for {data.get('domain', 'unknown')}:\n"
        f"  Total Backlinks:       {data.get('total_backlinks', 0):,}\n"
        f"  Referring Domains:     {data.get('referring_domains', 0):,}\n"
        f"  Referring IPs:         {data.get('referring_ips', 0):,}\n"
        f"  Broken Backlinks:      {data.get('broken_backlinks', 0):,}\n"
        f"  Nofollow Ref Domains:  {data.get('referring_domains_nofollow', 0):,}\n"
        f"  Domain Rank:           {data.get('rank', 0)}\n"
        f"  Spam Score:            {data.get('backlinks_spam_score', 0)}"
    )


def format_referring_domains(data: list[dict]) -> str:
    """Format top referring domains for Claude prompt."""
    if not data:
        return "No referring domain data available."

    lines = [f"Top {len(data)} Referring Domains (by rank):\n"]
    for rd in data:
        status = " [BROKEN]" if rd.get("is_broken") else ""
        lines.append(
            f"  {rd['domain']} — {rd.get('backlinks_count', 0)} backlinks, "
            f"Rank {rd.get('rank', 0)}{status}"
        )
    return "\n".join(lines)


def format_backlink_anchors(data: list[dict]) -> str:
    """Format anchor text distribution for Claude prompt."""
    if not data:
        return "No anchor text data available."

    lines = ["Anchor Text Distribution (top anchors):\n"]
    for a in data:
        lines.append(
            f"  \"{a['anchor']}\" — {a.get('backlinks_count', 0)} backlinks "
            f"from {a.get('referring_domains', 0)} domains"
        )
    return "\n".join(lines)


def format_backlink_competitors(data: list[dict]) -> str:
    """Format backlink competitors for Claude prompt."""
    if not data:
        return "No backlink competitor data available."

    lines = ["Backlink Competitors (domains competing for the same link sources):\n"]
    for c in data:
        lines.append(
            f"  {c['domain']} — {c.get('keywords_count', 0):,} keywords, "
            f"~{c.get('etv', 0):,.0f} est. traffic, "
            f"{c.get('intersections', 0)} shared sources"
        )
    return "\n".join(lines)


def format_full_backlink_profile(profile: dict) -> str:
    """Format the complete backlink profile for Claude prompt injection."""
    sections = ["## BACKLINK PROFILE ANALYSIS\n"]

    summary = profile.get("summary", {})
    if summary:
        sections.append(format_backlink_summary(summary))

    ref_domains = profile.get("referring_domains", [])
    if ref_domains:
        sections.append(format_referring_domains(ref_domains))

    anchors = profile.get("anchors", [])
    if anchors:
        sections.append(format_backlink_anchors(anchors))

    competitors = profile.get("competitors", [])
    if competitors:
        sections.append(format_backlink_competitors(competitors))

    return "\n\n".join(sections)


# ══════════════════════════════════════════════════════════════════════════════
# ON-PAGE API — instant single-page audit
# ══════════════════════════════════════════════════════════════════════════════

async def get_instant_page_audit(url: str) -> dict:
    """
    Run an instant on-page audit for a single URL.
    Endpoint: on_page/instant_pages

    Returns comprehensive page-level SEO data: meta tags, headings,
    images, links, page speed metrics, schema, and more.
    """
    if not url.startswith("http"):
        url = f"https://{url}"

    try:
        data = await _dfs_post("on_page/instant_pages", [{
            "url": url,
            "enable_javascript": True,
            "enable_browser_rendering": True,
        }])

        try:
            items = data["tasks"][0]["result"][0]["items"] or []
        except (KeyError, IndexError, TypeError):
            return {"url": url, "error": "No data returned"}

        if not items:
            return {"url": url, "error": "No data returned"}

        page = items[0]
        meta = page.get("meta", {}) or {}
        onpage = page.get("page_timing", {}) or {}
        checks = page.get("checks", {}) or {}

        return {
            "url":                 page.get("url", url),
            "status_code":         page.get("status_code"),
            "size":                page.get("size", 0),
            "encoded_size":        page.get("encoded_size", 0),
            "total_dom_size":      page.get("total_dom_size", 0),
            "title":               meta.get("title", ""),
            "title_length":        meta.get("title_length", 0),
            "description":         meta.get("description", ""),
            "description_length":  meta.get("description_length", 0),
            "h1":                  meta.get("htags", {}).get("h1", []),
            "h2":                  meta.get("htags", {}).get("h2", []),
            "h3":                  meta.get("htags", {}).get("h3", []),
            "canonical":           meta.get("canonical", ""),
            "images_count":        meta.get("images_count", 0),
            "images_without_alt":  meta.get("images_size", 0),
            "internal_links":      meta.get("internal_links_count", 0),
            "external_links":      meta.get("external_links_count", 0),
            "scripts_count":       meta.get("scripts_count", 0),
            "stylesheets_count":   meta.get("stylesheets_count", 0),
            "content_charset":     meta.get("content_charset", ""),
            "is_https":            page.get("url", "").startswith("https"),
            "schema_types":        page.get("resource_errors", []),
            "time_to_interactive": onpage.get("time_to_interactive"),
            "dom_complete":        onpage.get("dom_complete"),
            "largest_contentful_paint": onpage.get("largest_contentful_paint"),
            "cumulative_layout_shift":  onpage.get("cumulative_layout_shift"),
            "checks":              checks,
        }
    except Exception as e:
        return {"url": url, "error": str(e)}


def format_instant_page_audit(data: dict) -> str:
    """Format on-page audit data for Claude prompt injection."""
    if data.get("error"):
        return f"On-page audit failed for {data.get('url', 'unknown')}: {data['error']}"

    url = data.get("url", "unknown")
    lines = [f"## ON-PAGE TECHNICAL AUDIT — {url}\n"]

    # Status & basics
    lines.append(f"Status Code: {data.get('status_code', '?')}")
    lines.append(f"Page Size: {data.get('size', 0):,} bytes")
    lines.append(f"HTTPS: {'Yes' if data.get('is_https') else 'NO — CRITICAL ISSUE'}")

    # Meta tags
    lines.append(f"\nTitle: \"{data.get('title', 'MISSING')}\" ({data.get('title_length', 0)} chars)")
    lines.append(f"Description: \"{data.get('description', 'MISSING')}\" ({data.get('description_length', 0)} chars)")
    lines.append(f"Canonical: {data.get('canonical') or 'Not set'}")

    # Heading structure
    h1s = data.get("h1", [])
    h2s = data.get("h2", [])
    h3s = data.get("h3", [])
    lines.append("\nHeading Structure:")
    if h1s:
        for h in h1s[:3]:
            lines.append(f"  H1: \"{h}\"")
    else:
        lines.append("  H1: MISSING — critical for SEO")
    lines.append(f"  H2 count: {len(h2s)}")
    lines.append(f"  H3 count: {len(h3s)}")

    # Links & images
    lines.append(f"\nInternal Links: {data.get('internal_links', 0)}")
    lines.append(f"External Links: {data.get('external_links', 0)}")
    lines.append(f"Images: {data.get('images_count', 0)}")

    # Performance
    tti = data.get("time_to_interactive")
    lcp = data.get("largest_contentful_paint")
    cls = data.get("cumulative_layout_shift")
    if any([tti, lcp, cls]):
        lines.append("\nCore Web Vitals:")
        if tti:
            lines.append(f"  Time to Interactive: {tti}ms")
        if lcp:
            lines.append(f"  Largest Contentful Paint: {lcp}ms")
        if cls is not None:
            lines.append(f"  Cumulative Layout Shift: {cls}")

    # Checks (issues found)
    checks = data.get("checks", {})
    if checks:
        issues = [k for k, v in checks.items() if v is True]
        if issues:
            lines.append(f"\nIssues Detected ({len(issues)}):")
            for issue in issues[:15]:
                lines.append(f"  - {issue.replace('_', ' ')}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# SERP API — AI Overview / featured snippets
# ══════════════════════════════════════════════════════════════════════════════

async def get_serp_with_ai_overview(
    keyword: str,
    location_name: str,
) -> dict:
    """
    Get full SERP results including AI Overview, featured snippets,
    people_also_ask, and knowledge graph for a keyword.

    Uses serp/google/organic/live/advanced which returns all SERP features.

    Returns:
        Dict with: ai_overview, featured_snippet, organic, people_also_ask,
        knowledge_graph, keyword, location
    """
    data = await _dfs_post("serp/google/organic/live/advanced", [{
        "keyword": keyword,
        "location_name": location_name,
        "language_name": "English",
        "depth": 20,
    }])

    try:
        items = data["tasks"][0]["result"][0]["items"] or []
    except (KeyError, IndexError, TypeError):
        return {"keyword": keyword, "location": location_name, "organic": []}

    result = {
        "keyword": keyword,
        "location": location_name,
        "ai_overview": None,
        "featured_snippet": None,
        "organic": [],
        "people_also_ask": [],
        "knowledge_graph": None,
        "local_pack": [],
        "related_searches": [],
    }

    for item in items:
        item_type = item.get("type", "")

        if item_type == "ai_overview":
            result["ai_overview"] = {
                "text": item.get("text", ""),
                "references": [
                    {
                        "title": ref.get("title", ""),
                        "url": ref.get("url", ""),
                        "domain": _domain_from_url(ref.get("url", "")),
                    }
                    for ref in (item.get("references") or item.get("items") or [])[:10]
                ],
            }

        elif item_type == "featured_snippet":
            result["featured_snippet"] = {
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "url": item.get("url", ""),
                "domain": _domain_from_url(item.get("url", "")),
            }

        elif item_type == "organic":
            if len(result["organic"]) < 10:
                result["organic"].append({
                    "rank": item.get("rank_group", 0),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "domain": _domain_from_url(item.get("url", "")),
                    "description": item.get("description", ""),
                })

        elif item_type == "people_also_ask":
            for q in (item.get("items") or [])[:8]:
                result["people_also_ask"].append({
                    "question": q.get("title", ""),
                    "url": q.get("url", ""),
                })

        elif item_type == "knowledge_graph":
            result["knowledge_graph"] = {
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "type": item.get("sub_title", ""),
            }

        elif item_type == "local_pack":
            for lp in (item.get("items") or [])[:5]:
                result["local_pack"].append({
                    "title": lp.get("title", ""),
                    "rating": (lp.get("rating") or {}).get("value"),
                    "reviews": (lp.get("rating") or {}).get("votes_count"),
                    "domain": _domain_from_url(lp.get("url", "")),
                })

        elif item_type == "related_searches":
            for rs in (item.get("items") or [])[:8]:
                result["related_searches"].append(rs.get("title", ""))

    return result


async def get_ai_search_landscape(
    keywords: list[str],
    location_name: str,
) -> list[dict]:
    """
    Run SERP analysis for multiple keywords in parallel, capturing
    AI Overviews, featured snippets, and SERP features for each.

    Used to build a complete picture of how AI search treats a topic.
    """
    tasks = [
        get_serp_with_ai_overview(kw, location_name) for kw in keywords[:10]
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]


def format_ai_search_landscape(data: list[dict], domain: str = "") -> str:
    """Format AI search landscape data for Claude prompt injection."""
    if not data:
        return "No AI search landscape data available."

    lines = ["## AI SEARCH LANDSCAPE ANALYSIS\n"]

    mentioned_count = 0
    total_keywords = len(data)
    ai_overview_count = 0

    for serp in data:
        keyword = serp.get("keyword", "")
        ai_ov = serp.get("ai_overview")
        featured = serp.get("featured_snippet")
        organic = serp.get("organic", [])

        lines.append(f"### \"{keyword}\"")

        # AI Overview
        if ai_ov:
            ai_overview_count += 1
            text_preview = (ai_ov.get("text") or "")[:200]
            refs = ai_ov.get("references", [])
            ref_domains = [r.get("domain", "") for r in refs]
            lines.append("  AI Overview: YES")
            if text_preview:
                lines.append(f"  Preview: {text_preview}...")
            if ref_domains:
                lines.append(f"  Referenced domains: {', '.join(ref_domains)}")
                if domain and domain.lower() in [d.lower() for d in ref_domains]:
                    mentioned_count += 1
                    lines.append(f"  ✓ {domain} IS cited in this AI Overview")
                elif domain:
                    lines.append(f"  ✗ {domain} NOT cited in this AI Overview")
        else:
            lines.append("  AI Overview: None")

        # Featured snippet
        if featured:
            lines.append(f"  Featured Snippet: {featured.get('domain', 'unknown')} — \"{featured.get('title', '')}\"")

        # Top 3 organic
        top3 = organic[:3]
        if top3:
            lines.append(f"  Top 3: {', '.join(r.get('domain', '') for r in top3)}")
            if domain:
                client_rank = next(
                    (r["rank"] for r in organic if domain.lower() in (r.get("domain", "").lower())),
                    None,
                )
                if client_rank:
                    lines.append(f"  {domain} ranks #{client_rank}")
                else:
                    lines.append(f"  {domain} not in top 10")

        # PAA
        paa = serp.get("people_also_ask", [])
        if paa:
            lines.append(f"  People Also Ask: {', '.join(q['question'] for q in paa[:4])}")

        lines.append("")

    # Summary stats
    lines.insert(1, f"Keywords analyzed: {total_keywords}")
    lines.insert(2, f"AI Overviews present: {ai_overview_count}/{total_keywords}")
    if domain:
        lines.insert(3, f"Domain {domain} cited in AI Overviews: {mentioned_count}/{ai_overview_count}")
    lines.insert(4, "")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE TRENDS (via DataForSEO Keywords Data API)
# ══════════════════════════════════════════════════════════════════════════════

async def get_keyword_trends(
    keywords: list[str],
    location_name: str = "United States",
) -> list[dict]:
    """
    Get Google Trends data for keywords — shows search interest over time.
    Endpoint: keywords_data/google_trends/explore/live

    Returns:
        List of dicts: keyword, trend_data (list of date/value pairs)
    """
    if not keywords:
        return []

    try:
        data = await _dfs_post("keywords_data/google_trends/explore/live", [{
            "keywords": keywords[:5],  # Trends API max 5 per request
            "location_name": location_name,
            "language_name": "English",
            "type": "web",
            "time_range": "past_12_months",
        }])

        try:
            items = data["tasks"][0]["result"] or []
        except (KeyError, IndexError, TypeError):
            return []

        results = []
        for item in items:
            if not item:
                continue
            keyword_data = item.get("data") or []
            for kd in keyword_data:
                keyword = kd.get("keyword", "")
                values = kd.get("values") or []
                trend_points = [
                    {"date": v.get("date_from", ""), "value": v.get("value", 0)}
                    for v in values
                ]
                if keyword and trend_points:
                    # Calculate trend direction
                    recent = [p["value"] for p in trend_points[-3:]]
                    older = [p["value"] for p in trend_points[:3]]
                    avg_recent = sum(recent) / len(recent) if recent else 0
                    avg_older = sum(older) / len(older) if older else 0
                    if avg_older > 0:
                        change_pct = ((avg_recent - avg_older) / avg_older) * 100
                    else:
                        change_pct = 0

                    results.append({
                        "keyword": keyword,
                        "trend_points": trend_points,
                        "trend_direction": "rising" if change_pct > 15 else "declining" if change_pct < -15 else "stable",
                        "change_pct": round(change_pct, 1),
                        "peak_value": max(p["value"] for p in trend_points) if trend_points else 0,
                    })

        return results
    except Exception:
        return []


def format_keyword_trends(data: list[dict]) -> str:
    """Format Google Trends data for Claude prompt."""
    if not data:
        return "No Google Trends data available."

    lines = ["Keyword Trend Analysis (Google Trends, 12 months):\n"]
    for kw in data:
        direction = kw.get("trend_direction", "stable")
        arrow = "↑" if direction == "rising" else "↓" if direction == "declining" else "→"
        change = kw.get("change_pct", 0)
        peak = kw.get("peak_value", 0)
        lines.append(
            f"  \"{kw['keyword']}\": {arrow} {direction} ({change:+.1f}%), "
            f"peak interest: {peak}/100"
        )
    return "\n".join(lines)
