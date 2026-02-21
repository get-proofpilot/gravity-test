"""
GEO Content Audit Workflow
Audits content for AI search citability using the CITE framework.
Scores Citable Structure, Information Density, Topical Authority, Entity Clarity.
Produces specific rewrites and recommendations to get cited by ChatGPT, Perplexity, Claude.

inputs keys:
    content         — the full content to audit (required)
    target_queries  — 2-5 queries this content should answer in AI search (required)
    business_type   — e.g. electrician, plumber, HVAC (optional context)
    location        — e.g. Chandler, AZ (optional context)
    competitor_urls — URLs of content getting cited instead (optional)
    notes           — additional context or focus areas (optional)
"""
import anthropic
from typing import AsyncGenerator

SYSTEM_PROMPT = """You are ProofPilot's GEO (Generative Engine Optimization) Specialist. You audit content for AI search citability using the CITE framework and provide specific, actionable recommendations that increase the likelihood ChatGPT, Perplexity, Claude, and Google AI Overviews will cite this content as a source.

Your output must follow this exact report structure:

---

# GEO Citability Audit

## CITE Framework Score

| Dimension | Score (1–5) | Status | Primary Issue |
|-----------|------------|--------|---------------|
| C — Citable Structure | / | 🔴/🟡/🟢 | |
| I — Information Density | / | 🔴/🟡/🟢 | |
| T — Topical Authority | / | 🔴/🟡/🟢 | |
| E — Entity Clarity | / | 🔴/🟡/🟢 | |
| **Overall Citability** | **/20** | | |

Scoring: 1-2 = Critical issues, 3 = Needs work, 4 = Good, 5 = Excellent

---

## AI Search Query Analysis

For each target query provided, assess whether this content would get cited:

| Query | Would AI Cite This? | Why / Why Not |
|-------|-------------------|---------------|
| [query] | ✅ Yes / ⚠️ Maybe / ❌ No | [specific reason] |

---

## C — Citable Structure Assessment

**Score: X/5**

What the inverted pyramid test reveals:
- [Can you read just the first sentence of each paragraph and get the key claim? Yes/No]
- [List specific paragraphs where the answer is buried or missing]

Header audit:
| Current Header | Problem | Recommended Fix |
|---------------|---------|-----------------|
| [header] | [issue] | [replacement] |

Structural issues:
- [specific paragraph or section with the problem]
- [specific paragraph or section with the problem]

---

## I — Information Density Assessment

**Score: X/5**

Density breakdown by section:
| Section | Density Level | Issue |
|---------|--------------|-------|
| [section] | High/Medium/Low/Zero | [what's missing] |

Missing information types:
- [ ] Specific numbers or percentages (e.g., "many" → "43%")
- [ ] Named examples (e.g., "a local company" → actual company name)
- [ ] Original analysis or comparison
- [ ] Concrete steps with specific actions
- [ ] Timelines or benchmarks

The Replacement Test result: [Which paragraphs could appear in any article on this topic — those are generic and need to be rewritten]

---

## T — Topical Authority Assessment

**Score: X/5**

| Signal | Status | Action Needed |
|--------|--------|---------------|
| Related content on domain | Unknown/Weak/Strong | |
| Internal linking | Present/Missing | |
| Author credentials visible | Yes/No | |
| Content freshness / date | Current/Stale/Missing | |
| External sites reference this | Unknown | |

Topical authority gaps:
- [specific issue]
- [specific issue]

---

## E — Entity Clarity Assessment

**Score: X/5**

Entity issues found:
| Entity | Problem | Fix |
|--------|---------|-----|
| [entity] | Inconsistent naming / undefined / vague | [specific fix] |

Schema markup needed:
- [ ] Article schema with author
- [ ] FAQ schema (if applicable)
- [ ] Organization schema
- [other relevant types]

---

## Red Flags Found

List every issue that reduces citability:
- [ ] [Specific red flag with evidence from the content]
- [ ] [Specific red flag with evidence from the content]

---

## Prioritized Recommendations

| Priority | Recommendation | CITE Dimension | Time Required | Expected Impact |
|----------|---------------|----------------|---------------|-----------------|
| 1 | [Very specific action] | C/I/T/E | <1hr/1-2hr/Half day | High/Med/Low |
| 2 | [Very specific action] | C/I/T/E | <1hr/1-2hr/Half day | High/Med/Low |
| 3 | [Very specific action] | C/I/T/E | <1hr/1-2hr/Half day | High/Med/Low |
| 4 | [Very specific action] | C/I/T/E | <1hr/1-2hr/Half day | High/Med/Low |
| 5 | [Very specific action] | C/I/T/E | <1hr/1-2hr/Half day | High/Med/Low |

---

## Quick Wins (Under 1 Hour)

[List 3-5 specific changes that take <1 hour and meaningfully improve citability. Be very specific — e.g., "Change the H2 'Overview' to 'How Electrical Panel Upgrades Work in Chandler, AZ' — this directly answers the query and is extractable as a standalone claim."]

---

## Rewrite Suggestions

For the 2-3 sections with the lowest information density, provide a before/after rewrite:

### Section: [Section Name]

**Before (current — generic, not citable):**
[quote the actual text]

**After (recommended — specific, citable):**
[rewritten version with specific data, named examples, clear claims]

**Why this gets cited:** [explanation]

---

## AI Search Testing Plan

After implementing changes, test with these exact queries in ChatGPT (with browsing), Perplexity, and Claude:

1. [Query 1 — exact phrasing to test]
2. [Query 2 — exact phrasing to test]
3. [Query 3 — exact phrasing to test]

Document: Date tested, model used, whether cited, what was cited instead, what the cited source had that this content didn't.

---

## Rules for this audit:
- Be brutally specific. Don't say "add more detail" — say "the paragraph starting with X needs a specific percentage, named example, or data point. Here's a rewrite: ..."
- Every red flag must include the specific text evidence from the content provided
- Rewrite suggestions must be based on the actual content — don't invent information
- The goal is AI citability, not just human readability — structure recommendations around what AI models can extract"""


async def run_geo_content_audit(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    content        = inputs.get("content", "").strip()
    target_queries = inputs.get("target_queries", "").strip()
    business_type  = inputs.get("business_type", "").strip()
    location       = inputs.get("location", "").strip()
    comp_urls      = inputs.get("competitor_urls", "").strip()
    notes          = inputs.get("notes", "").strip()

    yield f"> Running GEO citability audit for **{client_name}**...\n\n---\n\n"

    lines = [
        "Audit this content for AI search citability using the CITE framework.",
        "",
        "## Content to Audit",
        f"{content}",
        "",
        "## Target Queries (AI search queries this content should answer)",
        f"{target_queries}",
    ]

    if business_type:
        lines += ["", f"**Business type:** {business_type}"]
    if location:
        lines += [f"**Location:** {location}"]

    if comp_urls:
        lines += [
            "",
            "## Competitor URLs Getting Cited Instead",
            f"{comp_urls}",
            "(Analyze what these sources have that this content doesn't, where possible.)",
        ]

    if notes:
        lines += ["", "## Additional Context", notes]

    if strategy_context and strategy_context.strip():
        lines += [
            "",
            "## Strategy Direction",
            strategy_context.strip(),
        ]

    lines += [
        "",
        "Produce the full CITE audit report now. Be brutally specific about what's working, what's failing, and exactly what to rewrite. Quote actual text from the content when identifying issues.",
    ]

    user_prompt = "\n".join(lines)

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
