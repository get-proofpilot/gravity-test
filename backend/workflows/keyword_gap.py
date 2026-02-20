"""
Keyword Gap Analysis Workflow
Identifies keywords that a client's top competitors rank for but the client doesn't.

This is the #1 most actionable SEO deliverable — it shows exactly what keywords to
go after, clustered by topic and sorted by revenue opportunity.

Data sources:
  DataForSEO Labs  — ranked keywords per domain (client + competitors)
  DataForSEO SERP  — top competitor discovery (if none provided)
  DataForSEO Keywords Data — search volume + CPC for gap keywords

inputs keys:
    domain              e.g. "allthingzelectric.com"
    service             e.g. "electrician"
    location            e.g. "Chandler, AZ"
    competitor_domains  optional comma-separated competitors to compare against
    notes               optional context about target markets, recent campaigns
"""

import os
import asyncio
import re
import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    research_competitors,
    get_domain_ranked_keywords,
    get_keyword_search_volumes,
    build_service_keyword_seeds,
    format_keyword_volumes,
)


# ── State abbreviation → full name ────────────────────────────────────────────

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
    parts = re.split(r"[,\s]+", location_raw.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        city = " ".join(parts[:-1]).title()
        state_input = parts[-1].upper()
        state_full = _STATE_MAP.get(state_input, state_input.title())
        return f"{city},{state_full},United States"
    return location_raw.strip()


# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior Keyword Gap Analyst at ProofPilot, a results-driven digital marketing agency.

Your job is to write a Keyword Gap Analysis that shows a client exactly which keywords their competitors are winning and how to attack those gaps. This is an ACTION document — every section should point toward revenue.

## Core objectives
- Show the exact size of the keyword gap in plain numbers (keywords missed, total search volume missed)
- Translate search volume into realistic revenue estimates (clicks → calls → revenue)
- Group gap keywords into logical topic clusters so the client knows which service pages to build first
- Separate quick wins (lower competition, achievable in 30-60 days) from longer-term plays
- End with a specific 90-day attack plan that tells them exactly what to create and optimize

## Tone
- Confident and direct — you've done this analysis and you know what the data says
- Revenue-focused — everything translates to calls, leads, and dollars
- Specific — real keyword names, real competitor domains, real volume numbers
- No fluff — every sentence earns its place
- Business advisor voice, not agency jargon

## Format (strict markdown)
- # H1 — report title
- ## H2 — section headers
- ### H3 — sub-sections and clusters
- **bold** for key metrics, keyword targets, competitor names, dollar figures, action items
- Bullet lists for findings and keyword lists
- Use --- for section dividers
- No tables (clean for .docx conversion)

Do NOT write any preamble or meta-commentary. Start the report immediately with the H1 title."""


# ── Data gathering helpers ─────────────────────────────────────────────────────

async def _get_ranked_keywords_safe(domain: str, location_name: str, limit: int = 100) -> list[dict]:
    """Fetch ranked keywords for a domain, returning empty list on failure."""
    try:
        return await get_domain_ranked_keywords(domain, location_name, limit=limit)
    except Exception:
        return []


async def _discover_competitors(service: str, location: str, location_name: str) -> list[str]:
    """Find top competitor domains via SERP research."""
    try:
        city = location.split(",")[0].strip()
        keyword = f"{service} {city}"
        result = await research_competitors(
            keyword=keyword,
            location_name=location_name,
            maps_count=5,
            organic_count=5,
        )
        return result.get("all_domains", [])[:5]
    except Exception:
        return []


def _compute_keyword_gap(
    client_keywords: list[dict],
    competitor_keyword_sets: list[tuple[str, list[dict]]],
) -> list[dict]:
    """
    Find keywords that at least one competitor ranks for but the client doesn't.

    Args:
        client_keywords:        List of keyword dicts the client ranks for.
        competitor_keyword_sets: List of (domain, keywords_list) tuples.

    Returns:
        List of gap keyword dicts sorted by search_volume desc.
        Each dict: keyword, search_volume, traffic_estimate, top_competitor, rank_at_competitor
    """
    # Build a set of keywords the client already ranks for (lowercase, stripped)
    client_kw_set: set[str] = {
        kw["keyword"].lower().strip()
        for kw in client_keywords
        if kw.get("keyword")
    }

    # Collect competitor keywords not in client set
    # Use a dict so we keep the highest-volume entry per keyword
    gap: dict[str, dict] = {}

    for domain, kw_list in competitor_keyword_sets:
        for kw in kw_list:
            term = (kw.get("keyword") or "").lower().strip()
            if not term or term in client_kw_set:
                continue
            vol = kw.get("search_volume") or 0
            existing = gap.get(term)
            if existing is None or vol > (existing.get("search_volume") or 0):
                gap[term] = {
                    "keyword":           term,
                    "search_volume":     vol,
                    "traffic_estimate":  kw.get("traffic_estimate") or 0,
                    "top_competitor":    domain,
                    "rank_at_competitor": kw.get("rank"),
                }

    # Sort by search volume descending
    return sorted(gap.values(), key=lambda x: x.get("search_volume") or 0, reverse=True)


def _format_client_keywords(data: list[dict]) -> str:
    """Format client ranked keywords for Claude prompt."""
    if not data:
        return "No ranked keyword data found for this domain."
    lines = [f"Client Currently Ranks For ({len(data)} keywords pulled):\n"]
    for kw in data[:30]:
        rank = kw.get("rank", "?")
        vol = kw.get("search_volume") or 0
        lines.append(f"  #{rank}: \"{kw['keyword']}\" — {vol:,}/mo")
    if len(data) > 30:
        lines.append(f"  ... and {len(data) - 30} more")
    return "\n".join(lines)


def _format_competitor_keywords(domain: str, data: list[dict]) -> str:
    """Format a competitor's ranked keywords for Claude prompt."""
    if not data:
        return f"{domain}: No ranked keyword data available."
    lines = [f"{domain} — Ranking for {len(data)} keywords:\n"]
    for kw in data[:20]:
        rank = kw.get("rank", "?")
        vol = kw.get("search_volume") or 0
        lines.append(f"  #{rank}: \"{kw['keyword']}\" — {vol:,}/mo")
    if len(data) > 20:
        lines.append(f"  ... and {len(data) - 20} more")
    return "\n".join(lines)


def _format_gap_keywords(gap_keywords: list[dict]) -> str:
    """Format gap keyword list for Claude prompt."""
    if not gap_keywords:
        return "No keyword gap data computed."

    total_vol = sum(kw.get("search_volume") or 0 for kw in gap_keywords)
    lines = [
        f"KEYWORD GAP — {len(gap_keywords)} keywords competitors rank for that client doesn't",
        f"Total missed monthly search volume: {total_vol:,}\n",
    ]
    for kw in gap_keywords[:50]:
        vol = kw.get("search_volume") or 0
        competitor = kw.get("top_competitor", "unknown")
        rank = kw.get("rank_at_competitor", "?")
        lines.append(
            f"  \"{kw['keyword']}\" — {vol:,}/mo  [competitor: {competitor} ranks #{rank}]"
        )
    if len(gap_keywords) > 50:
        lines.append(f"  ... and {len(gap_keywords) - 50} more gap keywords")
    return "\n".join(lines)


# ── Main workflow ──────────────────────────────────────────────────────────────

async def run_keyword_gap(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Yields tokens forming a complete Keyword Gap Analysis.

    inputs keys:
        domain              — client's website domain
        service             — primary service type (e.g. "electrician")
        location            — city, state (e.g. "Chandler, AZ")
        competitor_domains  — optional comma-separated competitor domains
        notes               — optional context
    """
    domain = inputs.get("domain", "").strip().lower()
    if not domain:
        yield "Error: No domain provided."
        return

    # Check DataForSEO credentials early — this workflow depends entirely on DFS Labs
    dfs_login = os.environ.get("DATAFORSEO_LOGIN", "")
    dfs_pass  = os.environ.get("DATAFORSEO_PASSWORD", "")
    if not dfs_login or not dfs_pass:
        yield (
            "> DataForSEO credentials (DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD) are not "
            "configured on the server. The Keyword Gap workflow requires DataForSEO Labs "
            "access to pull ranked keywords per domain. Please add these environment "
            "variables and retry.\n\n"
        )
        return

    service            = inputs.get("service", "").strip()
    location           = inputs.get("location", "").strip()
    competitor_domains_raw = inputs.get("competitor_domains", "").strip()
    notes              = inputs.get("notes", "").strip()

    location_name = _build_location_name(location) if location else "United States"
    city = location.split(",")[0].strip() if location else ""

    # ── Phase 1: Status messages ────────────────────────────────────────────
    yield f"> Pulling ranked keywords for **{domain}**...\n\n"

    # ── Phase 2: Gather client keywords + competitor discovery in parallel ──

    async def _get_competitor_domains() -> list[str]:
        """Return parsed competitor domains from input, or auto-discover via SERP."""
        if competitor_domains_raw:
            raw_list = [d.strip().lower().replace("www.", "") for d in competitor_domains_raw.split(",")]
            return [d for d in raw_list if d][:5]
        if service and location:
            return await _discover_competitors(service, location, location_name)
        return []

    # Kick off client ranked keywords immediately
    client_kw_task = _get_ranked_keywords_safe(domain, location_name, limit=100)

    # Also start competitor domain resolution in parallel
    competitor_domain_coro = _get_competitor_domains()

    client_keywords, competitor_domains = await asyncio.gather(
        client_kw_task,
        competitor_domain_coro,
        return_exceptions=True,
    )

    if isinstance(client_keywords, Exception):
        client_keywords = []
    if isinstance(competitor_domains, Exception):
        competitor_domains = []

    # If auto-discovered, let the user know
    if not competitor_domains_raw and competitor_domains:
        yield f"> Auto-detected competitors: **{', '.join(competitor_domains[:3])}**{' and more' if len(competitor_domains) > 3 else ''}...\n\n"
    elif not competitor_domains:
        yield "> No competitors found — attempting keyword gap with seed keywords only...\n\n"

    # ── Phase 3: Get ranked keywords for top 3 competitors in parallel ──────
    top_competitors = competitor_domains[:3]

    if top_competitors:
        yield f"> Analyzing keyword rankings for top {len(top_competitors)} competitors...\n\n"

    competitor_kw_tasks = [
        _get_ranked_keywords_safe(comp_domain, location_name, limit=100)
        for comp_domain in top_competitors
    ]

    # Also queue keyword volume lookup for seed keywords (runs alongside competitor fetches)
    async def _get_seed_volumes() -> list[dict]:
        if not service or not city:
            return []
        try:
            seeds = build_service_keyword_seeds(service, city, count=10)
            return await get_keyword_search_volumes(seeds, location_name)
        except Exception:
            return []

    competitor_kw_results_raw, seed_volumes = await asyncio.gather(
        asyncio.gather(*competitor_kw_tasks, return_exceptions=True),
        _get_seed_volumes(),
        return_exceptions=True,
    )

    # Normalise competitor results
    if isinstance(competitor_kw_results_raw, Exception) or competitor_kw_results_raw is None:
        competitor_kw_results_raw = [[] for _ in top_competitors]
    if isinstance(seed_volumes, Exception):
        seed_volumes = []

    competitor_keyword_sets: list[tuple[str, list[dict]]] = []
    for domain_name, result in zip(top_competitors, competitor_kw_results_raw):
        kw_list = result if not isinstance(result, Exception) else []
        competitor_keyword_sets.append((domain_name, kw_list))

    # ── Phase 4: Compute the gap ─────────────────────────────────────────────
    gap_keywords = _compute_keyword_gap(client_keywords, competitor_keyword_sets)

    # ── Phase 5: Get volume data for top 20 gap keywords ─────────────────────
    top_gap_kws_for_volume = [kw["keyword"] for kw in gap_keywords[:20]]
    gap_volumes: list[dict] = []

    if top_gap_kws_for_volume:
        try:
            gap_volumes = await get_keyword_search_volumes(top_gap_kws_for_volume, location_name)
        except Exception:
            gap_volumes = []

    yield "> Gap analysis complete — generating report with Claude Opus...\n\n"
    yield "---\n\n"

    # ── Phase 6: Build context document for Claude ────────────────────────────
    today = __import__("datetime").date.today().isoformat()

    context_sections = [
        f"## Client: {client_name}",
        f"## Domain: {domain}",
        f"## Primary Service: {service or 'Not specified'}",
        f"## Service Area: {location or 'Not specified'}",
        f"## Analysis Date: {today}",
        "",
        "---",
        "",
    ]

    # Client keyword profile
    context_sections += [
        "## CLIENT KEYWORD PROFILE",
        _format_client_keywords(client_keywords),
        "",
    ]

    # Competitor keyword profiles
    if competitor_keyword_sets:
        context_sections.append("## COMPETITOR KEYWORD PROFILES")
        for comp_domain, comp_kws in competitor_keyword_sets:
            context_sections += [
                _format_competitor_keywords(comp_domain, comp_kws),
                "",
            ]
    else:
        context_sections += [
            "## COMPETITOR KEYWORD PROFILES",
            "No competitor data available — no competitor domains found or provided.",
            "",
        ]

    # Gap analysis
    context_sections += [
        "## KEYWORD GAP ANALYSIS",
        _format_gap_keywords(gap_keywords),
        "",
    ]

    # Volume data for gap keywords
    if gap_volumes:
        context_sections += [
            "## SEARCH VOLUME DATA FOR TOP GAP KEYWORDS (Google Ads)",
            format_keyword_volumes(gap_volumes),
            "",
        ]

    # Seed keyword volumes (market baseline)
    if seed_volumes:
        context_sections += [
            "## MARKET BASELINE — SEED KEYWORD VOLUMES",
            format_keyword_volumes(seed_volumes),
            "",
        ]

    context_doc = "\n".join(context_sections)

    # ── Phase 7: Build Claude prompt ─────────────────────────────────────────
    total_gap_volume = sum(kw.get("search_volume") or 0 for kw in gap_keywords)

    prompt_lines = [
        f"Write a Keyword Gap Analysis for **{client_name}** ({domain}).",
        f"They are a **{service}** serving **{location}**.",
        "",
        f"The analysis found **{len(gap_keywords)} gap keywords** — terms their competitors rank for "
        f"that they don't. Total missed monthly search volume: **{total_gap_volume:,}**.",
        "",
        "Here is the full data collected:",
        "",
        context_doc,
    ]

    if notes:
        prompt_lines += ["", "**Additional context from the ProofPilot team:**", notes]

    if strategy_context and strategy_context.strip():
        prompt_lines += [
            "", "**Agency strategy direction:**",
            strategy_context.strip(),
        ]

    report_sections = [
        "1. Executive Summary — size of the gap in plain numbers: total gap keywords, "
        "total missed monthly search volume, estimated monthly revenue being left on the table "
        "(use realistic local conversion rates: ~2-4% of searchers call, use an estimated job "
        "value for the service type if none provided)",

        "2. Competitor Ranking Profile — for each competitor domain, what are they winning at? "
        "What service categories do they dominate? What does their keyword footprint tell you "
        "about their SEO strategy? Keep each profile focused and specific.",

        "3. Priority Gap Keywords — cluster the gap keywords into logical topic groups "
        "(e.g. 'Emergency Services', 'Residential Repair', 'Commercial Work', 'Specific Equipment', "
        "'Location-Specific Terms'). For each cluster: list the top keywords with volume, "
        "estimated monthly value, and why this cluster matters.",

        "4. Quick Wins — identify 5-10 specific keywords where the client has the best chance "
        "to rank within 30-60 days. Criteria: moderate volume, not dominated by national brands, "
        "likely covered by an existing or easily-created page.",

        "5. Content Opportunities — keywords in the gap that suggest blog posts, FAQ pages, "
        "or service sub-pages the client doesn't have yet. Name the exact page/article to create "
        "and the primary keyword it should target.",

        "6. 90-Day Attack Plan — specific and actionable:\n"
        "   - Month 1: Existing pages to optimize (which pages, which keywords to add)\n"
        "   - Month 2: New service pages to create (exact page titles and target keywords)\n"
        "   - Month 3: Content pieces to publish + internal linking targets\n"
        "   Frame each action as a concrete task, not a vague recommendation.",
    ]

    prompt_lines += [
        "",
        "Write the full Keyword Gap Analysis now. Structure it as:",
        *[f"   {s}" for s in report_sections],
        "",
        "Use the actual keyword names, competitor domains, and volume numbers from the data above. "
        "Every recommendation should be specific and actionable. "
        "Start immediately with the H1 title.",
    ]

    user_prompt = "\n".join(prompt_lines)

    # ── Phase 8: Stream Claude's analysis ────────────────────────────────────
    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
