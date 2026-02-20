"""
Prospect SEO Market Analysis Workflow — ProofPilot v4

SEO manager logic:
  - Searches across the full metro area (5 nearest cities), not just the prospect's city
  - Finds the actual dominant local player, not national chains like Cobblestone
  - Filters out directories, aggregators, and chains automatically
  - Takes the top 1-2 local competitors per city, deduplicates, sorts by traffic
  - Organic + GBP/Maps traffic unified (DFS Labs returns all ranked keywords for a domain,
    which includes local pack positions when the GBP is linked to a website)

inputs keys:
    domain          e.g. "motorcityautodetailing.com"
    service         e.g. "auto detailing"
    location        e.g. "Chandler, AZ"
    monthly_revenue optional
    avg_job_value   optional
    notes           optional sales context
"""

import os
import asyncio
import re
import math
import anthropic
from typing import AsyncGenerator

from utils.searchatlas import sa_call
from utils.dataforseo import (
    research_competitors,
    get_competitor_sa_profiles,
    get_keyword_search_volumes,
    get_bulk_keyword_difficulty,
    get_domain_ranked_keywords,
    get_domain_rank_overview,
)


# ── State map ────────────────────────────────────────────────────────────────

_STATE_MAP = {
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
    "WI": "Wisconsin", "WY": "Wyoming",
}

_STATE_ABBR = {v: k for k, v in _STATE_MAP.items()}


def _build_location_name(location_raw: str) -> str:
    parts = re.split(r"[,\s]+", location_raw.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        city = " ".join(parts[:-1]).title()
        state_input = parts[-1].upper()
        state_full = _STATE_MAP.get(state_input, state_input.title())
        return f"{city},{state_full},United States"
    return location_raw.strip()


# ── Metro area lookup ─────────────────────────────────────────────────────────
# Returns nearby cities to search for competitors — so we find the actual
# dominant local player across the whole metro, not just the prospect's city.

_METRO_LOOKUP: dict[tuple[str, str], list[str]] = {
    # Arizona — Phoenix metro
    ("phoenix", "az"):    ["Phoenix", "Scottsdale", "Tempe", "Mesa", "Chandler", "Glendale"],
    ("scottsdale", "az"): ["Scottsdale", "Phoenix", "Tempe", "Mesa", "Paradise Valley", "Fountain Hills"],
    ("chandler", "az"):   ["Chandler", "Mesa", "Tempe", "Gilbert", "Scottsdale", "Phoenix"],
    ("mesa", "az"):       ["Mesa", "Chandler", "Tempe", "Gilbert", "Scottsdale", "Phoenix"],
    ("tempe", "az"):      ["Tempe", "Mesa", "Chandler", "Phoenix", "Scottsdale", "Gilbert"],
    ("gilbert", "az"):    ["Gilbert", "Chandler", "Mesa", "Tempe", "Queen Creek", "Scottsdale"],
    ("glendale", "az"):   ["Glendale", "Phoenix", "Peoria", "Surprise", "Avondale", "Goodyear"],
    ("peoria", "az"):     ["Peoria", "Glendale", "Phoenix", "Surprise", "Goodyear", "Avondale"],
    # California — LA metro
    ("los angeles", "ca"):  ["Los Angeles", "Glendale", "Burbank", "Pasadena", "Long Beach", "Torrance"],
    ("glendale", "ca"):     ["Glendale", "Burbank", "Pasadena", "Los Angeles", "North Hollywood"],
    ("anaheim", "ca"):      ["Anaheim", "Orange", "Santa Ana", "Fullerton", "Garden Grove", "Irvine"],
    ("irvine", "ca"):       ["Irvine", "Anaheim", "Orange", "Santa Ana", "Costa Mesa", "Newport Beach"],
    ("san diego", "ca"):    ["San Diego", "Chula Vista", "El Cajon", "Escondido", "Santee", "La Mesa"],
    ("san jose", "ca"):     ["San Jose", "Santa Clara", "Sunnyvale", "Fremont", "Milpitas", "Campbell"],
    ("fremont", "ca"):      ["Fremont", "Newark", "Union City", "Hayward", "San Jose", "Milpitas"],
    ("sacramento", "ca"):   ["Sacramento", "Elk Grove", "Roseville", "Folsom", "Rancho Cordova", "Citrus Heights"],
    ("fresno", "ca"):       ["Fresno", "Clovis", "Madera", "Tulare", "Visalia"],
    # Texas
    ("dallas", "tx"):       ["Dallas", "Plano", "Frisco", "McKinney", "Arlington", "Irving"],
    ("plano", "tx"):        ["Plano", "Dallas", "Frisco", "McKinney", "Allen", "Richardson"],
    ("frisco", "tx"):       ["Frisco", "Plano", "McKinney", "Allen", "Little Elm", "Dallas"],
    ("fort worth", "tx"):   ["Fort Worth", "Arlington", "Mansfield", "Burleson", "Keller", "Southlake"],
    ("arlington", "tx"):    ["Arlington", "Fort Worth", "Grand Prairie", "Mansfield", "Irving", "Dallas"],
    ("houston", "tx"):      ["Houston", "Sugar Land", "Katy", "Pearland", "League City", "Pasadena"],
    ("sugar land", "tx"):   ["Sugar Land", "Missouri City", "Pearland", "Stafford", "Houston"],
    ("austin", "tx"):       ["Austin", "Round Rock", "Cedar Park", "Georgetown", "Pflugerville", "Kyle"],
    ("round rock", "tx"):   ["Round Rock", "Austin", "Cedar Park", "Georgetown", "Pflugerville"],
    ("san antonio", "tx"):  ["San Antonio", "New Braunfels", "Schertz", "Boerne", "Converse", "Seguin"],
    # Florida
    ("miami", "fl"):        ["Miami", "Coral Gables", "Hialeah", "Doral", "Kendall", "Miramar"],
    ("orlando", "fl"):      ["Orlando", "Kissimmee", "Sanford", "Oviedo", "Winter Garden", "Clermont"],
    ("kissimmee", "fl"):    ["Kissimmee", "Orlando", "Celebration", "Poinciana", "Saint Cloud"],
    ("tampa", "fl"):        ["Tampa", "St. Petersburg", "Clearwater", "Brandon", "Lakeland", "Wesley Chapel"],
    ("jacksonville", "fl"): ["Jacksonville", "Orange Park", "St. Augustine", "Fleming Island", "Ponte Vedra"],
    ("fort lauderdale", "fl"): ["Fort Lauderdale", "Hollywood", "Pompano Beach", "Coral Springs", "Miramar"],
    ("st. petersburg", "fl"):  ["St. Petersburg", "Tampa", "Clearwater", "Pinellas Park", "Largo"],
    # Georgia
    ("atlanta", "ga"):      ["Atlanta", "Marietta", "Alpharetta", "Roswell", "Decatur", "Sandy Springs"],
    ("marietta", "ga"):     ["Marietta", "Kennesaw", "Smyrna", "Atlanta", "Roswell", "Acworth"],
    # North Carolina
    ("charlotte", "nc"):    ["Charlotte", "Concord", "Gastonia", "Matthews", "Huntersville", "Mooresville"],
    ("raleigh", "nc"):      ["Raleigh", "Durham", "Cary", "Chapel Hill", "Morrisville", "Apex"],
    # Colorado
    ("denver", "co"):       ["Denver", "Aurora", "Lakewood", "Englewood", "Westminster", "Arvada"],
    ("aurora", "co"):       ["Aurora", "Denver", "Parker", "Centennial", "Commerce City", "Thornton"],
    # Nevada
    ("las vegas", "nv"):    ["Las Vegas", "Henderson", "North Las Vegas", "Summerlin", "Boulder City"],
    ("henderson", "nv"):    ["Henderson", "Las Vegas", "Boulder City", "North Las Vegas"],
    # Washington
    ("seattle", "wa"):      ["Seattle", "Bellevue", "Redmond", "Kirkland", "Renton", "Tacoma"],
    ("bellevue", "wa"):     ["Bellevue", "Redmond", "Kirkland", "Seattle", "Mercer Island", "Issaquah"],
    # Oregon
    ("portland", "or"):     ["Portland", "Beaverton", "Hillsboro", "Lake Oswego", "Gresham", "Tualatin"],
    # Illinois
    ("chicago", "il"):      ["Chicago", "Naperville", "Aurora", "Joliet", "Elgin", "Schaumburg"],
    ("naperville", "il"):   ["Naperville", "Aurora", "Bolingbrook", "Plainfield", "Downers Grove", "Wheaton"],
    # Ohio
    ("columbus", "oh"):     ["Columbus", "Dublin", "Westerville", "Grove City", "Hilliard", "Gahanna"],
    ("cleveland", "oh"):    ["Cleveland", "Akron", "Lakewood", "Parma", "Euclid", "Strongsville"],
    # Michigan
    ("detroit", "mi"):      ["Detroit", "Dearborn", "Sterling Heights", "Warren", "Troy", "Livonia"],
    ("grand rapids", "mi"): ["Grand Rapids", "Wyoming", "Kentwood", "Holland", "Norton Shores", "Muskegon"],
    # Pennsylvania
    ("philadelphia", "pa"): ["Philadelphia", "Camden", "Cherry Hill", "Wilmington", "Conshohocken"],
    # New York
    ("new york", "ny"):     ["New York", "Brooklyn", "Queens", "Bronx", "Staten Island", "Newark"],
    # New Jersey
    ("newark", "nj"):       ["Newark", "Jersey City", "Elizabeth", "Paterson", "Edison", "Woodbridge"],
    # Tennessee
    ("nashville", "tn"):    ["Nashville", "Murfreesboro", "Franklin", "Brentwood", "Hendersonville"],
    ("memphis", "tn"):      ["Memphis", "Germantown", "Collierville", "Bartlett", "Cordova"],
    ("knoxville", "tn"):    ["Knoxville", "Maryville", "Oak Ridge", "Sevierville", "Alcoa"],
    # Minnesota
    ("minneapolis", "mn"):  ["Minneapolis", "St. Paul", "Bloomington", "Plymouth", "Eagan", "Maple Grove"],
    # Missouri
    ("st. louis", "mo"):    ["St. Louis", "Chesterfield", "Ballwin", "Kirkwood", "Clayton", "Florissant"],
    # Wisconsin
    ("milwaukee", "wi"):    ["Milwaukee", "Wauwatosa", "West Allis", "Brookfield", "Greenfield", "Oak Creek"],
    # Maryland / Virginia
    ("baltimore", "md"):    ["Baltimore", "Towson", "Columbia", "Catonsville", "Bowie", "Gaithersburg"],
    ("virginia beach", "va"): ["Virginia Beach", "Norfolk", "Chesapeake", "Hampton", "Newport News"],
    # Massachusetts
    ("boston", "ma"):       ["Boston", "Cambridge", "Quincy", "Newton", "Somerville", "Brookline"],
    # Connecticut
    ("hartford", "ct"):     ["Hartford", "West Hartford", "Manchester", "New Britain", "Bristol"],
    # South Carolina
    ("charleston", "sc"):   ["Charleston", "North Charleston", "Mount Pleasant", "Summerville", "Goose Creek"],
    # Alabama
    ("birmingham", "al"):   ["Birmingham", "Hoover", "Vestavia Hills", "Tuscaloosa", "Homewood"],
    # Louisiana
    ("new orleans", "la"):  ["New Orleans", "Metairie", "Kenner", "Gretna", "Harvey", "Baton Rouge"],
    # Oklahoma
    ("oklahoma city", "ok"): ["Oklahoma City", "Edmond", "Norman", "Moore", "Midwest City", "Yukon"],
    # Kansas
    ("wichita", "ks"):      ["Wichita", "Derby", "Andover", "Haysville", "Maize", "Newton"],
    # Utah
    ("salt lake city", "ut"): ["Salt Lake City", "Sandy", "West Jordan", "Orem", "Provo", "Ogden"],
    # New Mexico
    ("albuquerque", "nm"):  ["Albuquerque", "Rio Rancho", "Santa Fe", "Roswell", "Farmington"],
    # Idaho
    ("boise", "id"):        ["Boise", "Nampa", "Meridian", "Caldwell", "Garden City", "Eagle"],
}


def _get_metro_cities(city: str, state_abbr: str, n: int = 5) -> list[str]:
    """Return nearby metro cities to search for competitors."""
    key = (city.lower().strip(), state_abbr.lower().strip())
    cities = _METRO_LOOKUP.get(key)
    if cities:
        # Lead with the input city if not already first
        city_title = city.title()
        if cities[0].lower() != city.lower():
            cities = [city_title] + [c for c in cities if c.lower() != city.lower()]
        return cities[:n]
    # Fallback: just use the input city
    return [city.title()]


# ── Excluded competitor domains ───────────────────────────────────────────────
# Directories, aggregators, review sites, and national chains.
# Local competitors are small/medium local businesses with their own sites.

_EXCLUDED_DOMAINS = {
    # Directories & aggregators
    "yelp.com", "yellowpages.com", "angi.com", "homeadvisor.com",
    "thumbtack.com", "google.com", "bbb.org", "reddit.com",
    "nextdoor.com", "facebook.com", "instagram.com", "houzz.com",
    "bark.com", "porch.com", "fixr.com", "angieslist.com",
    "manta.com", "expertise.com", "mapquest.com", "whitepages.com",
    "citysearch.com", "superpages.com", "dexknows.com", "local.com",
    "merchantcircle.com", "brownbook.net", "hotfrog.com",
    # Auto / car wash chains
    "cobblestone.com", "mister-car-wash.com", "waterway.com",
    "expresscarwash.com", "speedyshine.com", "autobell.com",
    "goo-goo.com", "turtlewax.com",
    # Home service platforms
    "servicemaster.com", "neighborly.com", "handyman.com",
    "serviceseeking.com", "hipages.com.au",
    # National franchise directories
    "ziprecruiter.com", "indeed.com", "glassdoor.com",
}


def _is_excluded_domain(domain: str) -> bool:
    """Return True if the domain should be excluded from competitor analysis."""
    if not domain:
        return True
    d = domain.lower().strip().replace("www.", "")
    # Exact match
    if d in _EXCLUDED_DOMAINS:
        return True
    # Pattern match — aggregators that use subdomains or paths
    skip_patterns = [
        "yelp.com", "google.com", "facebook.com", "instagram.com",
        "angi.com", "thumbtack.com", "homeadvisor.com",
    ]
    return any(p in d for p in skip_patterns)


# ── SA data gather ────────────────────────────────────────────────────────────

async def _gather_sa_data(domain: str) -> dict[str, str]:
    async def safe(tool, op, params, label):
        try:
            return label, await sa_call(tool, op, params)
        except Exception as e:
            return label, f"Data unavailable: {e}"

    tasks = [
        safe("Site_Explorer_Organic_Tool", "get_organic_keywords",
             {"project_identifier": domain, "page_size": 20, "ordering": "-traffic"}, "organic_keywords"),
        safe("Site_Explorer_Organic_Tool", "get_organic_competitors",
             {"project_identifier": domain, "page_size": 6}, "sa_competitors"),
        safe("Site_Explorer_Backlinks_Tool", "get_site_referring_domains",
             {"project_identifier": domain, "page_size": 10, "ordering": "-domain_rating"}, "referring_domains"),
        safe("Site_Explorer_Analysis_Tool", "get_position_distribution",
             {"identifier": domain}, "position_distribution"),
        safe("Site_Explorer_Holistic_Audit_Tool", "get_holistic_seo_pillar_scores",
             {"domain": domain}, "pillar_scores"),
    ]
    results = await asyncio.gather(*tasks)
    return dict(results)


# ── Metro competitor discovery ────────────────────────────────────────────────

async def _discover_metro_competitors(
    service: str,
    metro_cities: list[str],
    state_abbr: str,
    state_full: str,
) -> dict[str, list[str]]:
    """
    Search for competitors across each metro city.
    Returns {domain: [cities_it_appeared_in]} sorted by most appearances.

    Logic:
      - For each city, search "{service} {city}" (organic + maps via research_competitors)
      - Exclude directories/aggregators/chains
      - Take the top 2 local domains from each city result
      - Dedup across cities; domains appearing in more cities = more dominant
    """
    has_creds = bool(os.environ.get("DATAFORSEO_LOGIN"))
    if not has_creds:
        return {}

    async def _search_city(city: str) -> list[str]:
        """Return top non-excluded domains for this city."""
        loc = _build_location_name(f"{city}, {state_abbr}")
        keyword = f"{service} {city}"
        try:
            result = await research_competitors(
                keyword=keyword,
                location_name=loc,
                maps_count=5,
                organic_count=8,
            )
            # Combine all domains, filter, take top results
            all_domains = result.get("all_domains", [])
            local_domains = [d for d in all_domains if not _is_excluded_domain(d)]
            return local_domains[:4]  # top 4 per city
        except Exception:
            return []

    # Run all city searches in parallel
    city_results = await asyncio.gather(*[_search_city(c) for c in metro_cities])

    # Aggregate: count which cities each domain appeared in
    domain_cities: dict[str, list[str]] = {}
    for city, domains in zip(metro_cities, city_results):
        for domain in domains:
            if domain not in domain_cities:
                domain_cities[domain] = []
            domain_cities[domain].append(city)

    # Sort: most cities first (dominant player), then deduplicate
    sorted_domains = sorted(
        domain_cities.keys(),
        key=lambda d: len(domain_cities[d]),
        reverse=True,
    )

    # Cap at 7 competitors
    top_domains = sorted_domains[:7]
    return {d: domain_cities[d] for d in top_domains}


# ── Competitor traffic profiling ──────────────────────────────────────────────

async def _profile_competitors(
    domain_city_map: dict[str, list[str]],
    location_name: str,
) -> list[dict]:
    """
    For each competitor domain, fetch:
      - Domain rank overview: total keywords, estimated monthly traffic, traffic value
      - Top 15 ranked keywords (includes both organic + local pack positions from DFS Labs)

    Returns list sorted by traffic (highest = market leader).
    """
    if not domain_city_map:
        return []

    async def _fetch_one(domain: str, cities: list[str]) -> dict:
        try:
            overview, top_kws = await asyncio.gather(
                get_domain_rank_overview(domain, location_name),
                get_domain_ranked_keywords(domain, location_name, limit=15),
                return_exceptions=True,
            )
            if isinstance(overview, Exception):
                overview = {"domain": domain, "keywords": 0, "etv": 0, "etv_cost": 0}
            if isinstance(top_kws, Exception):
                top_kws = []
            return {
                "domain":   domain,
                "cities":   cities,          # which cities this competitor appeared in
                "keywords": int(overview.get("keywords", 0)),
                "traffic":  int(overview.get("etv", 0)),
                "etv_cost": int(overview.get("etv_cost", 0)),
                "top_kws":  top_kws or [],
            }
        except Exception:
            return {
                "domain":   domain,
                "cities":   cities,
                "keywords": 0,
                "traffic":  0,
                "etv_cost": 0,
                "top_kws":  [],
            }

    profiles = await asyncio.gather(
        *[_fetch_one(d, c) for d, c in domain_city_map.items()],
        return_exceptions=True,
    )

    out = []
    for p in profiles:
        if isinstance(p, Exception):
            continue
        out.append(p)

    # Sort by traffic descending — market leader first
    out.sort(key=lambda x: x.get("traffic", 0), reverse=True)
    return out


# ── Multi-city keyword seeds ──────────────────────────────────────────────────

def _build_metro_seeds(service: str, metro_cities: list[str]) -> list[str]:
    """
    Build keyword seeds across all metro cities + intent variants.
    Gives a true picture of the market (not just one city).
    """
    s = service.lower().strip()
    seeds = []

    # Per-city core seeds
    for city in metro_cities[:4]:
        c = city.lower()
        seeds += [
            f"{s} {c}",
            f"mobile {s} {c}",
            f"best {s} {c}",
            f"car detailing {c}",  # common near-synonym
        ]

    # Broad / near-me intent (not city-specific but high value)
    seeds += [
        f"{s} near me",
        f"best {s} near me",
        f"mobile {s} near me",
        f"{s} service near me",
    ]

    # Premium / specialty variants (city-agnostic)
    city1 = metro_cities[0].lower() if metro_cities else ""
    seeds += [
        f"ceramic coating {city1}",
        f"paint correction {city1}",
        f"interior detailing {city1}",
        f"exterior detailing {city1}",
        f"full detail {city1}",
        f"auto detailing packages {city1}",
        f"mobile auto detailing {city1}",
        f"{s} prices {city1}",
    ]

    # Dedup, remove empties
    seen = set()
    out = []
    for kw in seeds:
        kw = kw.strip()
        if kw and kw not in seen:
            seen.add(kw)
            out.append(kw)
    return out[:50]


# ── Prospect traffic ──────────────────────────────────────────────────────────

async def _get_prospect_rank(domain: str, location_name: str) -> dict:
    try:
        return await get_domain_rank_overview(domain, location_name)
    except Exception:
        return {"domain": domain, "keywords": 0, "etv": 0, "etv_cost": 0}


# ── Formatting helpers ────────────────────────────────────────────────────────

def _fmt_num(n) -> str:
    if not n:
        return "—"
    return f"{int(n):,}"


def _fmt_dollar(n) -> str:
    if not n:
        return "—"
    return f"${int(n):,}"


def _fmt_cpc(cpc) -> str:
    if cpc is None:
        return "—"
    v = float(cpc)
    if v == 0:
        return "$0"
    return f"${v:.2f}"


# ── Table builders ────────────────────────────────────────────────────────────

def _build_competitor_overview_table(
    profiles: list[dict],
    client_name: str,
    prospect_rank: dict,
) -> str:
    """
    Build the big competitor overview table.
    Market leader row is first (highest traffic).
    Prospect row at the bottom for contrast.
    """
    lines = [
        "| Competitor | Cities Found | Monthly Traffic | Traffic Value | Keywords | Market Position |",
        "|-----------|-------------|-----------------|---------------|---------|----------------|",
    ]

    for i, p in enumerate(profiles[:6]):
        d = p["domain"]
        cities_str = ", ".join(p.get("cities", [])[:3])
        traffic = _fmt_num(p.get("traffic"))
        value = _fmt_dollar(p.get("etv_cost"))
        kws = _fmt_num(p.get("keywords"))
        if i == 0 and (p.get("traffic") or 0) > 0:
            position = "**MARKET LEADER**"
        elif i == 1:
            position = "Strong contender"
        else:
            position = "Local competitor"
        lines.append(f"| {d} | {cities_str} | {traffic}/mo | {value}/mo | {kws} | {position} |")

    # Prospect row
    p_traffic = _fmt_num(prospect_rank.get("traffic"))
    p_value = _fmt_dollar(prospect_rank.get("etv_cost"))
    p_kws = _fmt_num(prospect_rank.get("keywords"))
    lines.append(
        f"| **{client_name}** | Your market | **{p_traffic}/mo** | **{p_value}/mo** | **{p_kws}** | **Your Opportunity** |"
    )

    return "\n".join(lines)


def _build_market_leader_section(leader: dict) -> str:
    """
    Full breakdown of the #1 competitor — mirrors how Steadfast featured EZ Flow.
    Shows their domain, traffic, traffic value, and top ranking keywords.
    """
    d = leader["domain"]
    traffic = leader.get("traffic", 0)
    value = leader.get("etv_cost", 0)
    kws = leader.get("keywords", 0)
    top_kws = leader.get("top_kws", [])
    cities = leader.get("cities", [])

    lines = []
    lines.append(f"**{d}** — currently gets **{_fmt_num(traffic)} organic visits/month** worth **{_fmt_dollar(value)}/month** in traffic value")
    if cities:
        lines.append(f"Dominating searches across: {', '.join(cities)}")
    lines.append(f"Ranking for approximately **{_fmt_num(kws)} keywords** in your market.")
    lines.append("")

    if top_kws:
        lines += [
            "| Keyword | Position | Est. Traffic | Volume |",
            "|---------|----------|-------------|--------|",
        ]
        for kw in top_kws[:10]:
            keyword = kw.get("keyword", "")
            rank = kw.get("rank") or "—"
            est_t = _fmt_num(kw.get("traffic_estimate"))
            vol = _fmt_num(kw.get("search_volume"))
            lines.append(f"| {keyword} | #{rank} | {est_t} | {vol} |")
    else:
        lines.append(f"*Detailed keyword breakdown unavailable for {d} — limited DFS Labs data for this domain.*")

    return "\n".join(lines)


def _build_other_competitors_section(profiles: list[dict]) -> str:
    """Build keyword tables for competitors 2-5 (after the market leader)."""
    if len(profiles) < 2:
        return ""

    sections = []
    for p in profiles[1:5]:
        d = p["domain"]
        traffic = p.get("traffic", 0)
        value = p.get("etv_cost", 0)
        top_kws = p.get("top_kws", [])
        cities = p.get("cities", [])

        if not traffic and not top_kws:
            continue

        lines = [
            f"### {d.upper()}",
            f"**{_fmt_num(traffic)} visits/month** worth **{_fmt_dollar(value)}/mo** — found ranking in: {', '.join(cities)}",
            "",
        ]

        if top_kws:
            lines += [
                "| Keyword | Position | Est. Traffic | Volume |",
                "|---------|----------|-------------|--------|",
            ]
            for kw in top_kws[:6]:
                keyword = kw.get("keyword", "")
                rank = kw.get("rank") or "—"
                est_t = _fmt_num(kw.get("traffic_estimate"))
                vol = _fmt_num(kw.get("search_volume"))
                lines.append(f"| {keyword} | #{rank} | {est_t} | {vol} |")
        else:
            lines.append(f"*Limited DFS Labs data available for {d}.*")

        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _build_keyword_pillar_table(
    volumes: list[dict],
    service: str,
) -> tuple[str, list[dict]]:
    """Group keyword volumes by service pillar. Returns (table, high_value_kws)."""
    if not volumes:
        return "", []

    pillar_rules = [
        ("Emergency / Urgent",   ["emergency", "urgent", "24 hour", "same day", "24/7"]),
        ("Premium / Specialty",  ["ceramic", "paint correction", "ppf", "protection film",
                                   "restoration", "premium", "packages", "full detail"]),
        ("Interior",             ["interior", "inside", "upholstery", "carpet", "steam"]),
        ("Exterior / Wash",      ["exterior", "outside", "wash", "wax", "polish"]),
        ("Mobile",               ["mobile", "come to", "at home", "your home", "on-site"]),
    ]

    buckets: dict[str, list[dict]] = {}
    for kw_data in volumes:
        kw = kw_data.get("keyword", "").lower()
        assigned = False
        for pillar_name, keywords in pillar_rules:
            if any(k in kw for k in keywords):
                if pillar_name not in buckets:
                    buckets[pillar_name] = []
                buckets[pillar_name].append(kw_data)
                assigned = True
                break
        if not assigned:
            core_name = f"Core {service.title()}"
            if core_name not in buckets:
                buckets[core_name] = []
            buckets[core_name].append(kw_data)

    lines = [
        "| Service Pillar | Monthly Searches | Avg CPC | Est. Annual Ad Value | Competition |",
        "|----------------|-----------------|---------|---------------------|-------------|",
    ]

    for pillar_name, kw_list in sorted(
        buckets.items(),
        key=lambda x: -sum(k.get("search_volume") or 0 for k in x[1])
    ):
        total_vol = sum(k.get("search_volume") or 0 for k in kw_list)
        if total_vol == 0:
            continue
        cpcs = [float(k["cpc"]) for k in kw_list if k.get("cpc") and float(k.get("cpc", 0)) > 0]
        avg_cpc = sum(cpcs) / len(cpcs) if cpcs else 0
        annual_val = total_vol * 0.10 * avg_cpc * 12
        comp_levels = [k.get("competition_level", "") for k in kw_list if k.get("competition_level")]
        comp_str = max(set(comp_levels), key=comp_levels.count) if comp_levels else "—"
        lines.append(
            f"| {pillar_name} | {total_vol:,} | {_fmt_cpc(avg_cpc) if avg_cpc else '—'} "
            f"| {_fmt_dollar(annual_val) if annual_val else '—'} | {comp_str.title() if comp_str != '—' else '—'} |"
        )

    high_value = [
        kw for kw in volumes
        if kw.get("cpc") and float(kw.get("cpc", 0)) >= 20 and (kw.get("search_volume") or 0) > 0
    ]
    high_value.sort(key=lambda x: float(x.get("cpc", 0)), reverse=True)

    return "\n".join(lines), high_value[:12]


def _build_high_value_keyword_table(high_value_kws: list[dict]) -> str:
    if not high_value_kws:
        return ""
    lines = [
        "| Keyword | Monthly Volume | Google Ads CPC | Annual Value (10% CTR) |",
        "|---------|---------------|----------------|----------------------|",
    ]
    for kw in high_value_kws:
        keyword = kw.get("keyword", "")
        vol = kw.get("search_volume") or 0
        cpc = float(kw.get("cpc", 0))
        annual = vol * 0.10 * cpc * 12
        lines.append(f"| {keyword} | {_fmt_num(vol)} | {_fmt_cpc(cpc)} | {_fmt_dollar(annual)} |")
    return "\n".join(lines)


def _build_priority_keyword_table(
    volumes: list[dict],
    difficulty: list[dict],
    service: str,
    city: str,
) -> str:
    if not volumes:
        return ""

    diff_lookup = {kw.get("keyword", ""): kw.get("keyword_difficulty") for kw in difficulty}

    scored = []
    for kw in volumes:
        keyword = kw.get("keyword", "")
        vol = kw.get("search_volume") or 0
        if vol == 0:
            continue
        cpc = float(kw.get("cpc", 0) or 0)
        diff = diff_lookup.get(keyword)
        score = (vol * 0.1) + (cpc * 5) - ((diff or 50) * 0.5)
        scored.append((score, kw, diff))

    scored.sort(key=lambda x: x[0], reverse=True)

    lines = [
        "| Priority | Keyword | Volume | CPC | Difficulty | Why |",
        "|----------|---------|--------|-----|-----------|-----|",
    ]

    for idx, (score, kw, diff) in enumerate(scored[:10], 1):
        keyword = kw.get("keyword", "")
        vol = kw.get("search_volume") or 0
        cpc = _fmt_cpc(kw.get("cpc"))
        diff_str = f"{diff}/100" if diff is not None else "—"
        kw_lower = keyword.lower()
        if "emergency" in kw_lower:
            reason = "Highest CPC — urgent buyers, premium value"
        elif "near me" in kw_lower:
            reason = "High purchase intent, proximity signal"
        elif "ceramic" in kw_lower or "paint correction" in kw_lower:
            reason = "Premium service — highest avg job value"
        elif city.lower() in kw_lower:
            reason = f"Core market — rank in {city} first"
        elif diff is not None and diff < 30:
            reason = "Low competition — quick ranking win"
        elif kw.get("cpc") and float(kw.get("cpc", 0) or 0) > 10:
            reason = "High commercial value, strong buying intent"
        else:
            reason = "Consistent local search demand"
        lines.append(f"| {idx} | {keyword} | {_fmt_num(vol)} | {cpc} | {diff_str} | {reason} |")

    return "\n".join(lines)


def _build_roi_table(
    total_traffic_goal: int,
    avg_job_value_str: str,
    service: str,
) -> tuple[str, str]:
    try:
        job_val = float(re.sub(r"[^\d.]", "", avg_job_value_str)) if avg_job_value_str else 350
    except (ValueError, TypeError):
        job_val = 350

    con_traffic = max(500, min(total_traffic_goal // 4, 1000))
    con_leads = math.ceil(con_traffic * 0.03)
    con_jobs = math.ceil(con_leads * 0.40)
    con_revenue = con_jobs * job_val
    con_annual = con_revenue * 12

    grow_traffic = max(2000, min(total_traffic_goal, 3000))
    grow_leads = math.ceil(grow_traffic * 0.04)
    grow_jobs = math.ceil(grow_leads * 0.40)
    grow_revenue = grow_jobs * job_val
    grow_annual = grow_revenue * 12

    con_table = "\n".join([
        "| Metric | Value | Calculation |",
        "|--------|-------|-------------|",
        f"| Organic Traffic Goal | {_fmt_num(con_traffic)}/month | Achievable with 20-30 page-1 rankings |",
        f"| Conversion Rate | 3% | Industry average for {service} businesses |",
        f"| Leads/Month | {con_leads} | {_fmt_num(con_traffic)} × 3% |",
        f"| Close Rate | 40% | Good sales process |",
        f"| New Customers/Month | {con_jobs} | {con_leads} × 40% |",
        f"| Avg Job Value | {_fmt_dollar(job_val)} | Your stated average |",
        f"| **Monthly Revenue** | **{_fmt_dollar(con_revenue)}** | {con_jobs} × {_fmt_dollar(job_val)} |",
        f"| **Annual Revenue from SEO** | **{_fmt_dollar(con_annual)}** | Conservative estimate |",
    ])

    grow_table = "\n".join([
        "| Metric | Value | Calculation |",
        "|--------|-------|-------------|",
        f"| Organic Traffic Goal | {_fmt_num(grow_traffic)}/month | With 50+ keywords ranking page 1 |",
        f"| Conversion Rate | 4% | Optimized website |",
        f"| Leads/Month | {grow_leads} | {_fmt_num(grow_traffic)} × 4% |",
        f"| Close Rate | 40% | Consistent process |",
        f"| New Customers/Month | {grow_jobs} | {grow_leads} × 40% |",
        f"| Avg Job Value | {_fmt_dollar(job_val)} | Your stated average |",
        f"| **Monthly Revenue** | **{_fmt_dollar(grow_revenue)}** | {grow_jobs} × {_fmt_dollar(job_val)} |",
        f"| **Annual Revenue from SEO** | **{_fmt_dollar(grow_annual)}** | Transformational growth |",
    ])

    return con_table, grow_table


def _build_ads_comparison_table(avg_cpc: float) -> str:
    if avg_cpc == 0:
        avg_cpc = 15.00
    return "\n".join([
        "| Scenario | Organic Traffic | Avg CPC | Monthly Ad Cost | Annual Ad Cost |",
        "|----------|----------------|---------|----------------|----------------|",
        f"| Conservative (500/mo) | 500 | {_fmt_cpc(avg_cpc)} | {_fmt_dollar(500 * avg_cpc)} | {_fmt_dollar(500 * avg_cpc * 12)} |",
        f"| Growth (2,000/mo) | 2,000 | {_fmt_cpc(avg_cpc)} | {_fmt_dollar(2000 * avg_cpc)} | {_fmt_dollar(2000 * avg_cpc * 12)} |",
    ])


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior SEO strategist at ProofPilot writing a market analysis for a prospect.

## Brand voice (follow exactly)
- Direct, confrontational, specific. Active voice. Short sentences.
- Address reader as "you" and "your business."
- Name competitors specifically by their domain/business name.
- NO em dashes, NO semicolons. Periods and commas only.
- Revenue language: clicks = calls = booked jobs.
- Frame everything as opportunity, not failure.

## Output rules
- Start immediately with the # heading. Zero preamble.
- Follow the template exactly. Replace every [bracketed instruction] with real content.
- Do not modify pre-built data tables — reproduce them exactly as given.
- Write in the same punchy style as the Steadfast Plumbing reference:
  "That's 3,124 free visits per month going to EZFlow. Not you."

## Table format
- Keep all pre-filled tables exactly as provided in the template."""


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _empty_list() -> list:
    return []


# ── Main workflow ─────────────────────────────────────────────────────────────

async def run_prospect_audit(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    domain = inputs.get("domain", "").strip().lower()
    if not domain:
        yield "Error: No domain provided."
        return

    service         = inputs.get("service", "").strip()
    location        = inputs.get("location", "").strip()
    avg_job_value   = inputs.get("avg_job_value", "").strip()
    notes           = inputs.get("notes", "").strip()

    location_name = _build_location_name(location) if location else ""
    city          = location.split(",")[0].strip() if location else ""
    state_raw     = location.split(",")[1].strip() if "," in location else ""
    state_abbr    = state_raw.upper()
    state_full    = _STATE_MAP.get(state_abbr, state_raw)

    # Get nearby cities for metro-wide competitor search
    metro_cities = _get_metro_cities(city, state_abbr, n=5)

    yield f"> Pulling SEO data for **{domain}**...\n\n"
    if service and city:
        yield f"> Researching who dominates **{service}** across **{', '.join(metro_cities[:3])}** and nearby...\n\n"

    # ── Phase 1: Parallel data gather ─────────────────────────────────────
    keyword_seeds = _build_metro_seeds(service, metro_cities)

    sa_task  = _gather_sa_data(domain)
    vol_task = (
        get_keyword_search_volumes(keyword_seeds, location_name)
        if keyword_seeds and location_name else _empty_list()
    )
    metro_competitors_task = _discover_metro_competitors(
        service, metro_cities, state_abbr, state_full
    )

    sa_data, keyword_volumes, domain_city_map = await asyncio.gather(
        sa_task, vol_task, metro_competitors_task,
        return_exceptions=True,
    )
    if isinstance(sa_data, Exception):
        sa_data = {}
    if isinstance(keyword_volumes, Exception):
        keyword_volumes = []
    if isinstance(domain_city_map, Exception):
        domain_city_map = {}

    yield f"> Pulling traffic data for {len(domain_city_map)} competitors across the {city} metro...\n\n"

    # ── Phase 2: Competitor profiling + prospect rank ──────────────────────
    competitor_profiles, prospect_rank, keyword_difficulty = await asyncio.gather(
        _profile_competitors(domain_city_map, location_name),
        _get_prospect_rank(domain, location_name),
        (
            get_bulk_keyword_difficulty(
                [v["keyword"] for v in (keyword_volumes or [])[:20] if v.get("keyword") and (v.get("search_volume") or 0) > 0],
                location_name,
            )
            if keyword_volumes and location_name else _empty_list()
        ),
        return_exceptions=True,
    )
    if isinstance(competitor_profiles, Exception):
        competitor_profiles = []
    if isinstance(prospect_rank, Exception):
        prospect_rank = {"domain": domain, "keywords": 0, "etv": 0, "etv_cost": 0}
    if isinstance(keyword_difficulty, Exception):
        keyword_difficulty = []

    yield f"> Building analysis with real market data...\n\n"
    yield "---\n\n"

    # ── Phase 3: Compute market metrics ───────────────────────────────────
    today = __import__("datetime").date.today().strftime("%B %d, %Y")

    kw_vol_list = keyword_volumes or []
    total_searches = sum(kw.get("search_volume") or 0 for kw in kw_vol_list)
    cpcs_all = [float(kw["cpc"]) for kw in kw_vol_list if kw.get("cpc") and float(kw.get("cpc", 0)) > 0]
    avg_cpc = sum(cpcs_all) / len(cpcs_all) if cpcs_all else 0
    max_cpc = max(cpcs_all) if cpcs_all else 0
    monthly_ad_val = total_searches * 0.10 * avg_cpc
    annual_ad_val = monthly_ad_val * 12

    # Market leader = highest traffic competitor
    market_leader = competitor_profiles[0] if competitor_profiles else None
    leader_traffic = market_leader.get("traffic", 0) if market_leader else 0
    leader_value = market_leader.get("etv_cost", 0) if market_leader else 0
    leader_domain = market_leader.get("domain", "your top competitor") if market_leader else "your top competitor"

    # ── Phase 4: Build tables ──────────────────────────────────────────────
    competitor_overview_table = _build_competitor_overview_table(
        competitor_profiles, client_name, prospect_rank
    )

    market_leader_section = (
        _build_market_leader_section(market_leader) if market_leader else ""
    )

    other_competitors_section = _build_other_competitors_section(competitor_profiles)

    pillar_table, high_value_kws = _build_keyword_pillar_table(kw_vol_list, service)
    high_value_table = _build_high_value_keyword_table(high_value_kws)
    priority_table = _build_priority_keyword_table(kw_vol_list, keyword_difficulty or [], service, city)

    con_roi_table, grow_roi_table = _build_roi_table(
        total_searches, avg_job_value, service
    )
    ads_comparison_table = _build_ads_comparison_table(avg_cpc)

    # Company info table
    company_info = (
        f"| | |\n|---|---|\n"
        f"| **Company** | {client_name} |\n"
        f"| **Website** | {domain} |\n"
        f"| **Market** | {location} |\n"
        f"| **Metro Area Covered** | {', '.join(metro_cities)} |\n"
        f"| **Analysis Date** | {today} |\n"
        f"| **Prepared By** | ProofPilot |"
    )

    # Market metrics table
    total_searches_display = f"{total_searches:,}" if total_searches else "significant"
    market_metrics_table = "\n".join([
        "| Metric | Value | What It Means |",
        "|--------|-------|---------------|",
        f"| Total Monthly Searches (metro) | {total_searches_display} | Real demand across your target cities |",
        f"| Average CPC (Google Ads) | {_fmt_cpc(avg_cpc) if avg_cpc else '—'} | What competitors pay per click |",
        f"| Top Keyword CPC | {_fmt_cpc(max_cpc) if max_cpc else '—'} | SEO saves you {_fmt_cpc(max_cpc) if max_cpc else 'this'} per lead |",
        f"| Est. Monthly Ad Value | {_fmt_dollar(monthly_ad_val) if monthly_ad_val else '—'} | Value of ranking #1 organically |",
        f"| Est. Annual Ad Value | {_fmt_dollar(annual_ad_val) if annual_ad_val else '—'} | What you'd spend on Google Ads |",
        f"| Market Leader Traffic | {_fmt_num(leader_traffic)}/mo | {leader_domain} gets this for free |",
    ])

    # Reveals bullets
    reveals_bullets = []
    if total_searches:
        reveals_bullets.append(f"- **{total_searches:,}+ monthly searches** for {service} across your metro area")
    if annual_ad_val:
        reveals_bullets.append(f"- **{_fmt_dollar(annual_ad_val)} in annual Google Ads value** sitting on the table")
    if leader_traffic:
        reveals_bullets.append(f"- **{leader_domain}** is collecting **{_fmt_num(leader_traffic)} free visits/month** — here's exactly how")
    if leader_value:
        reveals_bullets.append(f"- That traffic is worth **{_fmt_dollar(leader_value)}/month** in ad value — going to them, not you")
    if max_cpc:
        reveals_bullets.append(f"- Keywords costing up to **{_fmt_cpc(max_cpc)}/click** on Google Ads — SEO gets them free")
    if not reveals_bullets:
        reveals_bullets = [
            f"- Who's dominating Google for {service} across {', '.join(metro_cities[:3])}",
            "- What keywords drive the most bookings and how hard they are to win",
            "- Your current SEO footprint vs. where you need to be",
            "- A 90-day roadmap to start taking real market share",
        ]
    reveals_text = "\n".join(reveals_bullets)

    # Context for Claude
    sa_context = "\n".join([
        "## PROSPECT CURRENT RANKINGS (Search Atlas)",
        str(sa_data.get("organic_keywords", "No data")),
        "",
        "## PROSPECT POSITION DISTRIBUTION",
        str(sa_data.get("position_distribution", "Not available")),
        "",
        "## PROSPECT SEO PILLAR SCORES",
        str(sa_data.get("pillar_scores", "Not available")),
        "",
        "## PROSPECT DFS LABS OVERVIEW",
        f"Monthly organic traffic: {_fmt_num(prospect_rank.get('traffic'))}",
        f"Traffic value: {_fmt_dollar(prospect_rank.get('etv_cost'))}",
        f"Keywords in top 100: {_fmt_num(prospect_rank.get('keywords'))}",
    ])
    if notes:
        sa_context += f"\n\n## SALES CONTEXT\n{notes}"
    if strategy_context and strategy_context.strip():
        sa_context += f"\n\n## AGENCY STRATEGY DIRECTION\n{strategy_context.strip()}"

    # ── Phase 5: Build document template ──────────────────────────────────
    leader_name = leader_domain if market_leader else "the market leader"

    # Top 10 keywords by volume for Claude to format
    top_kw_data = sorted(kw_vol_list, key=lambda x: x.get("search_volume") or 0, reverse=True)[:10]
    top_kw_lines = "\n".join([
        f"  {kw.get('keyword')}: {kw.get('search_volume') or 0:,}/mo, CPC {_fmt_cpc(kw.get('cpc'))}, competition: {kw.get('competition_level', '—')}"
        for kw in top_kw_data if (kw.get("search_volume") or 0) > 0
    ]) or "  No volume data available"

    competitor_section = ""
    if competitor_overview_table:
        competitor_section = f"""### COMPETITIVE LANDSCAPE: {city.upper()} METRO

{competitor_overview_table}"""
    else:
        competitor_section = "[No competitor data retrieved — check DataForSEO credentials]"

    leader_full_section = ""
    if market_leader_section:
        leader_full_section = f"""### THE MARKET LEADER: {leader_domain.upper()}

{market_leader_section}"""

    other_section = ""
    if other_competitors_section:
        other_section = f"""### OTHER COMPETITORS IN YOUR MARKET

{other_competitors_section}"""

    pillar_section = ""
    if pillar_table:
        pillar_section = f"""### KEYWORD MARKET BREAKDOWN BY SERVICE TYPE

{pillar_table}"""

    high_value_section = ""
    if high_value_table:
        high_value_section = f"""### HIGH-VALUE KEYWORD OPPORTUNITIES

These keywords have CPCs above $20 — every organic click saves you that amount vs. Google Ads.

{high_value_table}"""

    _fallback_priority_row = (
        "| Priority | Keyword | Volume | CPC | Why |\n"
        "|--|--|--|--|--|\n"
        f"| 1 | {service} {city} | — | — | Core market keyword |"
    )
    priority_table_str = priority_table if priority_table else _fallback_priority_row

    template = f"""# SEO MARKET OPPORTUNITY & COMPETITIVE ANALYSIS

Real Data. Real Opportunity. Real ROI.

{company_info}

---

## WHAT THIS ANALYSIS REVEALS

{reveals_text}

**EXECUTIVE SUMMARY**

[Write 4-5 sentences. State total monthly searches ({total_searches_display}) across the metro area. Name {leader_name} as the market leader getting {_fmt_num(leader_traffic)} visits/month worth {_fmt_dollar(leader_value)}/mo. State that Motor City is currently invisible in organic search. Frame it as: this market is real, the competition is beatable, and the data shows exactly where the opportunity is. ProofPilot has the plan.]

**{total_searches_display}**
**MONTHLY METRO SEARCHES**
People searching for {service} across {', '.join(metro_cities[:3])} every month

{market_metrics_table}

---

## COMPETITOR ANALYSIS: WHO'S WINNING YOUR METRO

[Write 2-3 sentences. Explain that we searched across {len(metro_cities)} cities in the metro to find the real competitors — not directories, not national chains. We found who's actually getting traffic. Name {leader_name} as the dominant player.]

{competitor_section}

{leader_full_section}

{other_section}

---

## KEYWORD PILLAR ANALYSIS

[Write 2-3 sentences. Explain that you analyzed searches across the full metro: {', '.join(metro_cities)}. Reference which pillar has the most volume. Identify 1-2 premium keyword opportunities with the best ROI.]

{pillar_section}

{high_value_section}

---

## SERVICE-SPECIFIC KEYWORD OPPORTUNITIES

[Write 2-3 sentences about the best keyword opportunities specific to {service} in the {city} metro. Name the top 3 keywords by volume with their exact search volume and CPC. Explain which keywords to target first and why.]

### KEYWORD OPPORTUNITIES BY SEARCH VOLUME

[Build a markdown table from this data:
{top_kw_lines}

Use this format:
| Keyword | Volume | CPC | Competition |
|---------|--------|-----|------------|
(fill rows from data above, only include keywords with volume > 0)]

---

## ROI PROJECTIONS: WHAT SEO CAN DELIVER

[Write 2 sentences. Reference avg job value of {avg_job_value or "standard for this industry"}. Frame as: here's what realistic SEO results look like in your market when the right keywords start converting.]

**CONSERVATIVE SCENARIO (Month 6-12)**

{con_roi_table}

**GROWTH SCENARIO (Month 12-18)**

{grow_roi_table}

**WHAT YOU'D PAY GOOGLE ADS FOR THE SAME TRAFFIC**

{ads_comparison_table}

---

## WHY SEO BEATS GOOGLE ADS FOR {client_name.upper()}

[Write the comparison section. Build a table:
| Factor | Google Ads | SEO |
|--------|-----------|-----|
| Cost per Click | {_fmt_cpc(max_cpc) if max_cpc else '$3-10'} per click | $0 once you rank |
| Traffic when budget runs out | Stops immediately | Keeps working |
| Click-Through Rate | 5-15% (labeled "Sponsored") | 30-40% organic position 1 |
| Trust Factor | Buyers skip sponsored results | Organic = instant credibility |
| Long-term Asset Value | Renting visibility | Building equity |
| Annual Cost for 2,000 visitors | {_fmt_dollar(2000 * avg_cpc * 12) if avg_cpc else "$30,000+"} | Included in monthly retainer |

Then write 2-3 sentences about the specific math in this market using the real CPC numbers.]

---

## RECOMMENDED SEO STRATEGY

### PHASE 1: FOUNDATION (Months 1-3)

[Write 5 bullet points for Phase 1, specific to {service} in {city}. Include: GBP optimization across all service areas, service page creation for each detailing service, technical SEO fixes, tracking setup, NAP consistency.]

### PHASE 2: CONTENT & AUTHORITY (Months 3-8)

[Write 5 bullet points for Phase 2. Include: location pages for {', '.join(metro_cities[1:4] if len(metro_cities) > 1 else ['nearby cities'])}, educational content specific to Arizona/the local climate, citation building, review velocity system, local link outreach.]

### PHASE 3: DOMINATION (Months 8-12+)

[Write 4 bullet points. Include: targeting {leader_name}'s keywords specifically, expanding to all {len(metro_cities)} metro cities, scaling content output, owning the Map Pack across the East Valley.]

---

## PRIORITY KEYWORDS TO TARGET FIRST

[Write 2 sentences about why these specific keywords were selected — highest traffic potential vs. ranking difficulty.]

{priority_table_str}

---

## CONCLUSION: THE PATH FORWARD

[Write the conclusion exactly like the Steadfast reference:
- Start with: "This is not theoretical. This is real data from real competitors in your market."
- State that {leader_name} is getting {_fmt_num(leader_traffic)} visits/month that should be going to {client_name}
- List 4 specific bullet point outcomes (rank page 1 for X, generate Y-Z new customers/month, dollar ranges)
- End with: "The opportunity is real. The competitors are beatable. The only question is whether {client_name} moves now or watches another year of customers drive to {leader_name} instead."
- Final line: "ProofPilot is ready to build the plan and execute it."]"""

    # ── Phase 6: Stream Claude ─────────────────────────────────────────────
    user_prompt = f"""Write the complete SEO Market Analysis for **{client_name}** ({domain}).
They are a **{service}** business serving **{location}** and the surrounding metro: {', '.join(metro_cities)}.

Fill in every [bracketed instruction] with real, specific content. Keep all pre-built tables exactly as shown. Write direct, punchy narrative between sections. Name competitors by domain name. Use real numbers.

---

{template}

---

CONTEXT DATA (use to inform scoring and narrative):

{sa_context}

Write the complete document now. Start with # SEO MARKET OPPORTUNITY."""

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=14000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
