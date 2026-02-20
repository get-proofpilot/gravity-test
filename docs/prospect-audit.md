# Prospect SEO Market Analysis — Technical Documentation

**File:** `backend/workflows/prospect_audit.py`
**Workflow ID:** `prospect-audit`
**Current Version:** v4
**Last Updated:** February 2026

---

## What This Workflow Does

The Prospect Audit takes a potential client's domain, service type, and city, then produces a full SEO market opportunity report — the kind you'd hand to a prospect in a sales meeting to show them who's beating them and why they should hire you.

**Output document includes:**
- Company info + analysis date table
- Market metrics (total monthly searches, avg CPC, annual ad value)
- Full competitor overview table with market leader identified
- Deep dive on the market leader (their keywords, traffic, cities they dominate)
- Keyword pillar breakdown by service type
- High-value keywords (>$20 CPC) where organic beats ads on ROI
- Keyword opportunities ranked by volume
- ROI projections (conservative + growth scenarios)
- SEO vs. Google Ads comparison table
- 3-phase recommended strategy
- Priority keywords to target first (scored by traffic potential vs. difficulty)
- Conclusion built around the gap between prospect and market leader

---

## Architecture Overview

```
run_prospect_audit()
│
├── Phase 0 — Input parsing + metro lookup
│   └── _get_metro_cities() → 5 nearby cities
│
├── Phase 1 — Parallel data gather (asyncio.gather)
│   ├── _gather_sa_data(domain)          → Search Atlas organic/backlinks/pillar scores
│   ├── get_keyword_search_volumes()     → volumes + CPCs for 50 seeds across the metro
│   └── _discover_metro_competitors()   → top local domains across 5 cities
│
├── Phase 2 — Competitor profiling + prospect rank (asyncio.gather)
│   ├── _profile_competitors()          → traffic + top 15 keywords per competitor
│   ├── _get_prospect_rank()            → prospect's own DFS Labs overview
│   └── get_bulk_keyword_difficulty()  → difficulty scores for top 20 keywords
│
├── Phase 3 — Compute market metrics
│   └── totals, averages, market leader identification
│
├── Phase 4 — Build pre-rendered tables
│   ├── _build_competitor_overview_table()
│   ├── _build_market_leader_section()
│   ├── _build_other_competitors_section()
│   ├── _build_keyword_pillar_table()
│   ├── _build_high_value_keyword_table()
│   ├── _build_priority_keyword_table()
│   ├── _build_roi_table()
│   └── _build_ads_comparison_table()
│
├── Phase 5 — Assemble document template
│   └── f-string template with all tables pre-filled + bracketed instructions
│
└── Phase 6 — Stream Claude
    └── claude-opus-4-6 fills in narrative between pre-built tables
```

---

## Data Sources

### Search Atlas (Search Atlas MCP)
Used for **prospect's own site** — not competitors.

| Tool | Operation | Data Retrieved |
|------|-----------|---------------|
| `Site_Explorer_Organic_Tool` | `get_organic_keywords` | Top 20 keywords the prospect ranks for |
| `Site_Explorer_Organic_Tool` | `get_organic_competitors` | SA's view of competitor domains |
| `Site_Explorer_Backlinks_Tool` | `get_site_referring_domains` | Top 10 referring domains by DR |
| `Site_Explorer_Analysis_Tool` | `get_position_distribution` | Rankings bucketed by position range |
| `Site_Explorer_Holistic_Audit_Tool` | `get_holistic_seo_pillar_scores` | Technical/content/authority pillar scores |

All 5 SA calls run in parallel via `asyncio.gather()`. Failures are caught per-call and return `"Data unavailable: {error}"` — the rest of the workflow continues.

### DataForSEO (utils/dataforseo.py)

| Function | Endpoint | Purpose |
|----------|----------|---------|
| `research_competitors()` | `serp/google/maps/live/advanced` + `serp/google/organic/live/advanced` | SERP results per city to find competitor domains |
| `get_domain_rank_overview()` | `dataforseo_labs/google/domain_rank_overview/live` | Competitor's total keywords + monthly traffic + traffic value |
| `get_domain_ranked_keywords()` | `dataforseo_labs/google/ranked_keywords/live` | Competitor's top 15 keywords with position, volume, traffic estimate |
| `get_keyword_search_volumes()` | `keywords_data/google_ads/search_volume/live` | Volume, CPC, competition level for up to 50 seed keywords |
| `get_bulk_keyword_difficulty()` | `dataforseo_labs/google/bulk_keyword_difficulty/live` | Difficulty (0-100) for top 20 keywords |

**Note on unified organic + GBP data:** DFS Labs `ranked_keywords` returns all keywords a domain ranks for, including local pack (maps) positions when the business's GBP is linked to its website. No separate maps lookup is needed for competitor traffic profiling — it's all in one call.

---

## Key Functions Reference

### `_get_metro_cities(city, state_abbr, n=5)`
Returns nearby cities to search for competitors. Always puts the input city first.

```python
_get_metro_cities("Chandler", "AZ", n=5)
# → ["Chandler", "Mesa", "Tempe", "Gilbert", "Scottsdale"]
```

Falls back to `[city]` if the city isn't in `_METRO_LOOKUP`. Lookup is keyed by `(city.lower(), state_abbr.lower())`.

---

### `_discover_metro_competitors(service, metro_cities, state_abbr, state_full)`
The core SEO manager logic. Runs all city searches in parallel, then scores by coverage.

**Steps:**
1. For each metro city: search `"{service} {city}"` via `research_competitors()` (maps + organic combined)
2. Filter results through `_is_excluded_domain()` — removes directories, aggregators, national chains
3. Take top 4 local domains per city
4. Aggregate: count how many cities each domain appeared in
5. Sort by appearance count descending — domain appearing in 3/5 cities = metro dominant player
6. Return top 7 domains with their city lists

**Returns:** `dict[domain → list[cities_appeared_in]]`, sorted by dominance.

**Why this approach beats single-city:** A national chain like Cobblestone ranks in Google Maps for "car wash Chandler" but shows zero DFS Labs traffic for Chandler. A real mobile detailer operating across Phoenix metro appears in multiple city searches and has actual local search footprint.

---

### `_profile_competitors(domain_city_map, location_name)`
For each competitor domain, fetches overview + keywords in parallel.

**Data shape returned per competitor:**
```python
{
    "domain":   "example.com",
    "cities":   ["Chandler", "Mesa", "Tempe"],  # where they appeared
    "keywords": 847,                             # total keywords ranked
    "traffic":  3240,                            # estimated monthly visits
    "etv_cost": 12800,                           # traffic value in $ (what it'd cost in ads)
    "top_kws":  [
        {"keyword": "auto detailing chandler", "rank": 1, "search_volume": 480, "traffic_estimate": 192},
        ...
    ]
}
```

Sorted by `traffic` descending — index 0 is always the **market leader**.

---

### `_build_metro_seeds(service, metro_cities)`
Builds up to 50 keyword seeds across the metro for volume lookup.

**Seed categories:**
- Per-city: `"{service} {city}"`, `"mobile {service} {city}"`, `"best {service} {city}"`, `"car detailing {city}"`
- Near-me intent: `"{service} near me"`, `"best {service} near me"`, etc.
- Premium/specialty (city-specific to first metro city): ceramic coating, paint correction, PPF, interior, exterior, full detail, packages, prices

**Important:** The near-me and specialty seeds are currently hardcoded for auto detailing terminology (e.g., "car detailing", "ceramic coating", "paint correction"). **See [Extending: Keyword Seeds](#extending-keyword-seeds) to make these service-aware.**

---

### `_build_priority_keyword_table(volumes, difficulty, service, city)`
Scores and ranks keywords to find what to target first.

**Priority score formula:**
```
score = (search_volume × 0.1) + (cpc × 5) - ((difficulty or 50) × 0.5)
```

- Volume: 100 searches/mo = +10 score
- CPC: $10 CPC = +50 score (commercial value weighted heavily)
- Difficulty: score 60 = -30 penalty (harder = deprioritized)
- Missing difficulty defaults to 50 (neutral penalty)

**Why reasons get assigned:** Each top-10 keyword gets a "Why" label based on keyword content:
- Contains "emergency" → "Highest CPC — urgent buyers, premium value"
- Contains "near me" → "High purchase intent, proximity signal"
- Contains "ceramic" or "paint correction" → "Premium service — highest avg job value"
- Contains the city name → "Core market — rank in {city} first"
- Difficulty < 30 → "Low competition — quick ranking win"
- CPC > $10 → "High commercial value, strong buying intent"
- Else → "Consistent local search demand"

---

### `_build_roi_table(total_traffic_goal, avg_job_value_str, service)`
Calculates two revenue scenarios from the total keyword search volume.

**Conservative scenario** (uses 25% of total searches as traffic target, min 500):
- Conversion rate: 3%
- Lead-to-job close rate: 40%

**Growth scenario** (uses 100% of total searches, capped at 3,000):
- Conversion rate: 4%
- Lead-to-job close rate: 40%

Falls back to `$350` avg job value if none provided or unparseable.

---

## Metro Lookup System

### How It Works
`_METRO_LOOKUP` is a dict keyed by `(city_lower, state_abbr_lower)` tuples. Each entry is an ordered list of cities — the first city in the list is the "core" of that metro.

```python
("chandler", "az"): ["Chandler", "Mesa", "Tempe", "Gilbert", "Scottsdale", "Phoenix"]
```

`_get_metro_cities()` ensures the **prospect's input city always appears first** in the returned list, even if the lookup puts a different city first. This matters for keyword seeds — the prospect's actual city gets the per-city seed keywords.

### Current Coverage (62 cities, 30 metros)
Arizona, California (LA, OC, San Diego, Bay Area, Sacramento, Fresno), Texas (DFW, Houston, Austin, San Antonio), Florida (Miami, Orlando, Tampa, Jacksonville, Fort Lauderdale), Georgia, North Carolina, Colorado, Nevada, Washington, Oregon, Illinois, Ohio, Michigan, Pennsylvania, New York, New Jersey, Tennessee, Minnesota, Missouri, Wisconsin, Maryland/Virginia, Massachusetts, Connecticut, South Carolina, Alabama, Louisiana, Oklahoma, Kansas, Utah, New Mexico, Idaho.

### Adding a New Metro
Add an entry for every major city in the metro. Key rule: **list nearby cities in order of relevance** — a prospect in city X should see its closest service-area competitors, not cities 40 miles away.

```python
# Example: adding Tulsa, OK
("tulsa", "ok"):      ["Tulsa", "Broken Arrow", "Sand Springs", "Owasso", "Bixby", "Jenks"],
("broken arrow", "ok"): ["Broken Arrow", "Tulsa", "Owasso", "Sand Springs", "Jenks"],
```

**Fallback behavior:** If a city isn't in the lookup, the workflow still runs — it just searches that single city only. The output won't have metro-wide coverage but won't break.

---

## Competitor Filtering

### `_EXCLUDED_DOMAINS` Set
Hard-excluded by exact domain match:

| Category | Domains |
|----------|---------|
| General directories | yelp.com, yellowpages.com, angi.com, homeadvisor.com, thumbtack.com, bbb.org, reddit.com, houzz.com, bark.com, porch.com, manta.com, expertise.com, and others |
| Social / search | google.com, facebook.com, instagram.com, nextdoor.com |
| Auto/car wash chains | cobblestone.com, mister-car-wash.com, waterway.com, expresscarwash.com, autobell.com, goo-goo.com |
| Home service platforms | servicemaster.com, neighborly.com, handyman.com |
| Job boards | ziprecruiter.com, indeed.com, glassdoor.com |

### `_is_excluded_domain()` Pattern Match
In addition to exact matches, uses substring matching for domains that appear as subdomains or have URL paths:
`yelp.com`, `google.com`, `facebook.com`, `instagram.com`, `angi.com`, `thumbtack.com`, `homeadvisor.com`

### Adding to the Exclude List
**Add national chains specific to a service vertical** — the list is currently weighted toward auto detailing. For plumbing prospects, you'd want to add `rooter.com`, `roto-rooter.com`, etc. Add them to `_EXCLUDED_DOMAINS`:

```python
# Plumbing chains
"rotorooter.com", "roto-rooter.com", "mrrooter.com", "mr-rooter.com",
# HVAC chains
"one-hour-heating-air.com", "aireserv.com",
# Electrical chains
"mr-electric.com", "mister-sparky.com",
```

---

## Document Template Structure

The template is a pre-assembled f-string with two types of content:

**Pre-built tables (Claude must not change these):**
- Company info table
- Market metrics table
- Competitor overview table
- Market leader keywords table
- Other competitors keyword tables
- Keyword pillar table
- High-value keywords table
- Priority keywords table
- ROI tables (conservative + growth)
- Ads comparison table

**Bracketed instructions (Claude fills these in):**
- `[Write the conclusion exactly like the Steadfast reference: ...]`
- `[Write 4-5 sentences. State total monthly searches... ]`
- `[Build a markdown table from this data: ...]`
- Etc.

The system prompt explicitly tells Claude: **reproduce pre-built tables exactly as given** and fill in every `[bracketed instruction]`. This hybrid approach means the data-critical parts are deterministic (computed in Python, not generated by the model) while the narrative sections are left to Claude.

---

## Claude Configuration

```python
model    = "claude-opus-4-6"
max_tokens = 14000          # Long docs need headroom
thinking = {"type": "adaptive"}  # Opus 4.6 native — no budget_tokens
```

### System Prompt Design
The system prompt (`SYSTEM_PROMPT`) enforces ProofPilot's brand voice:
- Direct, confrontational, specific. Active voice. Short sentences.
- Address reader as "you" / "your business"
- Name competitors by domain/business name
- No em dashes, no semicolons
- Revenue framing: "clicks = calls = booked jobs"
- Frame everything as opportunity, not failure

The `user_prompt` passes:
1. The business context (client name, domain, service, location, metro cities)
2. The full pre-assembled template with real data tables already filled in
3. The `sa_context` block (prospect's current rankings, pillar scores, DFS overview, optional notes/strategy)

---

## Extending This Workflow

### Keyword Seeds
`_build_metro_seeds()` currently has hardcoded specialty seeds for auto detailing (ceramic coating, paint correction, etc.). To make it service-aware:

```python
_SERVICE_SPECIALTY_SEEDS = {
    "auto detailing": ["ceramic coating", "paint correction", "ppf", "interior detailing"],
    "plumber": ["water heater installation", "drain cleaning", "pipe repair", "leak detection"],
    "electrician": ["panel upgrade", "ev charger installation", "generator installation"],
    "hvac": ["ac repair", "furnace replacement", "hvac tune up", "heat pump installation"],
    "roofer": ["roof replacement", "roof repair", "gutter cleaning", "shingle replacement"],
}

# In _build_metro_seeds():
specialty_terms = _SERVICE_SPECIALTY_SEEDS.get(s, [f"best {s}", f"{s} cost", f"{s} prices"])
```

### Keyword Pillar Rules
`_build_keyword_pillar_table()` has pillar detection rules currently tuned for auto detailing. To extend:

```python
pillar_rules = [
    ("Emergency / Urgent",   ["emergency", "urgent", "24 hour", "same day", "24/7"]),
    ("Premium / Specialty",  ["ceramic", "paint correction", "ppf", ...]),
    ...
]
```

Add service-specific pillars or make this configurable per workflow input. For a plumber: `("Water Heater", ["water heater", "hot water"])`, `("Drain & Sewer", ["drain", "sewer", "clog"])`.

### Adding Review Intelligence (Future)
The `_profile_competitors()` function already has city data per competitor. A natural extension is pulling competitor Google reviews via DataForSEO `business_data/google/reviews/live` — this gives sentiment themes you can use to identify their weaknesses (e.g., "always late" appearing in their reviews becomes a selling point for the prospect).

### Adding GBP Profile Depth (Future)
`get_competitor_gmb_profiles()` exists in `utils/dataforseo.py` but isn't used in v4. It returns GBP details: review count, rating, photos count, services listed, hours. Incorporating this would let the analysis say "The market leader has 847 reviews and 200+ photos. You have 12 reviews. Here's what that means."

### Adding Seasonality (Future)
DataForSEO `trends/google_trends/explore` can show search volume seasonality by metro. For service businesses this matters — auto detailing peaks in spring/summer, HVAC peaks in July and January. A seasonality section would show the prospect when to launch campaigns.

---

## Output Document Example Structure

```
# SEO MARKET OPPORTUNITY & COMPETITIVE ANALYSIS
Real Data. Real Opportunity. Real ROI.

[Company info table]

## WHAT THIS ANALYSIS REVEALS
[Auto-generated bullet points from real data]
[Executive summary narrative — Claude]

[Market metrics table]

## COMPETITOR ANALYSIS: WHO'S WINNING YOUR METRO
[Narrative — Claude]
[Competitor overview table — pre-built]
### THE MARKET LEADER: TOPCOMPETITOR.COM
[Leader stats + top 10 keyword table — pre-built]
### OTHER COMPETITORS IN YOUR MARKET
[Competitors 2-5 with keyword tables — pre-built]

## KEYWORD PILLAR ANALYSIS
[Narrative — Claude]
[Pillar table — pre-built]
[High-value keywords table — pre-built, if any keywords > $20 CPC]

## SERVICE-SPECIFIC KEYWORD OPPORTUNITIES
[Narrative — Claude]
[Keyword volume table — Claude fills from data]

## ROI PROJECTIONS
[Narrative — Claude]
[Conservative ROI table — pre-built]
[Growth ROI table — pre-built]
[Ads comparison table — pre-built]

## WHY SEO BEATS GOOGLE ADS FOR [CLIENT]
[SEO vs Ads table — Claude fills from real CPC data]
[Narrative — Claude]

## RECOMMENDED SEO STRATEGY
### PHASE 1: FOUNDATION (Months 1-3)
[5 bullet points — Claude, specific to service + city]
### PHASE 2: CONTENT & AUTHORITY (Months 3-8)
[5 bullet points — Claude, includes metro cities]
### PHASE 3: DOMINATION (Months 8-12+)
[5 bullet points — Claude]

## PRIORITY KEYWORDS TO TARGET FIRST
[Narrative — Claude]
[Priority keyword table — pre-built, scored by Python]

## CONCLUSION: THE PATH FORWARD
[Full conclusion — Claude, using real traffic numbers + client name]
```

---

## Deployment Notes

**Railway deployment:**
```bash
cd ~/Documents/Gravity-Test/backend
railway up --detach
```

**Dockerfile cache buster:** The comment in `COPY . .` line is bumped on each deploy that needs a fresh build:
```dockerfile
# Copy application code — v14 (...)
COPY . .
```

**Env vars required:**
- `ANTHROPIC_API_KEY` — Claude Opus 4.6
- `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` — all competitor data calls
- `SEARCHATLAS_API_KEY` — prospect's own site data

If `DATAFORSEO_LOGIN` is missing, `_discover_metro_competitors()` returns `{}` (empty dict) and the workflow still runs — it just won't have competitor data.

---

## Known Limitations

| Issue | Impact | Fix |
|-------|--------|-----|
| Specialty keyword seeds are auto detailing-specific | Seeds for plumbers/electricians/HVAC are less accurate | Add `_SERVICE_SPECIALTY_SEEDS` dict keyed by service |
| Metros not in `_METRO_LOOKUP` get single-city search only | Less accurate competitor picture for smaller markets | Add metro entries or build a fallback using Google Trends geographic data |
| DFS Labs data sometimes thin for small local businesses | Competitor traffic shows "—" if domain has low organic footprint | Expected behavior — GBP-only businesses don't rank organically, which is a selling point |
| `research_competitors()` uses LIVE SERP | ~$0.004/call × 5 cities per run = ~$0.02/prospect audit | Consider Standard queue for non-realtime at 66% discount if cost becomes an issue |
| `client_name` in the template currently refers to the prospect's business name | The conclusion section personalizes to client_name correctly | Works as designed — client_name = prospect's business, not the agency client |
| No caching between runs | Same domain + city + service costs full API fees every run | Add Redis or SQLite job caching keyed by hash of inputs |

---

## Version History

| Version | Key Changes |
|---------|-------------|
| v1 | Initial build — single-city competitor search, basic tables |
| v2 | Added Search Atlas data gather, pillar table, priority scoring |
| v3 | Fixed sort comparison bug on keyword scoring tuples |
| v4 | Metro-wide competitor search across 5 cities, chain/directory filtering, market leader section, `_METRO_LOOKUP` with 62 cities, `asyncio.coroutine` fix, f-string backslash fix, `client_name` personalization in conclusion |
