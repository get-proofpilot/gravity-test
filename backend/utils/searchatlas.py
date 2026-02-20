"""
Search Atlas MCP Client
Async HTTP helper for calling the Search Atlas MCP endpoint from the backend.
API key must be set via SEARCHATLAS_API_KEY env var.

Approved tool namespaces (per CLAUDE.md):
  site_explorer, otto (analysis only), local_seo, gbp (read),
  llm_visibility, rb_report, website_studio, indexer, BrandVaultTools

Never call: content_genius, digital_pr, linklab, otto_ppc, press_release,
            cloud_stack, OTTO_SEO_Deployment, OTTO_Wildfire, gbp_posts_automation,
            gbp_locations_deployment, Content_Publication_Tools
"""

from __future__ import annotations

import os
import httpx

SA_MCP_URL = "https://mcp.searchatlas.com/api/v1/mcp"


def _api_key() -> str:
    key = os.environ.get("SEARCHATLAS_API_KEY", "")
    if not key:
        raise ValueError("SEARCHATLAS_API_KEY env var is not set")
    return key


async def sa_call(tool: str, op: str, params: dict | None = None) -> str:
    """
    Call a Search Atlas MCP tool operation.
    Returns the raw text response from the tool (already formatted as markdown).
    Raises ValueError on MCP-level errors.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": {
                "op": op,
                **({"params": params} if params else {}),
            },
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            SA_MCP_URL,
            headers={
                "X-API-KEY": _api_key(),
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()

    data = resp.json()

    if "error" in data:
        raise ValueError(f"Search Atlas MCP error [{tool}.{op}]: {data['error'].get('message', data['error'])}")

    content = data.get("result", {}).get("content", [])
    if content and isinstance(content[0], dict):
        return content[0].get("text", "")

    return str(data.get("result", ""))
