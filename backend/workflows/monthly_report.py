"""
Monthly Client Report Workflow — ProofPilot

Generates a branded monthly performance report for active clients. Pulls real-time
ranking, traffic, backlink, and trend data from DataForSEO, then streams a narrative
report through Claude Opus that justifies the retainer and demonstrates value.

Data sources:
  DataForSEO Labs      — domain ranked keywords snapshot, domain rank overview
  DataForSEO Backlinks — backlink summary (total links, referring domains, rank)
  DataForSEO Keywords  — search volumes for seed keywords (market context)
  DataForSEO Trends    — Google Trends direction for top keywords

inputs keys:
    domain            e.g. "allthingzelectric.com"
    service           e.g. "electrician"
    location          e.g. "Chandler, AZ"
    reporting_period  e.g. "January 2026" (defaults to current month)
    highlights        optional — manual wins/deliverables to include
    notes             optional — additional context
"""

import asyncio
import anthropic
from typing import AsyncGenerator
from datetime import date

from utils.dataforseo import (
    get_domain_ranked_keywords,
    get_domain_rank_overview,
    get_backlink_summary,
    get_keyword_trends,
    get_keyword_search_volumes,
    build_location_name,
    build_service_keyword_seeds,
    format_domain_ranked_keywords,
    format_backlink_summary,
    format_keyword_trends,
    format_keyword_volumes,
)


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are ProofPilot's Monthly Report Analyst. You produce branded monthly performance reports that justify retainers and demonstrate value. The report should make clients feel like they're getting incredible ROI.

Report structure:

### 1. Executive Summary
- Overall SEO health score (1-100)
- Key metrics: total keywords ranked, estimated monthly traffic, traffic value
- Month-over-month direction (up/down/stable)
- One-line summary: "Your organic presence [grew/held/needs attention] this month"

### 2. Rankings Performance
- Total keywords ranking on page 1, page 2, page 3+
- Top performing keywords with positions
- Keywords that moved UP this month
- Keywords close to page 1 (positions 11-20 — "almost there" opportunities)
- New keywords that appeared this month

### 3. Traffic & Visibility
- Estimated organic traffic and value
- Traffic trends (from keyword trend data)
- Which pages/keywords drive the most value

### 4. Backlink Profile Health
- Total backlinks and referring domains
- New links acquired
- Domain authority context vs. competitors

### 5. Content Delivered This Month
Reference any highlights/notes provided. List deliverables completed.

### 6. Wins & Achievements
Celebrate specific improvements — position gains, new page 1 rankings, traffic increases.

### 7. Strategic Recommendations for Next Month
- Quick wins: keywords almost on page 1
- Content to create
- Technical fixes needed
- Link building opportunities

### 8. Month Ahead Preview
What the team will focus on next month.

## Style Guidelines
- Professional but warm. Use exact numbers from the data.
- Make the client feel confident their investment is working.
- Present data as wins wherever possible — "You rank for 47 keywords" not "You only rank for 47 keywords."
- Be specific: name exact keywords, positions, traffic numbers.
- Use markdown formatting: headers, bold for key metrics, tables for data.
- NO em dashes, NO semicolons. Periods and commas only.
- Start immediately with the report title. Zero preamble."""


# ── Main workflow ─────────────────────────────────────────────────────────────

async def run_monthly_report(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams the Monthly Client Report.

    inputs keys: domain, service, location, reporting_period, highlights, notes
    """
    domain = inputs.get("domain", "").strip().lower()
    if not domain:
        yield "**Error:** Domain is required.\n"
        return

    service = inputs.get("service", "").strip()
    location = inputs.get("location", "").strip()
    reporting_period = inputs.get("reporting_period", "").strip()
    highlights = inputs.get("highlights", "").strip()
    notes = inputs.get("notes", "").strip()

    # Default reporting period to current month
    if not reporting_period:
        today = date.today()
        reporting_period = today.strftime("%B %Y")

    location_name = build_location_name(location) if location else "United States"
    city = location.split(",")[0].strip() if location else ""

    # Build keyword seeds for market context
    keyword_seeds = []
    if service and city:
        keyword_seeds = build_service_keyword_seeds(service, city, 10)

    yield f"> Phase 1: Pulling current rankings data for **{client_name}** ({domain})...\n\n"

    # ── Phase 1: Parallel data collection ─────────────────────────────────
    # Pull rankings snapshot, domain overview, and backlink summary in parallel

    async def safe_ranked_keywords():
        try:
            return await get_domain_ranked_keywords(domain, location_name, 30)
        except Exception:
            return []

    async def safe_rank_overview():
        try:
            return await get_domain_rank_overview(domain, location_name)
        except Exception:
            return {"domain": domain, "keywords": 0, "etv": 0, "etv_cost": 0}

    async def safe_backlink_summary():
        try:
            return await get_backlink_summary(domain)
        except Exception:
            return {"domain": domain}

    ranked_keywords, rank_overview, backlink_data = await asyncio.gather(
        safe_ranked_keywords(),
        safe_rank_overview(),
        safe_backlink_summary(),
        return_exceptions=True,
    )

    # Handle exceptions from gather
    if isinstance(ranked_keywords, Exception):
        ranked_keywords = []
    if isinstance(rank_overview, Exception):
        rank_overview = {"domain": domain, "keywords": 0, "etv": 0, "etv_cost": 0}
    if isinstance(backlink_data, Exception):
        backlink_data = {"domain": domain}

    yield "> Phase 2: Pulling trend data and market context...\n\n"

    # ── Phase 2: Trends + keyword volumes in parallel ─────────────────────
    # Use top 5 ranked keywords for trend data, seed keywords for market context

    top_keywords_for_trends = [
        kw.get("keyword", "") for kw in (ranked_keywords or [])[:5]
        if kw.get("keyword")
    ]

    async def safe_keyword_trends():
        if not top_keywords_for_trends:
            return []
        try:
            return await get_keyword_trends(top_keywords_for_trends, location_name)
        except Exception:
            return []

    async def safe_keyword_volumes():
        if not keyword_seeds:
            return []
        try:
            return await get_keyword_search_volumes(keyword_seeds, location_name)
        except Exception:
            return []

    trend_data, market_volumes = await asyncio.gather(
        safe_keyword_trends(),
        safe_keyword_volumes(),
        return_exceptions=True,
    )

    if isinstance(trend_data, Exception):
        trend_data = []
    if isinstance(market_volumes, Exception):
        market_volumes = []

    yield "> Data collection complete — generating Monthly Report with Claude Opus...\n\n"
    yield "---\n\n"

    # ── Phase 3: Build data context for Claude ────────────────────────────
    today_str = date.today().strftime("%B %d, %Y")

    data_sections = [
        f"## CLIENT INFO\n"
        f"Client: {client_name}\n"
        f"Domain: {domain}\n"
        f"Service: {service or 'Not specified'}\n"
        f"Location: {location or 'Not specified'}\n"
        f"Reporting Period: {reporting_period}\n"
        f"Report Generated: {today_str}",
    ]

    # Domain rank overview
    if rank_overview:
        total_kws = rank_overview.get("keywords", 0)
        est_traffic = rank_overview.get("etv", 0)
        traffic_value = rank_overview.get("etv_cost", 0)
        data_sections.append(
            f"## DOMAIN RANK OVERVIEW\n"
            f"Total keywords in top 100: {int(total_kws):,}\n"
            f"Estimated monthly organic traffic: {int(est_traffic):,}\n"
            f"Traffic value (equivalent Google Ads spend): ${int(traffic_value):,}/month"
        )

    # Ranked keywords snapshot
    if ranked_keywords:
        data_sections.append(
            "## CURRENT RANKINGS SNAPSHOT (Top 30 by traffic)\n"
            + format_domain_ranked_keywords(ranked_keywords)
        )

        # Compute page distribution
        page1 = [kw for kw in ranked_keywords if kw.get("rank") and kw["rank"] <= 10]
        page2 = [kw for kw in ranked_keywords if kw.get("rank") and 11 <= kw["rank"] <= 20]
        page3_plus = [kw for kw in ranked_keywords if kw.get("rank") and kw["rank"] > 20]
        almost_page1 = [kw for kw in ranked_keywords if kw.get("rank") and 11 <= kw["rank"] <= 20]

        data_sections.append(
            f"## RANKING DISTRIBUTION\n"
            f"Page 1 (positions 1-10): {len(page1)} keywords\n"
            f"Page 2 (positions 11-20): {len(page2)} keywords\n"
            f"Page 3+ (positions 21+): {len(page3_plus)} keywords\n"
            f"'Almost Page 1' opportunities (positions 11-20): {len(almost_page1)} keywords"
        )

        if almost_page1:
            almost_lines = []
            for kw in almost_page1:
                almost_lines.append(
                    f"  #{kw.get('rank', '?')}: \"{kw.get('keyword', '')}\" — "
                    f"{kw.get('search_volume', 0):,}/mo search volume"
                )
            data_sections.append(
                "## ALMOST PAGE 1 OPPORTUNITIES\n" + "\n".join(almost_lines)
            )

    # Backlink profile
    if backlink_data and backlink_data.get("total_backlinks"):
        data_sections.append(
            "## BACKLINK PROFILE\n" + format_backlink_summary(backlink_data)
        )

    # Trend data
    if trend_data:
        data_sections.append(
            "## KEYWORD TRENDS (12-month direction)\n"
            + format_keyword_trends(trend_data)
        )

    # Market context
    if market_volumes:
        data_sections.append(
            "## MARKET CONTEXT — KEYWORD SEARCH VOLUMES\n"
            + format_keyword_volumes(market_volumes)
        )

    # Highlights / deliverables
    if highlights:
        data_sections.append(
            f"## HIGHLIGHTS & DELIVERABLES THIS MONTH\n{highlights}"
        )

    # Notes
    if notes:
        data_sections.append(f"## ADDITIONAL NOTES\n{notes}")

    # Strategy context
    if strategy_context and strategy_context.strip():
        data_sections.append(
            f"## AGENCY STRATEGY DIRECTION\n{strategy_context.strip()}"
        )

    # ── Phase 4: Stream Claude ────────────────────────────────────────────
    user_prompt = (
        f"Write the complete Monthly Performance Report for **{client_name}** ({domain}) "
        f"for the reporting period **{reporting_period}**.\n\n"
        f"They are a **{service or 'home service'}** business serving "
        f"**{location or 'their local market'}**.\n\n"
        f"Use ALL of the following data to produce the report. Every metric must come "
        f"from this data. Present the data as wins wherever possible.\n\n"
        + "\n\n".join(data_sections)
        + "\n\nWrite the complete monthly report now. Start with the title."
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
