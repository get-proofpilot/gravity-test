"""
Programmatic Content Agent — bulk content generation at scale.

Generates unique, data-driven content for multiple locations, services,
or keywords in a single streaming session. Each page gets independent
DataForSEO research injected so content is genuinely local, not templated.

Supported content types:
  location-pages  — geo-targeted pages for multiple cities
  service-pages   — conversion pages for multiple services in one city
  blog-posts      — SEO blog posts for multiple target keywords

inputs keys:
  content_type     "location-pages" | "service-pages" | "blog-posts"
  business_type    e.g. "electrician"
  primary_service  e.g. "electrical service" (location-pages)
  location         e.g. "Chandler, AZ" (service-pages / blog-posts)
  home_base        e.g. "Chandler, AZ" (location-pages)
  items_list       newline-separated cities / services / keywords
  services_list    optional comma-separated services to mention
  differentiators  optional business differentiators
  notes            optional extra context
"""

import anthropic
from typing import AsyncGenerator

from utils.dataforseo import (
    get_location_research,
    format_location_research,
    get_keyword_search_volumes,
    get_organic_serp,
    build_location_name,
    build_service_keyword_seeds,
    format_keyword_volumes,
    format_organic_competitors,
)


# ── System prompts per content type ──────────────────────────────────────────

LOCATION_PAGE_SYSTEM = """You are a local SEO specialist writing geo-targeted landing pages for home service businesses under the ProofPilot agency.

These pages exist to capture "[service] in [city]" searches for service areas beyond a business's home base. They must pass two tests: (1) Does Google see enough local relevance signals to rank this page for "[service] [target city]"? (2) Does a resident of that city feel like this business actually knows and serves their area — or does it smell like a spun template?

## The anti-template mandate — CRITICAL for programmatic content
This is the most important rule: **never sound like a template.** You are writing one page in a batch of many. Every page MUST be genuinely unique. A homeowner can tell in 3 seconds if a page was mass-produced. Specific local details — even a single accurate reference to a neighborhood, a local housing era, a regional weather pattern — do more for trust and conversion than 500 words of generic service copy.

You will be given real market research data for this location. USE IT:
- Reference specific competitor businesses by name (from Maps/SERP data)
- Use actual keyword volumes to inform your headings and content focus
- Incorporate local competitor insights to differentiate the client

Use local details provided. If none are provided, draw on real knowledge of typical American cities:
- Housing stock era and what it means for the service (1970s Mesa homes → original plumbing, aluminum wiring; 1990s Phoenix suburbs → aging HVAC, original panels)
- Local climate impacts (Phoenix heat → HVAC runs 9 months/year → accelerated wear; coastal humidity → electrical corrosion)
- Water quality (hard water in Phoenix metro → accelerated pipe scaling, water heater failures)
- Local utility companies and relevant programs (APS, SRP in Phoenix metro)
- Real neighborhood names and subdivisions if known

## SEO requirements
- H1 must include both primary service type AND target location (e.g. "Plumbing Repair in Mesa, AZ")
- Primary keyword = [primary_service] in/near [target_location] — use in H1, first paragraph, 2–3 H2s, and final CTA
- Include real neighborhood names in an "Areas We Serve" section
- Connect to the home base naturally: "Based in [home_base], we've been serving [target_location] since..."
- Target length: 700–1,000 words

## Required sections (in order)
1. **# H1**: [Primary Service] in [Target Location] | [Business Type]
2. **Opening paragraph** (100–150 words): Establish we serve this area + why locals call us + 1–2 specific local context details. Include primary CTA.
3. **## [Business Type] Services in [Target Location]**: Service list with brief, specific descriptions.
4. **## Why [Target Location] Residents Call Us**: Trust signals + the home base connection.
5. **## [Target Location] Homes: What We See Most**: Anti-template secret weapon — describe what's actually common in homes in this city.
6. **## Neighborhoods We Serve in [Target Location]**: Real neighborhood/area names.
7. **## Frequently Asked Questions from [Target Location] Homeowners**: 5 Q&As that are location-specific. Use the format **Q: [question]** / A: [answer]
8. **## Get Fast, Local Service in [Target Location]**: Final CTA paragraph.

## Writing standards
- CTA placement: opening paragraph, after "Why Residents Call Us", and in the final section
- Write to ONE homeowner: "your home", "your neighborhood", "when you call us"
- Short paragraphs — 2–3 sentences max
- **Bold** the most important local signals, trust facts, and CTA phrases
- Never use filler phrases: "We pride ourselves on", "Our team of experts", "Don't hesitate to contact us"
- Every section should add LOCAL value — if a section could appear on a page for any city, rewrite it

## Format
Clean markdown only: # H1, ## H2, **bold**, bullet lists. No tables. No emojis.

Do NOT write any preamble or explanation. Start the output immediately with the # H1."""


SERVICE_PAGE_SYSTEM = """You are a conversion copywriter and local SEO specialist writing service pages for home service businesses under the ProofPilot agency.

Each page targets a specific "[service] in [city]" keyword and must convert visitors who are ready to book. You will be given real market research data — USE IT to reference competitors, use real keyword volumes, and differentiate.

## Anti-template mandate
You are writing one page in a batch of many service pages. Each MUST be genuinely unique. Vary your openings, section angles, and supporting details. Never use the same structure filler across pages.

## SEO requirements
- H1 = exact service + city (e.g. "Panel Upgrade in Chandler, AZ")
- Primary keyword in first 100 words, 2+ H2s, and final CTA
- Target length: 800–1,200 words

## Required sections (in order)
1. **# H1** + hero paragraph (problem-first CTA)
2. **## What's Included** — specific scope, not vague promises
3. **## Trust Signals** — license, insurance, years, reviews, certifications
4. **## Honest Pricing** — real price ranges + cost drivers (builds trust, reduces bounce)
5. **## Our Process** — step-by-step from call to completion
6. **## Local Experience** — neighborhoods served, local context, housing stock insights
7. **## Frequently Asked Questions** — 5+ real Google questions. Format: **Q:** / A:
8. **## Final CTA** — specific urgency, local

## Writing standards
- Customer's problem first, "you/your" language, short paragraphs
- **Bold** key claims, prices, guarantees
- No filler: "We pride ourselves on", "Our team of experts"
- Vary sentence structure and opening hooks between pages

## Format
Clean markdown: # H1, ## H2, **bold**, bullet lists. No tables. No emojis.

Start immediately with the # H1. No preamble."""


BLOG_POST_SYSTEM = """You are an SEO content writer specializing in home service businesses, writing under the ProofPilot agency.

Each blog post targets a specific informational keyword and must rank while providing genuine value. You will be given real market research data — USE IT to add specificity.

## Anti-template mandate
You are writing one post in a batch of many. Each MUST have a unique angle, unique hook, and unique supporting details. Never repeat the same opening formula or section pattern.

## Keyword strategy
- Primary keyword in H1, first 100 words, 2+ H2s, and conclusion
- Semantic variations throughout (don't stuff the exact keyword)
- Include local city references naturally

## Required structure
1. **META:** [compelling 160-char meta description with keyword]
2. **# H1** [keyword-driven, compelling title]
3. **## Key Takeaways** — 3–5 bullet summary (for featured snippets)
4. **Hook intro** (100–150 words) — grab attention, establish the problem, promise the answer
5. **## Sections** (5–7 H2s) — each with keyword variation, real data, actionable advice
6. **## FAQ** — 3–5 real Google questions. Format: **Q:** / A:
7. **## Ready to Get Started?** — Local CTA with city, service, call-to-action

## Writing standards
- Real numbers, real costs, real trade language — not generic AI filler
- 1,500–2,000 words, scannable with bullets/lists
- Local references: city, neighborhoods, regional context
- Write for someone with a problem NOW, not an academic audience
- Vary your openings and angles between posts

## Format
Clean markdown: # H1, ## H2, ### H3, **bold**, bullet lists. No tables. No emojis.

Start with META:. No preamble."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_items(text: str) -> list[str]:
    """Parse a newline-separated (or comma-separated) list into clean items."""
    if not text or not text.strip():
        return []

    # Try newlines first; fall back to commas if only one line
    lines = text.strip().split("\n")
    if len(lines) == 1 and "," in lines[0]:
        lines = lines[0].split(",")

    items = []
    for line in lines:
        cleaned = line.strip().strip("-").strip("•").strip("*").strip()
        if cleaned:
            items.append(cleaned)

    return items


def _get_system_prompt(content_type: str) -> str:
    """Return the system prompt for the given content type."""
    prompts = {
        "location-pages": LOCATION_PAGE_SYSTEM,
        "service-pages": SERVICE_PAGE_SYSTEM,
        "blog-posts": BLOG_POST_SYSTEM,
    }
    return prompts.get(content_type, LOCATION_PAGE_SYSTEM)


async def _research_item(
    content_type: str,
    business_type: str,
    primary_service: str,
    item: str,
    location: str,
    home_base: str,
) -> dict:
    """Research a single item via DataForSEO. Returns empty dict on failure."""
    try:
        if content_type == "location-pages":
            service = primary_service or business_type
            return await get_location_research(service, item)

        elif content_type == "service-pages":
            return await get_location_research(item, location)

        elif content_type == "blog-posts":
            # For blog posts, research the keyword + location
            if not location:
                return {}
            location_name = build_location_name(location)
            city = location.split(",")[0].strip()
            seeds = [item] + build_service_keyword_seeds(
                item.split()[0] if item.split() else business_type, city, 3
            )
            organic, volumes = None, None
            try:
                import asyncio
                organic_res, volumes_res = await asyncio.gather(
                    get_organic_serp(item, location_name, 5),
                    get_keyword_search_volumes(seeds, location_name),
                    return_exceptions=True,
                )
                organic = [] if isinstance(organic_res, Exception) else organic_res
                volumes = [] if isinstance(volumes_res, Exception) else volumes_res
            except Exception:
                organic, volumes = [], []
            return {"organic": organic or [], "maps": [], "volumes": volumes or [], "keyword": item}

        return {}
    except Exception:
        return {}


def _format_research(research: dict, item: str) -> str:
    """Format research data for prompt injection based on content type."""
    if not research:
        return f"No research data available for \"{item}\" — use your own knowledge to write genuinely unique content."

    sections = [f"## MARKET RESEARCH DATA — \"{item}\"\n"]

    maps = research.get("maps", [])
    organic = research.get("organic", [])
    volumes = research.get("volumes", [])

    from utils.dataforseo import (
        format_maps_competitors,
        format_organic_competitors,
        format_keyword_volumes,
    )

    if maps:
        sections.append(format_maps_competitors(maps))
    if organic:
        sections.append(format_organic_competitors(organic))
    if volumes:
        sections.append(format_keyword_volumes(volumes))
    if not any([maps, organic, volumes]):
        sections.append(f"No DataForSEO data available — use your knowledge to write genuinely local content.")

    return "\n\n".join(sections)


def _build_user_prompt(
    content_type: str,
    business_type: str,
    primary_service: str,
    item: str,
    location: str,
    home_base: str,
    services_list: str,
    differentiators: str,
    notes: str,
    research_text: str,
    strategy_context: str,
    client_name: str,
) -> str:
    """Build the user prompt for a single page/post generation."""

    if content_type == "location-pages":
        lines = [
            f"Write a geo-targeted location page for **{client_name}**, a {business_type} based in {home_base} serving {item}.",
            "",
            f"**Primary service:** {primary_service}",
            f"**Target location (the city this page ranks for):** {item}",
            f"**Business home base:** {home_base}",
            f"**Primary keyword to target:** {primary_service} in {item}",
        ]
        if services_list:
            lines.append(f"**Specific services to highlight:** {services_list}")
        if differentiators:
            lines.append(f"**Business differentiators:** {differentiators}")

    elif content_type == "service-pages":
        lines = [
            f"Write a conversion-optimized service page for **{client_name}**, a {business_type} in {location}.",
            "",
            f"**Service this page is about:** {item}",
            f"**Location:** {location}",
            f"**Primary keyword to target:** {item} in {location}",
        ]
        if differentiators:
            lines.append(f"**Business differentiators:** {differentiators}")

    elif content_type == "blog-posts":
        lines = [
            f"Write a publish-ready SEO blog post for **{client_name}**, a {business_type} in {location}.",
            "",
            f"**Target keyword:** {item}",
            f"**Location:** {location}",
        ]

    else:
        lines = [f"Write content about \"{item}\" for **{client_name}**."]

    if notes:
        lines += ["", f"**Additional context:** {notes}"]

    if strategy_context and strategy_context.strip():
        lines += ["", f"**Strategy direction:** {strategy_context.strip()}"]

    lines += [
        "",
        research_text,
        "",
        "Write the complete page now. Start immediately with the output (# H1 or META:). No preamble.",
        f"This content must feel genuinely unique — not like a template applied to \"{item}\".",
    ]

    return "\n".join(lines)


# ── Main workflow ────────────────────────────────────────────────────────────

async def run_programmatic_content(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Orchestrates programmatic content generation at scale.
    For each item in the list:
      1. Research via DataForSEO
      2. Generate unique content via Claude
      3. Stream with progress markers
    """
    content_type    = inputs.get("content_type", "location-pages").strip()
    business_type   = inputs.get("business_type", "home service business").strip()
    primary_service = inputs.get("primary_service", "").strip()
    location        = inputs.get("location", "").strip()
    home_base       = inputs.get("home_base", "").strip()
    items_list_raw  = inputs.get("items_list", "").strip()
    services_list   = inputs.get("services_list", "").strip()
    differentiators = inputs.get("differentiators", "").strip()
    notes           = inputs.get("notes", "").strip()

    items = _parse_items(items_list_raw)
    if not items:
        yield "> **Error:** No items found in the list. Please provide at least one item (one per line).\n"
        return

    total = len(items)
    type_labels = {
        "location-pages": "location pages",
        "service-pages": "service pages",
        "blog-posts": "blog posts",
    }
    type_label = type_labels.get(content_type, "pages")

    yield f"> Starting **Programmatic Content Agent** for **{client_name}**...\n"
    yield f"> Content type: **{type_label.title()}** | **{total} pages** | Business: {business_type}\n\n"

    system_prompt = _get_system_prompt(content_type)

    for i, item in enumerate(items, 1):
        # ── Page separator ──
        if i > 1:
            yield "\n\n---\n\n---\n\n"

        yield f"> **[{i}/{total}] Researching {item}...**\n\n"

        # ── Research via DataForSEO ──
        research = await _research_item(
            content_type, business_type, primary_service,
            item, location, home_base,
        )

        # Report research results
        if research:
            maps_count = len(research.get("maps", []))
            organic_count = len(research.get("organic", []))
            kw_count = len(research.get("volumes", []))
            if maps_count or organic_count or kw_count:
                yield f"> Found {maps_count} Maps competitors, {organic_count} organic results, {kw_count} keyword data points\n\n"
            else:
                yield f"> No DataForSEO data returned — generating with local knowledge\n\n"
        else:
            yield f"> DataForSEO research unavailable — generating with local knowledge\n\n"

        yield f"> **Writing {type_label.rstrip('s')} for {item}...**\n\n"

        # ── Build prompt with research data ──
        research_text = _format_research(research, item)
        user_prompt = _build_user_prompt(
            content_type, business_type, primary_service, item,
            location, home_base, services_list, differentiators,
            notes, research_text, strategy_context, client_name,
        )

        # ── Stream Claude response ──
        async with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=8000,
            thinking={"type": "adaptive"},
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    # ── Final status ──
    yield f"\n\n---\n\n> Programmatic content generation complete — **{total} {type_label}** created for **{client_name}**\n"
