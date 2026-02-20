"""
Google Ads Copy Workflow
Generates high-converting Google Ads copy (Responsive Search Ads, extensions,
negative keywords, landing page recommendations) for home service businesses —
powered by real CPC and volume data from DataForSEO.

inputs keys:
    service         e.g. "electrician", "plumber", "HVAC"
    location        e.g. "Chandler, AZ"
    business_name   the client's business name (optional, falls back to client_name)
    usp             unique selling propositions (optional)
    landing_url     landing page URL (optional)
    budget          monthly ad budget (optional)
    notes           anything specific (optional)
"""

import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    get_keyword_search_volumes,
    build_location_name,
    build_service_keyword_seeds,
    format_keyword_volumes,
)


SYSTEM_PROMPT = """You are ProofPilot's Google Ads Specialist. You create high-converting search ad copy that maximizes Quality Score and click-through rates for home service businesses.

You produce copy-paste ready Google Ads campaigns. Every headline is max 30 characters. Every description is max 90 characters. You count characters precisely. When in doubt, shorten.

## Report structure

### 1. Campaign Structure Recommendation
- Recommended campaign types (Search, Local Services)
- Ad group organization by intent
- Budget allocation suggestion (if budget provided)

### 2. Ad Group: [Service] — High Intent
**Responsive Search Ad:**
Headlines (15, each max 30 characters):
1. [Service] in [City] | Call Now
2. Licensed & Insured [Service]
... etc (generate 15 headlines)

Descriptions (4, each max 90 characters):
1. ...
... etc

**Keywords to target:**
- Exact match: [keyword] — vol/mo, $CPC
- Phrase match: "keyword" — vol/mo, $CPC

### 3. Ad Group: Emergency [Service]
Same structure as above, focused on emergency/urgent intent

### 4. Ad Group: Specific Services
Break into sub-groups based on the service type

### 5. Ad Extensions
**Sitelinks (4):**
- Extension name -> URL path, description

**Callouts (6):**
- "Free Estimates", "Licensed & Insured", etc.

**Structured Snippets:**
- Services: list of services
- Neighborhoods: list of areas served

**Call Extension:**
- Phone number placeholder with schedule

### 6. Negative Keywords
List of keywords to exclude (DIY, jobs, salary, training, etc.)

### 7. Landing Page Recommendations
- Key elements the landing page should have
- Headline/CTA alignment with ad copy
- Conversion tracking setup

## Writing rules
- Precise and actionable. Every headline and description must meet Google's character limits.
- Use the keyword data to show which keywords are highest value (CPC x volume).
- Group by intent.
- Make it copy-paste ready — a media buyer should be able to drop this straight into Google Ads.
- No filler. No fluff. Every line earns its place.
- Show character counts in parentheses after each headline and description so the user can verify.
- Start immediately with the # heading. No preamble."""


async def run_google_ads_copy(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams Google Ads copy (RSAs, extensions, negatives, landing page recs)
    for a home service business, informed by real keyword/CPC data.

    inputs keys:
        service       e.g. "electrician"
        location      e.g. "Chandler, AZ"
        business_name the client's business name (optional)
        usp           unique selling propositions (optional)
        landing_url   landing page URL (optional)
        budget        monthly ad budget (optional)
        notes         anything specific (optional)
    """
    service       = inputs.get("service", "").strip()
    location      = inputs.get("location", "").strip()
    business_name = inputs.get("business_name", "").strip() or client_name
    usp           = inputs.get("usp", "").strip()
    landing_url   = inputs.get("landing_url", "").strip()
    budget        = inputs.get("budget", "").strip()
    notes         = inputs.get("notes", "").strip()

    if not service or not location:
        yield "Error: Both **service** and **location** are required.\n"
        return

    yield f"> Generating Google Ads copy for **{business_name}** ({service} in {location})...\n\n"

    # ── Pull keyword data from DataForSEO ───────────────────────────────
    city = location.split(",")[0].strip()
    location_name = build_location_name(location)

    # Build keyword seeds — commercial, emergency, and service-specific
    commercial_seeds = [
        f"{service} {city}",
        f"{service} near me",
        f"best {service} {city}",
        f"{service} company {city}",
        f"hire {service} {city}",
    ]
    emergency_seeds = [
        f"emergency {service} {city}",
        f"24 hour {service}",
        f"emergency {service} near me",
    ]
    service_specific_seeds = build_service_keyword_seeds(service, city, 10)

    # Deduplicate all seeds
    seen: set[str] = set()
    all_seeds: list[str] = []
    for kw in commercial_seeds + emergency_seeds + service_specific_seeds:
        kw_lower = kw.lower().strip()
        if kw_lower and kw_lower not in seen:
            seen.add(kw_lower)
            all_seeds.append(kw_lower)

    yield f"> Pulling CPC and volume data for {len(all_seeds)} keyword seeds...\n\n"

    # Fetch keyword volumes — graceful fallback on failure
    keyword_data: list[dict] = []
    try:
        keyword_data = await get_keyword_search_volumes(all_seeds, location_name)
    except Exception as e:
        yield f"> Warning: Could not pull keyword data from DataForSEO: {e}\n\n"

    # ── Build data sections for the prompt ──────────────────────────────
    data_sections: list[str] = []

    if keyword_data:
        data_sections.append(format_keyword_volumes(keyword_data))

        # Compute summary stats
        total_volume = sum(kw.get("search_volume") or 0 for kw in keyword_data)
        cpcs = [float(kw["cpc"]) for kw in keyword_data if kw.get("cpc") and float(kw.get("cpc", 0)) > 0]
        avg_cpc = sum(cpcs) / len(cpcs) if cpcs else 0
        max_cpc_kw = max(keyword_data, key=lambda x: float(x.get("cpc") or 0), default=None)

        stats_lines = [
            "Keyword Summary Statistics:",
            f"  Total monthly search volume across all seeds: {total_volume:,}",
        ]
        if avg_cpc:
            stats_lines.append(f"  Average CPC: ${avg_cpc:.2f}")
        if max_cpc_kw and max_cpc_kw.get("cpc"):
            stats_lines.append(
                f"  Highest CPC keyword: \"{max_cpc_kw['keyword']}\" at ${float(max_cpc_kw['cpc']):.2f}"
            )
        data_sections.append("\n".join(stats_lines))

        # Separate keywords by intent for easier grouping
        high_intent = [
            kw for kw in keyword_data
            if (kw.get("search_volume") or 0) > 0
            and any(t in kw.get("keyword", "").lower() for t in [city.lower(), "near me", "best", "hire", "company"])
        ]
        emergency = [
            kw for kw in keyword_data
            if (kw.get("search_volume") or 0) > 0
            and any(t in kw.get("keyword", "").lower() for t in ["emergency", "24 hour", "urgent"])
        ]

        if high_intent:
            lines = ["High-Intent Keywords (use for primary ad group):"]
            for kw in sorted(high_intent, key=lambda x: x.get("search_volume") or 0, reverse=True):
                vol = kw.get("search_volume") or 0
                cpc = kw.get("cpc")
                cpc_str = f"${float(cpc):.2f}" if cpc else "N/A"
                lines.append(f"  \"{kw['keyword']}\": {vol:,}/mo, CPC {cpc_str}")
            data_sections.append("\n".join(lines))

        if emergency:
            lines = ["Emergency-Intent Keywords (use for emergency ad group):"]
            for kw in sorted(emergency, key=lambda x: x.get("search_volume") or 0, reverse=True):
                vol = kw.get("search_volume") or 0
                cpc = kw.get("cpc")
                cpc_str = f"${float(cpc):.2f}" if cpc else "N/A"
                lines.append(f"  \"{kw['keyword']}\": {vol:,}/mo, CPC {cpc_str}")
            data_sections.append("\n".join(lines))

        yield f"> Found data for {len(keyword_data)} keywords. Total monthly volume: {total_volume:,}.\n\n"
    else:
        data_sections.append(
            "No keyword volume data available from DataForSEO. "
            "Use your knowledge of typical CPCs and search volumes for this market."
        )

    yield "> Building ad copy with Claude...\n\n"
    yield "---\n\n"

    # ── Build user prompt ───────────────────────────────────────────────
    prompt_lines = [
        f"Create a complete Google Ads campaign for **{business_name}**, a {service} serving {location}.",
        "",
        f"**Service:** {service}",
        f"**Location:** {location}",
        f"**Business Name:** {business_name}",
    ]

    if usp:
        prompt_lines.append(f"**Unique Selling Propositions:** {usp}")

    if landing_url:
        prompt_lines.append(f"**Landing Page URL:** {landing_url}")

    if budget:
        prompt_lines.append(f"**Monthly Ad Budget:** {budget}")

    if notes:
        prompt_lines += ["", "**Additional Notes:**", notes]

    if strategy_context and strategy_context.strip():
        prompt_lines += [
            "",
            "**Strategy direction from account manager — follow this:**",
            strategy_context.strip(),
        ]

    if data_sections:
        prompt_lines += [
            "",
            "## KEYWORD & CPC DATA (use this to inform keyword targeting and show real values)",
            "",
        ]
        prompt_lines.append("\n\n".join(data_sections))

    prompt_lines += [
        "",
        "Write the complete Google Ads campaign now. Start immediately with the # heading.",
        "Include character counts after each headline and description.",
        "Use the real CPC and volume data above to prioritize keywords by value.",
    ]

    user_prompt = "\n".join(prompt_lines)

    # ── Stream from Claude ──────────────────────────────────────────────
    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
