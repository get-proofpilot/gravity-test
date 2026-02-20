# ProofPilot Agency Hub — Feature Roadmap

**Live:** `https://proofpilot-agents.up.railway.app`
**Stack:** Python 3.11 + FastAPI + SSE | Claude Opus 4.6 | Railway | Pure JS frontend

Phases are ordered by dependency and business value. Complete a phase before starting the next unless items are explicitly marked independent.

---

## Phase 1 — Core Platform ✅ COMPLETE

The foundational platform is live and production-ready.

- [x] 7 active AI workflows (SEO Audit, Prospect Audit, Keyword Gap, Blog Post, Service Page, Location Page, Home Service Content)
- [x] Live SSE streaming terminal — tokens stream in real time from Claude
- [x] Branded `.docx` export — every job generates a downloadable Word doc
- [x] SQLite job persistence — jobs survive server restarts via Railway Volume
- [x] Content Library — all completed jobs organized by client
- [x] Per-client hub — activity view per client with quick workflow launch
- [x] Workflow categorization with sample previews in the launch modal
- [x] DataForSEO integration — SERP, Maps, Labs, Keywords, GBP, Difficulty endpoints
- [x] Search Atlas integration — organic data, backlinks, holistic audit scores
- [x] Health check + crash-proof deployment (Dockerfile CMD, no Railway startCommand override)

---

## Phase 2 — Client Data Layer

**Why first:** Clients are currently hardcoded arrays in `script.js`. Every new client requires a code edit and re-deploy. This blocks everything downstream.

### 2.1 — Client CRUD API
- [ ] `POST /api/clients` — create client (name, domain, service, location, monthly_revenue, avg_job_value, notes, status)
- [ ] `GET /api/clients` — list all clients (replace hardcoded JS array)
- [ ] `PATCH /api/clients/{id}` — update client fields
- [ ] `DELETE /api/clients/{id}` — soft-delete (status = inactive)
- [ ] SQLite `clients` table with all fields + `created_at`, `updated_at`
- [ ] Frontend: "Add Client" modal in the Clients view
- [ ] Frontend: Edit client inline from client hub

### 2.2 — Strategy Context Persistence
- [ ] Save per-client strategy context in DB (currently typed fresh every workflow run)
- [ ] Auto-populate strategy context field when client is selected in workflow modal
- [ ] Edit strategy context from client hub → persists to DB

### 2.3 — Content Approval Status
- [ ] Add `approved`, `approved_at` columns to jobs table
- [ ] "Mark as Approved" toggle in Content Library card
- [ ] Approved content gets a visual badge (green checkmark)
- [ ] Filter Content Library by: All / Approved / Pending Review

### 2.4 — Input Validation & UX Polish
- [ ] Domain format validation before workflow launch (strip `https://`, `www.`, trailing slash)
- [ ] Required field error states in workflow modal
- [ ] TTL-based cleanup of `temp_docs/` — delete `.docx` files older than 30 days
- [ ] Regenerate missing `.docx` from stored content (if Railway restarted and wiped temp_docs)

---

## Phase 3 — Google Drive Publishing

**The content pipeline:** ProofPilot generates → agency reviews → approves → pushes to Drive → automation publishes to WordPress/Webflow/etc.

### Folder Structure (auto-created by ProofPilot)
```
ProofPilot Clients/               ← shared top-level folder
├── All Thingz Electric/
│   ├── Location Pages/
│   ├── Service Pages/
│   ├── Blog Posts/
│   ├── Home Service Content/
│   ├── SEO Audits/
│   ├── Prospect Analyses/
│   └── Keyword Gap Reports/
├── Steadfast Plumbing/
│   └── ...
└── [New Client]/
    └── ...
```

### Workflow → Drive Folder Mapping
| Workflow ID | Drive Folder |
|-------------|-------------|
| `location-page` | Location Pages |
| `service-page` | Service Pages |
| `seo-blog-post` | Blog Posts |
| `home-service-content` | Home Service Content |
| `website-seo-audit` | SEO Audits |
| `prospect-audit` | Prospect Analyses |
| `keyword-gap` | Keyword Gap Reports |

### Implementation

**Auth (Service Account — no user login required)**
- [ ] Create Google Cloud project + enable Drive API
- [ ] Create Service Account, download JSON key
- [ ] Share `ProofPilot Clients/` folder with service account email (Editor access)
- [ ] Set `GOOGLE_SERVICE_ACCOUNT_JSON` (base64-encoded) + `GOOGLE_DRIVE_ROOT_FOLDER_ID` in Railway env vars

**Backend**
- [ ] Add `google-api-python-client` + `google-auth` to `requirements.txt`
- [ ] Create `utils/google_drive.py`:
  - `get_or_create_folder(parent_id, name)` — idempotent folder creation
  - `upload_docx(client_name, workflow_id, job_id, docx_path)` → returns `(file_id, web_view_url)`
  - `regenerate_and_upload(job_id)` — rebuild `.docx` from stored content, then upload
- [ ] Add `drive_file_id`, `drive_url`, `approved`, `approved_at` columns to jobs table
- [ ] `POST /api/jobs/{job_id}/approve` — approve job + upload to Drive → returns `{ drive_url }`
- [ ] Handle missing `.docx` gracefully — regenerate from SQLite content before upload

**Frontend**
- [ ] "Approve & Push to Drive" button on each Content Library card (replaces plain "Approve" toggle)
- [ ] Loading state during Drive upload ("Pushing to Drive...")
- [ ] After push: show Google Drive icon + "Open in Drive" link on the card
- [ ] Green "Approved" badge on approved cards
- [ ] Content Library filter: All / Approved / Pending Review

**Future automation (out of scope for this phase — handled externally)**
- Google Drive → WordPress via Zapier/Make trigger on new file in folder
- Google Drive → Webflow CMS via same automation
- ProofPilot generates, agency approves, automation publishes — zero manual copy-paste

---

## Phase 4 — Advanced Workflows

New workflow types that expand what ProofPilot can deliver.

### 4.1 — On-Page Technical Audit
- [ ] `workflows/onpage_audit.py` — uses DataForSEO On-Page API (task-based, 2–10 min)
- [ ] Async task submission → poll pattern: submit crawl task, store `task_id`, poll until done
- [ ] Background task system in `server.py` (task status endpoint)
- [ ] Report: Core Web Vitals, crawl errors, missing meta, duplicate content, internal link health, page speed
- [ ] Requires: async task polling UI in frontend (progress bar with estimated time)

### 4.2 — Monthly Client Report
- [ ] `workflows/monthly_report.py` — aggregates job history + live rank data
- [ ] Pulls: all jobs created this month, current organic rankings vs. last month, keyword volume changes
- [ ] Claude synthesizes into executive summary + recommendations
- [ ] Output: branded `.docx` report card — suitable for client delivery

### 4.3 — GBP Audit Workflow
- [ ] `workflows/gbp_audit.py`
- [ ] Compare client GBP completeness vs. top 3 competitors
- [ ] Check: photos count, categories, attributes, Q&A, review response rate, post frequency
- [ ] Uses `get_competitor_gmb_profiles()` (already built in `utils/dataforseo.py`)
- [ ] Output: GBP Optimization Checklist with specific gaps + competitor benchmarks

### 4.4 — Review Intelligence
- [ ] `workflows/review_intelligence.py`
- [ ] Pull competitor reviews via DataForSEO Business Data API
- [ ] Claude performs sentiment analysis → identifies recurring themes, complaints, praise patterns
- [ ] Output: "What competitors' customers complain about" → client talking points + service differentiators

### 4.5 — Seasonality & Content Calendar
- [ ] `workflows/seasonality_report.py`
- [ ] Google Trends subregion data for the client's primary service keywords
- [ ] Maps seasonal demand peaks to content calendar
- [ ] Output: 12-month content calendar with recommended publish dates tied to search demand

---

## Phase 5 — Publishing & Distribution

Direct content publishing from ProofPilot to client websites.

### 5.1 — WordPress Direct Publish
- [ ] `POST /api/jobs/{job_id}/publish/wordpress` — push approved content to WordPress REST API
- [ ] Client configuration: store WP site URL + Application Password in clients table
- [ ] Content type routing: blog post → `wp/v2/posts`, service/location page → `wp/v2/pages`
- [ ] Set status to `draft` initially — agency reviews in WP before going live
- [ ] Return WP post URL, store in job record

### 5.2 — Webflow CMS Push
- [ ] Similar to WordPress but uses Webflow Data API
- [ ] Map ProofPilot workflow types to Webflow Collection IDs (configured per client)
- [ ] Push as draft CMS items

### 5.3 — Scheduled Automations
- [ ] Cron-triggered monthly report generation (first of each month, per active client)
- [ ] Configurable per client: which workflows to run automatically, on what schedule
- [ ] Notification system: email/Slack webhook when automated run completes
- [ ] Railway Cron service or background task queue (APScheduler)

### 5.4 — Bulk Content Generation
- [ ] Run the same workflow across multiple clients in sequence (overnight batch)
- [ ] Run location-page workflow for a list of 10 cities for one client
- [ ] Progress tracking, per-item status, bulk download as ZIP

---

## Phase 6 — Agency Intelligence & Scale

Analytics, client-facing access, and white-labeling.

### 6.1 — Performance Tracking
- [ ] GA4 integration: connect client GA4 properties, pull organic traffic metrics
- [ ] Track which ProofPilot-generated pages are ranking and driving traffic
- [ ] Rank change tracking: compare current DataForSEO rankings vs. baseline from first audit

### 6.2 — Cross-Client Dashboard
- [ ] Agency-level KPIs: total content pieces generated, total approved, total published
- [ ] Industry benchmarks by service type (average audit score, average keyword gap size)
- [ ] "Most active clients" and "clients needing attention" widgets

### 6.3 — Client-Facing Report Portal
- [ ] Read-only client login (separate from agency login)
- [ ] Clients can view their approved content, download reports, see what's in progress
- [ ] No workflow launch access — view only

### 6.4 — White-Label & Agency Settings
- [ ] Agency branding on `.docx` reports (upload logo, set agency name/colors)
- [ ] Custom subdomain support (`clients.youragency.com`)
- [ ] Per-agency configuration: which workflows are visible, default strategy contexts

---

## Tech Debt Backlog

Items that don't fit a phase but should be resolved as bandwidth allows.

| Issue | Priority | Notes |
|-------|----------|-------|
| Hardcoded CLIENTS in `script.js` | High | Resolved in Phase 2.1 |
| US-only location parsing | Medium | Add international format support via DFS Appendix API |
| No domain format validation | Medium | Resolved in Phase 2.4 |
| `temp_docs/` not cleaned up | Low | TTL cleanup in Phase 2.4 |
| No test coverage | Medium | At minimum: unit tests for keyword gap computation, docx generation |
| No request logging | Low | Add structured logging for all workflow runs |
| Missing `.env.example` file | Low | Create with all required env var keys documented |

---

## Google Drive Setup Guide (for Phase 3)

When ready to implement, here's what's needed from your side:

1. **Google Cloud Console** — create project, enable Drive API
2. **Service Account** — create, download JSON key file
3. **Share folder** — create `ProofPilot Clients/` in your Google Drive, share it with the service account email (it looks like `proofpilot@your-project.iam.gserviceaccount.com`)
4. **Railway env vars** to add:
   - `GOOGLE_SERVICE_ACCOUNT_JSON` — base64-encoded contents of the JSON key file
   - `GOOGLE_DRIVE_ROOT_FOLDER_ID` — the folder ID from the Drive URL of `ProofPilot Clients/`

Once those are in Railway, Phase 3 can be implemented in a single session.

