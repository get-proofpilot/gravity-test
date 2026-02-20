# ProofPilot Agent Hub

AI-powered SEO operations platform for home service agencies. Run workflows against real client data, stream live via Claude Opus 4.6, export branded `.docx` documents.

**Live:** `https://proofpilot-agents.up.railway.app`
**Repo:** `https://github.com/get-proofpilot/proofpilot-agent-hub`

---

## Mission

ProofPilot Agent Hub exists to **remove Matthew from the fulfillment bottleneck**. Every workflow automated here frees hours that go toward closing new clients or building acquisition systems. The platform is on the critical path to scaling ProofPilot from ~$25-30K MRR to $5M+ ARR.

**Who uses it:**
- **Matthew** — runs workflows, reviews output, uses for prospect audits and sales
- **Jo Paula** — reviews and publishes content (needs Drive integration for zero-friction handoff)

**What success looks like:** A full month of content for one client takes <10 minutes of Matthew's time. Monthly reports auto-generate. Prospect audits close deals without manual research.

---

## Current State

**Phase 1 (Core Platform): COMPLETE**
- 10 live workflows with real-time SSE streaming
- Branded `.docx` export on every job
- SQLite persistence (jobs + clients) on Railway Volume
- Content Library with client grouping, search, and filters
- Per-client hub with activity tracking
- Workflow categories with sample output previews
- DataForSEO integration (14+ functions: SERP, Maps, Labs, Keywords, GBP, Difficulty)
- Search Atlas integration (organic data, backlinks, holistic audit scores)
- Programmatic Content Agent (bulk location/service/blog generation)
- Client CRUD API (`/api/clients` — create, read, update, soft-delete)
- Job approval system (`/api/jobs/{id}/approve`)

**Phase 2 (Client Data Layer): COMPLETE**
- [x] Client CRUD API + SQLite table
- [x] Frontend client management
- [x] Job approval with badges
- [x] Content approval filtering (All / Approved / Pending)
- [x] Domain format validation on workflow launch
- [x] TTL cleanup for `temp_docs/` (7-day retention, auto-cleans on startup)

**Phase 3 (Reports + Client Portal): COMPLETE**
- [x] Monthly Client Report workflow (SA + DFS + job history → narrative report)
- [x] Client Portal (`/portal/{token}` — public-facing, shareable link per client)
- [x] Portal API (`/api/portal/{token}` — client info + all deliverables)
- [x] Portal token auto-generation for all clients
- [x] Portal link copy button in Client Hub
- [x] Content type filters for GBP Posts + Monthly Reports

**What's NOT built yet (high priority per growth plan):**
- Google Drive integration (Phase 4 — zero-friction content handoff to Jo Paula)
- Scheduled automations / cron (makes the platform run without Matthew)

---

## What to Build Next

Ordered by business impact. Each item maps to the master growth plan at `~/Agency-Brain/strategy/master-growth-plan.md`.

| Priority | Feature | Why | Effort |
|----------|---------|-----|--------|
| 1 | **Google Drive Integration** | Approved content auto-uploads to client folders. Jo Paula's inbox becomes zero-friction. | Medium |
| 2 | **On-Page Technical Audit** | Async DFS crawl → ranked issue list. Sells as one-time audit or recurring monitoring. | Medium |
| 3 | **Scheduled Automations** | Monthly reports on the 1st, GBP posts on the 28th, competitor monitoring daily. | High |
| 4 | **WordPress Direct Publish** | Push approved content straight to client WordPress sites as drafts. | Medium |
| 5 | **Portal Auth + Branding** | Add optional password protection, custom logo upload, and branded portal themes. | Medium |

Full roadmap with implementation details: `ROADMAP.md`

---

## Working Conventions

### Local Development
```bash
cd ~/Documents/ProofPilot-Agent-Hub/backend
cp .env.example .env   # ANTHROPIC_API_KEY, SEARCHATLAS_API_KEY, DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD
.venv/bin/uvicorn server:app --reload
# → http://localhost:8000
```

### Deployment
- **Railway auto-deploys on push to main** — root dir is `/backend`
- Railway Volume persists SQLite at `/app/data/jobs.db`
- Set env vars: `railway variables set KEY=value`
- Always test locally before pushing — there's no staging environment
- Check deployment health: `https://proofpilot-agents.up.railway.app/health`

### Code Patterns
- **Python:** Python 3.11, FastAPI, async generators for SSE streaming
- **Frontend:** Pure HTML/CSS/JS SPA — no frameworks, no build step. All in `backend/static/`
- **Claude API:** Always use `claude-opus-4-6`, `thinking: {"type": "adaptive"}`, `max_tokens: 8000`. No prefills — Opus 4.6 returns 400 on assistant turn prefills
- **Streaming:** `client.messages.stream()` → `async for text in stream.text_stream` → `yield text`
- **New features:** Prefer editing existing files over creating new ones. The frontend is a single SPA — add views/modals to the existing `index.html`, `script.js`, `style.css`

### Git & Commits
- Work on `main` branch (single developer, Railway auto-deploys)
- Commit messages: describe what changed and why, not just "update files"
- Don't push untested code — Railway deploys immediately
- Dockerfile comment tracks version: update the `# Copy application code — vN (description)` line

### What NOT to Do
- Never auto-publish or auto-deploy content to client sites without approval
- Never use Search Atlas `content_genius`, `digital_pr`, `OTTO_SEO_Deployment`, `OTTO_Wildfire`, `gbp_posts_automation`, `gbp_posts_publication`, or `Content_Publication_Tools`
- Never commit `.env` files or API keys
- Don't over-engineer — this is a production tool for one agency, not a SaaS platform (yet)

---

## Agent Playbook

Use these patterns to work faster and smarter in Claude Code sessions.

### When to Use Sub-Agents

| Situation | Agent Type | Why |
|-----------|-----------|-----|
| Exploring unfamiliar code | `Explore` | Keeps main context clean for implementation |
| Researching APIs or libraries | `general-purpose` | Can web search + read docs without polluting your context |
| Planning multi-file changes | `Plan` | Designs approach before you start coding |
| Independent parallel tasks | Multiple `Task` agents | Run 2-3 research tasks simultaneously |
| Building frontend + backend in parallel | Separate `Task` agents | One for Python changes, one for JS/HTML |

### Session Start Checklist
Every new session should begin with understanding current state:
1. Read this CLAUDE.md (happens automatically)
2. Check `git status` and `git log --oneline -5` to see recent work
3. Check ROADMAP.md if building a new feature
4. Check `~/Agency-Brain/strategy/master-growth-plan.md` if making strategic decisions

### Effective Patterns
- **Research before coding:** Use an Explore agent to understand existing patterns before modifying code
- **Parallel research:** Launch 2-3 Explore agents simultaneously for different aspects of a problem
- **Keep context focused:** Use sub-agents for exploration, keep the main thread for implementation
- **Test incrementally:** After each significant change, test locally before moving to the next
- **Update this file:** After shipping a feature, update the "Current State" and "What to Build Next" sections

### When Adding a New Feature
1. Read ROADMAP.md for the spec (if it exists)
2. Read the relevant existing code (workflow files, server.py, script.js)
3. Follow the 5-Step Workflow Pattern (documented below) if it's a new workflow
4. Test locally with `uvicorn server:app --reload`
5. Commit with a descriptive message
6. Push to main (triggers Railway deploy)
7. Update CLAUDE.md "Current State" section

### Keeping This File Current
This CLAUDE.md is the project's memory. Update it when:
- A feature ships → move from "What to Build Next" to "Current State"
- A new priority emerges → add to "What to Build Next" with reasoning
- A pattern changes → update "Working Conventions"
- A new API is integrated → add to the technical reference section
- Tech debt is resolved → remove from known limitations

---

## Stack

| Layer | Tech |
|-------|------|
| AI | Claude Opus 4.6 via `anthropic` SDK (streaming + adaptive thinking) |
| Backend | Python 3.11 + FastAPI + uvicorn + SSE |
| Database | SQLite on Railway Volume (`/app/data/jobs.db`) |
| Frontend | Vanilla HTML/CSS/JS SPA (`backend/static/`) |
| Export | `python-docx` → branded `.docx` files |
| SEO Data | DataForSEO (SERP, Labs, Keywords, GBP, On-Page) |
| SEO Data | Search Atlas MCP (organic, backlinks, holistic audit, local SEO) |
| Deploy | Railway — auto-deploy on push, Dockerfile in `/backend` |

### Key Files
```
backend/
  server.py              — FastAPI app, routes, SSE streaming, workflow dispatch
  utils/
    dataforseo.py        — DataForSEO API client (14+ functions)
    searchatlas.py       — Search Atlas MCP wrapper
    docx_generator.py    — Branded Word document output
    db.py                — SQLite schema, CRUD operations, seed data
  workflows/
    website_seo_audit.py — Full site SEO audit (SA + DFS + Labs)
    prospect_audit.py    — Sales-focused market analysis (SA + DFS + Keywords + GBP)
    keyword_gap.py       — Competitor keyword gap (DFS Labs + SA)
    seo_blog_post.py     — Blog post (Claude only)
    service_page.py      — Service page (Claude only)
    location_page.py     — Location page (Claude only)
    home_service_content.py — Home service article (Claude only)
    programmatic_content.py — Bulk generation agent (batch mode)
    gbp_posts.py         — GBP post batch generator (Claude only)
    monthly_report.py    — Monthly client report (SA + DFS + job history)
  static/
    index.html           — Full SPA markup (all views, modals)
    script.js            — WORKFLOWS array, view routing, SSE streaming, workflow launch
    style.css            — Dark theme with ProofPilot brand system
    portal.html          — Client portal (standalone, public-facing)
```

---

## Brand System

| Element | Value |
|---------|-------|
| Dark Blue | `#00184D` / `--dark-blue` |
| Electric Blue | `#0051FF` / `--elec-blue` |
| Neon Green | `#C8FF00` / `--neon-green` |
| Base Background | `#060D1F` |
| Panel Background | `#0A1530` |
| Panel Headers | `#0E1D3E` |
| Display Font | Bebas Neue |
| Code Font | Martian Mono |
| Body Font | Inter |
| Transitions | `--t-fast: 0.15s ease`, `--t-med: 0.22s ease` |

### .docx Brand Rendering
- `# H1` → Bebas Neue 24pt Dark Blue
- `## H2` → Bebas Neue 15pt Electric Blue
- `### H3` → Calibri 12pt bold Dark Blue
- `---` → Electric Blue rule
- Bold, italic, bullets, numbered lists all supported

---

## Live Workflows (10 Active)

| Workflow ID | Title | Data Sources | File |
|-------------|-------|-------------|------|
| `website-seo-audit` | Website & SEO Audit | Search Atlas + DataForSEO + DFS Labs | `workflows/website_seo_audit.py` |
| `prospect-audit` | Prospect SEO Market Analysis | SA + DFS SERP + Keywords + GBP + Difficulty | `workflows/prospect_audit.py` |
| `keyword-gap` | Keyword Gap Analysis | DFS Labs (ranked keywords diff) + SA | `workflows/keyword_gap.py` |
| `home-service-content` | Home Service SEO Content | Claude only | `workflows/home_service_content.py` |
| `seo-blog-post` | SEO Blog Post | Claude only | `workflows/seo_blog_post.py` |
| `service-page` | Service Page | Claude only | `workflows/service_page.py` |
| `location-page` | Location Page | Claude only | `workflows/location_page.py` |
| `programmatic-content` | Programmatic Content Agent | Claude + optional DFS | `workflows/programmatic_content.py` |
| `gbp-posts` | GBP Posts | Claude only | `workflows/gbp_posts.py` |
| `monthly-report` | Monthly Client Report | SA + DFS Labs + Job History | `workflows/monthly_report.py` |

### How Workflows Work
1. Frontend POSTs to `/api/run-workflow` with `workflow_id`, `client_name`, `inputs`, `strategy_context`
2. Backend streams SSE tokens (`type: token`) as Claude generates
3. On completion: generates branded `.docx`, persists to SQLite, returns `type: done`
4. Frontend: live streaming terminal → download button → adds to Content Library

---

## Adding a New Workflow (5-Step Pattern)

Every new workflow requires exactly these 5 changes:

### Step 1: Create `workflows/{name}.py`
```python
"""
Workflow description
inputs keys: domain, service, location, ...
"""
import anthropic
from typing import AsyncGenerator

SYSTEM_PROMPT = """You are ..."""

async def run_{name}(
    client: anthropic.AsyncAnthropic,
    inputs: dict,
    strategy_context: str,
    client_name: str,
) -> AsyncGenerator[str, None]:
    # 1. Extract inputs
    # 2. Yield status message
    # 3. Build user_prompt
    # 4. Stream Claude response
    async with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
```

### Step 2: Register in `server.py`
```python
from workflows.{name} import run_{name}
# Add to WORKFLOW_TITLES dict
# Add elif in event_stream()
```

### Step 3: Add to `static/script.js` WORKFLOWS array
```javascript
{ id: '{workflow-id}', icon: '...', title: '...', desc: '...', time: '~X min',
  status: 'active', skill: '{workflow-id}', category: 'seo|content|business|dev' },
```

### Step 4: Add modal panel to `static/index.html`
Add a `div#modalInputs{Name}` with input fields matching the workflow's input schema.

### Step 5: Wire in `static/script.js` (3 places)
- `selectWorkflow()` — show/hide the modal panel
- `checkRunReady()` — validate required fields
- `launchWorkflow()` — collect inputs and add to liveWorkflows array

---

## Backend API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/run-workflow` | POST | Start workflow → SSE stream |
| `/api/download/{job_id}` | GET | Download branded .docx |
| `/api/jobs/{job_id}` | GET | Job metadata + content preview |
| `/api/jobs/{job_id}/approve` | POST | Mark job as approved |
| `/api/jobs/{job_id}/approve` | DELETE | Remove approval |
| `/api/content` | GET | All completed jobs (content library) |
| `/api/clients` | GET | List all clients |
| `/api/clients` | POST | Create client |
| `/api/clients/{id}` | PATCH | Update client fields |
| `/api/clients/{id}` | DELETE | Soft-delete client |
| `/api/discover-cities` | POST | Find nearby cities (Haiku-powered) |
| `/api/portal/{token}` | GET | Client portal data (client info + jobs) |
| `/portal/{token}` | GET | Client portal page (public-facing) |

### SSE Event Types
```
type: "token" → { type, text }
type: "done"  → { type, job_id, client_name, workflow_title, workflow_id }
type: "error" → { type, message }
```

---

## Workflow Input Schemas

### `website-seo-audit`
```json
{ "domain": "allthingzelectric.com", "service": "electrician", "location": "Chandler, AZ", "notes": "optional" }
```

### `prospect-audit`
```json
{ "domain": "steadfastplumbingaz.com", "service": "plumber", "location": "Gilbert, AZ",
  "monthly_revenue": "$45,000", "avg_job_value": "$450", "notes": "optional sales context" }
```

### `keyword-gap`
```json
{ "domain": "allthingzelectric.com", "service": "electrician", "location": "Chandler, AZ",
  "competitor_domains": "competitor1.com, competitor2.com", "notes": "optional" }
```

### `home-service-content`
```json
{ "business_type": "electrician", "location": "Chandler, AZ", "keyword": "panel upgrade", "service_focus": "residential" }
```

### `seo-blog-post`
```json
{ "business_type": "electrician", "location": "Chandler, AZ", "keyword": "how much does it cost to rewire a house",
  "audience": "homeowners", "tone": "conversational", "internal_links": "optional", "notes": "optional" }
```

### `service-page`
```json
{ "business_type": "electrician", "service": "panel upgrade", "location": "Chandler, AZ",
  "differentiators": "same-day service, master electrician", "price_range": "$1,200–$3,500", "notes": "optional" }
```

### `location-page`
```json
{ "business_type": "plumber", "primary_service": "plumbing repair", "target_location": "Mesa, AZ",
  "home_base": "Chandler, AZ", "local_details": "optional local context", "services_list": "optional", "notes": "optional" }
```

### `gbp-posts`
```json
{ "business_type": "electrician", "location": "Chandler, AZ", "post_count": "8",
  "services": "panel upgrade, EV charger", "promos": "10% off panel upgrades", "notes": "optional" }
```

### `monthly-report`
```json
{ "domain": "allthingzelectric.com", "service": "electrician", "location": "Chandler, AZ",
  "report_month": "February 2026", "notes": "optional" }
```

---

## DataForSEO Integration

**Auth:** Basic auth (`DATAFORSEO_LOGIN:DATAFORSEO_PASSWORD`, base64)
**Pricing:** ~$0.002/call live SERP, ~$0.0006 standard queue
**Client:** `utils/dataforseo.py`

### Implemented Functions
| Function | Endpoint | Used In |
|----------|----------|---------|
| `get_local_pack()` | `serp/google/maps/live/advanced` | website-seo-audit, prospect-audit, keyword-gap |
| `get_organic_serp()` | `serp/google/organic/live/advanced` | website-seo-audit, prospect-audit, keyword-gap |
| `research_competitors()` | Maps + Organic in parallel | Both audits, keyword-gap |
| `get_keyword_search_volumes()` | `keywords_data/google_ads/search_volume/live` | prospect-audit, keyword-gap |
| `get_domain_ranked_keywords()` | `dataforseo_labs/google/ranked_keywords/live` | website-seo-audit, keyword-gap |
| `get_bulk_keyword_difficulty()` | `dataforseo_labs/google/bulk_keyword_difficulty/live` | prospect-audit |
| `get_competitor_gmb_profiles()` | `business_data/google/my_business_search/live` | prospect-audit |
| `build_service_keyword_seeds()` | (utility) | prospect-audit, keyword-gap |
| Format helpers | `format_keyword_volumes()`, `format_domain_ranked_keywords()`, `format_keyword_difficulty()`, `format_competitor_gmb_profiles()`, `format_full_competitor_section()` | Various |

### Unused But Available
| Category | Endpoints | Use Case |
|----------|----------|----------|
| On-Page | `task_post`, `summary`, `pages` | Technical audit (async, 2-10 min) |
| Business Data | `google/reviews` | Review intelligence |
| Backlinks | `summary`, `referring_domains`, `competitors` | Link profile audit |
| Trends | `google_trends/explore`, `subregion_interests` | Seasonality report |
| Content Analysis | `search/live`, `rating/live` | Brand monitoring |

---

## Search Atlas MCP

Configured in Claude Code global config. Key: `SEARCHATLAS_API_KEY`.

### Approved Tools
| Namespace | Capabilities |
|-----------|-------------|
| `Site_Explorer_Organic_Tool` | Organic keywords, pages, competitors |
| `Site_Explorer_Backlinks_Tool` | Referring domains, backlinks |
| `Site_Explorer_Analysis_Tool` | Position distribution |
| `Site_Explorer_Holistic_Audit_Tool` | SEO pillar scores |
| `Site_Explorer_Keyword_Research_Tool` | Keyword research |
| `local_seo` | Grids, Business, Data, Analytics |
| `gbp` | Locations (read), Reviews, Stats, Tasks |
| `llm_visibility` | Visibility Analysis, Sentiment |

### Off-Limits (never use)
`content_genius`, `digital_pr`, `linklab`, `otto_ppc`, `press_release`, `OTTO_SEO_Deployment`, `OTTO_Wildfire`, `gbp_posts_automation`, `gbp_posts_publication`, `Content_Publication_Tools`

---

## Frontend Views

| View | Description |
|------|-------------|
| Dashboard | KPIs, live task queue, client roster |
| AI Skills | 8 workflow cards organized by category (SEO, Content, Business, Dev) |
| Clients | Client list with add/edit, active/inactive toggle |
| Agent Tasks | Job history with status, client links |
| Content | Content Library — grouped by client, searchable, filterable |
| Reports | Report cards (placeholder) |
| Activity Log | Terminal-style log stream |
| Client Hub | Per-client activity view (click any client name) |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key (Opus 4.6) |
| `SEARCHATLAS_API_KEY` | Yes | Search Atlas MCP API key |
| `DATAFORSEO_LOGIN` | Yes | DataForSEO account email |
| `DATAFORSEO_PASSWORD` | Yes | DataForSEO account password |
| `DATABASE_PATH` | No | SQLite path (default: `./data/jobs.db`) |

---

## Known Limitations

| Issue | Impact | Planned Fix |
|-------|--------|-------------|
| US-only location parsing | International clients get wrong format | DFS appendix/locations API |
| No test coverage | Risky deploys | Add pytest for keyword gap, docx gen |
| No request logging | Hard to debug production issues | Structured logging |
