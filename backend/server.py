"""
ProofPilot Agency Hub — API Backend
FastAPI + SSE streaming → Claude API
Deploy on Railway: set root directory to /backend, add ANTHROPIC_API_KEY env var
"""

import os
import json
import uuid
import asyncio
import time
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional

from workflows.home_service_content import run_home_service_content
from workflows.website_seo_audit import run_website_seo_audit
from workflows.prospect_audit import run_prospect_audit
from workflows.keyword_gap import run_keyword_gap
from workflows.seo_blog_post import run_seo_blog_post
from workflows.service_page import run_service_page
from workflows.location_page import run_location_page
from workflows.programmatic_content import run_programmatic_content
from workflows.gbp_posts import run_gbp_posts
from workflows.monthly_report import run_monthly_report
from utils.docx_generator import generate_docx, TEMP_DIR
from utils.db import (
    init_db, save_job, update_docx_path, get_job as db_get_job, get_all_jobs,
    create_client, get_client as db_get_client, get_all_clients,
    update_client, delete_client, approve_job, unapprove_job,
    get_client_by_token, get_jobs_by_client,
)
from utils.dataforseo import (
    get_domain_rank_overview, build_location_name,
)
from utils.searchatlas import sa_call
from utils.localfalcon import (
    list_scan_reports, get_scan_report, run_scan,
    list_campaign_reports, get_campaign_report,
    create_campaign, run_campaign, pause_campaign, resume_campaign, reactivate_campaign,
    list_trend_reports, get_trend_report,
    get_competitor_reports, get_competitor_report,
    list_guard_reports, get_guard_report,
    add_to_guard, pause_guard, resume_guard, remove_guard,
    list_keyword_reports, get_keyword_report,
    list_locations, list_location_reports, get_location_report,
    list_reviews_reports, get_reviews_report,
    get_gbp_locations, search_business, save_business_location,
    list_auto_scans, get_account_info,
    search_knowledge_base, get_knowledge_base_article,
    extract_grid_data, extract_trend_data, extract_competitor_data,
)

# ── App setup ─────────────────────────────────────────────
app = FastAPI(title="ProofPilot Agency Hub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Initialise SQLite on startup ───────────────────────────
init_db()


def cleanup_temp_docs(max_age_days: int = 7) -> int:
    """Delete .docx files in temp_docs/ older than max_age_days. Returns count removed."""
    if not TEMP_DIR.exists():
        return 0
    cutoff = time.time() - (max_age_days * 86400)
    removed = 0
    for f in TEMP_DIR.glob("*.docx"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            pass
    return removed


@app.on_event("startup")
async def startup_cleanup():
    removed = await asyncio.to_thread(cleanup_temp_docs, 7)
    if removed:
        print(f"[cleanup] Removed {removed} temp_docs file(s) older than 7 days")

WORKFLOW_TITLES = {
    "home-service-content":   "Home Service SEO Content",
    "seo-blog-generator":     "SEO Blog Generator",
    "seo-blog-post":          "SEO Blog Post",
    "service-page":           "Service Page",
    "location-page":          "Location Page",
    "website-seo-audit":      "Website & SEO Audit",
    "prospect-audit":         "Prospect SEO Market Analysis",
    "keyword-gap":            "Keyword Gap Analysis",
    "proposals":              "Client Proposals",
    "seo-strategy-sheet":     "SEO Strategy Spreadsheet",
    "content-strategy-sheet": "Content Strategy Spreadsheet",
    "brand-styling":          "Brand Styling",
    "pnl-statement":          "P&L Statement",
    "property-mgmt-strategy": "Property Mgmt Strategy",
    "frontend-design":        "Frontend Interface Builder",
    "lovable-prompting":      "Lovable App Builder",
    "programmatic-content":   "Programmatic Content Agent",
    "gbp-posts":              "GBP Posts",
    "monthly-report":         "Monthly Client Report",
}


# ── Request / response schemas ─────────────────────────────
class WorkflowRequest(BaseModel):
    workflow_id: str
    client_id: int
    client_name: str
    inputs: dict
    strategy_context: Optional[str] = ""


class DiscoverCitiesRequest(BaseModel):
    city: str
    radius: int = 15


class ClientCreate(BaseModel):
    name: str
    domain: str = ""
    service: str = ""
    location: str = ""
    plan: str = "Starter"
    monthly_revenue: str = ""
    avg_job_value: str = ""
    notes: str = ""
    strategy_context: str = ""


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    service: Optional[str] = None
    location: Optional[str] = None
    plan: Optional[str] = None
    monthly_revenue: Optional[str] = None
    avg_job_value: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    strategy_context: Optional[str] = None


# ── Client routes ──────────────────────────────────────────

@app.get("/api/clients")
async def list_clients():
    """Return all active/inactive clients (excludes soft-deleted)."""
    clients = await asyncio.to_thread(get_all_clients)
    return {"clients": clients}


@app.post("/api/clients", status_code=201)
async def add_client(body: ClientCreate):
    """Create a new client and return the full row."""
    client = await asyncio.to_thread(create_client, body.model_dump())
    return client


@app.get("/api/clients/{client_id}")
async def get_client_detail(client_id: int):
    client = await asyncio.to_thread(db_get_client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@app.patch("/api/clients/{client_id}")
async def patch_client(client_id: int, body: ClientUpdate):
    """Partial update — only supplied non-null fields are written."""
    updated = await asyncio.to_thread(
        update_client, client_id, body.model_dump(exclude_none=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Client not found")
    return updated


@app.delete("/api/clients/{client_id}", status_code=204)
async def remove_client(client_id: int):
    """Soft-delete: marks status='deleted'."""
    ok = await asyncio.to_thread(delete_client, client_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Client not found")


# ── Job approval routes ────────────────────────────────────

@app.post("/api/jobs/{job_id}/approve")
async def approve_content(job_id: str):
    ok = await asyncio.to_thread(approve_job, job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"approved": True}


@app.delete("/api/jobs/{job_id}/approve")
async def unapprove_content(job_id: str):
    ok = await asyncio.to_thread(unapprove_job, job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"approved": False}


# ── Routes ────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "ProofPilot Agency Hub API"}


@app.post("/api/discover-cities")
async def discover_cities(req: DiscoverCitiesRequest):
    """Use Claude Haiku to find nearby cities for programmatic content."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    city_name = req.city.split(",")[0].strip()
    client = anthropic.AsyncAnthropic(api_key=api_key)

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": (
                f"List all real, incorporated cities and towns within approximately "
                f"{req.radius} miles of {req.city}. Do NOT include {city_name} itself. "
                f"Format each as 'City, ST' (2-letter state code). One per line. "
                f"No numbering, no bullets, no other text. Just the city list. "
                f"Maximum 50 cities. If fewer than 50 exist within that radius, list all of them."
            ),
        }],
    )

    import re
    text = response.content[0].text.strip()
    cities = []
    for line in text.split("\n"):
        line = line.strip().lstrip("- ").lstrip("• ").lstrip("* ")
        line = re.sub(r'^\d+[\.\)]\s*', '', line).strip()
        if line and "," in line:
            cities.append(line)

    return {"cities": cities[:50]}


@app.post("/api/run-workflow")
async def run_workflow(req: WorkflowRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    if req.workflow_id not in WORKFLOW_TITLES:
        raise HTTPException(status_code=400, detail=f"Unknown workflow: {req.workflow_id}")

    job_id = str(uuid.uuid4())[:8]
    client = anthropic.AsyncAnthropic(api_key=api_key)

    async def event_stream():
        full_content: list[str] = []

        try:
            # ── Route to the correct workflow ──
            if req.workflow_id == "home-service-content":
                generator = run_home_service_content(
                    client=client,
                    inputs=req.inputs,
                    strategy_context=req.strategy_context or "",
                    client_name=req.client_name,
                )
            elif req.workflow_id == "website-seo-audit":
                sa_key = os.environ.get("SEARCHATLAS_API_KEY")
                if not sa_key:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'SEARCHATLAS_API_KEY is not configured on the server.'})}\n\n"
                    return
                generator = run_website_seo_audit(
                    client=client,
                    inputs=req.inputs,
                    strategy_context=req.strategy_context or "",
                    client_name=req.client_name,
                )
            elif req.workflow_id == "prospect-audit":
                sa_key = os.environ.get("SEARCHATLAS_API_KEY")
                if not sa_key:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'SEARCHATLAS_API_KEY is not configured on the server.'})}\n\n"
                    return
                generator = run_prospect_audit(
                    client=client,
                    inputs=req.inputs,
                    strategy_context=req.strategy_context or "",
                    client_name=req.client_name,
                )
            elif req.workflow_id == "keyword-gap":
                generator = run_keyword_gap(
                    client=client,
                    inputs=req.inputs,
                    strategy_context=req.strategy_context or "",
                    client_name=req.client_name,
                )
            elif req.workflow_id == "seo-blog-post":
                generator = run_seo_blog_post(
                    client=client,
                    inputs=req.inputs,
                    strategy_context=req.strategy_context or "",
                    client_name=req.client_name,
                )
            elif req.workflow_id == "service-page":
                generator = run_service_page(
                    client=client,
                    inputs=req.inputs,
                    strategy_context=req.strategy_context or "",
                    client_name=req.client_name,
                )
            elif req.workflow_id == "location-page":
                generator = run_location_page(
                    client=client,
                    inputs=req.inputs,
                    strategy_context=req.strategy_context or "",
                    client_name=req.client_name,
                )
            elif req.workflow_id == "programmatic-content":
                generator = run_programmatic_content(
                    client=client,
                    inputs=req.inputs,
                    strategy_context=req.strategy_context or "",
                    client_name=req.client_name,
                )
            elif req.workflow_id == "gbp-posts":
                generator = run_gbp_posts(
                    client=client,
                    inputs=req.inputs,
                    strategy_context=req.strategy_context or "",
                    client_name=req.client_name,
                )
            elif req.workflow_id == "monthly-report":
                generator = run_monthly_report(
                    client=client,
                    inputs=req.inputs,
                    strategy_context=req.strategy_context or "",
                    client_name=req.client_name,
                    client_id=req.client_id,
                )
            else:
                msg = f'Workflow "{req.workflow_id}" is not yet wired up.'
                yield f"data: {json.dumps({'type': 'error', 'message': msg})}\n\n"
                return

            # ── Stream tokens to the browser ──
            async for token in generator:
                full_content.append(token)
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

            # ── Stream complete — persist job + generate .docx ──
            content_str = "".join(full_content)
            job_data = {
                "content": content_str,
                "client_name": req.client_name,
                "workflow_title": WORKFLOW_TITLES[req.workflow_id],
                "workflow_id": req.workflow_id,
                "inputs": req.inputs,
                "client_id": req.client_id,
            }

            # Persist to SQLite and generate docx (both run off the event loop)
            await asyncio.to_thread(save_job, job_id, job_data)
            docx_path = await asyncio.to_thread(generate_docx, job_id, job_data)
            await asyncio.to_thread(update_docx_path, job_id, str(docx_path))

            yield f"data: {json.dumps({'type': 'done', 'job_id': job_id, 'client_name': req.client_name, 'workflow_title': WORKFLOW_TITLES[req.workflow_id], 'workflow_id': req.workflow_id})}\n\n"

        except anthropic.AuthenticationError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid Anthropic API key.'})}\n\n"
        except anthropic.RateLimitError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Rate limited — please wait a moment and try again.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # prevents nginx from buffering SSE
            "Connection": "keep-alive",
        },
    )


@app.get("/api/download/{job_id}")
def download_docx(job_id: str):
    job = db_get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.get("docx_path"):
        raise HTTPException(status_code=404, detail="Document not ready yet")

    docx_path = Path(job["docx_path"])
    if not docx_path.exists():
        raise HTTPException(status_code=404, detail="Document file missing — server may have restarted")

    client_slug = job["client_name"].replace(" ", "_")
    wf_slug = job["workflow_id"].replace("-", "_")
    filename = f"ProofPilot_{client_slug}_{wf_slug}_{job_id}.docx"

    return FileResponse(
        path=docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@app.get("/api/content")
def list_content():
    """Return all completed jobs as content library items."""
    all_jobs = get_all_jobs()
    items = []
    for job in all_jobs:
        content_str = job.get("content", "")
        if not content_str:
            continue
        items.append({
            "job_id": job["job_id"],
            "client_name": job.get("client_name", ""),
            "workflow_title": job.get("workflow_title", ""),
            "workflow_id": job.get("workflow_id", ""),
            "has_docx": bool(job.get("docx_path")),
            "content_preview": content_str[:200] + "..." if len(content_str) > 200 else content_str,
            "approved": bool(job.get("approved", 0)),
            "approved_at": job.get("approved_at"),
        })
    return {"items": items}  # already sorted newest-first by get_all_jobs()


@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: str):
    job = db_get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    content = job.get("content", "")
    return {
        "job_id": job_id,
        "client_name": job["client_name"],
        "workflow_title": job["workflow_title"],
        "has_docx": bool(job.get("docx_path")),
        "content_preview": content[:300] + "..." if len(content) > 300 else content,
        "approved": bool(job.get("approved", 0)),
        "approved_at": job.get("approved_at"),
    }


# ── Local Falcon API ──────────────────────────────────────────────

@app.get("/api/localfalcon/status")
async def localfalcon_status():
    """Check if Local Falcon API key is configured."""
    key = os.environ.get("LOCALFALCON_API_KEY", "")
    return {"configured": bool(key)}


# ── Scans ──

@app.get("/api/localfalcon/scans")
async def localfalcon_scans():
    """List all Local Falcon scan reports."""
    try:
        scans = await list_scan_reports(limit=100)
        return {"scans": scans}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/localfalcon/scans/{report_key}")
async def localfalcon_scan_detail(report_key: str):
    """Get a single scan report with full grid data for heatmap rendering."""
    try:
        report = await get_scan_report(report_key)
        grid = extract_grid_data(report)
        return {"report": report, "grid": grid}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Campaigns ──

@app.get("/api/localfalcon/campaigns")
async def localfalcon_campaigns():
    """List Local Falcon campaign (recurring scan) reports."""
    try:
        campaigns = await list_campaign_reports(limit=50)
        return {"campaigns": campaigns}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/localfalcon/campaigns/{report_key}")
async def localfalcon_campaign_detail(report_key: str):
    """Get a single campaign report with scan history."""
    try:
        report = await get_campaign_report(report_key)
        return report
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Trends ──

@app.get("/api/localfalcon/trends")
async def localfalcon_trends():
    """List trend reports showing rank changes over time."""
    try:
        trends = await list_trend_reports(limit=50)
        return {"trends": trends}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/localfalcon/trends/{report_key}")
async def localfalcon_trend_detail(report_key: str):
    """Get a single trend report with historical data points."""
    try:
        report = await get_trend_report(report_key)
        trend_data = extract_trend_data(report)
        return {"report": report, "trend": trend_data}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Competitors ──

@app.get("/api/localfalcon/competitors")
async def localfalcon_competitors(
    place_id: str = "", keyword: str = "",
    start_date: str = "", end_date: str = "",
):
    """Get competitor rankings, optionally filtered."""
    try:
        competitors = await get_competitor_reports(
            place_id=place_id, keyword=keyword,
            start_date=start_date, end_date=end_date,
        )
        normalized = extract_competitor_data(competitors)
        return {"competitors": normalized, "raw": competitors}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/localfalcon/competitor/{report_key}")
async def localfalcon_competitor_detail(report_key: str):
    """Get detailed single competitor report."""
    try:
        report = await get_competitor_report(report_key)
        return report
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Guard (rank monitoring) ──

@app.get("/api/localfalcon/guards")
async def localfalcon_guards():
    """List guard reports (rank change monitoring alerts)."""
    try:
        guards = await list_guard_reports(limit=50)
        return {"guards": guards}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/localfalcon/guards/{place_id}")
async def localfalcon_guard_detail(place_id: str):
    """Get Guard report for a placeId (GBP monitoring + performance insights)."""
    try:
        report = await get_guard_report(place_id)
        return report
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Keywords ──

@app.get("/api/localfalcon/keywords")
async def localfalcon_keywords():
    """List keyword-level tracking reports."""
    try:
        keywords = await list_keyword_reports(limit=50)
        return {"keywords": keywords}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/localfalcon/keywords/{report_key}")
async def localfalcon_keyword_detail(report_key: str):
    """Get detailed keyword tracking report."""
    try:
        report = await get_keyword_report(report_key)
        return report
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Locations ──

@app.get("/api/localfalcon/locations")
async def localfalcon_locations():
    """List all tracked Local Falcon locations."""
    try:
        locations = await list_locations()
        return {"locations": locations}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/localfalcon/location-reports")
async def localfalcon_location_reports():
    """List per-location tracking reports."""
    try:
        reports = await list_location_reports(limit=50)
        return {"reports": reports}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/localfalcon/location-reports/{report_key}")
async def localfalcon_location_report_detail(report_key: str):
    """Get detailed location-level report."""
    try:
        report = await get_location_report(report_key)
        return report
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Reviews ──

@app.get("/api/localfalcon/reviews")
async def localfalcon_reviews():
    """List reviews analysis reports."""
    try:
        reviews = await list_reviews_reports(limit=50)
        return {"reviews": reviews}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/localfalcon/reviews/{report_key}")
async def localfalcon_review_detail(report_key: str):
    """Get detailed reviews analysis report."""
    try:
        report = await get_reviews_report(report_key)
        return report
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GBP Locations ──

@app.get("/api/localfalcon/gbp-locations")
async def localfalcon_gbp_locations(query: str = "", near: str = ""):
    """Search Google for business listings to find Place IDs."""
    if not query:
        return {"locations": [], "message": "Provide ?query= to search"}
    try:
        locations = await get_gbp_locations(query=query, near=near)
        return {"locations": locations}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Auto-scans ──

@app.get("/api/localfalcon/auto-scans")
async def localfalcon_auto_scans():
    """List configured automatic/scheduled scans."""
    try:
        auto_scans = await list_auto_scans(limit=50)
        return {"auto_scans": auto_scans}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Campaign management ──

@app.post("/api/localfalcon/campaigns/create")
async def localfalcon_create_campaign(req: Request):
    """Create a new campaign with scheduled recurring scans."""
    body = await req.json()
    try:
        result = await create_campaign(
            name=body["name"], place_id=body["placeId"],
            keyword=body["keyword"], grid_size=body["gridSize"],
            radius=body["radius"], measurement=body.get("measurement", "mi"),
            frequency=body["frequency"],
            start_date=body["startDate"], start_time=body["startTime"],
            ai_analysis=body.get("aiAnalysis", False),
            notify=body.get("notify", False),
            email_recipients=body.get("emailRecipients", ""),
        )
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/localfalcon/campaigns/{campaign_key}/run")
async def localfalcon_run_campaign(campaign_key: str):
    """Manually trigger a campaign run."""
    try:
        return await run_campaign(campaign_key)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/localfalcon/campaigns/{campaign_key}/pause")
async def localfalcon_pause_campaign(campaign_key: str):
    """Pause a campaign."""
    try:
        return await pause_campaign(campaign_key)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/localfalcon/campaigns/{campaign_key}/resume")
async def localfalcon_resume_campaign(campaign_key: str):
    """Resume a paused campaign."""
    try:
        return await resume_campaign(campaign_key)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/localfalcon/campaigns/{campaign_key}/reactivate")
async def localfalcon_reactivate_campaign(campaign_key: str):
    """Reactivate a campaign deactivated due to insufficient credits."""
    try:
        return await reactivate_campaign(campaign_key)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Run scan ──

@app.post("/api/localfalcon/scans/run")
async def localfalcon_run_scan(req: Request):
    """Run a new ranking scan. Costs credits — use with care."""
    body = await req.json()
    try:
        result = await run_scan(
            place_id=body["placeId"], keyword=body["keyword"],
            lat=body["lat"], lng=body["lng"],
            grid_size=body["gridSize"], radius=body["radius"],
            measurement=body.get("measurement", "mi"),
            platform=body.get("platform", "google"),
            ai_analysis=body.get("aiAnalysis", False),
        )
        return result
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Guard management ──

@app.post("/api/localfalcon/guards/add")
async def localfalcon_add_guard(req: Request):
    """Add location(s) to Falcon Guard protection."""
    body = await req.json()
    try:
        return await add_to_guard(body["placeId"])
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/localfalcon/guards/pause")
async def localfalcon_pause_guard(req: Request):
    """Pause Guard monitoring."""
    body = await req.json()
    try:
        return await pause_guard(
            place_id=body.get("placeId", ""),
            guard_key=body.get("guardKey", ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/localfalcon/guards/resume")
async def localfalcon_resume_guard(req: Request):
    """Resume Guard monitoring."""
    body = await req.json()
    try:
        return await resume_guard(
            place_id=body.get("placeId", ""),
            guard_key=body.get("guardKey", ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/localfalcon/guards/remove")
async def localfalcon_remove_guard(req: Request):
    """Remove Guard protection."""
    body = await req.json()
    try:
        return await remove_guard(
            place_id=body.get("placeId", ""),
            guard_key=body.get("guardKey", ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Business search ──

@app.get("/api/localfalcon/search-business")
async def localfalcon_search_business(term: str, platform: str = "google", proximity: str = ""):
    """Search for businesses on Google or Apple Maps."""
    try:
        results = await search_business(term=term, platform=platform, proximity=proximity)
        return {"results": results}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/localfalcon/save-location")
async def localfalcon_save_location(req: Request):
    """Save a business location to the account."""
    body = await req.json()
    try:
        return await save_business_location(
            platform=body.get("platform", "google"),
            place_id=body["placeId"],
            name=body.get("name", ""),
            lat=body.get("lat", ""),
            lng=body.get("lng", ""),
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Knowledge base ──

@app.get("/api/localfalcon/knowledge-base")
async def localfalcon_kb_search(q: str = "", limit: str = "10"):
    """Search Local Falcon knowledge base articles."""
    try:
        articles = await search_knowledge_base(query=q, limit=limit)
        return {"articles": articles}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/localfalcon/knowledge-base/{article_id}")
async def localfalcon_kb_article(article_id: str):
    """Get a knowledge base article."""
    try:
        article = await get_knowledge_base_article(article_id)
        return article
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Account ──

@app.get("/api/localfalcon/account")
async def localfalcon_account():
    """Get Local Falcon account info (credits, subscription)."""
    try:
        info = await get_account_info()
        return info
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Serve frontend ────────────────────────────────────────────────
# Explicit routes instead of StaticFiles mount — prevents the mount from
# intercepting /api/* routes (known FastAPI/Starlette issue with root mounts).
# ── Portal API ─────────────────────────────────────────────

@app.get("/api/portal/{token}")
async def portal_data(token: str):
    """Return client info + all their jobs for the client portal."""
    client_info = await asyncio.to_thread(get_client_by_token, token)
    if not client_info:
        raise HTTPException(status_code=404, detail="Portal not found")

    jobs = await asyncio.to_thread(get_jobs_by_client, client_info["client_id"])

    items = []
    for job in jobs:
        content_str = job.get("content", "")
        if not content_str:
            continue
        items.append({
            "job_id": job["job_id"],
            "workflow_title": job.get("workflow_title", ""),
            "workflow_id": job.get("workflow_id", ""),
            "has_docx": bool(job.get("docx_path")),
            "approved": bool(job.get("approved", 0)),
            "created_at": job.get("created_at", "")[:10],
            "preview": content_str[:300] + "..." if len(content_str) > 300 else content_str,
        })

    return {
        "client": {
            "name": client_info["name"],
            "domain": client_info.get("domain", ""),
            "service": client_info.get("service", ""),
            "location": client_info.get("location", ""),
            "plan": client_info.get("plan", ""),
            "initials": client_info.get("initials", ""),
            "color": client_info.get("color", "#0051FF"),
        },
        "items": items,
    }


@app.get("/api/portal/{token}/metrics")
async def portal_metrics(token: str):
    """Pull live SEO metrics for the portal dashboard. Async — may take a few seconds."""
    client_info = await asyncio.to_thread(get_client_by_token, token)
    if not client_info:
        raise HTTPException(status_code=404, detail="Portal not found")

    domain = client_info.get("domain", "")
    location = client_info.get("location", "")

    if not domain:
        return {"metrics": None, "reason": "no_domain"}

    metrics = {}

    # Pull DFS domain overview + SA pillar scores in parallel
    async def safe_dfs_overview():
        try:
            loc = build_location_name(location) if location else "United States"
            return await get_domain_rank_overview(domain, loc)
        except Exception:
            return None

    async def safe_sa_pillars():
        try:
            result = await sa_call(
                "Site_Explorer_Holistic_Audit_Tool",
                "get_holistic_seo_pillar_scores",
                {"domain": domain},
            )
            return result
        except Exception:
            return None

    dfs_result, sa_pillars = await asyncio.gather(
        safe_dfs_overview(), safe_sa_pillars(),
        return_exceptions=True,
    )

    if isinstance(dfs_result, dict) and dfs_result:
        metrics["keywords"] = dfs_result.get("keywords", 0)
        metrics["traffic"] = round(dfs_result.get("etv", 0))
        metrics["traffic_value"] = round(dfs_result.get("etv_cost", 0))

    if isinstance(sa_pillars, str) and sa_pillars and "unavailable" not in sa_pillars.lower():
        metrics["pillar_scores_raw"] = sa_pillars

    return {"metrics": metrics if metrics else None}


@app.get("/api/portal/{token}/heatmap")
async def portal_heatmap(token: str):
    """Pull Local Falcon heatmap + competitor data for a portal client."""
    client_info = await asyncio.to_thread(get_client_by_token, token)
    if not client_info:
        raise HTTPException(status_code=404, detail="Portal not found")

    if not os.environ.get("LOCALFALCON_API_KEY"):
        return {"heatmaps": [], "competitors": [], "reason": "localfalcon_not_configured"}

    try:
        scans = await list_scan_reports(limit=50)
        if not scans:
            return {"heatmaps": [], "competitors": []}

        # Match scans to this client by domain or business name
        domain = (client_info.get("domain") or "").lower()
        name = (client_info.get("name") or "").lower()

        client_scans = []
        for scan in scans:
            scan_str = json.dumps(scan).lower()
            if (domain and domain in scan_str) or (name and name in scan_str):
                client_scans.append(scan)

        # If no match by domain/name, return all (small accounts likely have one business)
        if not client_scans:
            client_scans = scans[:5]

        # Get detailed grid data for each scan
        heatmaps = []
        for scan in client_scans[:5]:
            report_key = (
                scan.get("report_key")
                or scan.get("reportKey")
                or scan.get("key")
                or scan.get("id")
                or ""
            )
            if not report_key:
                continue
            try:
                report = await get_scan_report(str(report_key))
                grid = extract_grid_data(report)
                if grid.get("grid"):
                    heatmaps.append(grid)
            except Exception:
                continue

        # Get competitor data
        competitors = []
        try:
            raw_competitors = await get_competitor_reports()
            competitors = extract_competitor_data(raw_competitors)
        except Exception:
            pass

        return {"heatmaps": heatmaps, "competitors": competitors}

    except Exception:
        return {"heatmaps": [], "competitors": [], "reason": "api_error"}


# ── Static files ──────────────────────────────────────────
static_dir = Path(__file__).parent / "static"

@app.get("/portal/{token}")
async def serve_portal(token: str):
    """Serve the client portal page."""
    f = static_dir / "portal.html"
    if f.exists():
        return FileResponse(f)
    raise HTTPException(status_code=404, detail="Portal page not found")


@app.get("/")
async def serve_index():
    f = static_dir / "index.html"
    if f.exists():
        return FileResponse(f)
    return {"status": "frontend not found"}

@app.get("/script.js")
async def serve_script():
    return FileResponse(static_dir / "script.js", media_type="application/javascript")

@app.get("/style.css")
async def serve_style():
    return FileResponse(static_dir / "style.css", media_type="text/css")

@app.get("/{spa_path:path}")
async def serve_spa(spa_path: str):
    """Catch-all for SPA client-side routing. API routes are matched first."""
    return FileResponse(static_dir / "index.html")
