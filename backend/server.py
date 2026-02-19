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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional

from workflows.home_service_content import run_home_service_content
from utils.docx_generator import generate_docx

# ── App setup ─────────────────────────────────────────────
app = FastAPI(title="ProofPilot Agency Hub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory job store (ephemeral — fine for v1) ─────────
jobs: dict[str, dict] = {}

WORKFLOW_TITLES = {
    "home-service-content":   "Home Service SEO Content",
    "seo-blog-generator":     "SEO Blog Generator",
    "website-seo-audit":      "Website & SEO Audit",
    "proposals":              "Client Proposals",
    "seo-strategy-sheet":     "SEO Strategy Spreadsheet",
    "content-strategy-sheet": "Content Strategy Spreadsheet",
    "brand-styling":          "Brand Styling",
    "pnl-statement":          "P&L Statement",
    "property-mgmt-strategy": "Property Mgmt Strategy",
    "frontend-design":        "Frontend Interface Builder",
    "lovable-prompting":      "Lovable App Builder",
}


# ── Request schema ────────────────────────────────────────
class WorkflowRequest(BaseModel):
    workflow_id: str
    client_id: int
    client_name: str
    inputs: dict
    strategy_context: Optional[str] = ""


# ── Routes ────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "service": "ProofPilot Agency Hub API"}


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
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Workflow \"{req.workflow_id}\" is not yet wired up.'})}\n\n"
                return

            # ── Stream tokens to the browser ──
            async for token in generator:
                full_content.append(token)
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

            # ── Stream complete — store job + generate .docx ──
            content_str = "".join(full_content)
            jobs[job_id] = {
                "content": content_str,
                "client_name": req.client_name,
                "workflow_title": WORKFLOW_TITLES[req.workflow_id],
                "workflow_id": req.workflow_id,
                "inputs": req.inputs,
            }

            # Run blocking docx generation off the event loop
            docx_path = await asyncio.to_thread(generate_docx, job_id, jobs[job_id])
            jobs[job_id]["docx_path"] = str(docx_path)

            yield f"data: {json.dumps({'type': 'done', 'job_id': job_id})}\n\n"

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
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    if "docx_path" not in jobs[job_id]:
        raise HTTPException(status_code=404, detail="Document not ready yet")

    docx_path = Path(jobs[job_id]["docx_path"])
    if not docx_path.exists():
        raise HTTPException(status_code=404, detail="Document file missing — server may have restarted")

    client_slug = jobs[job_id]["client_name"].replace(" ", "_")
    wf_slug = jobs[job_id]["workflow_id"].replace("-", "_")
    filename = f"ProofPilot_{client_slug}_{wf_slug}_{job_id}.docx"

    return FileResponse(
        path=docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "client_name": job["client_name"],
        "workflow_title": job["workflow_title"],
        "has_docx": "docx_path" in job,
        "content_preview": job["content"][:300] + "..." if len(job["content"]) > 300 else job["content"],
    }
