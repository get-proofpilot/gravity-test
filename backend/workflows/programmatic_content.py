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


COMPARISON_POST_SYSTEM = """You are an expert home service content writer creating comparison content that captures high-intent "X vs Y" search traffic. Writing under the ProofPilot agency.

These posts target searchers comparing products, brands, materials, or approaches — people who are deep in the buying process and close to hiring a professional.

## Anti-template mandate
You are writing one comparison post in a batch of many. Each MUST have a unique angle, unique data points, and unique recommendation logic. Never use the same comparison framework twice.

## Content strategy
Comparison posts convert because they:
- Answer the exact question someone types into Google
- Position the client as a knowledgeable expert (not a salesperson)
- Naturally lead to "hire a professional to help you decide" CTA

## Required structure
1. **META:** [160-char meta description with both comparison items + winner hint]
2. **# H1:** [Item A] vs [Item B]: [Which Is Right for Your Home/Business?]
3. **## Quick Answer** — 3-4 sentences for featured snippet capture. Give the verdict immediately.
4. **## Key Differences at a Glance** — Bullet comparison (cost, lifespan, best-for, pros, cons)
5. **## [Item A]: What You Need to Know** — Deep dive on first option. Real costs, real specs, real trade experience.
6. **## [Item B]: What You Need to Know** — Deep dive on second option. Same depth.
7. **## Head-to-Head: [Item A] vs [Item B]** — Direct comparison across 4-6 factors (cost, longevity, efficiency, installation complexity, maintenance, resale value)
8. **## When to Choose [Item A]** — Specific scenarios
9. **## When to Choose [Item B]** — Specific scenarios
10. **## What We Recommend (and Why)** — Expert recommendation based on the local market + climate + housing stock
11. **## FAQ** — 5+ real comparison questions. Format: **Q:** / A:
12. **## Need Help Deciding?** — CTA positioning the client as the expert who can assess their specific situation

## Writing standards
- Real numbers: actual costs, actual lifespans, actual specs
- Trade-specific language (what a real technician would say, not marketing copy)
- Local context: how climate, water quality, utility rates affect the comparison
- Honest: acknowledge when one option is genuinely better — builds trust
- 1,800–2,500 words
- **Bold** key cost figures, specs, and recommendations

## Format
Clean markdown: # H1, ## H2, **bold**, bullet lists. No emojis.

Start with META:. No preamble."""


COST_GUIDE_SYSTEM = """You are a pricing transparency expert writing cost guide content for home service businesses under the ProofPilot agency.

"How much does X cost" queries are the highest-intent informational keywords in home services. People searching these are about to hire someone. Your job is to give them real numbers, build trust through transparency, and position the client as the honest expert.

## Anti-template mandate
You are writing one cost guide in a batch of many. Each MUST have unique pricing data, unique cost drivers, and unique local context. Never reuse the same price tables or generic ranges.

## Why cost guides convert
- They answer the #1 question every homeowner has before calling
- Transparent pricing builds instant trust vs competitors who hide prices
- Featured snippet potential is massive — Google loves price tables
- They rank for "cost", "price", "how much", "average cost" variants simultaneously

## Required structure
1. **META:** [160-char meta description with price range + location]
2. **# H1:** How Much Does [Service] Cost in [City], [State]? ([Year] Pricing Guide)
3. **## Quick Answer** — Price range in first 2 sentences (for featured snippet). "In [city], [service] typically costs **$X–$Y**."
4. **## [City] [Service] Cost Breakdown** — Table-style breakdown of specific scenarios (basic, standard, premium, emergency)
5. **## What Drives the Cost** — 4-6 specific factors with dollar impact for each. Not vague "it depends" — give actual ranges per factor.
6. **## Hidden Costs to Watch For** — Permits, inspections, code upgrades, disposal fees, access issues. Real dollar amounts.
7. **## [City]-Specific Cost Factors** — Local context: permit fees in this municipality, code requirements, typical housing situations that affect price.
8. **## How to Get the Best Price** — Actionable tips. Not "get multiple quotes" — real insider advice.
9. **## Is It Worth the Investment?** — ROI angle: how this service saves money long-term, increases home value, prevents costly emergencies.
10. **## FAQ** — 5+ cost-related questions. Format: **Q:** / A: with real dollar answers.
11. **## Get a Free Estimate in [City]** — CTA with "now that you know the real costs" angle.

## Writing standards
- **Every price must be real and defensible** — use current market rates, not made-up numbers
- Include actual permit fees, material costs, labor rates for the specific city
- Reference local housing stock: "Most [city] homes built in the [decade] have [specific situation] — expect $X–$Y for this."
- Acknowledge regional variation: utility costs, code requirements, labor market
- 1,500–2,200 words
- **Bold** all price figures
- Use bullet lists for cost breakdowns — scannable, not buried in paragraphs

## Format
Clean markdown: # H1, ## H2, **bold**, bullet lists. No emojis.

Start with META:. No preamble."""


BEST_IN_CITY_SYSTEM = """You are a local authority writing "Best [Service] in [City]" content for home service businesses under the ProofPilot agency.

"Best X in Y" queries capture massive search volume and put your client at the top of a curated list. These are NOT generic listicles — they position the client as the authority who evaluates competitors, while naturally ranking #1 on the list.

## Anti-template mandate
You are writing one "best in" post in a batch of many. Each MUST reference real competitors from the SERP/Maps data, have unique evaluation criteria, and feel like genuinely local journalism — not a marketing page.

## Strategy
- Client is ALWAYS #1 on the list (they're the business publishing this)
- Competitors are referenced by real name from Google Maps data
- Evaluation criteria must be genuinely useful (not rigged to make the client win everything)
- This builds authority AND captures "best electrician in chandler" type searches

## Required structure
1. **META:** [160-char meta description — "We reviewed [city]'s top [services]. Here's who to call in [year]."]
2. **# H1:** Best [Service Providers] in [City], [State] ([Year] Reviews & Ratings)
3. **## How We Chose These [Service Providers]** — Evaluation criteria (licensing, reviews, response time, pricing transparency, specializations). Builds credibility.
4. **## The Top [5-7] [Service Providers] in [City]**
   - **### 1. [Client Business Name]** — The longest, most detailed write-up. Why they're #1. Specialties, service area, what customers say.
   - **### 2-5. [Real competitor names from Maps/SERP data]** — Shorter but fair write-ups. Real ratings, real review counts, real specialties. Reference real Google data.
5. **## What to Look for When Hiring a [Service Provider] in [City]** — Local-specific advice: licensing requirements in this state, what questions to ask, red flags.
6. **## Average [Service] Costs in [City]** — Quick cost reference to capture price-related searches.
7. **## FAQ** — 5+ questions about finding/hiring in this city. Format: **Q:** / A:
8. **## Ready to Book the Best?** — CTA back to the client.

## Writing standards
- Use REAL competitor data: actual Google ratings, actual review counts, actual business names
- Be fair but strategic: competitors get honest coverage, but client gets the most detailed and compelling write-up
- Local expertise: reference specific neighborhoods, local regulations, regional factors
- 1,800–2,500 words
- **Bold** ratings, review counts, and key differentiators

## CRITICAL: Competitor data usage
You WILL be given real Google Maps competitor data. USE IT:
- Reference businesses by their real name
- Quote real star ratings and review counts
- Mention real categories/specialties listed on their profile
- If a competitor has no website listed, note "no website available"
DO NOT fabricate competitor businesses. Only reference businesses from the provided data.

## Format
Clean markdown: # H1, ## H2, ### H3, **bold**, bullet lists. No emojis.

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
        "comparison-posts": COMPARISON_POST_SYSTEM,
        "cost-guides": COST_GUIDE_SYSTEM,
        "best-in-city": BEST_IN_CITY_SYSTEM,
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

        elif content_type in ("blog-posts", "comparison-posts", "cost-guides"):
            # Research the keyword/topic + location
            if not location:
                return {}
            location_name = build_location_name(location)
            city = location.split(",")[0].strip()

            # Build search query based on content type
            if content_type == "cost-guides":
                search_query = f"how much does {item} cost {city}"
            elif content_type == "comparison-posts":
                search_query = f"{item} {city}" if city.lower() not in item.lower() else item
            else:
                search_query = item

            seeds = [search_query] + build_service_keyword_seeds(
                item.split()[0] if item.split() else business_type, city, 3
            )
            if content_type == "cost-guides":
                seeds += [f"{item} cost {city}", f"{item} price {city}", f"average {item} cost"]
            elif content_type == "comparison-posts":
                seeds += [f"{item} pros and cons", f"{item} which is better"]

            organic, volumes = None, None
            try:
                import asyncio
                organic_res, volumes_res = await asyncio.gather(
                    get_organic_serp(search_query, location_name, 5),
                    get_keyword_search_volumes(seeds[:10], location_name),
                    return_exceptions=True,
                )
                organic = [] if isinstance(organic_res, Exception) else organic_res
                volumes = [] if isinstance(volumes_res, Exception) else volumes_res
            except Exception:
                organic, volumes = [], []
            return {"organic": organic or [], "maps": [], "volumes": volumes or [], "keyword": search_query}

        elif content_type == "best-in-city":
            # "Best X in Y" needs Maps data heavily — that's where competitor names come from
            service = item or business_type
            target_location = location or home_base
            if not target_location:
                return {}
            location_name = build_location_name(target_location)
            city = target_location.split(",")[0].strip()
            search_query = f"best {service} {city}"
            seeds = [search_query, f"{service} {city}", f"top {service} {city}", f"{service} near me {city}"]

            try:
                import asyncio
                from utils.dataforseo import get_local_pack
                maps_res, organic_res, volumes_res = await asyncio.gather(
                    get_local_pack(f"{service} {city}", location_name, 7),
                    get_organic_serp(search_query, location_name, 5),
                    get_keyword_search_volumes(seeds, location_name),
                    return_exceptions=True,
                )
                maps = [] if isinstance(maps_res, Exception) else maps_res
                organic = [] if isinstance(organic_res, Exception) else organic_res
                volumes = [] if isinstance(volumes_res, Exception) else volumes_res
            except Exception:
                maps, organic, volumes = [], [], []
            return {"organic": organic, "maps": maps, "volumes": volumes, "keyword": search_query}

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
    )

    if maps:
        sections.append(format_maps_competitors(maps))
    if organic:
        sections.append(format_organic_competitors(organic))
    if volumes:
        sections.append(format_keyword_volumes(volumes))
    if not any([maps, organic, volumes]):
        sections.append("No DataForSEO data available — use your knowledge to write genuinely local content.")

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

    elif content_type == "comparison-posts":
        lines = [
            f"Write a detailed comparison post for **{client_name}**, a {business_type} in {location}.",
            "",
            f"**Comparison topic:** {item}",
            f"**Location:** {location}",
            f"**Target keyword:** {item}",
        ]
        if differentiators:
            lines.append(f"**Business differentiators:** {differentiators}")

    elif content_type == "cost-guides":
        city = location.split(",")[0].strip() if location else ""
        lines = [
            f"Write a comprehensive cost guide for **{client_name}**, a {business_type} in {location}.",
            "",
            f"**Service to price:** {item}",
            f"**Location:** {location}",
            f"**Target keyword:** how much does {item} cost in {city}",
        ]
        if differentiators:
            lines.append(f"**Business differentiators:** {differentiators}")

    elif content_type == "best-in-city":
        city = location.split(",")[0].strip() if location else ""
        lines = [
            f"Write a 'Best {business_type}s in {city}' article for **{client_name}**.",
            f"**{client_name} is #1 on the list.** They are the business publishing this content.",
            "",
            f"**Service type:** {item or business_type}",
            f"**Location:** {location}",
            f"**Target keyword:** best {item or business_type} in {city}",
        ]
        if differentiators:
            lines.append(f"**Why {client_name} is #1:** {differentiators}")

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
        "comparison-posts": "comparison posts",
        "cost-guides": "cost guides",
        "best-in-city": "best-in-city posts",
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
                yield "> No DataForSEO data returned — generating with local knowledge\n\n"
        else:
            yield "> DataForSEO research unavailable — generating with local knowledge\n\n"

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
