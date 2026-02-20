"""
Client Proposals Workflow — ProofPilot v5

Generates persuasive, data-backed marketing proposals that close deals.
Pulls real market data from DataForSEO, then streams through Claude Opus
with the prospect's specific numbers, competitors, and opportunities.

Every proposal should make the prospect think "I'd be stupid NOT to do this."

inputs keys:
    domain          e.g. "steadfastplumbingaz.com" (required)
    service         e.g. "plumber" (required)
    location        e.g. "Gilbert, AZ" (required)
    package_tier    e.g. "growth-strategy" (default)
    competitors     optional comma-separated competitor domains
    notes           optional context about the prospect
"""

import asyncio
import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    get_domain_rank_overview,
    get_domain_ranked_keywords,
    research_competitors,
    get_keyword_search_volumes,
    build_location_name,
    build_service_keyword_seeds,
    format_domain_ranked_keywords,
    format_keyword_volumes,
    format_full_competitor_section,
)


# ── Pricing tiers ────────────────────────────────────────────────────────────

PRICING_TIERS = {
    "foundation": {
        "name": "Foundation",
        "price": 1200,
        "description": "Basic SEO + GBP optimization",
        "deliverables": [
            "GBP optimization and management",
            "On-page SEO for up to 5 pages",
            "Monthly SEO reporting",
            "Citation building (10/month)",
            "Basic keyword tracking (20 keywords)",
            "Technical SEO fixes (critical issues)",
        ],
    },
    "market-expansion": {
        "name": "Market Expansion",
        "price": 2000,
        "description": "SEO + content + local targeting",
        "deliverables": [
            "Everything in Foundation",
            "2 SEO blog posts per month",
            "2 location pages per month",
            "GBP posts (8/month)",
            "Keyword tracking (50 keywords)",
            "Competitor monitoring (3 competitors)",
            "Review generation strategy",
            "Monthly strategy call",
        ],
    },
    "digital-domination": {
        "name": "Digital Domination",
        "price": 3500,
        "description": "Full SEO + content + link building",
        "deliverables": [
            "Everything in Market Expansion",
            "4 SEO blog posts per month",
            "4 location pages per month",
            "GBP posts (12/month)",
            "Link building (5 quality backlinks/month)",
            "Keyword tracking (100 keywords)",
            "Competitor monitoring (5 competitors)",
            "Content calendar planning",
            "Bi-weekly strategy calls",
        ],
    },
    "growth-strategy": {
        "name": "Growth Strategy",
        "price": 6200,
        "description": "Complete SEO, content, paid, reputation",
        "deliverables": [
            "Everything in Digital Domination",
            "Google Ads management (up to $3K spend)",
            "6 SEO blog posts per month",
            "6 location pages per month",
            "Full reputation management system",
            "Service page creation and optimization",
            "Schema markup implementation",
            "Conversion rate optimization",
            "Keyword tracking (200 keywords)",
            "Weekly strategy calls",
            "Priority support",
        ],
    },
    "market-leader": {
        "name": "Market Leader",
        "price": 8000,
        "description": "Enterprise-level SEO + multi-location",
        "deliverables": [
            "Everything in Growth Strategy",
            "Multi-location GBP management",
            "8 SEO blog posts per month",
            "8 location pages per month",
            "Advanced link building (10 backlinks/month)",
            "Google Ads management (up to $5K spend)",
            "Social media content calendar",
            "Keyword tracking (300+ keywords)",
            "Custom reporting dashboard",
            "Dedicated account manager",
        ],
    },
    "industry-authority": {
        "name": "Industry Authority",
        "price": 10000,
        "description": "Authority building + PR + full service",
        "deliverables": [
            "Everything in Market Leader",
            "Digital PR and press releases",
            "Authority content (guides, whitepapers)",
            "10+ SEO blog posts per month",
            "10+ location pages per month",
            "Advanced link building (15+ backlinks/month)",
            "Google Ads management (up to $10K spend)",
            "Full social media management",
            "Video SEO optimization",
            "Quarterly business strategy reviews",
            "24/7 priority support",
        ],
    },
}

PRICING_TABLE = """| Tier | Name | Price/mo | Description |
|------|------|----------|-------------|
| 1 | Foundation | $1,200 | Basic SEO + GBP optimization |
| 2 | Market Expansion | $2,000 | SEO + content + local targeting |
| 3 | Digital Domination | $3,500 | Full SEO + content + link building |
| 4 | Growth Strategy | $6,200 | Complete SEO, content, paid, reputation |
| 5 | Market Leader | $8,000 | Enterprise-level SEO + multi-location |
| 6 | Industry Authority | $10,000 | Authority building + PR + full service |"""


# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are ProofPilot's Proposal Writer. You create persuasive, data-backed marketing proposals that close deals. Every proposal should make the prospect think "I'd be stupid NOT to do this."

## Brand Voice
- Confident, specific, data-heavy. Active voice. Short sentences.
- Address the prospect as "you" and "your business."
- Name competitors specifically by their domain/business name.
- NO em dashes. NO semicolons. Periods and commas only.
- Frame everything as opportunity and ROI, not failure.
- Use real numbers from the data. Never hedge with "approximately" or "roughly" when you have exact data.
- Make the prospect feel understood. Reference their specific market, competitors, and opportunities.
- The proposal should feel custom-built (because it IS, with real data).

## ProofPilot Pricing Packages

{PRICING_TABLE}

## Report Structure

### Cover
# Marketing Proposal: [Client Name]
Prepared by ProofPilot | [Date]

### 1. The Opportunity
- Current organic visibility (from DFS data)
- What they're missing: total addressable search volume in their market
- Revenue they're leaving on the table (estimate from keyword value data)
- Competitor comparison: "Your top competitor gets X monthly organic visits worth $Y"

### 2. Market Analysis
- Competitor landscape overview
- SERP competitive density
- Keyword opportunities with volumes and values
- Local market conditions

### 3. Our Strategy
Based on the selected package tier, outline:
- Specific deliverables with quantities
- Month 1 / Month 2-3 / Month 4-6 milestones
- Expected outcomes with realistic timelines
- What makes this approach different from generic SEO

### 4. Investment & ROI
- Package name and monthly investment
- What's included (detailed deliverables list)
- Expected timeline to results
- ROI projection: "If we capture just 10% of the addressable volume..."
- Contract terms: month-to-month, no long-term lock-in

### 5. Why ProofPilot
- Data-driven approach (we built the tools)
- Home service specialization
- Transparent reporting (monthly reports with real data)
- "We eat our own cooking" — our clients see real rankings, not vanity metrics

### 6. Next Steps
Clear CTA. Schedule a call, sign the agreement, get started.

## Output Rules
- Start immediately with the # heading. Zero preamble.
- Replace every [bracketed instruction] with real content.
- Reproduce pre-built data tables exactly as given.
- Write in a punchy, direct style: "That's 3,124 free visits per month going to your competitor. Not you."
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_num(n) -> str:
    if not n:
        return "0"
    return f"{int(n):,}"


def _fmt_dollar(n) -> str:
    if not n:
        return "$0"
    return f"${int(n):,}"


async def _empty_list() -> list:
    return []


async def _empty_dict() -> dict:
    return {}


# ── Main workflow ────────────────────────────────────────────────────────────

async def run_proposals(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams the Client Proposal document.

    inputs keys: domain, service, location, package_tier, competitors, notes
    """
    domain = inputs.get("domain", "").strip().lower()
    if not domain:
        yield "**Error:** Domain is required.\n"
        return

    service = inputs.get("service", "").strip()
    if not service:
        yield "**Error:** Service type is required.\n"
        return

    location = inputs.get("location", "").strip()
    if not location:
        yield "**Error:** Location is required.\n"
        return

    package_tier = inputs.get("package_tier", "growth-strategy").strip().lower()
    competitor_str = inputs.get("competitors", "").strip()
    notes = inputs.get("notes", "").strip()

    # Resolve package
    tier = PRICING_TIERS.get(package_tier, PRICING_TIERS["growth-strategy"])
    tier_name = tier["name"]
    tier_price = tier["price"]
    tier_deliverables = tier["deliverables"]

    # Parse location
    location_name = build_location_name(location) if location else "United States"
    city = location.split(",")[0].strip() if location else ""

    # Parse competitor domains
    competitors = []
    if competitor_str:
        competitors = [d.strip().lower() for d in competitor_str.replace("\n", ",").split(",") if d.strip()]

    yield f"> Starting **Client Proposal** for **{client_name}** ({domain})...\n\n"
    yield f"> Package: **{tier_name}** (${tier_price:,}/mo)\n\n"

    # ── Phase 1: Parallel data gather ─────────────────────────────────────
    yield "> Phase 1: Pulling domain data + market research...\n\n"

    keyword_seeds = build_service_keyword_seeds(service, city, 10) if service and city else []

    # Build parallel tasks
    domain_overview_task = get_domain_rank_overview(domain, "United States")
    domain_keywords_task = get_domain_ranked_keywords(domain, "United States", 20)

    competitor_research_task = (
        research_competitors(f"{service} {city}", location_name, 3, 3)
        if service and city else _empty_dict()
    )

    keyword_volumes_task = (
        get_keyword_search_volumes(keyword_seeds, location_name)
        if keyword_seeds and location_name else _empty_list()
    )

    # Run all in parallel
    domain_overview, domain_keywords, competitor_data, keyword_volumes = await asyncio.gather(
        domain_overview_task,
        domain_keywords_task,
        competitor_research_task,
        keyword_volumes_task,
        return_exceptions=True,
    )

    # Handle exceptions gracefully
    if isinstance(domain_overview, Exception):
        domain_overview = {"domain": domain, "keywords": 0, "etv": 0, "etv_cost": 0}
    if isinstance(domain_keywords, Exception):
        domain_keywords = []
    if isinstance(competitor_data, Exception):
        competitor_data = {}
    if isinstance(keyword_volumes, Exception):
        keyword_volumes = []

    yield f"> Domain overview: {_fmt_num(domain_overview.get('keywords'))} keywords, "
    yield f"{_fmt_num(domain_overview.get('etv'))} monthly traffic\n\n"

    # ── Phase 2: Pull competitor domain overviews ─────────────────────────
    # Merge auto-discovered competitors with user-provided ones
    discovered_competitors = competitor_data.get("all_domains", []) if competitor_data else []
    all_competitor_domains = list(dict.fromkeys(
        competitors + [d for d in discovered_competitors if d.lower() != domain.lower()]
    ))[:5]

    comp_overviews = []
    if all_competitor_domains:
        yield f"> Phase 2: Analyzing {len(all_competitor_domains)} competitor(s): {', '.join(all_competitor_domains[:3])}...\n\n"

        comp_overview_tasks = [
            get_domain_rank_overview(comp, "United States")
            for comp in all_competitor_domains
        ]
        comp_results = await asyncio.gather(*comp_overview_tasks, return_exceptions=True)

        for comp_domain, result in zip(all_competitor_domains, comp_results):
            if isinstance(result, Exception):
                comp_overviews.append({"domain": comp_domain, "keywords": 0, "etv": 0, "etv_cost": 0})
            else:
                comp_overviews.append(result)
    else:
        yield "> Phase 2: No competitors found or provided. Skipping competitor analysis.\n\n"

    yield "> Data collection complete. Generating proposal with Claude Opus...\n\n"
    yield "---\n\n"

    # ── Phase 3: Build data sections for the prompt ───────────────────────
    today = __import__("datetime").date.today().strftime("%B %d, %Y")

    data_sections = []

    # Domain overview section
    data_sections.append(
        f"## PROSPECT DOMAIN OVERVIEW — {domain}\n"
        f"Client: {client_name}\n"
        f"Service: {service}\n"
        f"Location: {location}\n"
        f"Keywords ranked: {_fmt_num(domain_overview.get('keywords'))}\n"
        f"Est. monthly organic traffic: {_fmt_num(domain_overview.get('etv'))}\n"
        f"Traffic value: {_fmt_dollar(domain_overview.get('etv_cost'))}/mo"
    )

    # Prospect ranked keywords
    if domain_keywords:
        data_sections.append("## PROSPECT CURRENT RANKINGS\n" + format_domain_ranked_keywords(domain_keywords))

    # Competitor landscape from SERP
    if competitor_data:
        maps_results = competitor_data.get("maps", [])
        organic_results = competitor_data.get("organic", [])
        data_sections.append(
            format_full_competitor_section(
                f"{service} {city}",
                maps_results,
                organic_results,
            )
        )

    # Competitor domain overviews
    if comp_overviews:
        comp_lines = ["## COMPETITOR DOMAIN OVERVIEWS\n"]
        for comp in sorted(comp_overviews, key=lambda x: x.get("etv", 0) or 0, reverse=True):
            comp_lines.append(
                f"  {comp.get('domain', 'unknown')}: "
                f"{_fmt_num(comp.get('keywords'))} keywords, "
                f"{_fmt_num(comp.get('etv'))} monthly traffic, "
                f"{_fmt_dollar(comp.get('etv_cost'))}/mo traffic value"
            )
        data_sections.append("\n".join(comp_lines))

    # Keyword volumes
    if keyword_volumes:
        data_sections.append("## MARKET KEYWORD VOLUMES\n" + format_keyword_volumes(keyword_volumes))

    # Market summary stats
    total_search_volume = sum(kw.get("search_volume") or 0 for kw in keyword_volumes) if keyword_volumes else 0
    cpcs = [float(kw["cpc"]) for kw in keyword_volumes if kw.get("cpc") and float(kw.get("cpc", 0)) > 0]
    avg_cpc = sum(cpcs) / len(cpcs) if cpcs else 0
    max_cpc = max(cpcs) if cpcs else 0
    monthly_ad_value = total_search_volume * 0.10 * avg_cpc
    annual_ad_value = monthly_ad_value * 12

    # Top competitor stats
    top_competitor = None
    if comp_overviews:
        sorted_comps = sorted(comp_overviews, key=lambda x: x.get("etv", 0) or 0, reverse=True)
        top_competitor = sorted_comps[0] if sorted_comps else None

    data_sections.append(
        f"## MARKET SUMMARY STATS\n"
        f"Total addressable search volume: {_fmt_num(total_search_volume)}/mo\n"
        f"Average CPC in market: {f'${avg_cpc:.2f}' if avg_cpc else 'N/A'}\n"
        f"Highest CPC keyword: {f'${max_cpc:.2f}' if max_cpc else 'N/A'}\n"
        f"Est. monthly ad value (10% CTR): {_fmt_dollar(monthly_ad_value)}\n"
        f"Est. annual ad value: {_fmt_dollar(annual_ad_value)}"
    )

    if top_competitor:
        data_sections.append(
            f"## TOP COMPETITOR\n"
            f"Domain: {top_competitor.get('domain', 'unknown')}\n"
            f"Monthly traffic: {_fmt_num(top_competitor.get('etv'))}\n"
            f"Traffic value: {_fmt_dollar(top_competitor.get('etv_cost'))}/mo\n"
            f"Keywords: {_fmt_num(top_competitor.get('keywords'))}"
        )

    # Notes and strategy context
    if notes:
        data_sections.append(f"## PROSPECT NOTES\n{notes}")

    if strategy_context and strategy_context.strip():
        data_sections.append(f"## AGENCY STRATEGY DIRECTION\n{strategy_context.strip()}")

    # ── Phase 4: Build package-specific context ───────────────────────────
    deliverables_text = "\n".join(f"  - {d}" for d in tier_deliverables)

    package_context = (
        f"## SELECTED PACKAGE\n"
        f"Package: {tier_name}\n"
        f"Monthly investment: ${tier_price:,}\n"
        f"Deliverables:\n{deliverables_text}\n\n"
        f"## ALL PROOFPILOT PACKAGES\n{PRICING_TABLE}"
    )
    data_sections.append(package_context)

    # ── Phase 5: Build ROI projections context ────────────────────────────
    # Conservative: capture 5% of addressable volume
    con_traffic = max(200, int(total_search_volume * 0.05)) if total_search_volume else 300
    con_leads = max(5, int(con_traffic * 0.03))
    con_jobs = max(2, int(con_leads * 0.40))

    # Growth: capture 15% of addressable volume
    grow_traffic = max(800, int(total_search_volume * 0.15)) if total_search_volume else 1000
    grow_leads = max(15, int(grow_traffic * 0.04))
    grow_jobs = max(6, int(grow_leads * 0.40))

    roi_context = (
        f"## ROI PROJECTION DATA\n"
        f"Conservative scenario (Month 6-12):\n"
        f"  Target traffic: {_fmt_num(con_traffic)}/mo\n"
        f"  Est. leads: {con_leads}/mo (3% conversion)\n"
        f"  Est. new customers: {con_jobs}/mo (40% close rate)\n\n"
        f"Growth scenario (Month 12-18):\n"
        f"  Target traffic: {_fmt_num(grow_traffic)}/mo\n"
        f"  Est. leads: {grow_leads}/mo (4% conversion)\n"
        f"  Est. new customers: {grow_jobs}/mo (40% close rate)\n\n"
        f"Monthly investment: ${tier_price:,}\n"
        f"Break-even: prospect needs just {max(1, int(tier_price / 350))} new jobs/month at $350 avg to cover the investment"
    )
    data_sections.append(roi_context)

    # ── Phase 6: Stream Claude ────────────────────────────────────────────
    top_comp_domain = top_competitor.get("domain", "your top competitor") if top_competitor else "your top competitor"
    top_comp_traffic = _fmt_num(top_competitor.get("etv")) if top_competitor else "significant"
    top_comp_value = _fmt_dollar(top_competitor.get("etv_cost")) if top_competitor else "significant"

    user_prompt = (
        f"Write a complete marketing proposal for **{client_name}** ({domain}).\n"
        f"They are a **{service}** business serving **{location}**.\n"
        f"Recommended package: **{tier_name}** at **${tier_price:,}/month**.\n"
        f"Date: {today}\n\n"
        f"Key selling points to weave in:\n"
        f"- Their top competitor ({top_comp_domain}) gets {top_comp_traffic} organic visits/month worth {top_comp_value}/mo in ad value\n"
        f"- Total addressable search volume: {_fmt_num(total_search_volume)}/mo\n"
        f"- Average CPC: {f'${avg_cpc:.2f}' if avg_cpc else 'N/A'} (this is what they'd pay Google Ads per click)\n"
        f"- Annual ad value of organic rankings: {_fmt_dollar(annual_ad_value)}\n"
        f"- ProofPilot investment: ${tier_price:,}/mo. Month-to-month. No long-term lock-in.\n\n"
        f"Follow the report structure exactly. Use all the data below to make this proposal "
        f"specific, persuasive, and impossible to say no to.\n\n"
        + "\n\n".join(data_sections)
        + "\n\nWrite the complete proposal now. Start with # Marketing Proposal: "
        + client_name
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
