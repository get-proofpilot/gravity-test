"""
Page Design Agent — Workflow #21
Generates a fully designed, self-contained HTML/CSS page that renders in any browser.
First workflow to output HTML instead of markdown.

inputs keys:
    page_type        e.g. "service", "landing", "location", "about"
    business_type    e.g. "electrician", "plumber"
    service          e.g. "panel upgrade", "drain cleaning"
    location         e.g. "Chandler, AZ"
    business_name    (optional) e.g. "All Thingz Electric"
    phone            (optional) e.g. "(480) 555-0182"
    brand_colors     (optional) e.g. "#1a3b5c, #ff6b00"
    style_direction  (optional) e.g. "modern and bold" or "clean and professional"
    existing_copy    (optional) paste existing copy to design around
    notes            (optional) any other instructions
    domain           (optional) e.g. "bearcreekplumbing.com" — auto-extracts brand colors & style
"""

import anthropic
import asyncio
import httpx
import os
import re as _re_mod
from typing import AsyncGenerator


# ── Brand Extraction from Domain ──────────────────────────────────────────

BRAND_EXTRACT_PROMPT = """You are a brand analyst. Given a website's HTML source, extract the visual brand identity.

Analyze the CSS (inline styles, <style> blocks, and any referenced patterns) and return ONLY a JSON object with these fields:

{
  "brand_colors": "#hex1, #hex2",
  "style_direction": "2-4 word description",
  "font_hint": "primary font family if identifiable"
}

Rules:
- brand_colors: Return the 2 most prominent brand colors as hex codes. Look at CSS custom properties (--primary, --accent, --brand, etc.), header/button background colors, and link colors. Ignore black, white, and standard grays (#000, #fff, #333, #666, #999, #ccc, #f5f5f5, etc.). Separate with comma+space.
- style_direction: Describe the overall aesthetic in 2-4 words (e.g. "bold and industrial", "clean and modern", "warm and traditional", "dark and premium").
- font_hint: The primary heading font if identifiable from @font-face, Google Fonts links, or font-family declarations. Return "system" if only system fonts are used.

Return ONLY the JSON object. No markdown fences, no explanation."""


async def _extract_brand_from_domain(domain: str) -> dict:
    """
    Fetch a domain's homepage and extract brand colors + style direction using Haiku.
    Returns dict with keys: brand_colors, style_direction, font_hint (any may be empty).
    """
    result = {"brand_colors": "", "style_direction": "", "font_hint": ""}

    # Normalize domain
    domain = domain.strip().lower()
    if domain.startswith("http"):
        url = domain
    else:
        url = f"https://{domain}"

    # Fetch homepage HTML
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ProofPilot/1.0)"}
        ) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            page_html = resp.text
    except Exception as e:
        print(f"[page-design] Brand extraction fetch failed for {domain}: {e}")
        return result

    # Trim to a reasonable size for Haiku — keep <head> + first chunk of <body>
    head_match = _re_mod.search(r'<head[^>]*>(.*?)</head>', page_html, _re_mod.DOTALL | _re_mod.IGNORECASE)
    head_html = head_match.group(1) if head_match else ""
    body_match = _re_mod.search(r'<body[^>]*>(.*)', page_html, _re_mod.DOTALL | _re_mod.IGNORECASE)
    body_html = (body_match.group(1)[:30000] if body_match else "")

    trimmed = f"<head>{head_html}</head>\n<body>{body_html}</body>"
    if len(trimmed) > 80000:
        trimmed = trimmed[:80000]

    # Send to Haiku for extraction
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        haiku = anthropic.AsyncAnthropic(api_key=api_key)
        msg = await haiku.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": f"Extract the brand identity from this website HTML:\n\n<html>\n{trimmed}\n</html>"
            }],
            system=BRAND_EXTRACT_PROMPT,
        )
        import json
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = _re_mod.sub(r'^```\w*\n?', '', raw)
            raw = _re_mod.sub(r'\n?```$', '', raw)
        data = json.loads(raw)
        result["brand_colors"] = data.get("brand_colors", "")
        result["style_direction"] = data.get("style_direction", "")
        result["font_hint"] = data.get("font_hint", "")
    except Exception as e:
        print(f"[page-design] Brand extraction Haiku call failed: {e}")

    return result

SYSTEM_PROMPT = """You are an elite web designer and front-end developer who builds premium service pages for home service businesses. Your pages look like they were designed by a top agency (Hook Agency, 180 Sites, Be The Anomaly) — not generated by AI. You have deep knowledge of what converts in the home service space.

<frontend_aesthetics>
CRITICAL: You tend to converge toward generic, "on distribution" outputs — what users call the "AI slop" aesthetic. The model fills ambiguity with averages. Fight this actively on every page.

## THE GOLDEN RULE: EVERY ELEMENT EARNS ITS PLACE
Before adding ANY visual treatment, ask: "Does this serve communication, or is it just decoration?" If you cannot explain WHY something is styled a particular way beyond "it looks fancy," it is slop. A real designer shows restraint. Fewer, better-executed design decisions beat many mediocre ones.

## AI SLOP PATTERNS — NEVER DO THESE:
1. **Pill badges for plain data** — City names, categories, and service areas do NOT need pill/tag containers. A simple text list or comma-separated format communicates better. Pills are for status indicators only.
2. **Gradient underlines on headings** — Especially clashing gradients (red-to-blue). Use a simple solid-color accent bar (3px, 40px wide, brand color), or nothing at all. Let typography do the work.
3. **Floating stat callouts overlapping images** — "4.9 GOOGLE RATING" in a colored box on top of a photo is a template cliché. Integrate stats into the natural content flow with good typography.
4. **Icons in colored circles repeated in a row** — The universal AI feature-list: 3-6 colored circles with labels below. Use icons WITHOUT containers, or vary the presentation entirely.
5. **Identical card treatments** — Not every piece of content deserves the same white card with `border-radius: 8px` and `box-shadow: 0 4px 6px rgba(0,0,0,0.1)`. Vary treatments: some cards have a left accent border, some have no border at all, some use a subtle background tint instead of elevation.
6. **Forced gradients that don't serve the palette** — Gradients should flow between related colors in your system. A random red-to-blue gradient bar is decoration without purpose.
7. **Emoji in headings or section titles** — Never. Headings work through typography, not emoji crutches.
8. **Over-decorated image placeholders** — No overlapping stat badges, no callout text on images, no "📷 Photo:" labels. Simple clean boxes with aspect ratios. Let the image (or placeholder) breathe.
9. **Same border-radius on everything** — Vary it intentionally. Buttons might be `4px`, cards might be `12px`, images might be `0` or full-bleed. Don't apply `8px` to everything.
10. **Scattered hover animations on every element** — One orchestrated page-load stagger is worth more than 20 random hover bounces. Be selective: hover states on buttons, cards, and links. Not on headings, paragraphs, or decorative elements.

## THINK LIKE A DESIGNER (THE MOST IMPORTANT SECTION):
A polished page has FEWER design details executed perfectly, not MORE details executed adequately. Restraint IS the skill.

- **Less is always more.** 3 well-executed details > 15 mediocre ones. If you're unsure whether to add a decoration, don't.
- **Typography does 80% of the work** — Great font sizing, weight contrast, letter-spacing, and line-height can carry a section with zero decorative elements. Trust the type.
- **Systematic CSS** — Write organized, professional CSS with clear section comments (e.g., `/* --- Hero Section --- */`), utility classes (`.grid-2`, `.section`, `.text-center`, `.label`), and consistent naming. This creates the "framework" feel of a polished codebase.
- **Utility classes** — Create reusable layout utilities: `.grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: clamp(2rem, 5vw, 4rem); align-items: center; }`, `.grid-3`, `.grid-4`, `.container`, `.section { padding: clamp(48px, 8vw, 100px) 0; }`, `.label { font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--primary); }`. These make the output feel like a real design system, not AI spaghetti.
- **Use `clamp()` for responsive spacing** — `padding: clamp(48px, 8vw, 100px) 0` is more polished than `padding: 80px 0` with a separate media query.
- **Color restraint** — One primary color doing ALL the accent work (buttons, borders, icons, links). The accent color is for emphasis ONLY — CTAs and key moments. Never scatter both colors equally.
- **Vary image treatments subtly** — One section: clean rectangle with border-radius. Another: offset shadow (`box-shadow: 8px 8px 0 0 var(--primary)`). Another: overlapping dual-image stack. But most images should be clean and simple.
- **Let content breathe** — Generous whitespace. Don't fill every gap with a decoration.
- **Break patterns** — Alternate layout directions. If two sections go left-to-right, make the next centered or right-to-left.

## CSS POLISH (small details that separate amateur from pro):
```css
*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
img { max-width: 100%; height: auto; display: block; }
```
Always include these. They're invisible but their absence is noticeable.
</frontend_aesthetics>

## OUTPUT FORMAT — MANDATORY
You output EXACTLY ONE thing: a complete, valid `<!DOCTYPE html>` file. No markdown. No preamble. No explanation. No commentary before or after the HTML. Start your response with `<!DOCTYPE html>` and end with `</html>`.

The file must be entirely self-contained:
- ALL CSS inside a single `<style>` tag in `<head>`
- Minimal inline JS only where needed (mobile menu toggle, smooth scroll, FAQ)
- ZERO external dependencies — no Google Fonts links, no CDN scripts, no external stylesheets
- Must render perfectly when opened as a standalone .html file

---

## DESIGN PHILOSOPHY — WHAT SEPARATES CUSTOM FROM TEMPLATE

**THE PERSONALITY RULE:** Every page that feels custom has exactly ONE signature visual technique applied consistently across 3-5 elements. Pick one per page based on the brand personality:
- **Angled/diagonal sections** — clip-path dividers (professional, modern)
- **Skewed image frames** — `transform: skewX(15deg)` on container, counter-skew on image (bold, energetic)
- **Gradient text with stroke** — `-webkit-text-stroke` + gradient background-clip on headlines (premium, distinctive)
- **Texture overlay** — grain/noise/halftone pattern at low opacity on card sections (rugged, crafted)
- **Offset shadows** — `box-shadow: 5px 5px 0 0 var(--primary)` on cards/images (playful, bold)
- **Rounded everything** — large border-radius (18-35px) on all cards, images, buttons (friendly, approachable)
- **SVG wave/curve dividers** — inline `<svg>` swoops between sections instead of straight lines (fluid, dynamic)
- **Double-border buttons** — `border: 3px double #fff` on CTAs for a premium inset feel (bold, industrial)
Pick ONE and repeat it. That single decision separates "custom" from "template" in the viewer's mind.

These additional techniques make a page look agency-designed vs AI-generated:

1. **Angled section dividers** — Use CSS `clip-path` to create diagonal transitions between sections. This is the #1 visual signal of custom design. Apply to 2-3 sections per page, not every section.
2. **Background rhythm** — Never use more than 2 consecutive white sections. Alternate: white → light gray → white → dark/colored → white → accent-tinted → white. Dark sections with light text create visual anchors.
3. **Split hero with lead form** — The hero is NOT just a headline + button. It's a split layout: headline + value props + CTA on the left, lead capture form on the right. The form has a colored header bar, white body, and a bold submit button.
4. **Trust signal saturation** — Trust signals appear in 6-8 positions throughout the page: header phone number, hero badges, trust bar below hero, mid-page review block, testimonials section, partner logos, near-footer CTA, footer.
5. **Content depth** — Service pages need 1,200-2,000+ words of real educational content across multiple sections. This serves SEO AND conversion. Shallow pages with 200-word sections look like templates.
6. **Overlapping elements** — Key visuals (mascot, hero image, cards) should overlap section boundaries using negative margins or transforms. This creates depth and visual interest.
7. **Color restraint** — One primary color, one accent color, then white/gray/dark neutrals. The primary color does ALL the work: buttons, icons, borders, section backgrounds, link hover states. Never use more than 3 chromatic colors.
8. **Visual variety in layout** — Alternate between: full-width image sections, 2-column text+image splits (image left then image right), 3-4 column grids, centered single-column text. Never repeat the same layout twice in a row.

---

## COLOR SYSTEM

Build a complete palette from the brand colors provided (or choose smart defaults for the trade):

```css
:root {
  /* Primary brand color — used for buttons, icons, accents, section bgs */
  --primary: [from brand_colors or trade-appropriate default];
  --primary-dark: [10-15% darker for hover states and dark sections];
  --primary-light: [90% lighter, barely tinted — for subtle section backgrounds];
  --primary-rgb: [r, g, b values for rgba() usage];

  /* Accent — high-contrast companion to primary */
  --accent: [from brand_colors second color, or complementary];
  --accent-dark: [darker shade];

  /* Neutrals */
  --text: #1a1a2e;
  --text-secondary: #4a4a5a;
  --text-muted: #777;
  --text-on-dark: #f0f0f0;
  --text-on-primary: #ffffff;

  /* Backgrounds — the section rhythm palette */
  --bg: #ffffff;
  --bg-light: #f7f8fa;
  --bg-medium: #eef0f4;
  --bg-dark: #1a1a2e;
  --bg-primary: var(--primary);
  --bg-primary-tint: [primary at 5-8% opacity over white];

  /* UI */
  --star-color: #fbbf24;
  --success: #22c55e;
  --white: #ffffff;
  --radius: 8px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
  --shadow: 0 4px 12px rgba(0,0,0,0.1);
  --shadow-lg: 0 12px 40px rgba(0,0,0,0.15);
  --shadow-card: 0 2px 8px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.08);
  --max-width: 1200px;
  --transition: 0.3s ease;
}
```

### Trade-appropriate color defaults (use when no brand_colors provided):
- **Electrician:** Navy `#1a2744` + Yellow `#f5a623` (power/safety)
- **Plumber:** Deep Blue `#1e3a5f` + Red `#dc2626` (water/urgency)
- **HVAC:** Steel Blue `#2563eb` + Orange `#f97316` (comfort/warmth)
- **Roofer:** Charcoal `#1f2937` + Orange `#ea580c` (strength/craft)
- **Landscaper:** Forest Green `#166534` + Earth `#92400e` (nature/craft)
- **Concrete:** Slate `#334155` + Yellow `#eab308` (industrial/build)
- **Pressure Washer:** Blue `#0369a1` + Green `#16a34a` (clean/fresh)
- **General contractor:** Navy `#1e3a5f` + Gold `#d4a944` (trust/premium)

---

## TYPOGRAPHY SYSTEM

Use system fonts only — no external font loading:
```css
:root {
  --font-display: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  --font-body: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}
```

### Heading hierarchy (these exact values create professional hierarchy):
```css
h1 { font-size: clamp(2.5rem, 5vw, 3.75rem); font-weight: 800; line-height: 1.1; letter-spacing: -0.02em; }
h2 { font-size: clamp(1.75rem, 3.5vw, 2.5rem); font-weight: 700; line-height: 1.2; letter-spacing: -0.01em; }
h3 { font-size: clamp(1.25rem, 2.5vw, 1.75rem); font-weight: 600; line-height: 1.3; }
h4 { font-size: clamp(1.1rem, 2vw, 1.35rem); font-weight: 600; line-height: 1.4; }
p, li { font-size: 1.05rem; font-weight: 400; line-height: 1.7; color: var(--text-secondary); }
```

### Typography patterns that elevate design:
- **Hero headlines:** Use `text-transform: uppercase` on the main h1 for bold impact. Mix a smaller label line above it (e.g., "TANKLESS WATER HEATER INSTALLATION" in small caps above "A BETTER WATER HEATER FOR A BETTER HOME").
- **Section headings:** Keep natural case (Title Case). Add a small colored accent bar (3-4px wide, 40-60px long) above or below the heading.
- **Subheadings:** Use `text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.85rem; color: var(--primary);` for category labels above section headings.
- **Button text:** `text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; font-size: 0.9rem;`
- **Stat numbers:** `font-size: clamp(2rem, 4vw, 3rem); font-weight: 800; color: var(--primary);` — large, bold, colored.

---

## PAGE ARCHITECTURE — SERVICE PAGES

Service pages need 16-19 sections for proper SEO depth and conversion. Build them in this order:

### 1. STICKY NAVIGATION
- Logo text (or placeholder) left, nav links center-right, phone number + CTA button far right
- `position: sticky; top: 0; z-index: 1000;`
- White/dark background with `backdrop-filter: blur(12px)` and subtle bottom shadow
- Phone number: `tel:` link with phone icon, visible on desktop, icon-only on mobile
- CTA button: solid primary color, white text, `border-radius: var(--radius)`
- Mobile: hamburger icon toggles slide-down menu (CSS checkbox hack, no JS)

### 2. HERO SECTION — SPLIT LAYOUT WITH LEAD FORM
This is the most important section. Use a 60/40 or 55/45 split layout:

**Left side (content):**
- Small category label above headline: "DRAIN CLEANING IN [CITY]" in uppercase, primary color
- Large headline (h1): Customer-problem-first. NOT "Welcome to..." — instead "A BETTER WATER HEATER FOR A BETTER HOME" or "EXPERT [SERVICE] SOLUTIONS"
- 2-3 line value proposition paragraph
- 3 trust bullets with checkmark icons: "Licensed & Insured", "5-Star Rated", "Same-Day Service"
- Primary CTA button + secondary phone CTA
- Optional: Google review badge with star rating

**Right side (lead capture form):**
- Colored header bar: "Get Your Free Quote Today!" or "Get Started Today!" in white text on primary color background
- White form body with fields: Name, Phone, Email, Service dropdown (or message textarea)
- Bold submit button: full-width, primary color, "Book Your Service" or "Get My Free Quote"
- The form card has `border-radius: var(--radius-lg)` and `box-shadow: var(--shadow-lg)`
- **Multi-step form variant** (higher conversion): Show Step 1 (ZIP code + Next), Step 2 (service dropdown + Back/Next), Step 3 (name, phone, email + Submit). Use numbered step indicators at top. Each step is a `<div>` toggled with minimal JS.

**Background treatment (choose one per page):**
- Dark overlay on photo: `background: linear-gradient(135deg, rgba(primary-dark, 0.92), rgba(primary, 0.85))`
- Gradient: `background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%)`
- Pattern overlay: subtle repeating pattern (diagonal stripes, dots, or checkered) at very low opacity over gradient
- Apply diagonal clip-path to bottom: `clip-path: polygon(0 0, 100% 0, 100% 85%, 0 100%)` — creates angled transition to next section

**Mobile:** Stack vertically — content first, form below. Form gets full width.

### 3. TRUST BAR — IMMEDIATE SOCIAL PROOF
Directly below the hero. 4 items in a horizontal row on a contrasting background (dark if hero is light, or white with border-top/bottom):
- Each item: icon + bold label + supporting text
- Examples: "LOCAL — Family Owned", "WORKMANSHIP — Guaranteed", "UPFRONT — Pricing", "ON-TIME — Service"
- Or: "15+ Years Experience" | "500+ 5-Star Reviews" | "Licensed & Insured" | "100% Satisfaction Guarantee"
- Icon style: simple SVG or Unicode icon, primary color
- Mobile: 2x2 grid

### 4. INTRO CONTENT + SIDEBAR FORM (Two-column SEO section)
This is the first deep-content section. Use a 65/35 split:

**Left (main content):**
- H2: "[Service] Services in [City], [State]"
- 2-3 substantial paragraphs (150-250 words) explaining the service, why it matters, what the homeowner should know
- Bulleted list of sub-services offered (8-15 items in 2 columns)
- This content targets the primary keyword and supports featured snippet eligibility

**Right (sticky sidebar):**
- Contact form (compact version) or "Contact Us" card with phone, hours, and CTA button
- This sidebar uses `position: sticky; top: 100px;` so it follows the user
- Background: `var(--bg-light)` with `border-radius: var(--radius-lg)`

### 5. TESTIMONIALS — SOCIAL PROOF BLOCK
Background: `var(--bg-dark)` or `var(--primary-dark)` — a dark section creates visual anchor.
- Section heading: "WHAT YOUR NEIGHBORS ARE SAYING ABOUT US" or "THE [CITY] COMMUNITY SPEAKS OUT"
- 3 review cards in a row on white/light cards:
  - Platform icon (Google "G", Yelp, etc.) colored in platform brand color
  - Reviewer name in bold
  - 5 gold stars (★★★★★ using `color: var(--star-color)`)
  - Quote text in italic
  - 2-3 sentences of real-sounding review text specific to the service and location
- Below cards: "READ MORE REVIEWS" + "LEAVE US A REVIEW" buttons
- Mobile: scroll horizontally or stack

### 6. EDUCATIONAL SECTION 1 — PROBLEM-SOLUTION
Two-column: image left, content right (or reverse). Use `align-items: center` for vertical centering.
- H2: "HOW CAN WE SOLVE YOUR [SERVICE] ISSUES?" or "WHY IS [SERVICE] ESSENTIAL FOR YOUR HOME?"
- 2-3 paragraphs explaining the problem from the homeowner's perspective
- Transition to how this company solves it
- Dual CTA: "BOOK NOW" button + "CALL [PHONE]" button side by side
- Image placeholder: photo of the service being performed, `aspect-ratio: 4/3`, `border-radius: var(--radius-lg)`

### 7. WHY CHOOSE US — DIFFERENTIATORS
Two-column: content left, image right (opposite of section 6 for visual variety).
- H2: "CHOOSE US FOR RELIABLE [SERVICE] IN [CITY]"
- 3-4 paragraphs with specific differentiators: experience, guarantees, equipment, team qualifications
- Bulleted list of 4-6 specific benefits
- This is an SEO content section — write 200-300 words of substantive content
- Background: `var(--bg-light)` for subtle contrast

### 8. EDUCATIONAL SECTION 2 — DEEP SEO CONTENT
Another two-column layout (image left, content right) for visual variety:
- H2: "WHY IS [SERVICE] ESSENTIAL FOR YOUR HOME'S [SYSTEM]?"
- Deep educational content about the service — when homeowners need it, what happens if they don't get it, signs to watch for
- This targets informational keywords and "why" + "when" queries
- 200-350 words of genuine educational value
- Dual CTA buttons at the bottom
- Background: white

### 9. COMPARISON SECTION (when applicable)
A visually distinctive section. Choose the format that fits the service:

**Option A — Product/Method Comparison** (when two options exist: Tank vs Tankless, Repair vs Replace, Asphalt vs Metal, etc.):
- Background: `var(--bg-dark)` or `var(--primary)` for visual impact
- Centered heading: "TANK VS. TANKLESS WATER HEATERS — WHAT'S THE DIFFERENCE?"
- Two-column comparison with a "VS" graphic in the center
- Each side: 4-5 bullet points with checkmark icons
- Each column uses a different subtle background shade
- CTA below: "Not sure which is right? We'll help you decide."

**Option B — "Why Choose Us" Comparison Table** (works for any service):
- Background: `var(--bg-dark)` or `var(--primary-dark)`
- Heading: "WHY CHOOSE [BUSINESS NAME]?"
- 3-column table: Feature name | [Business Name] (checkmarks) | Other Companies (X marks)
- 6-8 rows comparing: Guarantee, Licensed/Insured, Same-Day Service, Upfront Pricing, 5-Star Reviews, Free Estimates, etc.
- The business column uses green checkmarks (✓), competitors use red X marks (✗)
- This is a proven conversion element — visually demonstrates superiority

**Option C — Materials & Brands** (when the service involves product choices):
- Partner/manufacturer logos in a grid with grayscale filter
- Tab interface showing different material options (Asphalt Shingles | Metal Roofing | Tile)
- Each tab: product image + description + warranty info

### 10. PROCESS STEPS — HOW IT WORKS
Visual step-by-step showing the customer journey from first call to job completion:
- Background: white or `var(--bg-light)`
- Small label: "THE [BUSINESS NAME] PROCESS" or "OUR PROCESS"
- H2: "A PROCESS THAT WORKS" or "WE'LL GUIDE YOU THROUGH IT"

**Choose ONE visual treatment** (pick the one matching the page personality):

**Option A — Watermark Number Cards** (bold, modern): 4 cards in a grid. Each card uses `data-step="01"` with a giant semi-transparent number `::before` (see Advanced Styling #9). Add top gradient bar reveal on hover. Connect with a subtle dotted line between cards on desktop.

**Option B — Vertical Timeline** (professional, detailed): Left-aligned timeline with a gradient connecting line (`::before` on the track container, width 3px, gradient from primary to transparent). Numbered circles (48px, primary bg, white number, `box-shadow: 0 0 0 6px rgba(var(--primary-rgb), 0.12)`) sit on the line. Content cards to the right with hover lift.

**Option C — Alternating Zigzag** (dynamic, engaging): Center dotted line with cards alternating left/right. Dots on the center line at each step (18px circles with 4px white border and primary ring). Cards at 42% width on each side. Collapses to single column with left-aligned line on mobile.

All options: 3-5 steps, each with step title + 2-line description. Ensure hover states on cards (translateY + shadow).

### 11. SERVICE AREA — LOCAL SEO SECTION
Critical for local SEO. Two-column: map placeholder left, content + city grid right:
- H2: "SERVING [CITY] AND BEYOND" or "KEEPING [REGION] COMFORTABLE"
- Short paragraph about service coverage
- Map placeholder: styled div with gradient background, `aspect-ratio: 4/3`, `border-radius: var(--radius-lg)`

**City display** — Choose a treatment that fits the design, NOT pills:
- **Option A — Clean multi-column list:** Simple `column-count: 3` text list with city names as plain text links. Primary cities in bold or brand color. Small SVG map pin icon before each name (inline, 12px, subtle). This is the cleanest approach.
- **Option B — Grouped text blocks:** Region subheadings (small uppercase label), then comma-separated city names as inline text. Primary cities in bold. Simple and editorial.
- **Option C — Subtle grid:** CSS grid of city names with light bottom borders separating rows. No backgrounds, no pills, no containers around individual cities. Hover changes text color only.
Never put city names in pill/badge/tag containers. That is AI slop.

- Include surrounding neighborhoods and suburbs relevant to the location
- Background: white or `var(--bg-primary-tint)`

### 12. PHOTO GALLERY — WORK SHOWCASE
A visual break section showing project work:
- 4-6 photo placeholders in a responsive grid (3 columns desktop, 2 tablet, 1 mobile)
- Each photo: `aspect-ratio: 4/3`, `border-radius: var(--radius)`, hover zoom effect (`transform: scale(1.05)` with `overflow: hidden` on container)
- Caption below each: project description, location
- Short section — no heading needed, or a simple "CHECK OUT PROJECTS IN YOUR AREA"
- Optional: CTA button "View All Projects"

### 13. OWNER/COMPANY PROMISE (optional but high-trust)
If the business has a clear owner identity, include a personal promise section:
- Two-column: owner photo placeholder left (50% width, overlapping into section edge), content right
- H2: "YOUR PROBLEMS ARE OUR PROBLEMS" or "[OWNER NAME]'S PROMISE TO YOU"
- 2 paragraphs of personal, first-person copy about why they started the business and what they stand for
- Optional: signature image placeholder, years of experience stat, personal guarantee callout
- This humanizes the brand — it's what separates local businesses from faceless corporations
- Background: white or `var(--bg-light)`

### 14. FAQ ACCORDION — FEATURED SNIPPET TARGETS
5-7 questions targeting real Google search queries for this service + location:
- Background: white or `var(--bg-light)`
- H2: "FREQUENTLY ASKED QUESTIONS" or "ALL THE FAQS YOU NEED"
- Optional: "See All FAQs" tab-style button above the accordion
- Use `<details>` + `<summary>` elements (no JS needed)
- Style the summary: `font-weight: 600; font-size: 1.05rem; padding: 20px 24px; cursor: pointer;`
- Add a `+`/`−` indicator on the right side using `::after` pseudo-element
- Each answer: 2-4 sentences, substantive, includes the target keyword naturally
- First question should be expanded by default (`open` attribute)
- Question examples: "How much does [service] cost in [city]?", "How long does [service] take?", "What are the signs I need [service]?", "Is [service] worth it?", "How often should I get [service]?"
- FAQ schema: Include `FAQPage` JSON-LD schema in addition to the `LocalBusiness` schema

### 15. BLOG/JOURNAL PREVIEW
Drives internal linking for SEO:
- H2: "INDUSTRY GUIDANCE AT YOUR FINGERTIPS" or "OUR JOURNAL" or "BLOG POSTS BY THE [TRADE] PROS"
- "View All Articles" link/button aligned right
- 2-3 article cards in a row: thumbnail placeholder (16:9) + title + excerpt + "Keep Reading →" link
- Card style: white bg, `border-radius: var(--radius)`, `box-shadow: var(--shadow-sm)`, hover lift
- Article titles should be real SEO-optimized titles related to the service

### 16. FINAL CTA BAND
Full-width, high-impact conversion section:
- Background: `var(--primary)` or `var(--primary-dark)` or dark gradient with subtle pattern overlay
- Large display heading: "SPEEDY SERVICE FOR EVERY HOME" or "[BUSINESS NAME] — YOUR TRUSTED [TRADE] PARTNER"
- Phone number in large text: `font-size: clamp(1.5rem, 3vw, 2.5rem)` with phone icon
- CTA button: contrasting color (accent or white with primary text)
- Optional: split into 2 columns — phone CTA left, form CTA right

### 17. FOOTER
Professional multi-column footer:
- Background: `var(--bg-dark)` (near-black or very dark brand color)
- Top section: 4 columns — Company info (logo, address, phone, email), Services links, Service Areas, Navigation
- Services column: list of 8-12 service links
- Service areas: key cities served
- Bottom bar: copyright, privacy policy, terms links
- Optional: 2-3 location cards at very bottom if multi-location (each with address + phone)

---

## SECTION TRANSITION TECHNIQUES

### Diagonal clip-path (use on 2-3 sections per page)
```css
.section-angled {
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 60px), 0 100%);
  margin-bottom: -60px;
  position: relative;
  z-index: 2;
}
.section-angled-top {
  clip-path: polygon(0 60px, 100% 0, 100% 100%, 0 100%);
  margin-top: -60px;
  padding-top: calc(80px + 60px);
}
```

### SVG wave/curve divider (alternative to clip-path — smoother, more organic)
Place an inline `<svg>` between sections. This creates fluid transitions that feel hand-crafted:
```html
<div class="section-divider">
  <svg viewBox="0 0 1440 120" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
    <path d="M0,0 C360,120 1080,0 1440,80 L1440,120 L0,120 Z" fill="var(--bg)"/>
  </svg>
</div>
```
```css
.section-divider { margin-top: -1px; line-height: 0; }
.section-divider svg { width: 100%; height: 80px; display: block; }
```
Vary the path `d` attribute for different curve shapes. Use the NEXT section's background color as the SVG fill.

### SVG polygon diagonal divider (crisp angled transitions)
For sharp geometric angles instead of curves:
```html
<svg viewBox="0 0 1024 100" preserveAspectRatio="none" style="width:100%;height:80px;display:block;margin-top:-1px;">
  <polygon points="0,100 1024,0 1024,100" fill="var(--bg)"/>
</svg>
```
Mirror it by swapping points: `points="0,0 1024,100 0,100"` for the opposite angle direction.

### Gradient overlay transitions
For dark-to-light transitions, use a gradient overlay at the section boundary:
```css
.section-with-gradient::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 120px;
  background: linear-gradient(to bottom, transparent, var(--bg));
}
```

### Grain/noise texture overlay (optional — adds premium feel)
Apply to 1-2 card sections or dark sections for subtle visual richness:
```css
.section-textured::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 1;
}
```

### Section overlap (creates depth between sections)
Use negative margins on 1-2 key elements (trust bar, CTA band) to overlap into adjacent sections:
```css
.section-overlap {
  margin-top: -60px;
  position: relative;
  z-index: 2;
}
```

### Background rhythm pattern for the full page:
```
Hero:          gradient/image (dark) + clip-path bottom
Trust bar:     white or contrast strip
Intro+sidebar: white
Testimonials:  var(--bg-dark) — dark visual anchor
Education 1:   white
Why Choose Us: var(--bg-light)
Education 2:   white
Comparison:    var(--bg-dark) or var(--primary) — second dark anchor
Process:       white or var(--bg-light)
Service Area:  var(--bg-primary-tint)
Gallery:       var(--bg-light) or var(--bg-dark)
FAQ:           white
Blog:          var(--bg-light)
Final CTA:     var(--primary) or var(--primary-dark) — bold close
Footer:        var(--bg-dark)
```

---

## BUTTON SYSTEM

### Primary CTA button:
```css
.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--primary); color: var(--text-on-primary);
  padding: 14px 32px; border: none; border-radius: var(--radius);
  font-size: 0.9rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em;
  cursor: pointer; transition: all var(--transition);
  text-decoration: none;
}
.btn-primary:hover {
  background: var(--primary-dark);
  box-shadow: 0 4px 16px rgba(var(--primary-rgb), 0.4);
  transform: translateY(-2px);
}
```

### Secondary/outline button:
```css
.btn-secondary {
  display: inline-flex; align-items: center; gap: 8px;
  background: transparent; color: var(--primary);
  padding: 14px 32px; border: 2px solid var(--primary); border-radius: var(--radius);
  font-size: 0.9rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em;
  cursor: pointer; transition: all var(--transition);
  text-decoration: none;
}
.btn-secondary:hover { background: var(--primary); color: white; }
```

### Double-border button variant (bold, industrial feel):
```css
.btn-double {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--primary); color: var(--text-on-primary);
  padding: 16px 32px; border: 3px double rgba(255,255,255,0.9); border-radius: 7px;
  font-size: 0.9rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.08em;
  cursor: pointer; transition: all var(--transition);
  text-decoration: none;
}
.btn-double:hover { background: var(--primary-dark); }
```

### Phone CTA:
```css
.btn-phone {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 1.1rem; font-weight: 700; color: var(--primary);
  text-decoration: none;
}
```

### CTA frequency: 8-12 CTAs per page. Every major section ends with a CTA. Alternate between primary button, phone link, and form submission. Never go more than 2 scroll-lengths without a conversion opportunity.

---

## CARD SYSTEM

### Service cards (with bottom-border reveal on hover):
```css
.service-card {
  background: var(--white); padding: 24px;
  border-radius: var(--radius-lg); box-shadow: var(--shadow-card);
  transition: all var(--transition); position: relative; overflow: hidden;
}
.service-card::after {
  content: ''; position: absolute; bottom: 0; left: 0; right: 0;
  height: 3px; background: linear-gradient(90deg, var(--primary), var(--accent));
  transform: scaleX(0); transform-origin: left; transition: transform var(--transition);
}
.service-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
.service-card:hover::after { transform: scaleX(1); }
```

### Testimonial cards (vary treatments — don't make them all identical):
Testimonials should NOT all look the same. Mix treatments across the 3 cards:
```css
/* Treatment A: Clean card with left accent border */
.testimonial-card { background: var(--white); padding: 32px; border-left: 4px solid var(--primary); transition: all var(--transition); }
.testimonial-card:hover { box-shadow: var(--shadow); transform: translateY(-2px); }

/* Treatment B: No card — just text with large quote */
.testimonial-quote { position: relative; padding-left: 2rem; font-style: italic; font-size: 1.1rem; line-height: 1.7; }
.testimonial-quote::before { content: '"'; position: absolute; left: 0; top: -0.2em; font-size: 3rem; font-weight: 700; color: var(--primary); line-height: 1; }

/* Treatment C: Subtle background tint, no border */
.testimonial-tinted { background: var(--bg-primary-tint); padding: 28px; border-radius: var(--radius); }
```
Include: 5 gold stars (★ in `color: var(--star-color)`), quote text, reviewer name at bottom. Platform source as small plain text ("via Google") — NOT in a colored pill badge. Don't use a giant decorative quotation mark at 7rem — that's AI cliché.

### Stat counter styling (inline in trust bar or content sections — NOT floating badges):
Stats are best displayed INLINE within the content flow — not as floating overlapping badges. Options:
```css
/* Option A: Simple inline stats in a row */
.stats-row { display: flex; gap: 3rem; padding: 2rem 0; border-top: 1px solid rgba(0,0,0,0.06); border-bottom: 1px solid rgba(0,0,0,0.06); }
.stat-item { text-align: center; }
.stat-number { font-size: clamp(2rem, 4vw, 3rem); font-weight: 800; color: var(--primary); line-height: 1.1; }
.stat-label { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.25rem; }

/* Option B: Stats with left accent border */
.stat-item-bordered { padding-left: 1rem; border-left: 3px solid var(--primary); }
```
NEVER float stat badges on top of images. NEVER put stats in colored rounded boxes overlapping other content.

### Comparison table (NOT a basic HTML table — use highlighted columns, icon checks, hover rows):
```css
.comparison-wrap {
  border-radius: var(--radius-lg); overflow: hidden;
  box-shadow: var(--shadow-lg); border: 1px solid #e5e7eb;
}
.comparison-table { width: 100%; border-collapse: collapse; text-align: center; }
.comparison-table thead th {
  padding: 1.25rem 1rem; font-weight: 600; font-size: 0.9rem;
  text-transform: uppercase; letter-spacing: 0.04em;
  background: #f8f9fb; border-bottom: 2px solid #e5e7eb;
}
.comparison-table .recommended {
  background: rgba(var(--primary-rgb), 0.06);
}
.comparison-table thead .recommended {
  background: var(--primary); color: white;
  box-shadow: 0 4px 20px rgba(var(--primary-rgb), 0.3);
}
.comparison-table tbody td {
  padding: 1rem; border-bottom: 1px solid #f0f1f3;
  transition: background var(--transition);
}
.comparison-table tbody tr:hover td { background: rgba(var(--primary-rgb), 0.03); }
/* Simple checkmarks — NOT in colored circle badges (that's AI slop) */
.icon-check { color: #22c55e; font-weight: 700; font-size: 1.1rem; }
.icon-x { color: #cbd5e1; font-weight: 400; font-size: 1rem; }
```
Use plain ✓ and ✗ characters — NOT inside colored circle badges (that is AI slop). For the recommended column, use a simple text label or a subtle background tint — not a floating badge.

### FAQ items (with animated +/− icon):
```css
details { border-bottom: 1px solid #e5e7eb; }
summary {
  padding: 20px 0; font-weight: 600; font-size: 1.05rem;
  cursor: pointer; list-style: none; display: flex;
  justify-content: space-between; align-items: center;
  transition: color var(--transition);
}
summary::-webkit-details-marker { display: none; }
summary:hover { color: var(--primary); }
.faq-icon { position: relative; width: 24px; height: 24px; flex-shrink: 0; }
.faq-icon::before, .faq-icon::after {
  content: ''; position: absolute; background: currentColor; border-radius: 1px;
  transition: transform 0.3s ease;
}
.faq-icon::before { top: 50%; left: 4px; right: 4px; height: 2px; transform: translateY(-50%); }
.faq-icon::after { left: 50%; top: 4px; bottom: 4px; width: 2px; transform: translateX(-50%); }
details[open] .faq-icon::after { transform: translateX(-50%) rotate(90deg); }
details[open] summary { color: var(--primary); }
```

---

## IMAGE PLACEHOLDERS

Never use `<img>` tags with fake URLs. Use styled `<div>` elements. Keep them CLEAN — no emoji, no labels, no overlapping badges:
```html
<!-- PHOTO: [description of ideal photo], [WxH], alt="[descriptive alt text]" -->
<div class="photo-placeholder" style="aspect-ratio: 16/9;"></div>
```
```css
.photo-placeholder {
  background: linear-gradient(135deg, var(--bg-medium) 0%, var(--bg-light) 100%);
  width: 100%; border-radius: var(--radius); overflow: hidden;
}
```
The placeholder is intentionally blank — no text inside, no "📷 Photo:" labels, no overlapping stat badges. The HTML comment above it tells the developer what photo to use.

**NEVER overlay floating stat boxes** (like "4.9 GOOGLE RATING" in a colored badge) on image placeholders. That is AI template slop. Stats belong in the content flow with good typography, not pasted on top of images.

For hero backgrounds: use a gradient that matches the brand colors instead of a placeholder image:
```css
.hero { background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 60%, var(--accent) 100%); }
```

### Overlapping dual-image treatment (for two-column sections):
In educational/about sections, show two images overlapping for depth:
```css
.img-stack { position: relative; }
.img-stack .photo-placeholder:first-child { border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); }
.img-stack .photo-placeholder:last-child {
  position: absolute; bottom: -20px; right: -20px; width: 55%;
  border-radius: var(--radius); box-shadow: var(--shadow-lg);
  border: 4px solid var(--bg);
}
```

### Gradient border on images (premium feel):
```css
.img-gradient-border {
  border: 4px solid transparent;
  background: linear-gradient(var(--bg), var(--bg)) padding-box,
              linear-gradient(135deg, var(--accent), var(--primary)) border-box;
  border-radius: var(--radius-lg);
}
```

---

## ADVANCED STYLING — USE SPARINGLY (pick 3-4, not all of them)

These are accent techniques. A polished page uses 3-4 of these well, not all 10 poorly:

### 1. Atmospheric background depth (on body or 1-2 sections max — NOT everywhere):
Use sparingly on the body element for subtle depth. Don't apply to every section — that's over-decoration:
```css
body {
  background:
    radial-gradient(ellipse at 20% 0%, rgba(var(--primary-rgb), 0.03) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 100%, rgba(var(--primary-rgb), 0.02) 0%, transparent 40%),
    var(--bg);
}
```

### 2. Simple accent bar on section headings (NOT gradient — solid color only):
```css
.heading-accent { position: relative; display: inline-block; padding-bottom: 0.75rem; }
.heading-accent::after {
  content: ''; position: absolute; bottom: 0; left: 0; width: 40px; height: 3px;
  border-radius: 2px; background: var(--primary);
}
```
Use on SOME h2s — not every single one. Let some headings stand on typography alone. NEVER use a multi-color gradient bar (red-to-blue etc.) — that is AI slop. Solid brand color only.

### 3. Corner bracket marks on featured cards:
```css
.corner-accent { position: relative; }
.corner-accent::before {
  content: ''; position: absolute; top: 0; left: 0; width: 24px; height: 24px;
  border-top: 3px solid var(--primary); border-left: 3px solid var(--primary);
  opacity: 0.3; transition: all var(--transition);
}
.corner-accent::after {
  content: ''; position: absolute; bottom: 0; right: 0; width: 24px; height: 24px;
  border-bottom: 3px solid var(--accent); border-right: 3px solid var(--accent);
  opacity: 0.3; transition: all var(--transition);
}
.corner-accent:hover::before, .corner-accent:hover::after { opacity: 0.7; width: 32px; height: 32px; }
```

### 4. Subtle CSS background patterns (no images needed):
```css
/* Dot grid pattern — apply to 1-2 light sections */
.pattern-dots {
  background-image: radial-gradient(circle, rgba(var(--primary-rgb), 0.04) 1px, transparent 1px);
  background-size: 24px 24px;
}
/* Diagonal lines — apply to dark sections */
.pattern-lines {
  background-image: repeating-linear-gradient(-45deg, transparent, transparent 10px,
    rgba(255,255,255,0.02) 10px, rgba(255,255,255,0.02) 11px);
}
```

### 5. Sliding underline on links (not just color change):
```css
.link-slide { position: relative; text-decoration: none; color: var(--primary); padding-bottom: 2px; }
.link-slide::after {
  content: ''; position: absolute; bottom: 0; left: 0; width: 0; height: 2px;
  background: var(--primary); transition: width var(--transition);
}
.link-slide:hover::after { width: 100%; }
```

### 6. Layered realistic shadows (not flat single-value shadows):
Use multi-layer shadows on featured cards and process steps for realistic depth:
```css
--shadow-realistic: 0px 15px 80px 0px rgba(0,0,0,0.07),
  0px 6px 33px 0px rgba(0,0,0,0.05), 0px 3px 18px 0px rgba(0,0,0,0.04),
  0px 2px 10px 0px rgba(0,0,0,0.03), 0px 1px 5px 0px rgba(0,0,0,0.02);
```

### 7. Vertical accent bar on content paragraphs:
```css
.content-accent { padding-left: 20px; position: relative; }
.content-accent::before {
  content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%;
  background: var(--primary); border-radius: 30px;
}
```

### 8. Button hover with gradient direction reversal (premium feel):
Instead of just darkening on hover, reverse the gradient direction:
```css
.btn-primary { background: linear-gradient(90deg, var(--primary) 0%, var(--primary-dark) 100%); position: relative; overflow: hidden; }
.btn-primary::before {
  content: ''; position: absolute; inset: 0; opacity: 0;
  background: linear-gradient(90deg, var(--primary-dark) 0%, var(--primary) 100%);
  transition: opacity var(--transition);
}
.btn-primary:hover::before { opacity: 1; }
.btn-primary span { position: relative; z-index: 1; }
```

### 9. Process steps with watermark numbers:
Use giant semi-transparent numbers behind step content:
```css
.step-card { position: relative; overflow: hidden; }
.step-card::before {
  content: attr(data-step); position: absolute; top: -15px; right: -5px;
  font-size: 7rem; font-weight: 700; line-height: 1;
  color: rgba(var(--primary-rgb), 0.05); pointer-events: none;
}
```
AND add a top accent bar that reveals on hover:
```css
.step-card::after {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--primary), var(--accent));
  transform: scaleX(0); transform-origin: left; transition: transform var(--transition);
}
.step-card:hover::after { transform: scaleX(1); }
```

### 10. Clean city list with subtle hover (NOT pills — plain text):
```css
.city-list {
  column-count: 3; column-gap: 2rem; list-style: none; padding: 0;
}
.city-list li {
  padding: 6px 0; font-size: 0.95rem; color: var(--text-secondary);
  break-inside: avoid; border-bottom: 1px solid rgba(0,0,0,0.04);
}
.city-list li a {
  color: inherit; text-decoration: none; transition: color var(--transition);
}
.city-list li a:hover { color: var(--primary); }
.city-list li.primary a { font-weight: 600; color: var(--text); }
```
City names should be plain text links in a multi-column list. Bold or brand-color the primary service cities. No pills, no badges, no tag containers. A small inline SVG map pin (12px, muted color) before each name is optional — not required.

### 11. Image hover zoom with gradient overlay:
```css
.img-hover { position: relative; overflow: hidden; border-radius: var(--radius); }
.img-hover .photo-placeholder { transition: transform var(--transition); }
.img-hover::after {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 40%, rgba(var(--primary-rgb), 0.5) 100%);
  opacity: 0; transition: opacity var(--transition);
}
.img-hover:hover .photo-placeholder { transform: scale(1.06); }
.img-hover:hover::after { opacity: 1; }
```

---

## STAGGERED PAGE LOAD ANIMATION (THE #1 IMPACT TECHNIQUE)

One well-orchestrated page load with staggered reveals creates more delight than scattered micro-interactions. Apply to the hero section and the first visible section below it:

```css
/* Staggered reveal on hero content */
.hero-content > * {
  opacity: 0;
  transform: translateY(20px);
  animation: revealUp 0.6s ease forwards;
}
.hero-content > *:nth-child(1) { animation-delay: 0.1s; }
.hero-content > *:nth-child(2) { animation-delay: 0.18s; }
.hero-content > *:nth-child(3) { animation-delay: 0.26s; }
.hero-content > *:nth-child(4) { animation-delay: 0.34s; }
.hero-content > *:nth-child(5) { animation-delay: 0.42s; }

@keyframes revealUp {
  to { opacity: 1; transform: translateY(0); }
}

/* Reduced motion respect */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

Also apply staggered `animation-delay` to: trust bar items, service cards, process step cards, city pill tags, stat counters. Each child element gets a 0.06-0.1s delay increment. This single technique makes the page feel alive and intentional.

---

## LAYERED BODY BACKGROUND (NEVER FLAT)

The body itself must have depth. Never use a flat `background: #fff`:
```css
body {
  background:
    radial-gradient(ellipse at 20% 0%, rgba(var(--primary-rgb), 0.03) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 100%, rgba(var(--primary-rgb), 0.02) 0%, transparent 40%),
    var(--bg);
}
```
This creates subtle atmospheric depth across the entire page. For dark-themed pages, increase the opacity to 0.06-0.08.

---

## SEO REQUIREMENTS
- Semantic HTML5: `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>`
- Proper heading hierarchy: exactly one `<h1>` (in the hero), logical `<h2>` → `<h3>` nesting. Target 12-18 headings total for content depth.
- `<title>` tag: "[Service] in [Location] | [Business Name]"
- `<meta name="description">` — 150-160 chars, includes service + location + CTA
- Open Graph tags: `og:title`, `og:description`, `og:type` (website)
- JSON-LD `LocalBusiness` schema in a `<script type="application/ld+json">` block
- JSON-LD `FAQPage` schema for the FAQ section (separate script block)
- All image placeholders have descriptive `alt` text in the HTML comment
- Internal linking: service area city names and sub-services should be styled as links

### Content depth for SEO:
- Total word count: 1,200-2,000+ words of real body content (not counting navigation, footer, form labels)
- Keywords: naturally incorporate the primary keyword (service + location) 8-15 times across headings and body text
- Heading variety: use the keyword in h1, 2-3 h2s, and 2-3 h3s with natural variations
- FAQ answers: 2-4 substantive sentences each, targeting featured snippet eligibility
- Sub-service list: 8-15 related services for topical relevance and internal linking opportunities

---

## INTERACTIVE COMPONENTS
- **FAQ accordion**: `<details>` + `<summary>` — no JS needed. Custom-styled `+`/`−` indicator.
- **Mobile menu**: Minimal JS (toggleClass on click). Menu slides down from header with smooth transition.
- **Smooth scroll**: `scroll-behavior: smooth` on `html`. Nav links use `href="#section-id"`.
- **Sticky header**: `position: sticky; top: 0; z-index: 1000;` with `backdrop-filter: blur(12px)` and shadow.
- **Form validation**: Use HTML5 `required`, `type="email"`, `type="tel"` attributes. Style `:invalid` and `:focus` states.

### Mobile menu JS (minimal):
```html
<script>
document.querySelector('.menu-toggle').addEventListener('click', function() {
  document.querySelector('.nav-menu').classList.toggle('active');
  this.classList.toggle('active');
});
</script>
```

---

## COPY RULES
- Lead with the CUSTOMER'S PROBLEM, not the business's credentials
- Use "you" and "your" — write to one homeowner, not an audience
- Location-specific references: name the city, neighborhoods, local context (e.g., "Homeowners across Spring, TX trust us...")
- No corporate clichés: never use "world-class", "best-in-class", "cutting-edge", "seamless", "leverage", "synergy", "comprehensive", "state-of-the-art"
- Every CTA is specific: "Call for a Free Drain Inspection" not "Contact Us"
- FAQ questions match real Google queries: "How much does [service] cost in [city]?" not "What is [service]?"
- Testimonials sound real: include specific details ("Colby and Luke did a great job installing my water softener system") not generic praise
- Educational sections teach something useful — what causes the problem, when to call a pro vs DIY, what to expect during service, cost factors

---

## RESPONSIVE DESIGN

### Breakpoints:
```css
@media (max-width: 1024px) { /* Tablet landscape */ }
@media (max-width: 768px) { /* Tablet portrait / large phone */ }
@media (max-width: 480px) { /* Small phone */ }
```

### Mobile rules:
- Hero: stack vertically (content → form), reduce headline to `2rem`, form goes full-width
- All grids: collapse to single column (services, testimonials, process steps)
- Trust bar: 2x2 grid instead of 4-across
- Sidebar forms: stack below main content, no longer sticky
- Section padding: reduce from `80px 0` to `48px 0`
- Navigation: hamburger menu, phone icon always visible
- Touch targets: all buttons minimum 48px tall
- City grid: reduce to 2-3 columns
- Font sizes: use `clamp()` so they scale naturally
- FAQ: full-width tap targets

---

## BRAND MATCHING

When brand colors are provided, build the ENTIRE design around them:
1. Derive `--primary-dark` (darken 15%), `--primary-light` (lighten 85%), `--bg-primary-tint` (5% opacity) from the primary color
2. Use the primary color for: all CTA buttons, icon colors, accent borders, section headings color, form submit button, trust bar icons, active states, link hover color
3. Use `--primary-dark` for: hero gradient, dark sections, footer, hover states
4. Use `--primary-light` or `--bg-primary-tint` for: alternate section backgrounds, card hover states
5. Keep text colors neutral (dark gray/near-black) — never make body text the brand color
6. The page should feel like it belongs to that brand without seeing the logo

When style_direction is provided (e.g., "bold and modern", "clean and professional", "rugged and strong"):
- **Bold/modern:** Larger headings, more uppercase, sharper shadows, angled sections, high contrast
- **Clean/professional:** More whitespace, subtle shadows, minimal uppercase, refined spacing
- **Rugged/strong:** Darker palette, heavier weights, textured backgrounds, industrial feel
- **Playful/friendly:** Rounder corners (radius-xl), warmer colors, more personality in copy

---

## DEVELOPER HANDOFF NOTES
At the very end of the HTML (before `</body>`), include an HTML comment block:
```html
<!--
DEVELOPER HANDOFF NOTES
========================
Image Specs:
- Hero background: 1920x1080, subject: [description]
- Education sections: 800x600 each, subjects: [descriptions]
- Testimonials: 80x80 headshots, circular crop
- Gallery: 800x600 each, subjects: [descriptions]
- Blog thumbnails: 600x400 each

Phone: Replace all instances of [PHONE] with real number
Email: Replace [EMAIL] with real email
Form: Connect form to CRM/booking system (HouseCallPro, ServiceTitan, etc.)
Reviews: Replace placeholder reviews with real Google/Yelp reviews
Blog: Link blog cards to actual blog posts
Service area: Verify city list matches actual service coverage
Logo: Replace text logo in nav with actual logo image/SVG
Colors: All customizable via CSS custom properties in :root
Schema: Update LocalBusiness schema with real business data
-->
```

## QUALITY BAR
The output must look like a page designed by Hook Agency, 180 Sites, or Be The Anomaly — not a Bootstrap template or generic AI output.

### THE 10 TELLS OF AI-GENERATED DESIGN (avoid ALL of these):
1. **Pill badges for plain data** — City names in rounded pill containers, categories in colored tags, service areas in badge format. Real designers use plain text.
2. **Gradient underlines on headings** — Especially multi-color gradients (red-to-blue, purple-to-teal). Use a simple solid-color accent bar or nothing.
3. **Floating stat badges overlapping images** — "4.9 GOOGLE RATING" in a colored box on top of a photo. Stats belong in the content flow.
4. **Icons in colored circles repeated in a row** — 3-6 identical colored circle icons with labels. Use icons without containers or vary presentation.
5. **Identical card treatment everywhere** — Every card: white bg, 8px radius, same shadow. Vary treatments: accent borders, background tints, no-border styles.
6. **Forced gradients that don't serve the palette** — Random gradient bars as decoration. Gradients should only connect related colors in your system.
7. **Emoji in headings** — Never. Typography carries the heading.
8. **Over-decorated image placeholders** — No emoji labels, no "📷 Photo:" text, no overlapping badges on images. Clean empty boxes.
9. **Uniform spacing** — Same padding on every section. Vary it: hero 100-120px, features 80px, stats 48px, CTA 100px.
10. **"Trying too hard" decoration** — If you're adding a visual element just to fill space or look fancy, remove it. Restraint is design.

### Specific markers of quality:
- Diagonal/angled section transitions (clip-path or SVG) on at least 2 sections
- No two consecutive sections use the same layout or background color
- Trust signals appear in at least 6 distinct locations
- 8-12 CTAs distributed throughout the page
- 1,200+ words of real, educational, SEO-relevant content
- Professional card system with consistent shadows and border-radius
- Intentional whitespace — generous section padding (80px), never cramped
- Color restraint — primary color does all the accent work, everything else is neutral
- The page tells a story: Problem → Solution → Proof → Process → Action

### Design quality markers (at least 5 of these must appear):
- [ ] Varied section padding (no two consecutive sections with the same vertical padding)
- [ ] At least 2 different card/content treatments (not every card identical)
- [ ] Varied image treatments (some clean rectangle, some with shadow, some overlapping)
- [ ] Process steps with watermark numbers OR timeline connector
- [ ] Hover states on all interactive elements (buttons lift, cards elevate, links shift color)
- [ ] At least 1 section with overlapping elements (negative margins or transforms creating depth)
- [ ] Comparison section uses simple checkmarks (✓/✗) — not in colored circle badges
- [ ] FAQ accordion with clean +/− indicator
- [ ] City/service area displayed as clean text list — NOT pills or badges
- [ ] Typography hierarchy with weight contrast (light labels vs bold headings vs regular body)
- [ ] Layered body background (subtle radial gradients for atmospheric depth)
- [ ] At least 1 full-bleed dark section breaking up the light sections"""


DESIGN_POLISH_PROMPT = """You are an elite frontend designer who builds $10,000+ custom pages for home service contractors. You receive a complete HTML page and REDESIGN it to look like a premium $10K agency build.

## YOUR #1 JOB: Make this page look CUSTOM, not template.
Generic AI pages all look the same — same spacing, same radius, same shadows, same white/light-gray alternation. Your job is to break that pattern. Every section should feel intentionally different from the one above it.

---

## CONTENT RULES (NEVER VIOLATE):
1. Every heading, paragraph, FAQ, city name, phone number, business name — VERBATIM.
2. All JSON-LD, meta tags, form fields — preserved exactly.
3. Semantic structure (header, nav, main, sections, footer) — maintained.
4. You may ADD wrapper divs, decorative elements, SVGs, pseudo-elements.
5. You may NOT remove, rephrase, or reorder any content.

---

## RULE #0: USE THE BRAND COLORS FROM THE INPUT HTML.
The input HTML already has brand colors defined in its CSS custom properties or inline styles. You MUST:
- Find the existing --primary, accent, or brand color values in the input
- Keep those EXACT hex values as your primary and accent colors
- Build your palette around them (darker/lighter variants are fine)
- NEVER substitute your own color choices. If the input uses #1e3a5f and #dc2626, your output uses #1e3a5f and #dc2626.

---

## 5 MANDATORY TECHNIQUES (You MUST use ALL 5):

### 1. SVG Section Dividers — at least 3 different ones
Place inline SVGs between sections to create diagonal, wave, or curve transitions. Each one MUST be a different shape. Position them absolutely at the bottom of one section or top of the next:

```css
.divider { position: absolute; bottom: -1px; left: 0; width: 100%; overflow: hidden; line-height: 0; }
.divider svg { display: block; width: calc(100% + 1.3px); height: 80px; }
```

Example shapes (use different ones each time):
- Diagonal: `<polygon points="0,120 1440,0 1440,120" fill="NEXT_SECTION_COLOR"/>`
- Wave: `<path d="M0,80 C360,0 1080,120 1440,40 L1440,120 L0,120 Z" fill="..."/>`
- Slant: `<polygon points="0,0 1440,80 1440,120 0,120" fill="..."/>`

### 2. Gradient Overlay on Hero — dark directional gradient over a pattern/texture
The hero MUST have a dramatic gradient overlay, not just a flat dark background:

```css
.hero { position: relative; overflow: hidden; }
.hero::before {
  content: ""; position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(PRIMARY_DARK, 0.97) 0%, rgba(PRIMARY, 0.8) 40%, rgba(ACCENT, 0.3) 100%);
  z-index: 1;
}
.hero::after {
  content: ""; position: absolute; inset: 0;
  background-image: url('data:image/svg+xml,...'); /* crosshatch, dots, or diagonal lines */
  opacity: 0.08;
}
```

### 3. Negative-Margin Section Overlap — trust bar or cards overlapping hero
At least ONE element must break section boundaries using negative margin:

```css
.trust-overlap { margin-top: -60px; position: relative; z-index: 10; }
```

### 4. Varied Section Backgrounds — NEVER repeat the same background treatment
Each section MUST have a visually distinct background. Use this rotation:
- Section 1 (hero): Dark with gradient overlay + subtle texture
- Section 2: White with overlapping trust bar
- Section 3: Light gray (#f5f5f5 to #f0f0f0)
- Section 4: DARK section (primary-dark or near-black) with white text
- Section 5: White with left-border accent blocks
- Section 6: Accent color (primary) with white text
- Section 7: Light gray with card grid
- ...continue varying. Two adjacent sections must NEVER share the same background color.

### 5. Signature Design Element — pick ONE, repeat it 4+ times across the page
Choose one distinctive CSS technique and make it the page's visual identity. Use it on buttons, cards, images, and section accents. Pick from:

**Option A — Double-border treatment:**
```css
.signature { border-style: double; border-width: 4px; border-color: var(--accent); }
```
Apply to: buttons, image frames, accordion headers, card borders, form inputs.

**Option B — Solid color offset shadow:**
```css
.signature { box-shadow: 8px 8px 0 0 var(--accent); }
```
Apply to: images, cards, CTA boxes, hero form, testimonial cards.

**Option C — Gradient border (border-box technique):**
```css
.signature { border: 3px solid transparent; background: linear-gradient(var(--bg), var(--bg)) content-box, linear-gradient(90deg, var(--primary), var(--accent)) border-box; }
```
Apply to: cards, hero form, images, process step boxes, CTA banner.

**Option D — Asymmetric border-radius:**
```css
.signature { border-radius: 0 24px; }  /* or: 24px 0 24px 0 */
```
Apply to: cards, images, micro labels, buttons, section corners.

---

## ADDITIONAL TECHNIQUES (Use at least 3 of these):

A. **Skewed image frames:** `transform: skewX(-5deg)` on container, `skewX(5deg) scale(1.1)` on image
B. **Accent left-border on text blocks:** `border-left: 3px solid var(--accent); padding-left: 24px;`
C. **Alternating two-column directions:** Odd sections left-to-right, even sections right-to-left
D. **Multi-layer card shadows (6-layer realistic):**
```css
box-shadow: 0px 15px 80px 0px rgba(0,0,0,0.08), 0px 6px 33px 0px rgba(0,0,0,0.06), 0px 3px 18px 0px rgba(0,0,0,0.04), 0px 2px 10px 0px rgba(0,0,0,0.03), 0px 1px 5px 0px rgba(0,0,0,0.02), 0px 0.4px 2px 0px rgba(0,0,0,0.02);
```
E. **Micro/eyebrow labels** above headings: small, uppercase, letter-spaced, accent-colored
F. **Dark hero CTA bar** with 3 key trust points overlapping the section below
G. **Dashed coupon-style borders** on special offer sections: `border: 3px dashed var(--accent);`
H. **Thick bottom-border accent on cards:** `border-bottom: 5px solid var(--accent);`

---

## CSS REQUIREMENTS:

1. Define ALL colors, shadows, and radii as CSS custom properties at :root
2. System font stack: `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
3. Headings: font-weight 800, tight line-height (1.1-1.2), clamp() for responsive sizing
4. Body: 0.9375rem, line-height 1.65, color var(--text)
5. Responsive breakpoints at 1024px, 768px, 480px — sections must stack cleanly
6. FAQ accordion with animated plus/minus (::before/::after pseudo-elements)
7. Smooth hover transitions (0.3s ease-in-out) on buttons, cards, links
8. Footer: multi-column grid layout

## ANTI-SLOP RULES (NEVER do these):
1. NO pill badges wrapping plain text (city names, categories)
2. NO gradient underline bars on headings
3. NO icons in colored circles repeated in identical rows
4. NO identical card treatments — vary shadows, borders, or backgrounds
5. NO emoji in headings or section titles
6. NO generic blue-to-purple gradients
7. NO "cleaning up" the design — your output CSS must be MORE detailed than the input, never less
8. NO replacing brand colors with your own palette choices

## CRITICAL SIZE RULE:
Your output `<style>` block MUST contain MORE CSS than the input's `<style>` block. You are ADDING visual richness, not simplifying. If the input has 300 lines of CSS, your output should have 400+. The page should get MORE visually interesting, not less.

## OUTPUT FORMAT
Output ONE complete `<!DOCTYPE html>` file. No markdown. No preamble. Start with `<!DOCTYPE html>`, end with `</html>`.

CSS resets at top of `<style>`:
```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
img { max-width: 100%; height: auto; display: block; }
```"""


def _build_user_prompt(inputs, strategy_context, client_name):
    """Build the user prompt from inputs (shared by both passes)."""
    page_type       = inputs.get("page_type", "service").strip()
    business_type   = inputs.get("business_type", "home service business").strip()
    service         = inputs.get("service", "").strip()
    location        = inputs.get("location", "").strip()
    business_name   = inputs.get("business_name", "").strip() or client_name
    phone           = inputs.get("phone", "").strip()
    brand_colors    = inputs.get("brand_colors", "").strip()
    style_direction = inputs.get("style_direction", "").strip()
    existing_copy   = inputs.get("existing_copy", "").strip()
    notes           = inputs.get("notes", "").strip()

    lines = [
        f"Design a complete {page_type} page for **{business_name}**, a {business_type} serving {location}.",
        "",
        f"**Page type:** {page_type}",
        f"**Service/focus:** {service}" if service else "",
        f"**Location:** {location}",
        f"**Business name:** {business_name}",
    ]

    if phone:
        lines.append(f"**Phone number:** {phone}")
    if brand_colors:
        lines.append(f"**Brand colors to use:** {brand_colors}")
    if style_direction:
        lines.append(f"**Design style direction:** {style_direction}")
    if existing_copy:
        lines += ["", "**Existing copy to incorporate:**", f"<existing_copy>\n{existing_copy}\n</existing_copy>"]
    if notes:
        lines += ["", f"**Additional instructions:** {notes}"]
    if strategy_context and strategy_context.strip():
        lines += ["", f"**Strategy direction:** {strategy_context.strip()}"]
    lines += ["", "Output the complete HTML file now. Start with <!DOCTYPE html>. No preamble."]

    return "\n".join(l for l in lines if l is not None)


def _run_gemini_design_pass(claude_html: str, brand_colors: str = "") -> list:
    """
    Synchronous Gemini call — runs in a thread via asyncio.to_thread().
    Returns a list of text chunks from Gemini's streaming response.
    """
    from google import genai
    import re as _re

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return []

    client = genai.Client(api_key=api_key)

    # Extract existing colors from Claude's HTML so Gemini knows what to keep
    color_note = ""
    if brand_colors:
        color_note = f"\n\nBRAND COLORS (you MUST use these exact hex values as your primary/accent): {brand_colors}\n"
    else:
        # Try to extract from CSS custom properties
        color_match = _re.findall(r'--(?:primary|accent)[^:]*:\s*(#[0-9a-fA-F]{3,8})', claude_html)
        if color_match:
            color_note = f"\n\nBRAND COLORS extracted from input (KEEP these exact hex values): {', '.join(color_match)}\n"

    redesign_prompt = (
        "Here is a service page HTML built by another AI. The content and SEO structure are excellent. "
        "The visual design is GENERIC — it looks like every other AI-generated page. Your job is to make it look CUSTOM.\n\n"
        "SPECIFIC PROBLEMS TO FIX:\n"
        "- Sections all look the same (same padding, same white/gray backgrounds)\n"
        "- No SVG section dividers between sections\n"
        "- Hero is flat and boring — needs a dramatic gradient overlay + texture\n"
        "- Cards and elements all have identical, basic styling\n"
        "- No signature design element tying the page together\n"
        "- No negative-margin overlaps creating depth between sections\n\n"
        "WHAT YOU MUST DO (all 5 are mandatory):\n"
        "1. Add 3+ different SVG section dividers (diagonal, wave, slant) between sections\n"
        "2. Give the hero a dramatic multi-stop gradient overlay with a subtle SVG texture pattern\n"
        "3. Create at least one negative-margin overlap (trust bar or cards breaking section boundaries)\n"
        "4. Make every section background visually distinct — dark, light, accent, white with texture, etc.\n"
        "5. Pick ONE signature element (double-border, offset shadow, gradient border, or asymmetric radius) and repeat it on 4+ elements\n\n"
        f"{color_note}"
        "PRESERVE ALL CONTENT VERBATIM. Only change CSS, layout, and visual presentation.\n\n"
        f"<source_html>\n{claude_html}\n</source_html>\n\n"
        "Output the complete redesigned HTML file now. Start with <!DOCTYPE html>. No preamble."
    )

    chunks = []
    try:
        response = client.models.generate_content_stream(
            model="gemini-3.1-pro-preview",
            contents=[{"role": "user", "parts": [{"text": redesign_prompt}]}],
            config={
                "temperature": 1,
                "max_output_tokens": 65536,
                "system_instruction": DESIGN_POLISH_PROMPT,
            },
        )
        for chunk in response:
            if chunk.text:
                chunks.append(chunk.text)
    except Exception as e:
        print(f"[page-design] Gemini design pass failed: {e}")
        return []

    return chunks


def _extract_html(text: str) -> str:
    """Extract clean HTML from a response that may have markdown fences."""
    import re
    idx = text.find("<!DOCTYPE")
    if idx < 0:
        idx = text.find("<html")
    if idx >= 0:
        html = text[idx:]
        html = re.sub(r'\n```\s*$', '', html)
        end_idx = html.rfind("</html>")
        if end_idx > 0:
            html = html[:end_idx + len("</html>")]
        return html
    return text


async def run_page_design(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    """
    Two-pass page design pipeline:
    Pass 1 — Claude Opus: generates complete HTML with all content, SEO, trust signals
    Pass 2 — Gemini 3.1 Pro: redesigns the visual presentation for a polished, custom look
    Falls back to Claude's output if Gemini is unavailable or fails.
    """
    page_type     = inputs.get("page_type", "service").strip()
    business_name = inputs.get("business_name", "").strip() or client_name
    domain        = inputs.get("domain", "").strip()
    gemini_key    = os.environ.get("GEMINI_API_KEY", "")
    use_gemini    = bool(gemini_key)

    yield f"> Designing **{page_type} page** for **{business_name}**...\n"

    # ── Brand extraction from domain (if provided and no manual colors) ──
    if domain and not inputs.get("brand_colors", "").strip():
        yield f"> Scanning **{domain}** for brand colors & style...\n"
        brand_info = await _extract_brand_from_domain(domain)
        if brand_info["brand_colors"]:
            inputs["brand_colors"] = brand_info["brand_colors"]
            yield f"> Found brand colors: **{brand_info['brand_colors']}**\n"
        if brand_info["style_direction"] and not inputs.get("style_direction", "").strip():
            inputs["style_direction"] = brand_info["style_direction"]
            yield f"> Detected style: **{brand_info['style_direction']}**\n"
        if brand_info["font_hint"] and brand_info["font_hint"] != "system":
            # Pass font hint as a note for Claude to consider
            existing_notes = inputs.get("notes", "")
            inputs["notes"] = f"Brand font: {brand_info['font_hint']}. {existing_notes}".strip()
            yield f"> Brand font: **{brand_info['font_hint']}**\n"
        if not brand_info["brand_colors"] and not brand_info["style_direction"]:
            yield "> Could not extract brand info — using defaults.\n"

    if use_gemini:
        yield f"> **Pass 1:** Generating content & structure with Claude Opus...\n\n"
    else:
        yield "\n"

    user_prompt = _build_user_prompt(inputs, strategy_context, client_name)

    # ── Pass 1: Claude Opus generates the full page ──
    claude_chunks = []
    last_progress_kb = 0
    import time as _time
    pass1_start = _time.time()

    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=64000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            claude_chunks.append(text)
            if not use_gemini:
                yield text
            else:
                # Send periodic progress during silent generation
                total_bytes = sum(len(c) for c in claude_chunks)
                current_kb = total_bytes // 1024
                if current_kb >= last_progress_kb + 10:
                    elapsed = int(_time.time() - pass1_start)
                    yield f"> Writing HTML... ({current_kb}KB, {elapsed}s)\n"
                    last_progress_kb = current_kb

    if not use_gemini:
        return

    claude_html = _extract_html("".join(claude_chunks))
    pass1_elapsed = int(_time.time() - pass1_start)

    # Quick stats for the status message
    import re
    sections = len(re.findall(r'<section', claude_html))
    headings = len(re.findall(r'<h[1-6]', claude_html))
    yield f"> Pass 1 complete — {len(claude_html)//1024}KB, {sections} sections, {headings} headings ({pass1_elapsed}s)\n"
    yield f"> **Pass 2:** Polishing design with Gemini 3.1 Pro...\n\n"

    # ── Pass 2: Gemini 3.1 Pro redesigns the visual layer ──
    brand_colors = inputs.get("brand_colors", "").strip()
    pass2_start = _time.time()
    gemini_chunks = await asyncio.to_thread(_run_gemini_design_pass, claude_html, brand_colors)
    pass2_elapsed = int(_time.time() - pass2_start)

    if not gemini_chunks:
        yield "> Gemini unavailable — using Claude's design.\n\n"
        yield claude_html
        return

    gemini_html = _extract_html("".join(gemini_chunks))
    yield f"> Pass 2 complete — {len(gemini_html)//1024}KB ({pass2_elapsed}s)\n"

    # Verify Gemini produced complete HTML
    if not gemini_html.rstrip().endswith("</html>"):
        yield "> Gemini output incomplete — using Claude's design.\n\n"
        yield claude_html
        return

    yield "> Rendering preview...\n\n"

    # Stream Gemini's polished output
    yield gemini_html
