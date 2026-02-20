"""
Backlink Audit Workflow
Pulls comprehensive backlink data from DataForSEO — summary stats, top referring
domains, anchor text distribution, and backlink competitors — then feeds everything
to Claude Opus for a detailed backlink health report with prioritized actions.

Data sources:
  DataForSEO Backlinks API — summary, referring domains, anchors
  DataForSEO Labs          — competitor domains (domains competing for same links)
  DataForSEO Labs          — domain rank overview for context

inputs keys:
    domain      e.g. "allthingzelectric.com"
    service     e.g. "electrician" — gives Claude context for relevance analysis
    location    e.g. "Chandler, AZ"
    competitors optional — comma-separated competitor domains for comparison
    notes       optional — specific focus areas
"""

import asyncio
import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    get_full_backlink_profile,
    format_full_backlink_profile,
    get_domain_rank_overview,
    get_backlink_summary,
    format_backlink_summary,
    build_location_name,
)


SYSTEM_PROMPT = """You are ProofPilot's Backlink Intelligence Analyst — an expert at evaluating link profiles and identifying link-building opportunities for local service businesses.

You produce the **Backlink Audit Report** — a comprehensive analysis of a domain's backlink health with specific, actionable link-building strategies.

## Report Structure

### 1. Executive Summary
- Backlink health score (0-100)
- Total backlinks and referring domains
- Key strength and key vulnerability
- How the profile compares to competitors

### 2. Backlink Profile Overview
- Total backlinks, referring domains, referring IPs
- Follow vs nofollow ratio
- Spam score assessment
- Domain rank and what it means

### 3. Top Referring Domains Analysis
- Highest authority referring domains
- Which links are most valuable
- Any broken or at-risk links
- Quality distribution (how many are genuinely relevant vs. low-quality)

### 4. Anchor Text Analysis
- Distribution breakdown (branded vs. exact match vs. generic vs. URL)
- Over-optimization warnings
- Natural vs. suspicious patterns
- Recommendations for ideal anchor distribution

### 5. Competitive Comparison
- How the client's backlink profile compares to competitors
- Domains linking to competitors but not the client (link gaps)
- Competitor strengths to learn from

### 6. Link Building Opportunities
Priority-ranked list of specific actions:
- Directories to get listed in (local, industry-specific)
- Competitor links to replicate
- Content types that attract links in this industry
- Local link opportunities (chambers of commerce, local news, etc.)
- Broken link building opportunities

### 7. Toxic Link Warnings
- Spammy or potentially harmful links
- Whether a disavow is recommended
- Links that could trigger a manual action

## Style Guidelines
- Use exact numbers from the data — never fabricate metrics
- Be specific: "Get listed on chandlerchamber.com — they link to 3 of your competitors"
- Prioritize by impact: which links will move the needle most
- Think like a $200K SEO consultant — give insights worth premium pricing"""


async def run_backlink_audit(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams the Backlink Audit Report.

    inputs keys: domain, service, location, competitors, notes
    """
    domain = inputs.get("domain", "").strip()
    service = inputs.get("service", "").strip()
    location = inputs.get("location", "").strip()
    competitor_str = inputs.get("competitors", "").strip()
    notes = inputs.get("notes", "").strip()

    if not domain:
        yield "**Error:** Domain is required.\n"
        return

    yield f"> Pulling backlink data for **{client_name}** ({domain})...\n\n"

    # Parse competitor domains
    competitors = []
    if competitor_str:
        competitors = [d.strip() for d in competitor_str.replace("\n", ",").split(",") if d.strip()]

    location_name = build_location_name(location) if location else "United States"

    # Run main backlink profile + competitor comparison in parallel
    tasks = [get_full_backlink_profile(domain)]
    tasks.append(get_domain_rank_overview(domain, location_name))

    # Also pull backlink summaries for competitors for comparison
    for comp in competitors[:3]:
        tasks.append(get_backlink_summary(comp))

    yield f"> Analyzing backlink profile + {len(competitors[:3])} competitor(s)...\n\n"

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Unpack results
    profile = results[0] if not isinstance(results[0], Exception) else {}
    domain_overview = results[1] if not isinstance(results[1], Exception) else {}

    competitor_profiles = []
    for i, comp in enumerate(competitors[:3]):
        idx = i + 2
        if idx < len(results) and not isinstance(results[idx], Exception):
            comp_data = results[idx]
            comp_data["domain"] = comp
            competitor_profiles.append(comp_data)

    yield "> Data collected — generating Backlink Audit Report with Claude Opus...\n\n"
    yield "---\n\n"

    # Build data context
    data_sections = [
        f"## CLIENT INFO\nDomain: {domain}\nService: {service}\nLocation: {location}\nClient: {client_name}\n",
    ]

    if profile:
        data_sections.append(format_full_backlink_profile(profile))

    if domain_overview:
        data_sections.append(
            f"Domain Rank Overview:\n"
            f"  Keywords ranked: {domain_overview.get('keywords', 0):,}\n"
            f"  Est. monthly traffic: {domain_overview.get('etv', 0):,.0f}\n"
            f"  Traffic value: ${domain_overview.get('etv_cost', 0):,.0f}/mo"
        )

    if competitor_profiles:
        comp_section = "## COMPETITOR BACKLINK COMPARISON\n"
        for cp in competitor_profiles:
            comp_section += format_backlink_summary(cp) + "\n\n"
        data_sections.append(comp_section)

    if notes:
        data_sections.append(f"\n## ADDITIONAL CONTEXT\n{notes}")

    if strategy_context and strategy_context.strip():
        data_sections.append(f"\n## STRATEGY DIRECTION\n{strategy_context.strip()}")

    user_prompt = (
        f"Generate a comprehensive Backlink Audit Report for {client_name} "
        f"({domain}), a {service} business serving {location}.\n\n"
        f"Use ALL of the following research data to produce your analysis. "
        f"Every claim must be grounded in this data.\n\n"
        + "\n\n".join(data_sections)
        + "\n\nWrite the complete report now. Start with the title and executive summary."
    )

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
