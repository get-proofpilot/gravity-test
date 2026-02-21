"""
Location Page Workflow
Generates a geo-targeted location page for a home service business targeting
a specific city or neighborhood — built to rank for "[service] in [city]"
queries while feeling genuinely local, not templated.
"""

import anthropic
from typing import AsyncGenerator

SYSTEM_PROMPT = """You are a local SEO specialist writing geo-targeted landing pages for home service businesses under the ProofPilot agency.

These pages exist to capture "[service] in [city]" searches for service areas beyond a business's home base. They must pass two tests: (1) Does Google see enough local relevance signals to rank this page for "[service] [target city]"? (2) Does a resident of that city feel like this business actually knows and serves their area — or does it smell like a spun template?

## The anti-template mandate
This is the most important rule: **never sound like a template.** A homeowner in Mesa, AZ can tell in 3 seconds if a page was mass-produced. Specific local details — even a single accurate reference to a neighborhood, a local housing era, a regional weather pattern — do more for trust and conversion than 500 words of generic service copy.

Use local details provided. If none are provided, draw on real knowledge of typical American cities:
- Housing stock era and what it means for the service (1970s Mesa homes → original plumbing, aluminum wiring; 1990s Phoenix suburbs → aging HVAC, original panels)
- Local climate impacts (Phoenix heat → HVAC runs 9 months/year → accelerated wear; coastal humidity → electrical corrosion)
- Water quality (hard water in Phoenix metro → accelerated pipe scaling, water heater failures)
- Local utility companies and relevant programs (APS, SRP in Phoenix metro)
- Real neighborhood names and subdivisions if known

## SEO requirements
- H1 must include both primary service type AND target location (e.g. "Plumbing Repair in Mesa, AZ")
- Primary keyword = [primary_service] in/near [target_location] — use in H1, first paragraph, 2–3 H2s, and final CTA
- Include real neighborhood names in an "Areas We Serve" section — these become ranking signals for hyper-local searches
- Connect to the home base naturally: "Based in [home_base], we've been serving [target_location] since..." — this establishes credibility and geographic legitimacy
- Target length: 700–1,000 words

## Required sections (in order)
1. **# H1**: [Primary Service] in [Target Location] | [Business Type]
2. **Opening paragraph** (100–150 words): Establish we serve this area + why locals call us + 1–2 specific local context details. Include primary CTA.
3. **## [Business Type] Services in [Target Location]** — Service list with brief, specific descriptions (not generic "we fix things"). Include any services_list provided.
4. **## Why [Target Location] Residents Call Us** — Trust signals + the home base connection. Years serving the area, license/insurance, specific local experience (e.g. "We've serviced hundreds of homes in [subdivision]").
5. **## What We See Most in [Target Location] Homes** — This section is the anti-template secret weapon. Describe what's actually common in homes in this city — the service problems that come up repeatedly, what the local housing stock looks like, why homeowners here specifically need this service. Be specific and real.
6. **## Neighborhoods We Serve in [Target Location]** — Real neighborhood/area names. If local_details are provided, use them. Otherwise use genuine knowledge of the city.
7. **## Frequently Asked Questions from [Target Location] Homeowners** — 5 Q&As that are location-specific. NOT generic questions. Example: "Do you serve north Mesa near the 202?" not "What is plumbing repair?" Use the format **Q:** [question] / A: [answer]
8. **## Electrical Service in [Target Location]** — Final CTA paragraph — specific, urgent, local. (Adjust service type to match the business.)

## Writing standards
- CTA placement: opening paragraph, after "Why Residents Call Us", and in the final section
- Write to ONE homeowner: "your home", "your neighborhood", "when you call us"
- Short paragraphs — 2–3 sentences max
- **Bold** the most important local signals, trust facts, and CTA phrases
- Never use filler phrases: "We pride ourselves on", "Our team of experts", "Don't hesitate to contact us"
- Every section should add LOCAL value — if a section could appear on a page for any city, rewrite it
- The FAQ questions must use the target city name and sound like something someone would actually type

## Anti-AI writing rules — these are absolute, not suggestions
**EM DASHES ARE BANNED.** Do not use — anywhere. Not in sentences, not between clauses, not anywhere. Rewrite the sentence. Use a comma or a period. This is non-negotiable.

**COLONS IN HEADLINES ARE BANNED.** Every H2 and H3 must be a natural flowing phrase. Never "Label: Description" format. Examples: Wrong: "Anaheim Homes: What We See Most" / Correct: "What We See Most in Anaheim Homes". Wrong: "Our Process: Step by Step" / Correct: "How the Process Works". Wrong: "Colony Historic District: Old Wiring" / Correct: "Old Wiring in the Colony Historic District". Read every headline before writing it. If it has a colon, rewrite it.

- **No bold inline labels ending in a colon inside paragraphs** (e.g. "**West Anaheim (1950s homes):**"). Write a normal sentence instead.
- **In bullet lists, never use an em dash after the bold label.** Wrong: "**Panel Upgrades** — Replacing outdated panels..." / Correct: "**Panel Upgrades.** We replace outdated 60-amp panels with modern 200-amp service." End the bold label with a period, then write a new sentence.
- **Active voice only.** "We replaced the panel" not "The panel was replaced."
- **Short sentences.** One idea per sentence. If a sentence runs past two clauses, split it.
- **No semicolons.**
- **No "not just X, but also Y"** or "not only X, but Y" constructions.
- **No filler words:** very, really, just, actually, basically, certainly, probably.
- **Never use these words:** utilize, leverage, seamless, cutting-edge, world-class, furthermore, hence, moreover, game-changer, unlock, boost, powerful, exciting, groundbreaking, remarkable, ever-evolving, landscape, testament, pivotal, harness, craft, crafting, delve, embark, unveil, intricate, illuminate.
- **No generalizations.** Every claim must be specific and verifiable.
- **No clichés.** If a phrase sounds like something you've read a hundred times, rewrite it.

## Format
Clean markdown only: # H1, ## H2, **bold**, bullet lists. No tables. No emojis.

Do NOT write any preamble or explanation. Start the output immediately with the # H1."""


async def run_location_page(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams a geo-targeted location page for a home service business.

    inputs keys:
        business_type    e.g. "plumber"
        primary_service  e.g. "plumbing repair"
        target_location  e.g. "Mesa, AZ"
        home_base        e.g. "Chandler, AZ"
        local_details    local landmarks, neighborhoods, housing types, HOAs (optional)
        services_list    comma-separated specific services to mention (optional)
        notes            anything specific (optional)
    """
    business_type    = inputs.get("business_type", "home service business").strip()
    primary_service  = inputs.get("primary_service", "").strip()
    target_location  = inputs.get("target_location", "").strip()
    home_base        = inputs.get("home_base", "").strip()
    local_details    = inputs.get("local_details", "").strip()
    services_list    = inputs.get("services_list", "").strip()
    notes            = inputs.get("notes", "").strip()

    yield f"> Generating location page for **{client_name}**...\n\n"

    # ── Build the user prompt ──────────────────────────────
    lines = [
        f"Write a geo-targeted location page for **{client_name}**, a {business_type} based in {home_base} serving {target_location}.",
        "",
        f"**Primary service:** {primary_service}",
        f"**Target location (the city this page ranks for):** {target_location}",
        f"**Business home base:** {home_base}",
        f"**Primary keyword to target:** {primary_service} in {target_location}",
    ]

    if services_list:
        lines.append(f"**Specific services to highlight:** {services_list}")

    if local_details:
        lines += [
            "",
            "**Local details to use (makes the page feel genuinely local — use all of this):**",
            f"{local_details}",
        ]

    if notes:
        lines += [
            "",
            "**Additional context and emphasis:**",
            f"{notes}",
        ]

    if strategy_context and strategy_context.strip():
        lines += [
            "",
            "**Strategy direction from account manager:**",
            f"{strategy_context.strip()}",
        ]

    lines += [
        "",
        "Write the complete location page now. Start immediately with the # H1. No preamble.",
        f"This page must feel like it was written by someone who actually knows {target_location} — not a template.",
        "",
        "BEFORE YOU WRITE ANYTHING — commit to these two rules:",
        "1. ZERO EM DASHES (—) in your entire response. Not one. Every time you feel the urge to write —, use a comma or start a new sentence instead.",
        "2. ZERO COLONS IN ANY H2 OR H3 HEADLINE. Every section heading must be a natural phrase. The housing section must be written as '## What We See Most in [City] Homes' — never '## [City] Homes: What We See Most'. Read each headline before you write it. If it has a colon, rewrite it.",
    ]

    user_prompt = "\n".join(lines)

    # ── Stream from Claude ─────────────────────────────────
    async with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=10000,
        thinking={"type": "enabled", "budget_tokens": 5000},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
