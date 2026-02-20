"""
Monthly Client Report Workflow — Premium Edition
Auto-pulls Search Atlas + DataForSEO + GBP data + job history → business-focused
narrative report with real metrics, competitor benchmarking, and ROI framing.

inputs keys: domain, service, location, report_month, notes
"""

import os
import asyncio
import anthropic
from typing import AsyncGenerator
from datetime import datetime, timezone

from utils.searchatlas import sa_call
from utils.dataforseo import (
    get_domain_rank_overview,
    get_domain_ranked_keywords,
    get_local_pack,
    get_organic_serp,
    get_keyword_search_volumes,
    format_domain_ranked_keywords,
    build_location_name,
    build_service_keyword_seeds,
)
from utils.db import get_jobs_by_client
from utils.localfalcon import list_scan_reports, get_scan_report, format_scan_for_report, format_scans_summary

# ── Industry benchmarks for ROI framing ──────────────────────────────────────
# Source: WebFX 2026 Home Services Marketing Benchmarks, LocaliQ, First Page Sage
INDUSTRY_CPL = {
    "electrician":  150,
    "plumber":      167,
    "plumbing":     167,
    "hvac":         104,
    "roofer":       400,
    "roofing":      400,
    "landscaper":   85,
    "landscaping":  85,
    "pest control": 45,
    "painter":      120,
    "painting":     120,
    "garage door":  130,
    "handyman":     95,
    "default":      130,
}

INDUSTRY_CONVERSION = {
    "plumber": 0.14, "plumbing": 0.14,
    "electrician": 0.10, "hvac": 0.10,
    "roofer": 0.05, "roofing": 0.05,
    "landscaper": 0.12, "landscaping": 0.12,
    "pest control": 0.15, "default": 0.08,
}


SYSTEM_PROMPT = """You are a senior reporting strategist at ProofPilot, a results-driven digital marketing agency for home service businesses.

You write monthly client reports that busy business owners actually read. Your reports justify the retainer by showing BUSINESS IMPACT — not SEO jargon.

## Core Principles
1. LEAD WITH MONEY — every metric should connect to revenue, leads, or calls
2. COMPARE TO COMPETITORS — "you rank #4 for X" means nothing without "competitor ranks #1 and gets ~40 clicks/mo from it"
3. USE REAL NUMBERS — never say "improved" without a number. Say "moved from position 18 to position 7 (+11 spots)"
4. FRAME TRAFFIC AS VALUE — "Your organic traffic is worth $X,XXX/mo — that's what you'd pay in Google Ads for the same clicks"
5. DELIVERABLES = ROI — "We published 4 service pages this month. Combined target keyword volume: 2,400 searches/mo"
6. BE HONEST — if something declined, own it and explain the plan to fix it
7. NEXT MONTH MATTERS — always end with what's coming and why it matters to the client's bottom line

## Report Format (strict markdown — follow this exactly)

# Monthly SEO Performance Report
## [Client Name] — [Month Year]

---

## At a Glance

| Metric | Current | Change | What It Means |
|--------|---------|--------|---------------|
| Total Ranked Keywords | XXX | +/- XX | [business translation] |
| Estimated Monthly Traffic | X,XXX | +/- XXX | [business translation] |
| Traffic Value (vs. PPC) | $X,XXX/mo | +/- $XXX | [what you'd pay Google Ads] |
| Top 10 Rankings | XX | +/- X | [these drive the most calls] |
| Estimated Monthly Leads | XX-XX | — | [based on traffic × industry avg conversion] |

---

## Google Business Profile Performance

[Include rating, review count, how it compares to top local competitors. Reviews are HUGE for home service businesses — mention the impact on trust and click-through rate.]

---

## Rankings That Drive Revenue

[Top 10-15 keywords with position, search volume, and estimated monthly value. Focus on money keywords — the ones that lead to phone calls. Format as a table:]

| Keyword | Position | Monthly Searches | Est. Monthly Value |
|---------|----------|------------------|--------------------|

[After the table, call out the 2-3 biggest ranking wins and what they mean in terms of leads.]

---

## Local Search Visibility

[How the client appears in Google Maps/Local Pack. Who are the top 3-5 competitors? What's the gap? Rating comparison, review count comparison.]

[If Local Falcon grid data is available, include a Local Rank Tracking subsection. Report ARP (Average Rank Position), SoLV (Share of Local Voice), and describe how the business performs across the geographic grid — where they're strong (top 3 positions) and where they're weak. This is critical data for home service businesses because it shows how visibility varies across their service area.]

---

## Competitor Landscape

[Name the top competitors. Compare their ranked keywords, estimated traffic, and local presence to the client. Show where the client is winning and where the gap still exists.]

---

## Work Completed This Month

[List every deliverable with its purpose and expected impact. Don't just say "4 blog posts" — say "4 blog posts targeting keywords with combined 3,200 monthly searches, estimated to generate 15-25 additional visits/month within 90 days".]

---

## SEO Health Scorecard

[If pillar scores or technical data is available, present as a simple scorecard. Focus on what needs attention, not exhaustive technical details.]

| Category | Score | Status |
|----------|-------|--------|
| On-Page SEO | XX/100 | [Good/Needs Work/Critical] |
| Technical Health | XX/100 | [Good/Needs Work/Critical] |
| Backlink Profile | XX/100 | [Good/Needs Work/Critical] |
| Content Quality | XX/100 | [Good/Needs Work/Critical] |

---

## ROI Summary

[This is the MONEY section. Calculate:]
- Organic traffic value vs. equivalent PPC spend
- Estimated leads generated from organic traffic
- Cost per organic lead vs. industry average PPC cost per lead ($XX for this service type)
- ProofPilot retainer ROI (if retainer cost is known)

[Frame this as: "Your organic presence generated an estimated XX-XX leads this month. At the industry average cost of $XXX per lead via Google Ads, that's $X,XXX-$X,XXX in equivalent ad spend — delivered through your SEO investment."]

---

## Next Month's Roadmap

[3-5 specific, prioritized actions. Each with:]
- What we're doing
- Why it matters (tie to revenue/leads)
- Expected timeline and impact

---

*Report generated by ProofPilot Agency Hub — [date]*

## CRITICAL RULES
- Do NOT write any preamble, introduction, or explanation before the report
- Start DIRECTLY with the H1 title
- Every section MUST reference specific data from the data provided
- If a data point is unavailable, skip that row/section gracefully — never say "data unavailable"
- Use $ formatting for all monetary values
- Use commas in numbers over 999
- Round estimated values — precision suggests false confidence
- ALL tables must use proper markdown table format"""


# ── Data gathering ────────────────────────────────────────────────────────────

async def _gather_sa_report_data(domain: str) -> dict[str, str]:
    """Fetch Search Atlas data for the monthly report."""

    async def safe_call(tool: str, op: str, params: dict, label: str) -> tuple[str, str]:
        try:
            result = await sa_call(tool, op, params)
            return label, result
        except Exception as e:
            return label, f"Data unavailable: {e}"

    tasks = [
        safe_call(
            "Site_Explorer_Organic_Tool", "get_organic_keywords",
            {"project_identifier": domain, "page_size": 30, "ordering": "-traffic"},
            "organic_keywords",
        ),
        safe_call(
            "Site_Explorer_Organic_Tool", "get_organic_pages",
            {"project_identifier": domain, "page_size": 10, "ordering": "-traffic"},
            "organic_pages",
        ),
        safe_call(
            "Site_Explorer_Organic_Tool", "get_organic_competitors",
            {"project_identifier": domain, "page_size": 8},
            "sa_competitors",
        ),
        safe_call(
            "Site_Explorer_Analysis_Tool", "get_position_distribution",
            {"identifier": domain},
            "position_distribution",
        ),
        safe_call(
            "Site_Explorer_Holistic_Audit_Tool", "get_holistic_seo_pillar_scores",
            {"domain": domain},
            "pillar_scores",
        ),
        safe_call(
            "Site_Explorer_Backlinks_Tool", "get_site_referring_domains",
            {"project_identifier": domain, "page_size": 10, "ordering": "-domain_rating"},
            "referring_domains",
        ),
    ]

    results = await asyncio.gather(*tasks)
    return dict(results)


async def _gather_dfs_report_data(
    domain: str, service: str, location: str, location_name: str,
) -> dict:
    """Fetch DataForSEO data for the report — domain overview, ranked keywords,
    local pack, organic SERP, and keyword volumes."""
    dfs_login = os.environ.get("DATAFORSEO_LOGIN", "")
    dfs_pass = os.environ.get("DATAFORSEO_PASSWORD", "")
    if not dfs_login or not dfs_pass:
        return {}

    try:
        city = location.split(",")[0].strip() if location else ""
        keyword = f"{service} {city}" if service and city else ""

        # Build tasks — always get overview + ranked keywords
        coros = {
            "overview": get_domain_rank_overview(domain, location_name),
            "ranked_keywords": get_domain_ranked_keywords(domain, location_name, limit=30),
        }

        # Conditionally add SERP and Maps data if we have a service keyword
        if keyword:
            coros["local_pack"] = get_local_pack(keyword, location_name, num_results=5)
            coros["organic_serp"] = get_organic_serp(keyword, location_name, num_results=10)

            # Get keyword volumes for service-related terms
            seeds = build_service_keyword_seeds(service, city, count=15)
            coros["keyword_volumes"] = get_keyword_search_volumes(seeds, location_name)

        # Execute all in parallel
        keys = list(coros.keys())
        results = await asyncio.gather(*coros.values(), return_exceptions=True)

        output = {}
        for key, result in zip(keys, results):
            if not isinstance(result, Exception):
                output[key] = result
        return output

    except Exception:
        return {}


# ── Main workflow ─────────────────────────────────────────────────────────────

async def run_monthly_report(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
    client_id: int = 0,
) -> AsyncGenerator[str, None]:
    """
    Streams a premium monthly client report with real data.

    inputs keys:
        domain        e.g. "allthingzelectric.com"
        service       e.g. "electrician"
        location      e.g. "Chandler, AZ"
        report_month  e.g. "February 2026" (optional, defaults to current)
        notes         optional context
    """
    domain       = inputs.get("domain", "").strip()
    service      = inputs.get("service", "").strip().lower()
    location     = inputs.get("location", "").strip()
    report_month = inputs.get("report_month", "").strip()
    notes        = inputs.get("notes", "").strip()

    if not report_month:
        report_month = datetime.now(timezone.utc).strftime("%B %Y")

    # ── Phase 1: Gather all data concurrently ──────────────────
    yield f"> Pulling SEO performance data for **{client_name}** ({domain})...\n\n"

    async def _empty_dict():
        return {}

    sa_task = _gather_sa_report_data(domain) if domain else _empty_dict()

    location_name = build_location_name(location) if location else ""
    dfs_task = (
        _gather_dfs_report_data(domain, service, location, location_name)
        if (domain and location_name)
        else _empty_dict()
    )

    yield f"> Analyzing local competitors and market position...\n\n"

    # Local Falcon scan data (optional — only if API key is configured)
    async def _gather_lf_data() -> dict:
        try:
            if not os.environ.get("LOCALFALCON_API_KEY"):
                return {}
            scans = await list_scan_reports(limit=10)
            if not scans:
                return {"scans": []}

            # Try to get detailed grid data for the most recent scans
            detailed = []
            for scan in scans[:3]:
                key = (
                    scan.get("report_key")
                    or scan.get("reportKey")
                    or scan.get("key")
                    or scan.get("id")
                    or ""
                )
                if not key:
                    continue
                try:
                    report = await get_scan_report(str(key))
                    detailed.append(report)
                except Exception:
                    pass

            return {"scans": scans, "detailed": detailed}
        except Exception:
            return {}

    sa_data, dfs_data, job_history, lf_data = await asyncio.gather(
        sa_task, dfs_task,
        asyncio.to_thread(get_jobs_by_client, client_id),
        _gather_lf_data(),
        return_exceptions=True,
    )

    # Graceful fallbacks
    if isinstance(sa_data, Exception):
        sa_data = {}
    if isinstance(dfs_data, Exception):
        dfs_data = {}
    if isinstance(job_history, Exception):
        job_history = []
    if isinstance(lf_data, Exception):
        lf_data = {}

    yield f"> Building business performance report...\n\n"
    yield "---\n\n"

    # ── Phase 2: Build rich data context ───────────────────────
    context_sections = []

    # Industry benchmarks for this service type
    service_key = service.lower() if service else "default"
    cpl = INDUSTRY_CPL.get(service_key, INDUSTRY_CPL["default"])
    conv_rate = INDUSTRY_CONVERSION.get(service_key, INDUSTRY_CONVERSION["default"])

    context_sections.append(
        f"### Industry Benchmarks ({service or 'Home Services'})\n"
        f"- Average cost per lead (Google Ads): ${cpl}\n"
        f"- Average lead-to-customer conversion rate: {conv_rate:.0%}\n"
        f"- Use these to calculate ROI comparisons in the report\n"
    )

    # Domain overview (DFS Labs)
    overview = dfs_data.get("overview")
    if overview and overview.get("keywords", 0) > 0:
        etv = overview.get("etv", 0)
        etv_cost = overview.get("etv_cost", 0)
        kw_count = overview.get("keywords", 0)
        est_leads = round(etv * conv_rate) if etv else 0

        context_sections.append(
            f"### Domain Performance Overview\n"
            f"- Domain: {domain}\n"
            f"- Total ranked keywords: {kw_count:,}\n"
            f"- Estimated monthly organic traffic: {etv:,.0f} visits\n"
            f"- Estimated traffic value (PPC equivalent): ${etv_cost:,.0f}/mo\n"
            f"- Estimated monthly organic leads (traffic × {conv_rate:.0%} conversion): ~{est_leads}\n"
            f"- Equivalent PPC cost for those leads: ~${est_leads * cpl:,.0f}/mo at ${cpl}/lead\n"
        )

    # Top ranked keywords
    ranked = dfs_data.get("ranked_keywords")
    if ranked:
        context_sections.append(
            f"### Top Ranked Keywords (by estimated traffic value)\n"
            f"{format_domain_ranked_keywords(ranked)}"
        )

    # Local Pack / Maps results
    local_pack = dfs_data.get("local_pack")
    if local_pack:
        lines = ["### Google Maps / Local Pack Results\n"]
        for r in local_pack:
            rating = r.get("rating", "N/A")
            reviews = r.get("reviews", 0)
            lines.append(
                f"- #{r.get('rank', '?')}: {r.get('name', 'Unknown')} "
                f"— ★{rating} ({reviews} reviews) — {r.get('domain', 'no website')}"
            )
        # Check if client is in local pack
        client_in_pack = any(
            domain.lower() in (r.get("domain", "") or "").lower()
            for r in local_pack
        )
        if client_in_pack:
            lines.append(f"\n✅ {client_name} IS appearing in the Local Pack")
        else:
            lines.append(f"\n⚠️ {client_name} is NOT in the Local Pack for this query")
        context_sections.append("\n".join(lines))

    # Organic SERP results
    organic = dfs_data.get("organic_serp")
    if organic:
        lines = ["### Top Organic SERP Results\n"]
        for r in organic[:10]:
            lines.append(
                f"- #{r.get('rank', '?')}: {r.get('domain', '?')} — \"{r.get('title', '')}\""
            )
        client_in_organic = any(
            domain.lower() in (r.get("domain", "") or "").lower()
            for r in organic[:10]
        )
        if client_in_organic:
            pos = next(
                r.get("rank", "?") for r in organic
                if domain.lower() in (r.get("domain", "") or "").lower()
            )
            lines.append(f"\n✅ {client_name} ranks #{pos} organically")
        else:
            lines.append(f"\n⚠️ {client_name} is not in the top 10 organic results")
        context_sections.append("\n".join(lines))

    # Keyword volumes for service area
    volumes = dfs_data.get("keyword_volumes")
    if volumes:
        lines = ["### Service Keyword Search Volumes\n"]
        for kw in volumes[:15]:
            vol = kw.get("search_volume", 0)
            cpc_val = kw.get("cpc", 0)
            lines.append(
                f"- \"{kw.get('keyword', '')}\" — {vol:,} searches/mo, ${cpc_val:.2f} CPC"
            )
        total_vol = sum(kw.get("search_volume", 0) for kw in volumes[:15])
        lines.append(f"\nTotal addressable search volume for top 15 terms: {total_vol:,}/mo")
        context_sections.append("\n".join(lines))

    # Search Atlas data
    if sa_data:
        for key, label in [
            ("organic_keywords", "Current Organic Keywords (Search Atlas)"),
            ("organic_pages", "Top Organic Pages by Traffic"),
            ("sa_competitors", "Organic Competitors (Search Atlas)"),
            ("position_distribution", "Ranking Position Distribution"),
            ("pillar_scores", "SEO Health Pillar Scores"),
            ("referring_domains", "Top Referring Domains"),
        ]:
            val = sa_data.get(key, "")
            if val and "unavailable" not in val.lower():
                context_sections.append(f"### {label}\n{val}")

    # Local Falcon rank tracking data
    if lf_data:
        lf_detailed = lf_data.get("detailed", [])
        lf_scans = lf_data.get("scans", [])

        if lf_detailed:
            for scan in lf_detailed[:3]:
                scan_text = format_scan_for_report(scan)
                if scan_text:
                    context_sections.append(scan_text)
        elif lf_scans:
            context_sections.append(format_scans_summary(lf_scans))

    # Job history — deliverables completed
    if job_history:
        deliverables = []
        for job in job_history:
            created = job.get("created_at", "")[:10]
            title = job.get("workflow_title", "Unknown")
            wf_id = job.get("workflow_id", "")
            approved = " ✅ Approved" if job.get("approved") else ""
            # Try to extract useful input details
            job_inputs = job.get("inputs", {})
            detail = ""
            if wf_id in ("service-page", "location-page", "seo-blog-post"):
                kw = job_inputs.get("keyword", "") or job_inputs.get("service", "") or job_inputs.get("primary_service", "")
                if kw:
                    detail = f" — targeting: \"{kw}\""
            elif wf_id == "gbp-posts":
                count = job_inputs.get("post_count", "")
                if count:
                    detail = f" — {count} posts"
            deliverables.append(f"- {created}: {title}{detail}{approved}")
        context_sections.append(
            f"### Deliverables Completed for {client_name}\n" + "\n".join(deliverables)
        )
    else:
        context_sections.append(
            "### Deliverables Completed\nNo jobs on record yet — this may be the first report."
        )

    context_doc = "\n\n".join(context_sections)

    # ── Phase 3: Stream from Claude ────────────────────────────
    prompt_lines = [
        f"Write a Monthly SEO Performance Report for **{client_name}**.",
        f"",
        f"**Business type:** {service or 'home service business'}",
        f"**Market:** {location or 'their local market'}",
        f"**Domain:** {domain or 'Not specified'}",
        f"**Report period:** {report_month}",
        f"**Report date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
        f"",
        f"## Real Performance Data",
        f"Use ALL of this data to build a comprehensive, business-focused report.",
        f"Cite specific numbers — real data builds trust with clients.",
        f"",
        context_doc,
    ]

    if strategy_context and strategy_context.strip():
        prompt_lines += [
            f"",
            f"## Strategy Context (from client profile)",
            f"{strategy_context.strip()}",
        ]

    if notes:
        prompt_lines += [
            f"",
            f"## Additional Context for This Report",
            f"{notes}",
        ]

    prompt_lines += [
        f"",
        f"Write the complete report now. Follow the format in your system prompt exactly.",
        f"Start with the H1 title. Every section must reference specific data from above.",
        f"Frame everything in business terms — leads, revenue, competitive advantage.",
    ]

    user_prompt = "\n".join(prompt_lines)

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
