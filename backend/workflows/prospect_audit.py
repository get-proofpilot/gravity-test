"""
Prospect SEO Market Analysis Workflow — ProofPilot v5

SEO manager logic (from Matthew's audit walkthrough):
  - Searches across the full metro area (5 nearest cities), not just the prospect's city
  - Finds the actual dominant local player — not national chains, not directories
  - Filters out weak competitors with no search volume automatically
  - Takes top 1-2 local domains per city, deduplicates, sorts by traffic (dominant = most cities)
  - Organic + GBP/Maps traffic unified (DFS Labs returns all ranked keywords including local pack)
  - Service-aware keyword seeds — plumbing, electrician, HVAC, roofing, concrete, etc.
  - Service-aware pillar grouping — correct buckets for each industry
  - Competitor keyword tables include CPC + Traffic Value for each keyword
  - All keyword variants aggregated into pillars (not listed as duplicates)
  - City-based keyword thinking: "plumber gilbert az" not just "plumber"

inputs keys:
    domain          e.g. "steadfastplumbingaz.com"
    service         e.g. "plumber"
    location        e.g. "Gilbert, AZ"
    monthly_revenue optional
    avg_job_value   optional
    notes           optional sales context
"""

import os
import asyncio
import re
import math
import anthropic
from typing import AsyncGenerator, Optional

from utils.searchatlas import sa_call
from utils.dataforseo import (
    research_competitors,
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
    ("gilbert", "az"):    ["Gilbert", "Chandler", "Mesa", "Tempe", "Queen Creek", "San Tan Valley", "Scottsdale"],
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


# ── Service intelligence ──────────────────────────────────────────────────────
# Maps service descriptions → keyword seeds + pillar grouping rules.
# Ensures the audit uses the right vocabulary for each trade.

def _detect_service_type(service: str) -> str:
    """Detect broad service category from free-text service string."""
    s = service.lower()
    if any(k in s for k in ["plumb", "plumber", "drain", "sewer", "water heater"]):
        return "plumbing"
    if any(k in s for k in ["electric", "electrician", "wiring", "panel"]):
        return "electrician"
    if any(k in s for k in ["hvac", "ac repair", "air condition", "heating", "cooling", "furnace", "heat pump"]):
        return "hvac"
    if any(k in s for k in ["roof", "roofer", "shingle", "gutter"]):
        return "roofing"
    if any(k in s for k in ["detail", "detailing", "car wash", "auto detail"]):
        return "auto_detailing"
    if any(k in s for k in ["concrete", "cement", "pav"]):
        return "concrete"
    if any(k in s for k in ["landscape", "lawn", "grass", "tree service", "tree trim"]):
        return "landscaping"
    if any(k in s for k in ["paint", "painting", "painter"]):
        return "painting"
    if any(k in s for k in ["clean", "cleaning", "maid", "janitorial", "pressure wash"]):
        return "cleaning"
    if any(k in s for k in ["pest", "exterminator", "rodent", "termite", "bug"]):
        return "pest_control"
    return "general"


_SERVICE_SPECIALTY_KEYWORDS: dict[str, list[str]] = {
    "plumbing": [
        "emergency plumber", "plumbing repair", "drain cleaning",
        "water heater repair", "water heater installation", "tankless water heater",
        "water softener installation", "reverse osmosis system",
        "sewer line repair", "leak detection", "burst pipe repair",
        "toilet repair", "faucet installation",
    ],
    "electrician": [
        "electrician", "electrical contractor", "panel upgrade",
        "breaker panel replacement", "electrical repair",
        "ev charger installation", "ev charging station",
        "lighting installation", "emergency electrician", "house rewiring",
        "outlet installation", "ceiling fan installation",
    ],
    "hvac": [
        "ac repair", "air conditioner repair", "hvac repair", "hvac service",
        "furnace repair", "furnace installation", "ac installation",
        "heat pump repair", "ductwork repair", "air quality testing",
        "hvac maintenance", "central air installation",
    ],
    "roofing": [
        "roof repair", "roof replacement", "roofing contractor",
        "roof inspection", "storm damage roof repair", "gutter installation",
        "gutter repair", "gutter cleaning", "roof leak repair",
        "shingle replacement", "flat roof repair",
    ],
    "auto_detailing": [
        "ceramic coating", "paint correction", "interior detailing",
        "exterior detailing", "mobile detailing", "full detail",
        "auto detailing packages", "paint protection film",
        "headlight restoration", "engine detailing",
    ],
    "concrete": [
        "concrete driveway", "driveway installation", "concrete repair",
        "patio installation", "stamped concrete", "concrete contractor",
        "concrete flatwork", "concrete resurfacing", "retaining wall",
    ],
    "landscaping": [
        "lawn care service", "lawn mowing", "landscape design",
        "irrigation repair", "sprinkler repair", "tree trimming",
        "tree removal", "sod installation", "hardscape installation",
    ],
    "painting": [
        "interior painting", "exterior painting", "house painter",
        "commercial painting", "cabinet painting", "deck staining",
        "fence painting", "epoxy floor coating",
    ],
    "cleaning": [
        "house cleaning service", "maid service", "deep cleaning",
        "move in cleaning", "move out cleaning", "pressure washing",
        "commercial cleaning", "window cleaning",
    ],
    "pest_control": [
        "pest control", "exterminator", "termite treatment",
        "rodent control", "ant control", "bed bug treatment",
        "mosquito control", "wildlife removal",
    ],
}

# Pillar rules: ordered list of (name, trigger_keywords).
# First match wins. Empty trigger list = catch-all bucket.
_SERVICE_PILLAR_RULES: dict[str, list[tuple[str, list[str]]]] = {
    "plumbing": [
        ("Emergency Plumbing",  ["emergency", "urgent", "24 hour", "same day", "24/7"]),
        ("Water Heater",        ["water heater", "hot water", "tankless"]),
        ("Drain & Sewer",       ["drain", "sewer", "clog", "rooter", "sewer line"]),
        ("Water Treatment",     ["water softener", "softener", "water treatment",
                                  "reverse osmosis", "ro system", "filtration",
                                  "conditioning", "water purif"]),
        ("Leak & Pipe Repair",  ["leak", "pipe", "burst", "repiping"]),
        ("General Plumbing",    []),
    ],
    "electrician": [
        ("Emergency",           ["emergency", "urgent", "24 hour", "same day"]),
        ("Panel & Service",     ["panel", "breaker", "electrical box",
                                  "service upgrade", "200 amp", "100 amp"]),
        ("EV Charging",         ["ev charger", "electric vehicle", "tesla",
                                  "charger install", "charging station"]),
        ("Lighting",            ["lighting", "light fixture", "led", "dimmer", "recessed"]),
        ("Wiring & Outlets",    ["wiring", "rewire", "outlet", "switch", "gfci"]),
        ("General Electrical",  []),
    ],
    "hvac": [
        ("Emergency HVAC",      ["emergency", "urgent", "24 hour", "same day"]),
        ("AC Repair",           ["ac repair", "air conditioner repair", "ac service",
                                  "cooling repair", "ac not cooling"]),
        ("Heating",             ["heating", "furnace", "heat pump", "boiler", "heater"]),
        ("Installation",        ["installation", "install", "new unit",
                                  "replacement", "new ac", "new hvac"]),
        ("Air Quality",         ["air quality", "ductwork", "filter",
                                  "purifier", "humidity", "duct cleaning"]),
        ("General HVAC",        []),
    ],
    "roofing": [
        ("Emergency / Storm",   ["emergency", "storm damage", "urgent",
                                  "roof leak", "hail damage"]),
        ("Roof Replacement",    ["replacement", "new roof", "reroof"]),
        ("Roof Repair",         ["repair", "fix", "patch", "leak repair"]),
        ("Gutters",             ["gutter", "downspout", "fascia", "soffit"]),
        ("Inspection",          ["inspection", "estimate", "assessment"]),
        ("General Roofing",     []),
    ],
    "auto_detailing": [
        ("Emergency / Urgent",  ["emergency", "urgent", "24 hour", "same day", "24/7"]),
        ("Premium / Specialty", ["ceramic", "paint correction", "ppf",
                                  "protection film", "restoration",
                                  "premium", "packages", "full detail"]),
        ("Interior",            ["interior", "inside", "upholstery", "carpet", "steam"]),
        ("Exterior / Wash",     ["exterior", "outside", "wash", "wax", "polish"]),
        ("Mobile",              ["mobile", "come to", "at home", "your home", "on-site"]),
        ("Core Detailing",      []),
    ],
    "concrete": [
        ("Driveway",            ["driveway"]),
        ("Patio / Outdoor",     ["patio", "walkway", "pathway", "outdoor", "sidewalk"]),
        ("Decorative",          ["stamped", "decorative", "stained",
                                  "exposed aggregate", "colored"]),
        ("Repair",              ["repair", "crack", "fix", "resurface", "patch"]),
        ("Foundation",          ["foundation", "slab", "footing", "basement"]),
        ("General Concrete",    []),
    ],
    "landscaping": [
        ("Lawn Care",           ["lawn", "mowing", "grass", "turf", "sod"]),
        ("Tree Services",       ["tree trim", "tree removal", "tree service",
                                  "stump", "arborist"]),
        ("Irrigation",          ["irrigation", "sprinkler", "drip system"]),
        ("Hardscape",           ["patio", "retaining wall", "walkway",
                                  "pavers", "fire pit"]),
        ("Design & Install",    ["design", "landscape design", "renovation",
                                  "makeover", "install"]),
        ("General Landscaping", []),
    ],
    "general": [
        ("Emergency",           ["emergency", "urgent", "24 hour", "same day"]),
        ("Premium Service",     ["premium", "best", "top rated", "professional"]),
        ("Local Demand",        []),
    ],
}


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

            # Gap 1 fix: DFS Labs returns near-empty for small local domains.
            # If we got fewer than 3 keywords, fall back to Search Atlas which
            # resolves at local resolution and finds what DFS misses.
            if len(top_kws or []) < 3:
                try:
                    sa_resp = await sa_call(
                        "Site_Explorer_Organic_Tool",
                        "get_organic_keywords",
                        {"project_identifier": domain, "page_size": 20, "ordering": "-traffic"},
                    )
                    sa_kws = _parse_sa_keywords(sa_resp)
                    if sa_kws:
                        top_kws = sa_kws
                except Exception:
                    pass  # keep sparse DFS data rather than crashing

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
    Build keyword seeds across metro cities with service-aware specialty terms.

    Logic (from Matthew's audit walkthrough):
      - Core {service} {city} seeds for each metro city
      - Near-me / high-intent seeds (emergency, best, near me)
      - Service-specific specialty keywords × primary + secondary city
        (e.g. for plumbing: water heater repair, drain cleaning, water softener)
      - City-based keyword thinking: local businesses need city-qualified terms
    """
    s = service.lower().strip()
    service_type = _detect_service_type(s)
    specialty_terms = _SERVICE_SPECIALTY_KEYWORDS.get(service_type, [])

    seeds = []

    # Core per-city seeds (first 4 metro cities)
    for city in metro_cities[:4]:
        c = city.lower()
        seeds += [
            f"{s} {c}",
            f"best {s} {c}",
        ]

    # High-commercial-intent near-me seeds
    seeds += [
        f"{s} near me",
        f"best {s} near me",
        f"emergency {s} near me",
        f"{s} service near me",
        f"{s} prices near me",
    ]

    # Service specialty terms × primary city
    city1 = metro_cities[0].lower() if metro_cities else ""
    for spec in specialty_terms[:14]:
        if city1:
            seeds.append(f"{spec} {city1}")
        seeds.append(spec)  # Include bare term for volume reference

    # Service specialty terms × second city (metro coverage)
    if len(metro_cities) > 1:
        city2 = metro_cities[1].lower()
        for spec in specialty_terms[:7]:
            seeds.append(f"{spec} {city2}")

    # Dedup, remove empties, cap at 50
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
            "| Keyword | Position | Traffic | Search Vol | CPC | Traffic Value |",
            "|---------|----------|---------|-----------|-----|--------------|",
        ]
        for kw in top_kws[:10]:
            keyword = kw.get("keyword", "")
            rank = kw.get("rank") or "—"
            est_t = _fmt_num(kw.get("traffic_estimate"))
            vol = _fmt_num(kw.get("search_volume"))
            cpc = kw.get("cpc")
            cpc_str = _fmt_cpc(cpc) if cpc is not None else "—"
            traffic_val = (kw.get("traffic_estimate") or 0) * float(cpc or 0)
            tval_str = _fmt_dollar(traffic_val) if traffic_val > 0 else "—"
            lines.append(f"| {keyword} | #{rank} | {est_t} | {vol} | {cpc_str} | {tval_str} |")
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
                "| Keyword | Position | Traffic | Search Vol | CPC | Traffic Value |",
                "|---------|----------|---------|-----------|-----|--------------|",
            ]
            for kw in top_kws[:6]:
                keyword = kw.get("keyword", "")
                rank = kw.get("rank") or "—"
                est_t = _fmt_num(kw.get("traffic_estimate"))
                vol = _fmt_num(kw.get("search_volume"))
                cpc = kw.get("cpc")
                cpc_str = _fmt_cpc(cpc) if cpc is not None else "—"
                traffic_val = (kw.get("traffic_estimate") or 0) * float(cpc or 0)
                tval_str = _fmt_dollar(traffic_val) if traffic_val > 0 else "—"
                lines.append(f"| {keyword} | #{rank} | {est_t} | {vol} | {cpc_str} | {tval_str} |")
        else:
            lines.append(f"*Limited DFS Labs data available for {d}.*")

        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _build_keyword_pillar_table(
    volumes: list[dict],
    service: str,
) -> tuple[str, list[dict]]:
    """
    Group keyword volumes by service pillar using service-aware rules.
    Returns (table_markdown, high_value_kws).

    Uses _SERVICE_PILLAR_RULES to bucket keywords correctly for each trade:
    plumbing → water heater / drain / water treatment / emergency / etc.
    electrician → panel / EV charger / lighting / wiring / etc.
    (not auto-detailing buckets for every industry)
    """
    if not volumes:
        return "", []

    service_type = _detect_service_type(service)
    pillar_rules = _SERVICE_PILLAR_RULES.get(service_type, _SERVICE_PILLAR_RULES["general"])

    buckets: dict[str, list[dict]] = {}
    for kw_data in volumes:
        kw = kw_data.get("keyword", "").lower()
        assigned = False
        for pillar_name, trigger_keywords in pillar_rules:
            if trigger_keywords and any(k in kw for k in trigger_keywords):
                if pillar_name not in buckets:
                    buckets[pillar_name] = []
                buckets[pillar_name].append(kw_data)
                assigned = True
                break
        if not assigned:
            # Find the catch-all (empty trigger list) and assign there
            for pillar_name, trigger_keywords in pillar_rules:
                if not trigger_keywords:
                    if pillar_name not in buckets:
                        buckets[pillar_name] = []
                    buckets[pillar_name].append(kw_data)
                    break

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


def _build_why_this_matters_box(high_value_kws: list[dict], service: str) -> str:
    """
    "Why This Matters" calculation callout from the Steadfast reference.
    Shows exact math: top high-CPC keyword × volume × CTR × 12 months = annual ad savings.
    """
    if not high_value_kws:
        return ""

    # Prefer emergency/urgent keyword — highest intent, highest CPC
    top_kw = None
    for kw in high_value_kws:
        if any(t in kw.get("keyword", "").lower() for t in ["emergency", "urgent", "24 hour"]):
            top_kw = kw
            break
    if top_kw is None:
        top_kw = high_value_kws[0]

    keyword = top_kw.get("keyword", "")
    vol = top_kw.get("search_volume") or 0
    cpc = float(top_kw.get("cpc", 0) or 0)

    if not vol or not cpc:
        return ""

    monthly_clicks = round(vol * 0.10)
    monthly_value = monthly_clicks * cpc
    annual_value = monthly_value * 12

    return (
        f"**WHY THIS MATTERS**\n\n"
        f"Every month, **{vol:,} people** search for \"{keyword}\".\n"
        f"Google charges **{_fmt_cpc(cpc)} per click** for this keyword.\n"
        f"At a 10% CTR that's **{monthly_clicks} monthly clicks** worth **{_fmt_dollar(int(monthly_value))}/month** in ad traffic.\n"
        f"Over 12 months: **{_fmt_dollar(int(annual_value))} in Google Ads spend you never have to write a check for.**\n"
        f"Rank organically — keep that money."
    )


def _build_total_ads_cost_callout(
    total_volume: int,
    avg_cpc: float,
    high_value_kws: list[dict],
) -> str:
    """
    Gap 3: Show the aggregate "what Google Ads would cost" number across ALL
    metro keywords at a 10% CTR capture rate, plus one top-keyword spotlight.
    Renders inside the WHY SEO BEATS ADS section.
    """
    if not total_volume or not avg_cpc:
        return ""

    monthly_clicks = round(total_volume * 0.10)
    monthly_cost   = monthly_clicks * avg_cpc
    annual_cost    = monthly_cost * 12

    lines = [
        "**THE COST OF GOOGLE ADS IN YOUR MARKET**",
        "",
        f"To capture 10% of the {total_volume:,} monthly searches across your metro:",
        (
            f"**{monthly_clicks:,} clicks × {_fmt_cpc(avg_cpc)} avg CPC = "
            f"{_fmt_dollar(int(monthly_cost))}/month → {_fmt_dollar(int(annual_cost))}/year**"
        ),
        "",
    ]

    # Spotlight the single most expensive keyword
    if high_value_kws:
        top = high_value_kws[0]
        kw  = top.get("keyword", "")
        vol = top.get("search_volume") or 0
        cpc = float(top.get("cpc") or 0)
        if kw and vol and cpc:
            mo_clicks = round(vol * 0.10)
            mo_cost   = mo_clicks * cpc
            ann_cost  = mo_cost * 12
            lines += [
                f'For "{kw}" alone:',
                (
                    f"**{mo_clicks} clicks/month × {_fmt_cpc(cpc)} = "
                    f"{_fmt_dollar(int(mo_cost))}/month → {_fmt_dollar(int(ann_cost))}/year for ONE keyword**"
                ),
                "",
            ]

    lines += [
        f"Across all 50+ target keywords: **{_fmt_dollar(int(annual_cost * 2))}–{_fmt_dollar(int(annual_cost * 3))}/year** in Google Ads.",
        "SEO delivers the same traffic on a monthly retainer.",
    ]
    return "\n".join(lines)


def _build_meta_bonus_block(city: str, metro_cities: list[str]) -> str:
    """
    Gap 5: Pre-built Meta/Facebook Ads bonus section, gated on water treatment signals.
    Positions ProofPilot as thinking beyond SEO and neutralises the "I need leads NOW" objection.
    """
    metro_str = "/".join(metro_cities[:3])
    return f"""---

## BONUS: WHY META ADS ARE UNDERRATED FOR WATER TREATMENT

Water softeners and reverse osmosis systems are not emergency purchases. Nobody wakes up and searches "water softener." They need to be educated first. That makes Meta ads unusually effective here — you are creating demand instead of competing for it.

**Example Campaign**

| Element | Spec |
|---------|------|
| Audience | {metro_str} homeowners, health-conscious, recent movers |
| Creative | "Is Your Tap Water Safe?" video showing local water quality test results |
| Offer | Free in-home water quality test |
| Budget | $1,500/month |
| Expected result | 60–100 leads/month at $15–25/lead |

**Why this works:** Google Ads for "water softener {city}" costs $40–80/click for a keyword with 50–100 monthly searches. That is $2,000–8,000/month for a fraction of the leads Meta can deliver at the same budget. Meta targets who your customer is, not what they searched. For education-first services, that is a decisive advantage.

**The math:** $1,500/month budget. At 60 leads: $25/lead. At 100 leads: $15/lead. Close rate at 30%: 18–30 new water treatment customers per month. Average water softener job at $2,500: that is $45,000–75,000 in revenue from a $1,500 ad spend.

This is 1/3 the cost of Google Ads for the same lead volume, because you are creating demand instead of fighting over the same 50 monthly searchers."""


async def _discover_water_treatment_competitors(
    metro_cities: list[str],
    state_abbr: str,
    main_domains: set[str],
) -> dict[str, list[str]]:
    """
    Gap 2: Second SERP competitor discovery pass using water treatment seed queries.
    Water softener shops only rank for "water softener {city}" — they never appear
    in "plumber {city}" SERPs, so the main discovery pass misses them entirely.
    De-dups against main_domains so we never double-count a competitor.
    """
    has_creds = bool(os.environ.get("DATAFORSEO_LOGIN"))
    if not has_creds:
        return {}

    wt_seeds   = ["water softener", "reverse osmosis"]
    search_cities = metro_cities[:3]

    async def _search_wt(city: str, seed: str) -> list[str]:
        loc     = _build_location_name(f"{city}, {state_abbr}")
        keyword = f"{seed} {city}"
        try:
            result = await research_competitors(
                keyword=keyword,
                location_name=loc,
                maps_count=5,
                organic_count=6,
            )
            all_domains = result.get("all_domains", [])
            return [
                d for d in all_domains
                if not _is_excluded_domain(d) and d not in main_domains
            ]
        except Exception:
            return []

    pairs   = [(c, s) for c in search_cities for s in wt_seeds]
    results = await asyncio.gather(*[_search_wt(c, s) for c, s in pairs], return_exceptions=True)

    domain_cities: dict[str, list[str]] = {}
    for (city, _seed), domains in zip(pairs, results):
        if isinstance(domains, Exception):
            continue
        for domain in domains:
            if domain not in domain_cities:
                domain_cities[domain] = []
            if city not in domain_cities[domain]:
                domain_cities[domain].append(city)

    sorted_domains = sorted(
        domain_cities.keys(),
        key=lambda d: len(domain_cities[d]),
        reverse=True,
    )
    top = sorted_domains[:5]
    return {d: domain_cities[d] for d in top}


def _build_water_treatment_section(wt_profiles: list[dict]) -> str:
    """
    Gap 2: Render the WATER TREATMENT NICHE COMPETITORS subsection.
    These are the businesses competing for Steadfast's highest-margin water treatment jobs.
    """
    if not wt_profiles:
        return ""

    lines = [
        "### WATER TREATMENT NICHE COMPETITORS",
        "",
        "These businesses specifically target your highest-margin water treatment jobs.",
        "None have broad market dominance — this niche is wide open.",
        "",
        "| Competitor | Monthly Traffic | Focus | Cities |",
        "|-----------|----------------|-------|--------|",
    ]
    for p in wt_profiles[:5]:
        d          = p["domain"]
        traffic    = p.get("traffic", 0)
        cities_str = ", ".join(p.get("cities", [])[:2])
        traffic_str = _fmt_num(traffic) + "/mo" if traffic else "~low"
        lines.append(f"| {d} | {traffic_str} | Water Softeners / RO | {cities_str} |")

    lines += [
        "",
        "**Opportunity:** These competitors run thin sites with limited location pages.",
        "A dedicated water treatment content hub — one page per city, one page per system type —",
        "can own this niche across the East Valley with minimal competition.",
    ]
    return "\n".join(lines)


def _build_service_subsection_tables(volumes: list[dict], service: str) -> str:
    """
    Build service-specific keyword sub-tables.
    Plumbing → Water Heater | Water Treatment | Drain & Sewer | Emergency
    Electrician → Panel | EV Charging | Emergency
    etc.
    Mirrors the Steadfast PDF's separate tables for each service sub-category.
    """
    if not volumes:
        return ""

    service_type = _detect_service_type(service)

    subsection_rules: dict[str, list[tuple[str, list[str]]]] = {
        "plumbing": [
            ("Water Heater Keywords",      ["water heater", "tankless", "hot water"]),
            ("Water Treatment Keywords",   ["water softener", "softener", "reverse osmosis",
                                             "ro system", "filtration", "water treatment",
                                             "water purif", "ro filter"]),
            ("Drain & Sewer Keywords",     ["drain", "sewer", "clog", "rooter", "drain cleaning"]),
            ("Emergency Plumbing Keywords",["emergency", "urgent", "24 hour", "burst pipe"]),
        ],
        "electrician": [
            ("Panel & Service Upgrade Keywords", ["panel", "breaker", "200 amp", "service upgrade",
                                                   "electrical box"]),
            ("EV Charger Keywords",              ["ev charger", "electric vehicle", "charging station",
                                                   "level 2 charger"]),
            ("Emergency Electrical Keywords",    ["emergency", "urgent", "24 hour"]),
        ],
        "hvac": [
            ("AC Repair Keywords",     ["ac repair", "air conditioner repair", "cooling repair",
                                         "ac not cooling"]),
            ("Heating Keywords",       ["heating", "furnace", "heat pump", "boiler"]),
            ("Installation Keywords",  ["installation", "install", "replacement", "new unit"]),
        ],
        "roofing": [
            ("Storm & Emergency Keywords", ["emergency", "storm damage", "hail", "roof leak"]),
            ("Replacement Keywords",       ["replacement", "new roof", "reroof"]),
            ("Gutter Keywords",            ["gutter", "downspout"]),
        ],
        "auto_detailing": [
            ("Premium Service Keywords", ["ceramic coating", "paint correction", "ppf",
                                           "paint protection", "full detail"]),
            ("Mobile Detailing Keywords", ["mobile", "on-site", "come to you", "at your home"]),
        ],
    }

    rules = subsection_rules.get(service_type, [])
    if not rules:
        return ""

    sections = []
    used_keywords: set[str] = set()

    for section_name, triggers in rules:
        kws_in_section = [
            kw for kw in volumes
            if kw.get("keyword") not in used_keywords
            and any(t in kw.get("keyword", "").lower() for t in triggers)
            and (kw.get("search_volume") or 0) > 0
        ]
        if not kws_in_section:
            continue

        kws_sorted = sorted(kws_in_section, key=lambda x: x.get("search_volume") or 0, reverse=True)

        lines = [
            f"**{section_name}**",
            "",
            "| Keyword | Monthly Volume | CPC | Competition |",
            "|---------|---------------|-----|------------|",
        ]
        for kw in kws_sorted[:6]:
            keyword = kw.get("keyword", "")
            vol = _fmt_num(kw.get("search_volume"))
            cpc = _fmt_cpc(kw.get("cpc"))
            comp = kw.get("competition_level", "—")
            comp_str = comp.title() if comp and comp != "—" else "—"
            lines.append(f"| {keyword} | {vol} | {cpc} | {comp_str} |")
            used_keywords.add(keyword)

        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def _build_per_city_keyword_tables(
    volumes: list[dict],
    metro_cities: list[str],
    extra_cities: Optional[list] = None,
) -> str:
    """
    Per-city keyword breakdown — mirrors the Steadfast PDF's city sections.
    Gilbert | Mesa | Queen Creek | San Tan Valley each get their own table.
    Groups keywords that contain the city name, shows Volume + CPC.

    Gap 4 fix:
    - `extra_cities` are cities parsed from notes/strategy_context that may not
      appear in the DFS keyword results (low population → <10 searches/month).
    - For those cities, we render a "low competition" framing instead of silently
      skipping them — this is actually a stronger sales point.
    """
    if not metro_cities:
        return ""

    # Merge metro_cities + extra_cities, preserving order, deduping
    all_cities: list[str] = list(dict.fromkeys(
        metro_cities[:5] + (extra_cities or [])
    ))

    sections = []
    for city in all_cities:
        city_lower = city.lower()
        city_kws = [
            kw for kw in (volumes or [])
            if city_lower in kw.get("keyword", "").lower()
            and (kw.get("search_volume") or 0) > 0
        ]

        if not city_kws:
            # Only add a section for cities explicitly mentioned in client context
            if city in (extra_cities or []):
                sections.append(
                    f"**{city.upper()}**\n\n"
                    f"Search volume for keywords in {city} is below 10/month. "
                    f"Low population density means lower search demand but also near-zero competition. "
                    f"A single location page targeting this city can rank on page 1 with minimal effort — "
                    f"and it stays there because nobody else bothers to build one."
                )
            continue

        city_kws_sorted = sorted(city_kws, key=lambda x: x.get("search_volume") or 0, reverse=True)

        lines = [
            f"**{city.upper()}**",
            "",
            "| Keyword | Monthly Volume | CPC |",
            "|---------|---------------|-----|",
        ]
        for kw in city_kws_sorted[:6]:
            keyword = kw.get("keyword", "")
            vol = _fmt_num(kw.get("search_volume"))
            cpc = _fmt_cpc(kw.get("cpc"))
            lines.append(f"| {keyword} | {vol} | {cpc} |")

        sections.append("\n".join(lines))

    if not sections:
        return ""

    return "\n\n".join(sections)


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
        "| Close Rate | 40% | Good sales process |",
        f"| New Customers/Month | {con_jobs} | {con_leads} × 40% |",
        f"| Avg Job Value | {_fmt_dollar(job_val)} | Your stated average |",
        f"| **Monthly Revenue** | **{_fmt_dollar(con_revenue)}** | {con_jobs} × {_fmt_dollar(job_val)} |",
        f"| **Annual Revenue from SEO** | **{_fmt_dollar(con_annual)}** | Conservative estimate |",
    ])

    grow_table = "\n".join([
        "| Metric | Value | Calculation |",
        "|--------|-------|-------------|",
        f"| Organic Traffic Goal | {_fmt_num(grow_traffic)}/month | With 50+ keywords ranking page 1 |",
        "| Conversion Rate | 4% | Optimized website |",
        f"| Leads/Month | {grow_leads} | {_fmt_num(grow_traffic)} × 4% |",
        "| Close Rate | 40% | Consistent process |",
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

SYSTEM_PROMPT = """You are a senior SEO strategist at ProofPilot. You have run market analyses for hundreds of home service businesses and know exactly what the data means the moment you see it.

This document goes directly to a business owner. They will read it and decide whether to hire ProofPilot. Write like someone who has done this 500 times and has a clear opinion.

## Voice
First person plural: "we analyzed," "we found," "here's what we're seeing." Address the prospect as "you" and "your business." Direct. Specific. Have a point of view.

WRITE LIKE THIS:
"ezflowplumbingaz.com gets 3,124 free visits a month. They rank for water heater keywords worth $94K in ad value. You are not in that conversation yet. Here's how to change that."

NOT LIKE THIS:
"Based on our analysis, EZFlow appears to perform well across multiple keyword categories in the Chandler market area, suggesting significant search visibility."

## Section headers
Short. No colons. Use the template headers as given. Do not add your own.

## Callout boxes
Use this format for key insights, strategic observations, and math callouts. They render as branded dark-blue boxes in the exported document.

> **KEY INSIGHT**
> Sharp, specific observation. One or two sentences. Name the competitor or keyword.

> **WHY THIS MATTERS**
> - Specific point with a number
> - What it means for the prospect directly

> **STRATEGIC TAKEAWAY**
> What the prospect should do with this information. Not hedged. Direct.

## Writing bullets
No colon after the action label. State the action directly.

WRONG: "GBP optimization: Claim and optimize Google Business Profile across all service areas"
RIGHT: "Claim and fully build out the Google Business Profile for every service area. Add every city. Add photos weekly."

## Numbers
Use exact figures from the data. "$94,163/month" not "significant traffic value." "3,124 visits" not "thousands of visits." If a number tells the story, lead with it.

## Rules
- Start immediately with the # heading. Zero preamble.
- Fill every [bracketed instruction] with specific, data-driven content.
- Do not modify pre-built data tables. Reproduce them exactly.
- Every competitor section ends with a > callout box.
- No colons after bullet labels. No semicolons. No em dashes in body text. Periods only.
- No filler phrases: "it's worth noting," "this is a great opportunity," "essentially," "importantly."
- No passive voice."""


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _empty_list() -> list:
    return []


def _parse_sa_keywords(sa_response) -> list[dict]:
    """
    Parse a Search Atlas organic keywords API response into the standard
    top_kws dict format used by _build_market_leader_section et al.
    Handles the various shapes SA may return (dict with results/data/items key, or raw list).
    """
    if not sa_response or isinstance(sa_response, str):
        return []
    items: list = []
    if isinstance(sa_response, dict):
        for key in ("results", "data", "items", "keywords", "organic_keywords"):
            candidate = sa_response.get(key)
            if candidate and isinstance(candidate, list):
                items = candidate
                break
    elif isinstance(sa_response, list):
        items = sa_response

    out = []
    for item in items[:15]:
        if not isinstance(item, dict):
            continue
        keyword = item.get("keyword") or item.get("term") or item.get("query") or ""
        if not keyword:
            continue
        rank = item.get("position") or item.get("rank_position") or item.get("rank") or "—"
        volume = item.get("search_volume") or item.get("volume") or item.get("monthly_searches") or 0
        cpc_raw = item.get("cpc") or item.get("cost_per_click") or 0
        try:
            cpc = float(cpc_raw)
        except (TypeError, ValueError):
            cpc = 0.0
        traffic_raw = (
            item.get("traffic") or item.get("estimated_traffic")
            or item.get("traffic_estimate") or 0
        )
        try:
            traffic = int(traffic_raw)
        except (TypeError, ValueError):
            traffic = 0
        out.append({
            "keyword":          keyword,
            "rank":             rank,
            "traffic_estimate": traffic or None,
            "search_volume":    int(volume) if volume else 0,
            "cpc":              cpc,
        })
    return out


def _has_water_treatment_signals(notes: str, strategy_context: str) -> bool:
    """Return True when the prospect's notes/context mention water treatment services."""
    combined = (notes + " " + strategy_context).lower()
    return any(term in combined for term in [
        "water softener", "softener", "ro system", "reverse osmosis",
        "water treatment", "water filter", "filtration", "water purif",
    ])


def _extract_mentioned_cities(text: str, metro_cities: list[str]) -> list[str]:
    """
    Scan free-text (notes + strategy_context) for known metro city names
    that aren't already in the metro_cities list.
    Returns deduplicated list of extra cities found.
    """
    all_known: set[str] = set()
    for cities_list in _METRO_LOOKUP.values():
        all_known.update(c.lower() for c in cities_list)

    metro_lower = {c.lower() for c in metro_cities}
    mentioned: list[str] = []
    for city_lower in all_known:
        pattern = r'\b' + re.escape(city_lower) + r'\b'
        if re.search(pattern, text.lower()):
            if city_lower not in metro_lower:
                city_title = city_lower.title()
                if city_title not in mentioned:
                    mentioned.append(city_title)
    return mentioned


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

    # US-national location for DFS Labs domain overview + ranked keyword calls.
    # City-level and state-level are too granular for DFS Labs — these endpoints
    # return accurate domain-level traffic at country scope only.
    # SERP + keyword volume calls still use city-level location for local relevance.
    state_location_name = "United States"

    # Get nearby cities for metro-wide competitor search
    metro_cities = _get_metro_cities(city, state_abbr, n=5)

    # Gap 4: scan notes + strategy_context for city names not in the default metro list
    extra_cities = _extract_mentioned_cities(
        notes + " " + (strategy_context or ""), metro_cities
    )

    # Water treatment signal detection (used in Gap 2 and Gap 5)
    is_water_treatment = (
        _detect_service_type(service) == "plumbing"
        and _has_water_treatment_signals(notes, strategy_context or "")
    )

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
    # Use state-level location for DFS Labs calls — city-level is too granular
    # and returns empty traffic data for metro-wide competitors.
    competitor_profiles, prospect_rank, keyword_difficulty = await asyncio.gather(
        _profile_competitors(domain_city_map, state_location_name),
        _get_prospect_rank(domain, state_location_name),
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

    # Gap 2: second SERP pass for water treatment niche competitors
    wt_profiles: list[dict] = []
    if is_water_treatment:
        main_domains = set(d for d in (domain_city_map or {}).keys())
        main_domains.add(domain)
        try:
            wt_domain_map = await _discover_water_treatment_competitors(
                metro_cities, state_abbr, main_domains
            )
            if wt_domain_map:
                wt_profiles = await _profile_competitors(wt_domain_map, state_location_name)
                if isinstance(wt_profiles, Exception):
                    wt_profiles = []
        except Exception:
            wt_profiles = []

    yield "> Building analysis with real market data...\n\n"
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
    why_this_matters = _build_why_this_matters_box(high_value_kws, service)
    service_subsections = _build_service_subsection_tables(kw_vol_list, service)
    # Gap 4: pass extra_cities so Queen Creek / San Tan Valley etc. appear even with no DFS volume
    per_city_tables = _build_per_city_keyword_tables(kw_vol_list, metro_cities, extra_cities=extra_cities)
    priority_table = _build_priority_keyword_table(kw_vol_list, keyword_difficulty or [], service, city)

    # Gap 3: aggregate "what Google Ads would cost you" callout
    total_ads_cost_callout = _build_total_ads_cost_callout(total_searches, avg_cpc, high_value_kws)

    # Gap 2: water treatment niche competitors section
    water_treatment_section = _build_water_treatment_section(wt_profiles)

    # Gap 5: Meta bonus block (only for water treatment plumbers)
    meta_bonus_block = _build_meta_bonus_block(city, metro_cities) if is_water_treatment else ""

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

    # Gap 2: water treatment niche competitors block
    water_treatment_block = ""
    if water_treatment_section:
        water_treatment_block = f"\n{water_treatment_section}"

    # Gap 3: total ads cost callout block
    total_ads_cost_block = ""
    if total_ads_cost_callout:
        total_ads_cost_block = f"\n{total_ads_cost_callout}\n"

    pillar_section = ""
    if pillar_table:
        pillar_section = f"""### KEYWORD MARKET BREAKDOWN BY SERVICE TYPE

{pillar_table}"""

    high_value_section = ""
    if high_value_table:
        why_box = f"\n\n{why_this_matters}" if why_this_matters else ""
        high_value_section = f"""### HIGH-VALUE KEYWORD OPPORTUNITIES

These keywords have CPCs above $20 — every organic click saves you that amount vs. Google Ads.

{high_value_table}{why_box}"""

    _fallback_priority_row = (
        "| Priority | Keyword | Volume | CPC | Why |\n"
        "|--|--|--|--|--|\n"
        f"| 1 | {service} {city} | — | — | Core market keyword |"
    )
    priority_table_str = priority_table if priority_table else _fallback_priority_row

    # Build optional sub-sections for the template
    service_subsections_block = ""
    if service_subsections:
        service_subsections_block = f"### SERVICE-SPECIFIC KEYWORD BREAKDOWN\n\n{service_subsections}"

    per_city_block = ""
    if per_city_tables:
        per_city_block = f"### KEYWORDS BY CITY\n\n{per_city_tables}"

    template = f"""# SEO MARKET OPPORTUNITY & COMPETITIVE ANALYSIS

Real Data. Real Opportunity. Real ROI.

{company_info}

---

## WHAT THIS ANALYSIS REVEALS

{reveals_text}

[Write an executive summary of 3-4 punchy sentences. Open with the total search volume — "{total_searches_display} people search for {service} across {', '.join(metro_cities[:3])} every month." Name {leader_name} and their exact traffic. One sentence on where {client_name} stands right now. Close with what this document proves. No hedging. No "it appears." State it.]

**{total_searches_display}**
**MONTHLY METRO SEARCHES**
People searching for {service} across {', '.join(metro_cities[:3])} every month

{market_metrics_table}

---

## WHO'S WINNING YOUR MARKET

We searched across {len(metro_cities)} cities — {', '.join(metro_cities)} — and filtered out every directory, every aggregator, every national chain. What's left is the real competition. The businesses actually getting the calls.

[One sentence: name {leader_name} as the market leader and state their monthly traffic.]

{competitor_section}

{leader_full_section}

> **KEY INSIGHT**
> [Name {leader_name}. State exactly what they rank for and what that traffic is worth in ad dollars. One sharp sentence about what this means for {client_name} right now.]

{other_section}
{water_treatment_block}

---

## THE KEYWORD OPPORTUNITY

[Lead with the biggest number. "We analyzed {total_searches_display} monthly searches across {', '.join(metro_cities)}." Name the highest-volume pillar. Then name the highest-CPC opportunity. Two sentences total. No filler.]

{pillar_section}

{high_value_section}

> **STRATEGIC TAKEAWAY**
> [Pick one keyword from the high-value table. Show the math: volume x 10% CTR x CPC = monthly ad value. "Rank organically for this one keyword and you never write that check." One more sentence about what the full keyword set represents.]

---

## THE KEYWORDS WORTH CHASING

[One sentence naming the top 3 keywords by volume with exact numbers. One sentence about which ones to target first and why — be specific about the reason (low competition, high CPC, or both).]

### TOP KEYWORDS BY SEARCH VOLUME

[Build a markdown table from this data:
{top_kw_lines}

Use this format:
| Keyword | Volume | CPC | Competition |
|---------|--------|-----|------------|
(rows from data above, only keywords with volume > 0)]

{service_subsections_block}
{per_city_block}

---

## WHAT SEO CAN DELIVER

[One sentence with avg job value of {avg_job_value or "standard for this trade"}. One sentence framing what the numbers below assume — realistic traffic, real conversion rates, standard close rates for a well-run {service} business.]

**CONSERVATIVE SCENARIO (Month 6-12)**

{con_roi_table}

**GROWTH SCENARIO (Month 12-18)**

{grow_roi_table}

**WHAT YOU'D PAY GOOGLE ADS FOR THE SAME TRAFFIC**

{ads_comparison_table}

---

## THE MATH: SEO VS. GOOGLE ADS

| Factor | Google Ads | SEO |
|--------|-----------|-----|
| Cost per Click | {_fmt_cpc(max_cpc) if max_cpc else '$3-10'} per click | $0 once you rank |
| Traffic when budget runs out | Stops immediately | Keeps compounding |
| Click-Through Rate | 5-15% (labeled "Sponsored") | 30-40% at position 1 |
| Trust | Buyers skip sponsored results | Organic = earned authority |
| Long-term value | Renting visibility | Building an asset |
| Annual cost for 2,000 visitors | {_fmt_dollar(int(2000 * avg_cpc * 12)) if avg_cpc else "$30,000+"} | Included in monthly retainer |

[Write 2 sentences. Use the actual CPC numbers from this market. Make the math feel real — specific to {client_name}'s keywords, not generic.]
{total_ads_cost_block}

---

## THE PLAN

### PHASE 1: FOUNDATION (Months 1-3)

[Write 5 bullets. Each is one direct action — no colon after the action label. Specific to {service} in {city}. Cover: GBP optimization across all service areas, service page creation for core services, technical SEO fixes, tracking setup, NAP consistency. Write each bullet like a practitioner giving instructions, not a consultant making recommendations.]

**Paid + Organic Bridge:** SEO takes 3-6 months to show results. While rankings build, a targeted Google Ads campaign on your top 5 keywords (budget: $1,500-3,000/mo) captures leads immediately. As organic grows, ad spend comes down. By month 12: 70-80% organic, 20-30% paid for surge capacity.

### PHASE 2: CONTENT AND AUTHORITY (Months 3-8)

[Write 5 bullets. Direct actions. Cover: location pages for {', '.join(metro_cities[1:4] if len(metro_cities) > 1 else ['nearby cities'])}, educational content specific to the local climate and water quality, citation building, review velocity system, local link outreach. No hedging.]

### PHASE 3: DOMINATION (Months 8-12)

[Write 4 bullets. Cover: targeting {leader_name}'s specific keywords, expanding to all {len(metro_cities)} metro cities, scaling content output based on what ranked in Phase 2, owning the Map Pack across the metro. Write like you've done this before.]

---

## WHERE TO START

[One sentence: these are the keywords with the best combination of search volume, commercial intent, and ranking difficulty. One sentence about the specific opportunity — low-hanging fruit first, then the high-value targets.]

{priority_table_str}

---

## THE BOTTOM LINE

This is not theoretical. This is real data from real competitors in your market.

[Name {leader_name}. Exact traffic number. Then: "That traffic should be going to {client_name}. Here's what capturing it looks like."]

- [Specific outcome: rank page 1 for X keywords within Y months]
- [Specific outcome: generate Z new customers per month — use the conservative scenario math]
- [Specific outcome: dollar range — use the ROI table numbers]
- [Specific outcome: what happens to {leader_name}'s market share when {client_name} starts ranking]

The opportunity is real. The competitors are beatable. The only question is whether {client_name} moves now or watches another year of customers drive to {leader_name} instead.

ProofPilot is ready to execute.
{meta_bonus_block}"""

    # ── Phase 6: Stream Claude ─────────────────────────────────────────────
    user_prompt = f"""Write the complete SEO Market Analysis for **{client_name}** ({domain}).
They are a **{service}** business serving **{location}** and the surrounding metro: {', '.join(metro_cities)}.

Fill in every [bracketed instruction] with specific content based on the real data provided. Keep all pre-built tables exactly as shown. Every competitor section ends with a > callout box. Write like a strategist who has done this hundreds of times — direct, specific, no filler.

---

{template}

---

DATA CONTEXT (use this to inform all narrative and callout boxes):

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
