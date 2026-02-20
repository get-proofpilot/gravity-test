"""
On-Page Technical SEO Audit Workflow
Runs a live technical audit on a single page using DataForSEO's On-Page
instant pages API — gets 60+ metrics including Core Web Vitals, meta tags,
heading structure, image optimization, and more. Claude produces a prioritized
fix list ranked by SEO impact.

Data sources:
  DataForSEO On-Page API — instant single-page audit (live, no async polling)
  DataForSEO SERP API    — organic results for the target keyword to compare

inputs keys:
    url         e.g. "https://allthingzelectric.com/panel-upgrade"
    keyword     e.g. "panel upgrade chandler az" — the keyword this page targets
    location    e.g. "Chandler, AZ"
    notes       optional — specific concerns or focus areas
"""

import asyncio
import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    get_instant_page_audit,
    format_instant_page_audit,
    get_organic_serp,
    format_organic_competitors,
    get_keyword_search_volumes,
    format_keyword_volumes,
    build_location_name,
)


SYSTEM_PROMPT = """You are ProofPilot's Technical SEO Audit Specialist — an expert at analyzing on-page SEO factors and prioritizing fixes by impact for local service businesses.

You produce the **On-Page Technical Audit** — a comprehensive page-level analysis with specific, prioritized fixes that will improve rankings.

## Report Structure

### 1. Page Health Score (0-100)
Quick score based on the technical findings. Explain what drives the score.

### 2. Critical Issues (Fix Immediately)
Issues that are actively hurting rankings:
- Missing or duplicate H1
- Missing meta description
- Missing HTTPS
- Broken canonical
- Major Core Web Vitals failures
- No internal links

### 3. Meta Tag Analysis
- Title: length, keyword placement, click-worthiness
- Description: length, CTA inclusion, uniqueness
- Canonical: correctness
- How these compare to competitors ranking for the same keyword

### 4. Content Structure
- Heading hierarchy (H1 → H2 → H3)
- Content length assessment
- Keyword usage in headings
- Internal vs external link balance
- Image optimization (alt tags, compression)

### 5. Core Web Vitals
- LCP (Largest Contentful Paint) — target <2.5s
- CLS (Cumulative Layout Shift) — target <0.1
- TTI (Time to Interactive) — target <3.8s
- Page size and load time assessment
- Specific fixes for each failing metric

### 6. Competitive Page Comparison
- How the page stacks up against top 5 ranking pages for the target keyword
- What competitors are doing differently (longer content, better structure, etc.)
- Specific elements to add or improve

### 7. Prioritized Fix List
Numbered list ranked by SEO impact:
1. [Critical] Fix X — expected impact: Y
2. [High] Fix X — expected impact: Y
3. [Medium] Fix X — expected impact: Y

Each fix should include:
- What to change
- Why it matters
- Expected ranking impact
- Implementation difficulty (easy/medium/hard)

## Style Guidelines
- Use exact numbers from the audit data — never fabricate metrics
- Be specific: "Change title from 'Panel Upgrade' to 'Panel Upgrade in Chandler, AZ | All Thingz Electric' (currently 13 chars, should be 50-60)"
- Compare to competitors: "The #1 result has 2,400 words; this page has 340"
- Think like a $200K SEO consultant — every recommendation should justify its priority"""


async def run_onpage_audit(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams the On-Page Technical SEO Audit.

    inputs keys: url, keyword, location, notes
    """
    url = inputs.get("url", "").strip()
    keyword = inputs.get("keyword", "").strip()
    location = inputs.get("location", "").strip()
    notes = inputs.get("notes", "").strip()

    if not url:
        yield "**Error:** Page URL is required.\n"
        return

    yield f"> Running technical audit on **{url}** for {client_name}...\n\n"

    location_name = build_location_name(location) if location else "United States"

    # Run page audit + competitive SERP in parallel
    tasks = [get_instant_page_audit(url)]
    if keyword:
        tasks.append(get_organic_serp(keyword, location_name, 5))
        tasks.append(get_keyword_search_volumes([keyword], location_name))

    yield "> Crawling page + checking competitor rankings...\n\n"

    results = await asyncio.gather(*tasks, return_exceptions=True)

    page_data = results[0] if not isinstance(results[0], Exception) else {"url": url, "error": "Audit failed"}

    serp_data = []
    volume_data = []
    if keyword and len(results) > 1:
        if not isinstance(results[1], Exception):
            serp_data = results[1]
        if len(results) > 2 and not isinstance(results[2], Exception):
            volume_data = results[2]

    yield "> Data collected — generating On-Page Audit Report with Claude Opus...\n\n"
    yield "---\n\n"

    # Build data context
    data_sections = [
        f"## PAGE INFO\nURL: {url}\nTarget Keyword: {keyword or 'Not specified'}\nLocation: {location}\nClient: {client_name}\n",
        format_instant_page_audit(page_data),
    ]

    if serp_data:
        data_sections.append(
            f"## COMPETITOR SERP for \"{keyword}\"\n" +
            format_organic_competitors(serp_data)
        )

    if volume_data:
        data_sections.append(format_keyword_volumes(volume_data))

    if notes:
        data_sections.append(f"\n## ADDITIONAL CONTEXT\n{notes}")

    if strategy_context and strategy_context.strip():
        data_sections.append(f"\n## STRATEGY DIRECTION\n{strategy_context.strip()}")

    user_prompt = (
        f"Generate a comprehensive On-Page Technical SEO Audit for {client_name}'s page at {url}"
        + (f", targeting the keyword \"{keyword}\"" if keyword else "")
        + f" in {location}.\n\n"
        f"Use ALL of the following audit data to produce your analysis. "
        f"Every claim must be grounded in this data.\n\n"
        + "\n\n".join(data_sections)
        + "\n\nWrite the complete audit now. Start with the title and page health score."
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
