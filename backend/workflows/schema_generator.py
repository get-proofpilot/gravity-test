"""
Schema Generator Workflow
Generates valid, Google-compliant JSON-LD structured data (LocalBusiness, FAQPage,
Service, BreadcrumbList, AggregateRating, etc.) for a home service business —
ready to copy-paste into any page.
"""

import anthropic
from typing import AsyncGenerator

SYSTEM_PROMPT = """You are ProofPilot's Schema Markup Specialist. You generate valid, Google-compliant JSON-LD structured data that improves search visibility and enables rich results.

Your output must follow this exact report structure:

### 1. Schema Strategy Overview
- Which schema types are most valuable for this business
- Expected search impact (rich results, knowledge panel, etc.)
- Implementation priority

### 2. LocalBusiness Schema
```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness" (or more specific subtype like "Electrician"),
  ...complete valid JSON-LD
}
```
Implementation notes and where to place it.

### 3. Service Schema
For each major service, generate an individual Service schema.

### 4. FAQPage Schema
Generate FAQ schema with 5-8 relevant questions and answers for the business type and location.

### 5. Article / BlogPosting Schema (if requested)
Template for blog posts.

### 6. BreadcrumbList Schema
For site navigation.

### 7. Review / AggregateRating Schema
Template for review markup.

### 8. Implementation Guide
- Where to add each schema (which pages)
- How to validate (Google Rich Results Test link)
- Common mistakes to avoid
- Testing checklist

## Rules
- Every JSON-LD block must be VALID, complete, and ready to copy-paste
- Use realistic data based on the inputs provided
- Include Google's recommended properties, not just required ones
- Add comments explaining each section
- Use specific @type subtypes when available (e.g. "Electrician" instead of generic "LocalBusiness")
- All JSON must be syntactically correct — no trailing commas, no comments inside the JSON itself (put comments outside the code blocks)
- Include <script type="application/ld+json"> wrapper tags around each schema block so it's truly copy-paste ready
- For FAQPage schema, write questions the way real homeowners search Google — not corporate FAQ fluff"""


async def run_schema_generator(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Streams JSON-LD schema markup for a home service business.

    inputs keys:
        business_name    e.g. "All Thingz Electric"
        business_type    e.g. "electrician"
        location         e.g. "Chandler, AZ"
        schema_types     comma-separated types (default: "LocalBusiness, FAQPage, Service")
        phone            business phone (optional)
        address          full business address (optional)
        website          business URL (optional)
        services_list    comma-separated services offered (optional)
        hours            business hours (optional)
        notes            additional context — FAQ questions, specific pages, etc. (optional)
    """
    business_name = inputs.get("business_name", client_name).strip()
    business_type = inputs.get("business_type", "home service business").strip()
    location      = inputs.get("location", "").strip()
    schema_types  = inputs.get("schema_types", "LocalBusiness, FAQPage, Service").strip()
    phone         = inputs.get("phone", "").strip()
    address       = inputs.get("address", "").strip()
    website       = inputs.get("website", "").strip()
    services_list = inputs.get("services_list", "").strip()
    hours         = inputs.get("hours", "").strip()
    notes         = inputs.get("notes", "").strip()

    yield f"> Generating schema markup for **{client_name}**...\n\n---\n\n"

    # ── Build the user prompt ──────────────────────────────
    lines = [
        f"Generate complete JSON-LD structured data for **{business_name}**, a {business_type} serving {location}.",
        "",
        f"**Schema types to generate:** {schema_types}",
    ]

    if phone:
        lines.append(f"**Phone:** {phone}")

    if address:
        lines.append(f"**Address:** {address}")

    if website:
        lines.append(f"**Website:** {website}")

    if services_list:
        lines.append(f"**Services offered:** {services_list}")

    if hours:
        lines.append(f"**Business hours:** {hours}")

    if notes:
        lines += [
            "",
            "**Additional context and instructions:**",
            f"{notes}",
        ]

    if strategy_context and strategy_context.strip():
        lines += [
            "",
            "**Strategy direction from account manager — follow this:**",
            f"{strategy_context.strip()}",
        ]

    lines += [
        "",
        "Generate all schema blocks now. Every JSON-LD block must be valid, complete, and ready to copy-paste. Start with the Strategy Overview.",
    ]

    user_prompt = "\n".join(lines)

    # ── Stream from Claude ─────────────────────────────────
    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
