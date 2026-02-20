"""
ProofPilot Agency Hub — API Backend
FastAPI + SSE streaming → Claude API
Deploy on Railway: set root directory to /backend, add ANTHROPIC_API_KEY env var
"""

import os
import json
import uuid
import asyncio
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
from utils.docx_generator import generate_docx
from utils.db import (
    init_db, save_job, update_docx_path, get_job as db_get_job, get_all_jobs,
    create_client, get_client as db_get_client, get_all_clients,
    update_client, delete_client, approve_job, unapprove_job,
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


# ── Serve frontend ────────────────────────────────────────────────
# Explicit routes instead of StaticFiles mount — prevents the mount from
# intercepting /api/* routes (known FastAPI/Starlette issue with root mounts).
static_dir = Path(__file__).parent / "static"

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
