"""
SEO Research Agent — the strategic brain that tells you WHAT to write.
Pulls every available data source in parallel, clusters keywords by intent,
identifies content gaps, and produces a prioritized content roadmap.

This is the workflow you run BEFORE using the programmatic agent — it tells
you which location pages, service pages, blog posts, comparison posts,
and cost guides to create, in what order, for maximum revenue impact.

Data sources:
  DataForSEO Labs     — ranked keywords, domain overview, competitor domains, keyword difficulty
  DataForSEO SERP     — AI overviews, featured snippets, local pack, organic
  DataForSEO Keywords — search volumes, CPC, competition
  DataForSEO Backlinks — summary for domain authority context
  DataForSEO Trends   — seasonality and trending keywords
  Search Atlas        — organic keywords, backlinks (if available)

inputs keys:
    domain      e.g. "allthingzelectric.com"
    service     e.g. "electrician"
    location    e.g. "Chandler, AZ"
    competitors optional — comma-separated competitor domains
    notes       optional — specific focus areas, business goals
"""

import asyncio
import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    get_domain_ranked_keywords,
    get_domain_rank_overview,
    get_keyword_search_volumes,
    get_bulk_keyword_difficulty,
    get_backlink_summary,
    get_ai_search_landscape,
    get_keyword_trends,
    research_competitors,
    build_location_name,
    build_service_keyword_seeds,
    format_domain_ranked_keywords,
    format_keyword_volumes,
    format_keyword_difficulty,
    format_backlink_summary,
    format_ai_search_landscape,
    format_keyword_trends,
    format_full_competitor_section,
)


SYSTEM_PROMPT = """You are ProofPilot's SEO Research Strategist — the most thorough SEO research brain in the industry. You analyze data like a $200K/year SEO consultant and produce actionable content strategies that generate revenue.

You produce the **SEO Content Strategy & Research Report** — a complete roadmap that tells a home service business exactly what content to create, in what order, to maximize organic traffic and leads.

## Report Structure

### 1. Executive Summary
- Current organic visibility score (based on data)
- Total addressable search volume in their market
- Estimated revenue opportunity from organic search
- Top 3 strategic priorities

### 2. Current Rankings Assessment
- Keywords they currently rank for (from DFS Labs data)
- Ranking distribution: page 1 vs 2 vs 3+
- Traffic value of current rankings
- Quick wins: keywords on page 2 that could reach page 1

### 3. Keyword Universe & Clustering
Cluster ALL discovered keywords into intent groups:

**Commercial Intent (ready to buy):**
- "[service] [city]", "best [service] near me", "emergency [service]"
- Priority: HIGHEST — these convert to calls/bookings

**Cost/Price Intent (researching price):**
- "how much does [service] cost", "[service] price [city]"
- Priority: HIGH — these convert with transparent pricing content

**Comparison Intent (evaluating options):**
- "[brand A] vs [brand B]", "best [product] for [use case]"
- Priority: HIGH — captures decision-stage traffic

**Informational Intent (learning):**
- "signs you need [service]", "how to [related topic]"
- Priority: MEDIUM — builds authority, captures top-of-funnel

**Local Intent (finding nearby):**
- "[service] in [city]", "[service] near [neighborhood]"
- Priority: HIGHEST — location pages for each target city

### 4. Content Gap Analysis
- Keywords competitors rank for that the client doesn't
- Content types competitors have that the client lacks
- SERP features competitors own (AI Overviews, featured snippets, PAA)
- Specific pages to create to close each gap

### 5. AI Search Opportunity Analysis
- Which keywords trigger AI Overviews
- Who gets cited in AI Overviews (client vs competitors)
- Content format patterns that earn AI citations
- Featured snippet opportunities to target

### 6. Trend & Seasonality Intelligence
- Keywords trending up (capitalize now)
- Keywords trending down (deprioritize)
- Seasonal patterns to plan content around
- Emerging queries to target before competitors

### 7. Prioritized Content Roadmap
The money section. Specific pages to create, ordered by revenue impact:

**Immediate (Week 1-2):**
| Content Type | Title/Topic | Target Keyword | Monthly Volume | Difficulty | Est. Traffic Value |
|---|---|---|---|---|---|

**Short-term (Month 1):**
| Same format |

**Medium-term (Month 2-3):**
| Same format |

For EACH recommended piece of content, specify:
- Content type: location page, service page, blog post, comparison post, cost guide, or best-in-city
- Exact target keyword
- Search volume + difficulty
- Why this page matters (traffic, conversions, authority)
- Key angle/hook that differentiates from existing SERP results

### 8. Technical Quick Wins
- Pages to optimize (already ranking, need improvements)
- Internal linking recommendations
- Schema markup opportunities
- Meta tag improvements for existing pages

## Style Guidelines
- Every recommendation grounded in real data — cite volumes, positions, difficulty scores
- Prioritize by revenue impact, not just traffic volume (a 50/mo "emergency electrician" keyword converts 10x better than a 5,000/mo informational keyword)
- Be specific: "Create a service page targeting 'panel upgrade chandler az' (210/mo, KD 38)" not "Create service pages"
- Think like an agency strategist presenting to a $6,200/mo client — justify every recommendation with data and expected ROI"""


async def run_seo_research_agent(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams the SEO Content Strategy & Research Report.

    inputs keys: domain, service, location, competitors, notes
    """
    domain = inputs.get("domain", "").strip()
    service = inputs.get("service", "").strip()
    location = inputs.get("location", "").strip()
    competitor_str = inputs.get("competitors", "").strip()
    notes = inputs.get("notes", "").strip()

    if not domain or not service or not location:
        yield "**Error:** Domain, service, and location are all required.\n"
        return

    yield f"> Starting **SEO Research Agent** for **{client_name}** ({domain})...\n\n"

    location_name = build_location_name(location)
    city = location.split(",")[0].strip()

    # Parse competitors
    competitors = []
    if competitor_str:
        competitors = [d.strip() for d in competitor_str.replace("\n", ",").split(",") if d.strip()]

    # Build comprehensive keyword seeds
    commercial_seeds = build_service_keyword_seeds(service, city, 10)
    informational_seeds = [
        f"how much does {service} cost {city}",
        f"best {service} in {city}",
        f"when to hire a {service}",
        f"signs you need {service}",
        f"{service} vs diy",
        f"how to choose a {service} {city}",
        f"emergency {service} {city}",
        f"{service} reviews {city}",
    ]
    all_seeds = commercial_seeds + informational_seeds

    yield "> Phase 1: Pulling domain rankings + competitor landscape...\n\n"

    # Phase 1: Domain intelligence + competitor discovery
    phase1_tasks = [
        get_domain_ranked_keywords(domain, location_name, 30),
        get_domain_rank_overview(domain, location_name),
        get_backlink_summary(domain),
        research_competitors(f"{service} {city}", location_name, 5, 5),
    ]

    # Also get competitor domain overviews
    for comp in competitors[:3]:
        phase1_tasks.append(get_domain_rank_overview(comp, location_name))

    phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=True)

    ranked_kws = phase1_results[0] if not isinstance(phase1_results[0], Exception) else []
    domain_overview = phase1_results[1] if not isinstance(phase1_results[1], Exception) else {}
    backlink_summary = phase1_results[2] if not isinstance(phase1_results[2], Exception) else {}
    serp_competitors = phase1_results[3] if not isinstance(phase1_results[3], Exception) else {}

    comp_overviews = []
    for i, comp in enumerate(competitors[:3]):
        idx = 4 + i
        if idx < len(phase1_results) and not isinstance(phase1_results[idx], Exception):
            comp_overviews.append(phase1_results[idx])

    yield "> Phase 2: Keyword volumes, difficulty, AI overview analysis, trends...\n\n"

    # Phase 2: Keyword intelligence
    phase2_tasks = [
        get_keyword_search_volumes(all_seeds, location_name),
        get_bulk_keyword_difficulty(all_seeds, location_name),
        get_ai_search_landscape(all_seeds[:8], location_name),
        get_keyword_trends(commercial_seeds[:5], location_name),
    ]

    # Get competitor ranked keywords for gap analysis
    for comp in competitors[:2]:
        phase2_tasks.append(get_domain_ranked_keywords(comp, location_name, 20))

    phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)

    volumes = phase2_results[0] if not isinstance(phase2_results[0], Exception) else []
    difficulty = phase2_results[1] if not isinstance(phase2_results[1], Exception) else []
    ai_landscape = phase2_results[2] if not isinstance(phase2_results[2], Exception) else []
    trends = phase2_results[3] if not isinstance(phase2_results[3], Exception) else []

    comp_keywords = []
    for i in range(len(competitors[:2])):
        idx = 4 + i
        if idx < len(phase2_results) and not isinstance(phase2_results[idx], Exception):
            comp_keywords.append({
                "domain": competitors[i],
                "keywords": phase2_results[idx],
            })

    yield "> Data collection complete — generating strategy report with Claude Opus...\n\n"
    yield "---\n\n"

    # Build comprehensive data context
    data_sections = [
        f"## CLIENT INFO\nDomain: {domain}\nService: {service}\nLocation: {location}\nClient: {client_name}\n",
    ]

    # Domain overview
    if domain_overview:
        data_sections.append(
            f"## DOMAIN OVERVIEW — {domain}\n"
            f"Keywords ranked: {domain_overview.get('keywords', 0):,}\n"
            f"Est. monthly traffic: {domain_overview.get('etv', 0):,.0f}\n"
            f"Traffic value: ${domain_overview.get('etv_cost', 0):,.0f}/mo"
        )

    # Current ranked keywords
    if ranked_kws:
        data_sections.append(format_domain_ranked_keywords(ranked_kws))

    # Backlink context
    if backlink_summary:
        data_sections.append(format_backlink_summary(backlink_summary))

    # SERP competitor landscape
    if serp_competitors:
        data_sections.append(
            format_full_competitor_section(
                f"{service} {city}",
                serp_competitors.get("maps", []),
                serp_competitors.get("organic", []),
            )
        )

    # Keyword volumes
    if volumes:
        data_sections.append(format_keyword_volumes(volumes))

    # Keyword difficulty
    if difficulty:
        data_sections.append(format_keyword_difficulty(difficulty))

    # AI search landscape
    if ai_landscape:
        data_sections.append(format_ai_search_landscape(ai_landscape, domain))

    # Trends
    if trends:
        data_sections.append(format_keyword_trends(trends))

    # Competitor ranked keywords (for gap analysis)
    if comp_keywords:
        for ck in comp_keywords:
            data_sections.append(
                f"## COMPETITOR KEYWORDS — {ck['domain']}\n" +
                format_domain_ranked_keywords(ck["keywords"])
            )

    # Competitor domain overviews
    if comp_overviews:
        comp_section = "## COMPETITOR DOMAIN OVERVIEWS\n"
        for co in comp_overviews:
            comp_section += (
                f"  {co.get('domain', '?')}: "
                f"{co.get('keywords', 0):,} keywords, "
                f"~{co.get('etv', 0):,.0f} traffic, "
                f"${co.get('etv_cost', 0):,.0f}/mo value\n"
            )
        data_sections.append(comp_section)

    if notes:
        data_sections.append(f"\n## ADDITIONAL CONTEXT\n{notes}")

    if strategy_context and strategy_context.strip():
        data_sections.append(f"\n## STRATEGY DIRECTION\n{strategy_context.strip()}")

    user_prompt = (
        f"Generate a comprehensive SEO Content Strategy & Research Report for {client_name} "
        f"({domain}), a {service} business serving {location}.\n\n"
        f"Use ALL of the following research data to produce your analysis and recommendations. "
        f"Every recommendation must be grounded in real data — cite specific volumes, difficulty "
        f"scores, and competitor positions.\n\n"
        + "\n\n".join(data_sections)
        + "\n\nWrite the complete strategy report now. Start with the title and executive summary. "
        "Your content roadmap should include specific recommendations for location pages, "
        "service pages, blog posts, comparison posts, cost guides, and best-in-city posts."
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
