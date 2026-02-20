"""
AI Search Visibility Report
Analyzes how a brand/domain appears across AI search results (Google AI Overviews),
featured snippets, and traditional organic search. Shows where AI is citing your
competitors vs. you, and identifies opportunities to get referenced.

Data sources:
  DataForSEO SERP API — AI Overview items, featured snippets, PAA, knowledge graph
  DataForSEO Labs     — domain ranked keywords for seed keyword discovery
  DataForSEO Keywords — search volumes for context

inputs keys:
    domain      e.g. "allthingzelectric.com"
    service     e.g. "electrician" — used to build keyword seeds
    location    e.g. "Chandler, AZ"
    notes       optional — specific focus areas
"""

import asyncio
import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    get_ai_search_landscape,
    format_ai_search_landscape,
    get_domain_ranked_keywords,
    format_domain_ranked_keywords,
    get_keyword_search_volumes,
    format_keyword_volumes,
    get_keyword_trends,
    format_keyword_trends,
    build_location_name,
    build_service_keyword_seeds,
)


SYSTEM_PROMPT = """You are ProofPilot's AI Search Intelligence Analyst — the best in the industry at analyzing how AI-powered search (Google AI Overviews, featured snippets, knowledge panels) affects local service businesses.

You produce the **AI Search Visibility Report** — a comprehensive analysis of how a client's brand appears (or doesn't appear) across AI search features, with specific, actionable strategies to earn AI citations.

## Report Structure

### 1. Executive Summary (3-4 sentences)
- AI search visibility score (0-100 based on data)
- How many of their key queries trigger AI Overviews
- Whether they're being cited or competitors are
- The single biggest opportunity

### 2. AI Overview Landscape
For each keyword analyzed:
- Does an AI Overview appear?
- Which domains are cited in the AI Overview?
- Is the client cited? If not, who is and why?
- What content format gets cited (lists, stats, how-to, etc.)

### 3. Featured Snippet Analysis
- Which queries have featured snippets
- Who owns them
- Specific format the snippet uses (paragraph, list, table)
- How to steal each snippet

### 4. People Also Ask (PAA) Opportunities
- Questions being asked around their service keywords
- Which PAA questions could become blog posts or FAQ sections
- Priority by search volume and conversion intent

### 5. Competitive AI Visibility
- Which competitors appear most in AI Overviews
- What content patterns get them cited
- Domain authority comparison

### 6. Trend Analysis
- Are key queries trending up or down?
- Seasonal patterns to exploit
- Emerging queries to target early

### 7. Action Plan (Priority-Ranked)
Specific, implementable actions:
- Content to create or optimize for AI citation
- Schema markup additions
- FAQ sections to add
- Internal linking improvements
- Content format changes

## Style Guidelines
- Use real data from the research — never fabricate numbers
- Be specific: "Create an FAQ section answering 'How much does a panel upgrade cost in Chandler?'" not "Add FAQ content"
- Quantify everything: mention search volumes, positions, competitor counts
- Think like a $200K SEO consultant — give insights that justify premium pricing"""


async def run_ai_search_report(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams the AI Search Visibility Report.

    inputs keys: domain, service, location, notes
    """
    domain = inputs.get("domain", "").strip()
    service = inputs.get("service", "").strip()
    location = inputs.get("location", "").strip()
    notes = inputs.get("notes", "").strip()

    if not domain or not service or not location:
        yield "**Error:** Domain, service, and location are all required.\n"
        return

    yield f"> Analyzing AI search landscape for **{client_name}** ({domain})...\n\n"

    # Build keyword seeds for the service + location
    location_name = build_location_name(location)
    city = location.split(",")[0].strip()

    # Core commercial keywords + informational keywords for AI overview analysis
    commercial_seeds = build_service_keyword_seeds(service, city, 5)
    informational_seeds = [
        f"how much does {service} cost {city}",
        f"best {service} in {city}",
        f"when to hire a {service}",
        f"{service} vs diy",
        f"how to choose a {service}",
    ]
    all_keywords = commercial_seeds[:5] + informational_seeds[:5]

    yield f"> Researching {len(all_keywords)} keywords for AI Overview presence...\n\n"

    # Run everything in parallel
    landscape_task = get_ai_search_landscape(all_keywords, location_name)
    ranked_task = get_domain_ranked_keywords(domain, location_name, 15)
    volumes_task = get_keyword_search_volumes(all_keywords, location_name)
    trends_task = get_keyword_trends(all_keywords[:5], location_name)

    landscape, ranked_kws, volumes, trends = await asyncio.gather(
        landscape_task, ranked_task, volumes_task, trends_task,
        return_exceptions=True,
    )

    if isinstance(landscape, Exception):
        landscape = []
    if isinstance(ranked_kws, Exception):
        ranked_kws = []
    if isinstance(volumes, Exception):
        volumes = []
    if isinstance(trends, Exception):
        trends = []

    yield "> Data collected — generating AI Search Visibility Report with Claude Opus...\n\n"
    yield "---\n\n"

    # Build the data context for Claude
    data_sections = [
        f"## CLIENT INFO\nDomain: {domain}\nService: {service}\nLocation: {location}\nClient: {client_name}\n",
        format_ai_search_landscape(landscape, domain),
        format_domain_ranked_keywords(ranked_kws),
        format_keyword_volumes(volumes),
        format_keyword_trends(trends),
    ]

    if notes:
        data_sections.append(f"\n## ADDITIONAL CONTEXT\n{notes}")

    if strategy_context and strategy_context.strip():
        data_sections.append(f"\n## STRATEGY DIRECTION\n{strategy_context.strip()}")

    user_prompt = (
        f"Generate a comprehensive AI Search Visibility Report for {client_name} "
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
