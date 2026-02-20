"""
Property Management Marketing Strategy Workflow — deep marketing strategy
for property management companies covering SEO, content, lead generation,
and reputation management.

Pulls domain overview, ranked keywords, and keyword volumes from DataForSEO
to ground recommendations in real competitive data.

inputs keys:
    domain           e.g. "abcpropertymanagement.com"
    company_name     optional — e.g. "ABC Property Management"
    location         e.g. "Phoenix, AZ"
    property_types   optional — e.g. "residential, commercial, HOA"
    portfolio_size   optional — e.g. "500 units"
    notes            optional — additional context
"""

import asyncio
import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    get_domain_rank_overview,
    get_domain_ranked_keywords,
    get_keyword_search_volumes,
    build_location_name,
    format_domain_ranked_keywords,
    format_keyword_volumes,
)


SYSTEM_PROMPT = """You are ProofPilot's Property Management Marketing Strategist — an expert at designing marketing strategies for property management companies that attract property owners, streamline tenant acquisition, and build dominant local search presence.

You produce the **Property Management Marketing Strategy** — a comprehensive plan covering SEO, content, lead generation, reputation management, and implementation.

## Report Structure

### 1. Market Assessment
- Current SEO position based on domain data (traffic, keywords, rankings)
- Local competition analysis from ranked keyword data
- Market size estimation (# of rental properties, property managers in the area)
- SWOT analysis for the company's digital presence
- Key competitive advantages and vulnerabilities

### 2. Website Strategy
- Page structure recommendations (what pages to build/optimize):
  - Homepage messaging and conversion elements
  - Property owner landing pages (by property type: residential, commercial, HOA)
  - Tenant-facing pages (application portal, maintenance requests, current listings)
  - Service pages (each management service as its own page)
  - Area pages (neighborhoods, zip codes, cities managed)
- Conversion funnels:
  - **Owner funnel:** Free rental analysis CTA → consultation → management agreement
  - **Tenant funnel:** Available listings → application → move-in
- Trust signals: reviews, certifications, portfolio size, years in business
- Technical requirements: mobile optimization, page speed, schema markup

### 3. SEO Strategy
Target keywords organized by property type:
- **Residential:** property management [city], rental management, landlord services, tenant screening
- **Commercial:** commercial property management, retail space management, office building management
- **HOA:** HOA management company [city], community association management, homeowners association services
- Keyword priority matrix based on search volume, difficulty, and business value
- On-page optimization roadmap for existing pages
- New page targets with specific keywords and search volumes

### 4. Content Strategy
Dual-audience content plan:
- **Owner-facing content:**
  - "Is a property manager worth it?" cost/benefit guides
  - Landlord-tenant law updates for the state
  - ROI calculators and rental market reports
  - Property maintenance guides and checklists
  - Tax deduction guides for rental property owners
- **Tenant-facing content:**
  - Moving guides for the area
  - Neighborhood spotlights
  - Renter's rights guides
  - Maintenance request how-tos
  - Community event roundups
- Content calendar with specific topics and publishing cadence

### 5. Local SEO & GBP Strategy
- Google Business Profile optimization checklist
- Review generation system (targeting 50+ reviews)
- Local citation building (property management directories)
- Map Pack optimization strategy
- Service area configuration
- GBP posting schedule (weekly posts with property tips, market updates)

### 6. Lead Generation Funnels
Two distinct funnels:
- **Owner Acquisition Funnel:**
  - Top: Free rental analysis tool / "What's my property worth?" calculator
  - Middle: Email nurture sequence with market reports and management tips
  - Bottom: Free consultation booking with management proposal
  - Retargeting: Pixel owners who visited pricing page but didn't convert
- **Tenant Screening Funnel:**
  - Listings syndication (Zillow, Apartments.com, HotPads, Facebook Marketplace)
  - Application portal with online screening
  - Automated showing scheduling
  - Move-in process automation

### 7. Reputation Management Plan
- Review solicitation workflow (automated post-move-in and post-maintenance)
- Review response templates (positive and negative)
- Monitoring setup (Google, Yelp, BBB, Apartment ratings sites)
- Crisis response protocol for negative reviews
- Reputation benchmarking against local competitors

### 8. 90-Day Implementation Roadmap
Week-by-week action plan:
- **Weeks 1-2:** Technical SEO fixes, GBP optimization, review system setup
- **Weeks 3-4:** Core page creation/optimization (homepage, service pages, area pages)
- **Weeks 5-8:** Content production (owner guides, area pages, blog posts)
- **Weeks 9-12:** Link building, citation building, paid amplification launch
- Monthly KPIs and checkpoints
- Resource requirements (time, budget, tools)

## Style Guidelines
- Ground every recommendation in the domain and keyword data provided
- Use exact search volumes, traffic numbers, and rankings from the data
- Be specific to property management — not generic marketing advice
- Address both audiences (property owners AND tenants) throughout
- Differentiate strategy by property type when relevant (residential vs commercial vs HOA)
- Include specific keyword targets with search volumes in every section
- Format with clean markdown: tables, bullets, bold for emphasis
- Think like a property management marketing specialist, not a generic SEO consultant"""


async def run_property_mgmt_strategy(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams a property management marketing strategy report.

    inputs keys:
        domain          e.g. "abcpropertymanagement.com"
        company_name    optional
        location        e.g. "Phoenix, AZ"
        property_types  optional — e.g. "residential, commercial, HOA"
        portfolio_size  optional — e.g. "500 units"
        notes           optional
    """
    domain = inputs.get("domain", "").strip()
    company_name = inputs.get("company_name", "").strip() or client_name
    location = inputs.get("location", "").strip()
    property_types = inputs.get("property_types", "").strip()
    portfolio_size = inputs.get("portfolio_size", "").strip()
    notes = inputs.get("notes", "").strip()

    if not domain:
        yield "**Error:** Domain is required.\n"
        return
    if not location:
        yield "**Error:** Location is required.\n"
        return

    yield f"> Starting **Property Management Strategy Agent** for **{company_name}** ({domain})...\n\n"

    # Build location name for DataForSEO
    location_name = build_location_name(location) if location else "United States"
    city = location.split(",")[0].strip() if location else ""

    yield "> Phase 1: Pulling domain overview and ranked keywords from DataForSEO...\n\n"

    # Build property-management-specific keyword seeds
    pm_seeds = [
        f"property management {city}",
        f"property management company {city}",
        f"property manager {city}",
        f"rental management {city}",
        "property management near me",
        f"best property management {city}",
        f"hoa management {city}",
        f"commercial property management {city}",
        f"residential property management {city}",
        f"landlord services {city}",
        f"tenant screening {city}",
        f"property management fees {city}",
        "rental property management",
        "property management cost",
        f"property management reviews {city}",
    ]

    # Add property-type-specific seeds if provided
    if property_types:
        for pt in property_types.split(","):
            pt = pt.strip().lower()
            if pt:
                pm_seeds.append(f"{pt} property management {city}")

    pm_seeds = list(dict.fromkeys(pm_seeds))[:25]

    # Pull domain data + keyword volumes in parallel
    # Use US-level for domain overview (DFS Labs returns accurate data at country scope)
    try:
        domain_overview, domain_keywords, keyword_volumes = await asyncio.gather(
            get_domain_rank_overview(domain, "United States"),
            get_domain_ranked_keywords(domain, "United States", 30),
            get_keyword_search_volumes(pm_seeds, location_name),
            return_exceptions=True,
        )
    except Exception:
        domain_overview = {}
        domain_keywords = []
        keyword_volumes = []

    if isinstance(domain_overview, Exception):
        domain_overview = {}
    if isinstance(domain_keywords, Exception):
        domain_keywords = []
    if isinstance(keyword_volumes, Exception):
        keyword_volumes = []

    yield "> Phase 2: Analyzing competitive landscape and building strategy with Claude Opus...\n\n"
    yield "---\n\n"

    # Build data sections for the prompt
    data_sections = [
        f"## TARGET COMPANY\nCompany: {company_name}\nDomain: {domain}\nLocation: {location}",
    ]

    if property_types:
        data_sections.append(f"## PROPERTY TYPES MANAGED\n{property_types}")

    if portfolio_size:
        data_sections.append(f"## PORTFOLIO SIZE\n{portfolio_size}")

    # Domain overview
    if domain_overview and domain_overview.get("keywords", 0) > 0:
        data_sections.append(
            f"## DOMAIN OVERVIEW — {domain}\n"
            f"  Keywords ranked: {domain_overview.get('keywords', 0):,}\n"
            f"  Est. monthly traffic: {domain_overview.get('etv', 0):,.0f}\n"
            f"  Traffic value: ${domain_overview.get('etv_cost', 0):,.0f}/mo"
        )
    else:
        data_sections.append(
            f"## DOMAIN OVERVIEW — {domain}\n"
            f"  Limited or no organic data found. This likely means the site has minimal SEO presence — "
            f"a significant opportunity for growth."
        )

    if domain_keywords:
        data_sections.append("## CURRENT RANKED KEYWORDS\n" + format_domain_ranked_keywords(domain_keywords))

    if keyword_volumes:
        data_sections.append("## MARKET KEYWORD VOLUMES\n" + format_keyword_volumes(keyword_volumes))

    if notes:
        data_sections.append(f"## ADDITIONAL CONTEXT\n{notes}")

    if strategy_context and strategy_context.strip():
        data_sections.append(f"## STRATEGY DIRECTION\n{strategy_context.strip()}")

    user_prompt = (
        f"Generate a comprehensive Property Management Marketing Strategy for {company_name} "
        f"({domain}), a property management company serving {location}.\n\n"
        f"Property types: {property_types or 'residential (assumed)'}.\n"
        f"Portfolio size: {portfolio_size or 'not specified'}.\n\n"
        f"Use ALL of the domain data and keyword volumes provided below to ground your "
        f"recommendations in real competitive intelligence. Every strategy recommendation "
        f"should connect back to actual search data and the company's current SEO position.\n\n"
        + "\n\n".join(data_sections)
        + "\n\nWrite the complete property management marketing strategy now. Start with the title."
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
