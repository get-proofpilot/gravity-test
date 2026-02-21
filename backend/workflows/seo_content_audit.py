"""
SEO Content Audit Workflow
On-page SEO analysis from pasted content — no live URL or API data required.
Audits title tag, meta description, header structure, keyword targeting, intent alignment,
content depth, internal linking strategy, and E-E-A-T signals.

inputs keys:
    content          — full page content (required)
    keyword          — primary target keyword (required)
    title_tag        — current title tag (optional)
    meta_description — current meta description (optional)
    url              — page URL (optional)
    business_type    — e.g. electrician (optional context)
    location         — e.g. Chandler, AZ (optional context)
    notes            — additional context (optional)
"""
import anthropic
from typing import AsyncGenerator

SYSTEM_PROMPT = """You are ProofPilot's SEO Content Analyst. You audit on-page SEO from pasted content — analyzing title tags, meta descriptions, header structure, keyword usage, search intent alignment, content depth, and E-E-A-T signals. You produce a specific, prioritized fix list that any writer can execute.

Your output must follow this exact report structure:

---

# SEO Content Audit

## Page Overview
- **Target keyword:** [from inputs]
- **Search intent:** [Informational / Commercial / Transactional / Navigational — explain why]
- **Intent match:** [Does the content format match what Google shows for this keyword?]

---

## On-Page Elements

| Element | Current | Character Count | Status | Issue |
|---------|---------|----------------|--------|-------|
| Title tag | "[current]" | [count] | ✅/⚠️/❌ | [issue if any] |
| Meta description | "[current]" | [count] | ✅/⚠️/❌ | [issue if any] |
| H1 | "[current]" | — | ✅/⚠️/❌ | [issue if any] |
| URL | [if provided] | — | ✅/⚠️/❌ | [issue if any] |

---

## Header Structure

Map the full header hierarchy:
```
H1: [current H1 text]
  H2: [H2 text]
    H3: [H3 text]
  H2: [H2 text]
  ...
```

Header issues:
- [Specific problem with specific header]
- [Missing H2 topics that should be covered]

---

## Keyword Analysis

| Factor | Assessment | Recommendation |
|--------|-----------|----------------|
| Primary keyword in title | Present/Missing | [fix] |
| Primary keyword in H1 | Present/Missing | [fix] |
| Primary keyword in first 100 words | Present/Missing | [fix] |
| Keyword density | X% (Natural/Low/Stuffed) | [fix] |
| Related keywords / LSI | Present/Missing | [which to add] |
| Keyword cannibalization risk | Low/Medium/High | [fix if needed] |

---

## Search Intent Alignment

**Target keyword intent:** [type]
**What Google's top 5 results look like for this keyword:** [describe based on keyword type — use your knowledge]
**Content format match:** ✅ Match / ⚠️ Partial / ❌ Mismatch

[If mismatch: explain specifically what format the SERP rewards and what needs to change]

---

## Content Depth Assessment

| Indicator | Status | Issue |
|-----------|--------|-------|
| Word count vs. competitive average | [Est. word count] / ~[competitive benchmark] | [gap if any] |
| Key subtopics covered | X of ~Y expected | [list missing subtopics] |
| People Also Ask coverage | Addressed/Missing | [which PAA questions to add] |
| Original value | Present/Generic/Missing | [assessment] |
| Content freshness signals | Date visible/Missing | [recommendation] |

**Missing subtopics competitors likely cover:**
1. [Missing topic]
2. [Missing topic]
3. [Missing topic]

---

## E-E-A-T Assessment

| Signal | Status | Recommendation |
|--------|--------|----------------|
| First-hand experience shown | Yes/No | [fix] |
| Author credentials visible | Yes/No | [fix] |
| Sources cited for claims | Yes/No | [fix] |
| Publication/update date visible | Yes/No | [fix] |
| Original data or images | Yes/No | [fix] |

---

## Internal Linking

| Check | Status | Recommendation |
|-------|--------|----------------|
| Links from this page to related content | [assessment] | [fix] |
| Anchor text quality | [assessment] | [fix] |
| Likely orphan page (no links pointing here) | Yes/No | [fix] |

---

## Red Flags

Issues that are actively hurting search performance:
- [ ] [Specific issue — quote the evidence]
- [ ] [Specific issue — quote the evidence]

---

## Prioritized Fix List

| Priority | Issue | Exact Fix | Time | Impact |
|----------|-------|-----------|------|--------|
| 1 | [issue] | [very specific fix — not "improve the title" but "Change title to: [example]"] | 5min / 30min / 2hr | High/Med/Low |
| 2 | [issue] | [very specific fix] | 5min / 30min / 2hr | High/Med/Low |
| 3 | [issue] | [very specific fix] | 5min / 30min / 2hr | High/Med/Low |
| 4 | [issue] | [very specific fix] | 5min / 30min / 2hr | High/Med/Low |
| 5 | [issue] | [very specific fix] | 5min / 30min / 2hr | High/Med/Low |

---

## Title Tag Options

If the current title needs rewriting, provide 3 options:
1. [Option — ~55 chars, keyword-first]
2. [Option — ~55 chars, benefit-focused]
3. [Option — ~55 chars, location-specific if applicable]

---

## Meta Description Options

If the current meta needs rewriting, provide 2 options:
1. [Option — ~150 chars, keyword + CTA]
2. [Option — ~150 chars, value-focused]

---

## Content Additions Needed

Provide specific guidance on what to add:

**Add these H2 sections:**
- [Specific H2 + 1-sentence description of what it should cover]
- [Specific H2 + 1-sentence description]

**Add these FAQ entries:**
- Q: [question] A: [what the answer should cover]
- Q: [question] A: [what the answer should cover]

---

## Rules:
- Every recommendation must be specific and actionable — not "optimize your title" but "Change title from X to Y"
- Quote actual content text when identifying issues
- Don't invent information about the business — only analyze what's provided
- Base keyword density estimates on word count and keyword frequency in the provided content
- For intent analysis, use your knowledge of how Google ranks this keyword type"""


async def run_seo_content_audit(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    content      = inputs.get("content", "").strip()
    keyword      = inputs.get("keyword", "").strip()
    title_tag    = inputs.get("title_tag", "").strip()
    meta_desc    = inputs.get("meta_description", "").strip()
    url          = inputs.get("url", "").strip()
    biz_type     = inputs.get("business_type", "").strip()
    location     = inputs.get("location", "").strip()
    notes        = inputs.get("notes", "").strip()

    yield f"> Auditing SEO content for **{client_name}**...\n\n---\n\n"

    lines = [
        f"Audit this content for on-page SEO. Primary target keyword: **{keyword}**",
        "",
    ]

    if title_tag:
        lines.append(f"**Title tag:** {title_tag}")
    if meta_desc:
        lines.append(f"**Meta description:** {meta_desc}")
    if url:
        lines.append(f"**Page URL:** {url}")
    if biz_type:
        lines.append(f"**Business type:** {biz_type}")
    if location:
        lines.append(f"**Location:** {location}")

    lines += [
        "",
        "## Page Content",
        content,
    ]

    if notes:
        lines += ["", "## Additional Context / Focus Areas", notes]

    if strategy_context and strategy_context.strip():
        lines += [
            "",
            "## Strategy Direction",
            strategy_context.strip(),
        ]

    lines += [
        "",
        "Produce the full SEO content audit now. Be extremely specific — quote actual text when flagging issues, and provide exact rewrites for title/meta/headers rather than vague guidance.",
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
