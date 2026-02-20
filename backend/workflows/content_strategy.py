"""
Content Strategy Workflow — comprehensive content ecosystem map for a business.

Pulls keyword volumes + difficulty from DataForSEO to ground recommendations
in real search data. Produces buyer personas, content pillars, funnel maps,
12-month calendars, distribution plans, and measurement frameworks.

inputs keys:
    business_type     e.g. "electrician", "plumber", "HVAC contractor"
    service           e.g. "panel upgrades", "drain cleaning", "AC installation"
    location          e.g. "Chandler, AZ"
    target_audience   optional — e.g. "homeowners 35-55"
    content_goals     optional — e.g. "increase organic traffic, build authority"
    notes             optional — additional context
"""

import asyncio
import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    get_keyword_search_volumes,
    get_bulk_keyword_difficulty,
    build_location_name,
    build_service_keyword_seeds,
    format_keyword_volumes,
    format_keyword_difficulty,
)


SYSTEM_PROMPT = """You are ProofPilot's Content Strategy Specialist — an expert at designing comprehensive content ecosystems for local service businesses that drive organic traffic, build authority, and convert searchers into booked jobs.

You produce the **Content Ecosystem Map** — a deep, actionable content strategy document grounded in real keyword data.

## Report Structure

### 1. Audience Psychographic Profiles
Create 2-3 detailed buyer personas for the business:
- Persona name and demographic snapshot
- Pain points and frustrations (what drives them to search)
- Trigger events (what makes them pick up the phone NOW)
- Common objections to hiring (price, trust, timing)
- Information needs at each stage of the buying journey
- Where they spend time online (platforms, communities, forums)

### 2. Content Pillar Strategy
Define 4-6 content pillars with topic clusters under each:
- Pillar name and strategic rationale
- 5-8 cluster topics per pillar with target keywords
- Internal linking strategy between pillars and clusters
- Content format recommendations per cluster (blog, video, guide, tool)
- Priority ranking based on search volume and business value

### 3. Funnel-Stage Content Map
Map content types across the full customer journey:
- **Awareness:** Educational content that captures top-of-funnel searches
- **Consideration:** Comparison guides, cost breakdowns, "how to choose" content
- **Decision:** Case studies, testimonials, service pages, trust signals
- **Retention:** Follow-up guides, maintenance tips, referral prompts
For each stage: specific content titles, target keywords, CTAs, success metrics

### 4. Monthly Content Calendar
12-month rolling plan with specific topics:
- Month-by-month content themes tied to seasonality
- Specific article/page titles with target keywords
- Content type (blog, location page, service page, video script, social)
- Publishing cadence (weekly blog, monthly cost guide, etc.)
- Seasonal opportunities and local events to leverage

### 5. Distribution Strategy
How to maximize reach for each piece of content:
- **Organic Search:** On-page SEO requirements, internal linking
- **Social Media:** Platform-specific repurposing (which platforms, what format)
- **Email:** Newsletter cadence, segmentation, automation triggers
- **Paid Amplification:** Which content to boost, retargeting strategy
- **Local:** GBP posts, community engagement, local partnerships

### 6. Content Types & Templates
Specific templates and frameworks for each content type:
- Blog posts (structure, word count, CTA placement)
- Comparison guides ("X vs Y" format)
- Cost guides ("How much does X cost in [City]")
- Location pages (per-city SEO pages)
- Video scripts (YouTube, social shorts)
- Social posts (platform-specific formats)
- FAQ pages (schema-ready Q&A)

### 7. Measurement Framework
How to track content performance:
- KPIs per content type (traffic, rankings, conversions, engagement)
- Attribution model (first-touch, multi-touch, assisted conversions)
- Reporting cadence and dashboard recommendations
- Benchmarks and targets for months 3, 6, 12
- Content audit schedule (quarterly refresh cadence)

### 8. Competitive Content Gaps
What competitors publish that the business doesn't:
- Content types competitors have (identify specific gaps)
- Topics competitors rank for with no competing content
- Content quality comparison (depth, freshness, structure)
- Quick wins — low-difficulty keywords with no competitor coverage

## Style Guidelines
- Ground every recommendation in the keyword data provided
- Use exact search volumes and difficulty scores when available
- Be specific — name exact article titles, not vague categories
- Think like a content strategist who understands local SEO
- Prioritize content that drives booked jobs, not just traffic
- Reference the business type, location, and service throughout
- Format with clean markdown: tables, bullets, bold for emphasis"""


async def run_content_strategy(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams a comprehensive content strategy ecosystem map.

    inputs keys:
        business_type    e.g. "electrician", "plumber"
        service          e.g. "panel upgrades", "drain cleaning"
        location         e.g. "Chandler, AZ"
        target_audience  optional
        content_goals    optional
        notes            optional
    """
    business_type = inputs.get("business_type", "home service business").strip()
    service = inputs.get("service", "").strip()
    location = inputs.get("location", "").strip()
    target_audience = inputs.get("target_audience", "").strip()
    content_goals = inputs.get("content_goals", "").strip()
    notes = inputs.get("notes", "").strip()

    if not business_type or not service or not location:
        yield "**Error:** business_type, service, and location are all required.\n"
        return

    yield f"> Starting **Content Strategy Agent** for **{client_name}** ({business_type} / {service} in {location})...\n\n"

    # Build location name for DataForSEO
    location_name = build_location_name(location) if location else "United States"
    city = location.split(",")[0].strip() if location else ""

    yield "> Phase 1: Building keyword seeds and pulling search data from DataForSEO...\n\n"

    # Build keyword seeds — service-aware, city-qualified
    keyword_seeds = build_service_keyword_seeds(service, city, 10)

    # Add content-strategy-specific seeds
    content_seeds = [
        f"how much does {service} cost {city}",
        f"best {business_type} {city}",
        f"{service} vs",
        f"when to {service.split()[0] if service else 'hire'} {city}",
        f"diy {service}",
        f"{service} tips",
        f"{business_type} reviews {city}",
        f"cheap {service} {city}",
        f"{service} near me",
        f"{service} cost",
    ]

    all_seeds = list(dict.fromkeys(keyword_seeds + content_seeds))[:30]

    # Pull volumes + difficulty in parallel
    try:
        volumes, difficulty = await asyncio.gather(
            get_keyword_search_volumes(all_seeds, location_name),
            get_bulk_keyword_difficulty(all_seeds, location_name),
            return_exceptions=True,
        )
    except Exception:
        volumes = []
        difficulty = []

    if isinstance(volumes, Exception):
        volumes = []
    if isinstance(difficulty, Exception):
        difficulty = []

    yield "> Phase 2: Analyzing keyword landscape and building content strategy with Claude Opus...\n\n"
    yield "---\n\n"

    # Build data sections for the prompt
    data_sections = [
        f"## TARGET BUSINESS\nClient: {client_name}\nBusiness Type: {business_type}\nService Focus: {service}\nLocation: {location}",
    ]

    if target_audience:
        data_sections.append(f"## TARGET AUDIENCE\n{target_audience}")

    if content_goals:
        data_sections.append(f"## CONTENT GOALS\n{content_goals}")

    if volumes:
        data_sections.append("## KEYWORD SEARCH VOLUME DATA\n" + format_keyword_volumes(volumes))

    if difficulty:
        data_sections.append("## KEYWORD DIFFICULTY SCORES\n" + format_keyword_difficulty(difficulty))

    if notes:
        data_sections.append(f"## ADDITIONAL CONTEXT\n{notes}")

    if strategy_context and strategy_context.strip():
        data_sections.append(f"## STRATEGY DIRECTION\n{strategy_context.strip()}")

    user_prompt = (
        f"Generate a comprehensive Content Ecosystem Map for {client_name}, "
        f"a {business_type} business specializing in {service} and serving {location}.\n\n"
        f"Use ALL of the keyword data provided below to ground your recommendations "
        f"in real search demand. Every content pillar, topic cluster, and calendar entry "
        f"should connect back to actual search volume and difficulty data.\n\n"
        + "\n\n".join(data_sections)
        + "\n\nWrite the complete content strategy document now. Start with the title."
    )

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=10000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
