"""
Website & SEO Audit Workflow
Pulls live data from two sources in parallel, then feeds everything to Claude Opus
for a comprehensive branded audit report.

Data sources:
  Search Atlas  — organic keywords, pages, competitors, backlinks, position distribution
  DataForSEO    — top 5 Google Maps competitors + top 5 organic SERP competitors
                  (gracefully skipped if DATAFORSEO_LOGIN/PASSWORD not configured)

For each DataForSEO competitor, we also pull a Search Atlas profile (keywords + backlinks)
to enable a side-by-side comparison in the report.

inputs keys:
    domain      e.g. "allthingzelectric.com"
    service     e.g. "electrician"  — used as the Google search keyword
    location    e.g. "Chandler, AZ" — converted to DataForSEO location_name format
    notes       optional — specific focus areas, context for the agent
"""

import os
import asyncio
import re
import anthropic
from typing import AsyncGenerator

from utils.searchatlas import sa_call
from utils.dataforseo import (
    research_competitors,
    get_competitor_sa_profiles,
    format_full_competitor_section,
    get_domain_ranked_keywords,
    format_domain_ranked_keywords,
)
from utils.localfalcon import gather_full_lf_data, format_full_lf_context


# ── State abbreviation → full name (for DataForSEO location_name) ────────────

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


def _build_location_name(location_raw: str) -> str:
    """
    Convert user input like "Chandler, AZ" or "chandler az" to
    DataForSEO format: "Chandler,Arizona,United States"
    Falls back to the raw input if parsing fails.
    """
    parts = re.split(r"[,\s]+", location_raw.strip())
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) >= 2:
        city = " ".join(parts[:-1]).title()
        state_input = parts[-1].upper()
        state_full = _STATE_MAP.get(state_input, state_input.title())
        return f"{city},{state_full},United States"

    return location_raw.strip()


# ── Search Atlas data gathering ───────────────────────────────────────────────

async def _gather_sa_data(domain: str) -> dict[str, str]:
    """Fetch all Search Atlas data for the client domain concurrently."""

    async def safe_call(tool: str, op: str, params: dict, label: str) -> tuple[str, str]:
        try:
            result = await sa_call(tool, op, params)
            return label, result
        except Exception as e:
            return label, f"Data unavailable: {e}"

    tasks = [
        safe_call(
            "Site_Explorer_Organic_Tool", "get_organic_keywords",
            {"project_identifier": domain, "page_size": 30, "ordering": "-traffic"},
            "organic_keywords",
        ),
        safe_call(
            "Site_Explorer_Organic_Tool", "get_organic_pages",
            {"project_identifier": domain, "page_size": 15, "ordering": "-traffic"},
            "organic_pages",
        ),
        safe_call(
            "Site_Explorer_Organic_Tool", "get_organic_competitors",
            {"project_identifier": domain, "page_size": 8},
            "sa_competitors",
        ),
        safe_call(
            "Site_Explorer_Backlinks_Tool", "get_site_referring_domains",
            {"project_identifier": domain, "page_size": 20, "ordering": "-domain_rating"},
            "referring_domains",
        ),
        safe_call(
            "Site_Explorer_Backlinks_Tool", "get_site_backlinks",
            {"project_identifier": domain, "page_size": 10, "ordering": "-page_ascore"},
            "top_backlinks",
        ),
        safe_call(
            "Site_Explorer_Analysis_Tool", "get_position_distribution",
            {"identifier": domain},
            "position_distribution",
        ),
        safe_call(
            "Site_Explorer_Holistic_Audit_Tool", "get_holistic_seo_pillar_scores",
            {"domain": domain},
            "pillar_scores",
        ),
    ]

    results = await asyncio.gather(*tasks)
    return dict(results)


# ── DataForSEO competitor research ───────────────────────────────────────────

async def _gather_competitor_data(
    service: str,
    location_name: str,
) -> dict | None:
    """
    Run Google Maps + organic SERP search for the service/location.
    Returns None if DataForSEO isn't configured.
    """
    dfs_login = os.environ.get("DATAFORSEO_LOGIN", "")
    dfs_pass = os.environ.get("DATAFORSEO_PASSWORD", "")
    if not dfs_login or not dfs_pass:
        return None  # Graceful skip — DataForSEO not configured

    try:
        keyword = f"{service} {location_name.split(',')[0]}"  # e.g. "electrician Chandler"
        competitors = await research_competitors(
            keyword=keyword,
            location_name=location_name,
            maps_count=5,
            organic_count=5,
        )

        # Pull Search Atlas profiles for top competitor domains
        top_domains = competitors.get("all_domains", [])[:5]
        sa_profiles = await get_competitor_sa_profiles(top_domains) if top_domains else []
        competitors["sa_profiles"] = sa_profiles

        return competitors

    except Exception as e:
        return {"error": str(e), "maps": [], "organic": [], "sa_profiles": [], "all_domains": []}


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior SEO strategist at ProofPilot, a results-driven digital marketing agency.

Your job is to write clear, direct, actionable SEO audit reports for real business clients. These reports go directly to agency owners who need to understand what's happening and what to do — not consultants who want theory.

## Report principles
- Lead with what matters most: what's working, what's broken, biggest opportunities
- Be specific — use the actual numbers, domains, keywords, pages, and competitor names from the data
- Every finding must connect to a concrete business implication (rankings → leads → revenue)
- The competitor section is critical — name the competitors explicitly, show the gap, make it feel urgent
- Prioritize by impact — a focused top-5 beats a sprawling list of 20
- Write like a strategist, not a tool — synthesize the data, don't just restate it
- Flag genuine wins alongside problems — clients need both

## Tone
- Direct and confident
- No hedging, no passive voice
- No filler phrases like "it's important to note" or "in conclusion"
- Treat the client like a business owner who understands their market
- Make the competitor comparisons feel real and specific — not generic

## Format (strict markdown)
- # H1 — audit title
- ## H2 — section headers
- ### H3 — sub-sections or specific findings
- **bold** for key metrics, domain names, competitor names, priority actions
- Bullet lists for findings within sections
- Use --- for section dividers
- No tables (keep it clean for .docx conversion)

Do NOT write any preamble or meta-commentary. Start the report immediately with the H1 title."""


# ── Main workflow ─────────────────────────────────────────────────────────────

async def run_website_seo_audit(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Yields tokens forming a complete SEO audit report.

    inputs keys:
        domain    — e.g. "allthingzelectric.com"
        service   — e.g. "electrician"
        location  — e.g. "Chandler, AZ"
        notes     — optional focus areas
    """
    domain = inputs.get("domain", "").strip().lower()
    if not domain:
        yield "Error: No domain provided."
        return

    service  = inputs.get("service", "").strip()
    location = inputs.get("location", "").strip()
    notes    = inputs.get("notes", "").strip()

    location_name = _build_location_name(location) if location else ""
    search_keyword = f"{service} {location.split(',')[0].strip()}" if service and location else service

    # ── Phase 1: Status ────────────────────────────────────────────────────
    yield f"> Pulling Search Atlas data for **{domain}**...\n\n"
    if service and location:
        yield f"> Searching Google for **\"{search_keyword}\"** competitors...\n\n"
    if location_name and os.environ.get("DATAFORSEO_LOGIN"):
        yield f"> Fetching ranked keywords for **{domain}** from DataForSEO Labs...\n\n"
    if os.environ.get("LOCALFALCON_API_KEY"):
        yield f"> Pulling Local Falcon rank tracking data...\n\n"

    # ── Phase 2: Gather all data in parallel ──────────────────────────────
    async def _no_competitor_data():
        return None

    async def _gather_ranked_keywords():
        if not os.environ.get("DATAFORSEO_LOGIN") or not os.environ.get("DATAFORSEO_PASSWORD"):
            return []
        if not location_name:
            return []
        try:
            return await get_domain_ranked_keywords(domain, location_name, limit=20)
        except Exception:
            return []

    sa_task      = _gather_sa_data(domain)
    dfs_task     = _gather_competitor_data(service, location_name) if (service and location_name) else _no_competitor_data()
    ranked_task  = _gather_ranked_keywords()
    lf_task      = gather_full_lf_data(limit_scans=3)

    sa_data, competitor_data, ranked_keywords, lf_data = await asyncio.gather(
        sa_task, dfs_task, ranked_task, lf_task
    )

    yield f"> Data collected — generating audit with Claude Opus...\n\n"
    yield "---\n\n"

    # ── Phase 3: Build context document ───────────────────────────────────
    today = __import__("datetime").date.today().isoformat()

    context_sections = [
        f"## Client: {client_name}",
        f"## Domain: {domain}",
        f"## Primary Service: {service or 'Not specified'}",
        f"## Service Area: {location or 'Not specified'}",
        f"## Audit Date: {today}",
        "",
        "---",
        "",
        "## ORGANIC KEYWORDS DATA (Search Atlas)",
        sa_data["organic_keywords"],
        "",
        "## TOP PERFORMING PAGES (Search Atlas)",
        sa_data["organic_pages"],
        "",
        "## ORGANIC COMPETITOR OVERLAP (Search Atlas)",
        sa_data["sa_competitors"],
        "",
        "## REFERRING DOMAINS — BACKLINK PROFILE (Search Atlas)",
        sa_data["referring_domains"],
        "",
        "## TOP BACKLINKS (Search Atlas)",
        sa_data["top_backlinks"],
    ]

    # Optional SA sections
    pos_dist = sa_data.get("position_distribution", "")
    if pos_dist and "Data unavailable" not in pos_dist and "No position distribution" not in pos_dist:
        context_sections += ["", "## POSITION DISTRIBUTION", pos_dist]

    pillar = sa_data.get("pillar_scores", "")
    if pillar and "Data unavailable" not in pillar and "No holistic" not in pillar:
        context_sections += ["", "## SEO PILLAR SCORES", pillar]

    # DataForSEO Labs — domain ranked keywords (cross-reference to SA organic data)
    if ranked_keywords:
        context_sections += [
            "",
            "## DOMAIN RANKED KEYWORDS (DataForSEO Labs)",
            format_domain_ranked_keywords(ranked_keywords),
        ]

    # DataForSEO competitor section
    if competitor_data and not competitor_data.get("error"):
        maps_results    = competitor_data.get("maps", [])
        organic_results = competitor_data.get("organic", [])
        sa_profiles     = competitor_data.get("sa_profiles", [])

        competitor_section = format_full_competitor_section(
            keyword=search_keyword,
            maps=maps_results,
            organic=organic_results,
            sa_profiles=sa_profiles,
        )
        context_sections += ["", "---", "", competitor_section]

    elif competitor_data and competitor_data.get("error"):
        context_sections += [
            "", "## COMPETITOR RESEARCH",
            f"Competitor SERP lookup failed: {competitor_data['error']}",
        ]
    else:
        context_sections += [
            "", "## COMPETITOR RESEARCH",
            "DataForSEO not configured — competitor SERP data not available for this audit.",
        ]

    # Local Falcon — GBP rank tracking, competitors, trends
    lf_context = format_full_lf_context(lf_data) if lf_data else ""
    if lf_context:
        context_sections += [
            "", "---", "",
            "## LOCAL RANK TRACKING (Local Falcon — Google Business Profile)",
            lf_context,
        ]

    context_doc = "\n".join(context_sections)

    # ── Phase 4: Build Claude prompt ──────────────────────────────────────
    has_competitor_data = bool(
        competitor_data and not competitor_data.get("error") and
        (competitor_data.get("maps") or competitor_data.get("organic"))
    )
    has_lf_data = bool(lf_context)

    prompt_lines = [
        f"Write a comprehensive Website & SEO Audit report for **{client_name}** ({domain}).",
        f"Their primary service is **{service}** and they serve **{location}**.",
        "",
        "Here is the live data pulled from Search Atlas and Google:",
        "",
        context_doc,
    ]

    if notes:
        prompt_lines += ["", "**Additional context from the agency:**", notes]

    if strategy_context and strategy_context.strip():
        prompt_lines += [
            "", "**Strategic direction — factor this into recommendations:**",
            strategy_context.strip(),
        ]

    # Report structure
    report_sections = [
        "1. Executive Summary (3-4 sentences — current health + single biggest opportunity)",
        "2. Organic Search Performance (keyword rankings, traffic, position distribution)",
        "3. Top Performing Pages (which pages drive traffic and why — specific URLs)",
    ]

    if has_competitor_data:
        report_sections += [
            "4. Competitor Landscape — Google Maps + Organic (name competitors explicitly, show "
            "exactly what they're doing that this client isn't — reviews, rankings, page count, "
            "backlinks. Make it concrete and urgent.)",
            "5. Keyword Gap Analysis (specific keywords competitors rank for that this client "
            "doesn't — flag the revenue impact)",
        ]
    else:
        report_sections += [
            "4. Competitive Landscape (who they compete with based on Search Atlas overlap data)",
            "5. Keyword Gap Analysis (keywords they should be targeting based on their market)",
        ]

    if has_lf_data:
        report_sections.append(
            "6. Local Rank Visibility (Local Falcon grid data — where the business ranks "
            "across the service area, ARP/SoLV trends, geographic strengths and weaknesses, "
            "and how local competitors compare in the Google Maps pack)"
        )
        report_sections.append("7. Backlink Profile (authority score, referring domains, quality assessment)")
        report_sections += [
            "8. Priority Recommendations (top 5-7 actions ranked by revenue impact — each with "
            "a specific, actionable next step)",
            "9. 90-Day Action Plan (Month 1 / Month 2 / Month 3 phased roadmap)",
        ]
    else:
        report_sections += [
            "6. Backlink Profile (authority score, referring domains, quality assessment)",
            "7. Priority Recommendations (top 5-7 actions ranked by revenue impact — each with "
            "a specific, actionable next step)",
            "8. 90-Day Action Plan (Month 1 / Month 2 / Month 3 phased roadmap)",
        ]

    prompt_lines += [
        "",
        "Write the full audit report now. Structure it as:",
        *[f"   {s}" for s in report_sections],
        "",
        "Be specific — use the actual keywords, domains, competitor names, and numbers from "
        "the data. Start immediately with the H1 title.",
    ]

    user_prompt = "\n".join(prompt_lines)

    # ── Phase 5: Stream Claude's analysis ────────────────────────────────
    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
