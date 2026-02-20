"""
Competitor Intelligence Agent — deep competitive analysis for SEO strategy.
Pulls ranked keywords, backlink profiles, and SERP positions for the target
domain and up to 3 competitors, then analyzes gaps and opportunities.

Data sources:
  DataForSEO Labs      — ranked keywords per domain, domain rank overview, competitor discovery
  DataForSEO SERP      — organic + Maps results for key queries
  DataForSEO Backlinks — backlink summary per domain
  DataForSEO Keywords  — search volumes for discovered gap keywords

inputs keys:
    domain      e.g. "allthingzelectric.com"
    competitors comma-separated competitor domains (or auto-discovered from SERP)
    service     e.g. "electrician"
    location    e.g. "Chandler, AZ"
    notes       optional — specific focus areas
"""

import asyncio
import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    get_domain_ranked_keywords,
    get_domain_rank_overview,
    get_backlink_summary,
    get_backlink_competitors,
    research_competitors,
    get_keyword_search_volumes,
    get_ai_search_landscape,
    build_location_name,
    build_service_keyword_seeds,
    format_domain_ranked_keywords,
    format_backlink_summary,
    format_backlink_competitors,
    format_keyword_volumes,
    format_full_competitor_section,
    format_ai_search_landscape,
)


SYSTEM_PROMPT = """You are ProofPilot's Competitive Intelligence Analyst — an expert at dissecting competitor SEO strategies and finding exploitable gaps for local service businesses.

You produce the **Competitor Intelligence Report** — a detailed teardown of how competitors are winning organic search, what content/links they have that the client doesn't, and a specific action plan to close every gap.

## Report Structure

### 1. Executive Summary
- Client vs competitor traffic comparison (one line each)
- #1 competitive gap (the biggest missed opportunity)
- #1 competitive advantage (where the client already wins)
- Overall competitive position: "Outranked", "Competitive", or "Dominant"

### 2. Domain Authority Comparison
Side-by-side comparison:
| Metric | Client | Competitor 1 | Competitor 2 | Competitor 3 |
|---|---|---|---|---|
| Keywords Ranked | X | Y | Z | ... |
| Est. Monthly Traffic | X | Y | Z | ... |
| Traffic Value | $X | $Y | $Z | ... |
| Backlinks | X | Y | Z | ... |
| Referring Domains | X | Y | Z | ... |

Analysis of what these numbers mean and where the gaps are.

### 3. Keyword Gap Analysis
**Keywords competitors rank for that the client DOESN'T:**
For each gap keyword:
- The keyword
- Which competitor(s) rank for it
- Search volume
- Difficulty score (if available)
- Recommended content type to capture it
- Priority (high/medium/low based on volume x intent)

Group by intent:
- Commercial gaps (most valuable — ready to buy)
- Informational gaps (authority building)
- Local gaps (city-specific)

### 4. Content Gap Analysis
- Content types competitors have: service pages, location pages, blog posts, cost guides, comparison posts
- Specific pages competitors have that the client lacks
- Content quality comparison: word count, structure, freshness
- Internal linking patterns

### 5. Backlink Gap Analysis
- Domains linking to competitors but NOT the client
- Link acquisition strategies competitors are using
- Highest-value link sources to replicate
- Local link opportunities the client is missing

### 6. SERP Feature Ownership
- Who owns featured snippets for key queries
- Who appears in AI Overviews
- Who dominates the local pack
- Who has knowledge panels

### 7. Competitor Weaknesses to Exploit
Specific vulnerabilities:
- Thin or outdated content on competitor sites
- Missing service pages or location pages
- Low review counts or ratings
- No HTTPS, slow sites, poor mobile experience
- Keywords they rank weakly for (positions 5-20)

### 8. Action Plan: Competitive Domination Strategy
Priority-ranked actions with timeline:

**Quick Wins (This Week):**
- Specific actions to take immediately

**Month 1:**
- Content to create to close the biggest gaps

**Month 2-3:**
- Link building + content expansion

**Ongoing:**
- Monitoring and maintenance actions

## Style Guidelines
- Use exact numbers: "Competitor ranks #3 for 'electrician chandler az' (210/mo) — you rank #0"
- Compare side-by-side whenever possible
- Be strategic: don't just list gaps, explain which ones matter most for revenue
- Think like a hired gun: which moves will hurt competitors most while building the client fastest
- Reference specific competitor domains/businesses by name"""


async def run_competitor_intel(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams the Competitor Intelligence Report.

    inputs keys: domain, competitors, service, location, notes
    """
    domain = inputs.get("domain", "").strip()
    competitor_str = inputs.get("competitors", "").strip()
    service = inputs.get("service", "").strip()
    location = inputs.get("location", "").strip()
    notes = inputs.get("notes", "").strip()

    if not domain:
        yield "**Error:** Domain is required.\n"
        return

    yield f"> Starting **Competitor Intelligence Agent** for **{client_name}** ({domain})...\n\n"

    location_name = build_location_name(location) if location else "United States"
    city = location.split(",")[0].strip() if location else ""

    # Parse competitor domains
    competitors = []
    if competitor_str:
        competitors = [d.strip() for d in competitor_str.replace("\n", ",").split(",") if d.strip()]

    yield "> Phase 1: Discovering competitors + pulling domain data...\n\n"

    # Phase 1: Discover competitors if not provided, and get baseline data
    phase1_tasks = [
        get_domain_ranked_keywords(domain, location_name, 30),
        get_domain_rank_overview(domain, location_name),
        get_backlink_summary(domain),
    ]

    # Discover competitors from SERP if service + location provided
    if service and city:
        phase1_tasks.append(research_competitors(f"{service} {city}", location_name, 5, 5))

    # Get backlink competitors (domains competing for same link sources)
    phase1_tasks.append(get_backlink_competitors(domain, 10))

    phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=True)

    client_keywords = phase1_results[0] if not isinstance(phase1_results[0], Exception) else []
    client_overview = phase1_results[1] if not isinstance(phase1_results[1], Exception) else {}
    client_backlinks = phase1_results[2] if not isinstance(phase1_results[2], Exception) else {}

    serp_competitors = {}
    bl_competitors = []
    offset = 3
    if service and city:
        serp_competitors = phase1_results[offset] if not isinstance(phase1_results[offset], Exception) else {}
        offset += 1
    bl_competitors = phase1_results[offset] if not isinstance(phase1_results[offset], Exception) else []

    # Auto-discover competitors from SERP if none provided
    if not competitors and serp_competitors:
        discovered = serp_competitors.get("all_domains", [])
        competitors = [d for d in discovered if d.lower() != domain.lower()][:3]
        if competitors:
            yield f"> Auto-discovered competitors from SERP: {', '.join(competitors)}\n\n"

    yield f"> Analyzing {len(competitors)} competitor(s): {', '.join(competitors) if competitors else 'none found'}...\n\n"

    # Phase 2: Pull data for each competitor
    phase2_tasks = []
    for comp in competitors[:3]:
        phase2_tasks.append(get_domain_ranked_keywords(comp, location_name, 30))
        phase2_tasks.append(get_domain_rank_overview(comp, location_name))
        phase2_tasks.append(get_backlink_summary(comp))

    # Also get keyword volumes for gap keywords and AI landscape
    gap_keywords = build_service_keyword_seeds(service, city, 10) if service and city else []
    if gap_keywords:
        phase2_tasks.append(get_keyword_search_volumes(gap_keywords, location_name))
        phase2_tasks.append(get_ai_search_landscape(gap_keywords[:6], location_name))

    phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)

    # Unpack competitor data
    comp_data = []
    for i, comp in enumerate(competitors[:3]):
        base_idx = i * 3
        kws = phase2_results[base_idx] if not isinstance(phase2_results[base_idx], Exception) else []
        overview = phase2_results[base_idx + 1] if not isinstance(phase2_results[base_idx + 1], Exception) else {}
        bl = phase2_results[base_idx + 2] if not isinstance(phase2_results[base_idx + 2], Exception) else {}
        comp_data.append({
            "domain": comp,
            "keywords": kws,
            "overview": overview,
            "backlinks": bl,
        })

    gap_volumes = []
    ai_landscape = []
    extra_start = len(competitors[:3]) * 3
    if gap_keywords and extra_start < len(phase2_results):
        gap_volumes = phase2_results[extra_start] if not isinstance(phase2_results[extra_start], Exception) else []
        if extra_start + 1 < len(phase2_results):
            ai_landscape = phase2_results[extra_start + 1] if not isinstance(phase2_results[extra_start + 1], Exception) else []

    yield "> Data collection complete — generating Competitor Intelligence Report with Claude Opus...\n\n"
    yield "---\n\n"

    # Build data context
    data_sections = [
        f"## CLIENT DOMAIN — {domain}\nClient: {client_name}\nService: {service}\nLocation: {location}\n",
    ]

    # Client overview
    if client_overview:
        data_sections.append(
            f"Client Domain Overview:\n"
            f"  Keywords ranked: {client_overview.get('keywords', 0):,}\n"
            f"  Est. monthly traffic: {client_overview.get('etv', 0):,.0f}\n"
            f"  Traffic value: ${client_overview.get('etv_cost', 0):,.0f}/mo"
        )

    if client_keywords:
        data_sections.append("Client " + format_domain_ranked_keywords(client_keywords))

    if client_backlinks:
        data_sections.append("Client " + format_backlink_summary(client_backlinks))

    # SERP landscape
    if serp_competitors:
        data_sections.append(
            format_full_competitor_section(
                f"{service} {city}",
                serp_competitors.get("maps", []),
                serp_competitors.get("organic", []),
            )
        )

    # Each competitor
    for cd in comp_data:
        comp_section = f"\n## COMPETITOR — {cd['domain']}\n"
        if cd["overview"]:
            comp_section += (
                f"  Keywords ranked: {cd['overview'].get('keywords', 0):,}\n"
                f"  Est. monthly traffic: {cd['overview'].get('etv', 0):,.0f}\n"
                f"  Traffic value: ${cd['overview'].get('etv_cost', 0):,.0f}/mo\n"
            )
        if cd["backlinks"]:
            comp_section += format_backlink_summary(cd["backlinks"]) + "\n"
        if cd["keywords"]:
            comp_section += format_domain_ranked_keywords(cd["keywords"])
        data_sections.append(comp_section)

    # Backlink competitors
    if bl_competitors:
        data_sections.append(format_backlink_competitors(bl_competitors))

    # Gap keyword volumes
    if gap_volumes:
        data_sections.append("## MARKET KEYWORD VOLUMES\n" + format_keyword_volumes(gap_volumes))

    # AI landscape
    if ai_landscape:
        data_sections.append(format_ai_search_landscape(ai_landscape, domain))

    if notes:
        data_sections.append(f"\n## ADDITIONAL CONTEXT\n{notes}")

    if strategy_context and strategy_context.strip():
        data_sections.append(f"\n## STRATEGY DIRECTION\n{strategy_context.strip()}")

    user_prompt = (
        f"Generate a comprehensive Competitor Intelligence Report for {client_name} "
        f"({domain}), a {service} business serving {location}.\n\n"
        f"Competitors analyzed: {', '.join(c['domain'] for c in comp_data) if comp_data else 'auto-discovered from SERP'}\n\n"
        f"Use ALL of the following research data. Compare the client directly against "
        f"each competitor. Identify every gap and opportunity. Be ruthlessly specific.\n\n"
        + "\n\n".join(data_sections)
        + "\n\nWrite the complete competitor intelligence report now. Start with the title and executive summary."
    )

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=12000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
