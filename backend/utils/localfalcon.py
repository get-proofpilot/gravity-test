"""
Local Falcon API Client — local rank tracking heat maps for ProofPilot.

Calls the Local Falcon MCP server endpoint to pull scan reports, grid data,
campaign history, and location information.

Required env var:
    LOCALFALCON_API_KEY    Your Local Falcon API key (manage at localfalcon.com/api/credentials)

MCP endpoint: https://mcp.localfalcon.com/mcp
Auth: API key passed as query parameter

Available tools:
    listLocalFalconScanReports         — all scan reports
    getLocalFalconReport               — single scan with grid data
    listAllLocalFalconLocations        — all tracked locations
    listLocalFalconCampaignReports     — recurring campaign data
    listLocalFalconTrendReports        — trend reports
    viewLocalFalconAccountInformation  — account/credits info
"""

import os
import json
import httpx
from typing import Optional

LF_MCP_URL = "https://mcp.localfalcon.com/mcp"


def _api_key() -> str:
    key = os.environ.get("LOCALFALCON_API_KEY", "")
    if not key:
        raise ValueError("LOCALFALCON_API_KEY env var is not set")
    return key


async def lf_call(tool_name: str, arguments: dict | None = None) -> dict | list | str:
    """
    Call a Local Falcon MCP tool.

    Sends JSON-RPC to the MCP endpoint with the API key as a query parameter.
    Returns the parsed result (dict/list/str depending on the tool).

    Raises ValueError on MCP-level errors or missing API key.
    """
    key = _api_key()

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {},
        },
    }

    url = f"{LF_MCP_URL}?local_falcon_api_key={key}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Try direct JSON-RPC call first
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )

        # Handle SSE response — parse last data event
        content_type = resp.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            return _parse_sse_response(resp.text)

        # If we get a 405 or need initialization, try with session
        if resp.status_code in (405, 400):
            return await _lf_call_with_session(key, tool_name, arguments or {})

        resp.raise_for_status()

    data = resp.json()

    if "error" in data:
        raise ValueError(
            f"Local Falcon MCP error [{tool_name}]: "
            f"{data['error'].get('message', data['error'])}"
        )

    return _extract_result(data)


async def _lf_call_with_session(
    api_key: str, tool_name: str, arguments: dict
) -> dict | list | str:
    """
    Full MCP session flow: initialize → call tool → return result.
    Used as fallback if direct JSON-RPC doesn't work.
    """
    url = f"{LF_MCP_URL}?local_falcon_api_key={api_key}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Initialize session
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "proofpilot-agent-hub", "version": "1.0.0"},
            },
        }

        init_resp = await client.post(url, json=init_payload, headers=headers)
        init_ct = init_resp.headers.get("content-type", "")

        session_id = init_resp.headers.get("mcp-session-id", "")

        # Step 2: Send initialized notification
        if session_id:
            notif_headers = {**headers, "Mcp-Session-Id": session_id}
            await client.post(
                url,
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                headers=notif_headers,
            )

        # Step 3: Call the tool
        tool_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        tool_headers = {**headers}
        if session_id:
            tool_headers["Mcp-Session-Id"] = session_id

        tool_resp = await client.post(url, json=tool_payload, headers=tool_headers)
        tool_ct = tool_resp.headers.get("content-type", "")

        if "text/event-stream" in tool_ct:
            return _parse_sse_response(tool_resp.text)

        tool_resp.raise_for_status()
        data = tool_resp.json()

    if "error" in data:
        raise ValueError(
            f"Local Falcon MCP error [{tool_name}]: "
            f"{data['error'].get('message', data['error'])}"
        )

    return _extract_result(data)


def _parse_sse_response(text: str) -> dict | list | str:
    """Parse a text/event-stream response, extracting the last data payload."""
    last_data = ""
    for line in text.split("\n"):
        if line.startswith("data: "):
            last_data = line[6:]

    if not last_data:
        return text

    try:
        parsed = json.loads(last_data)
        return _extract_result(parsed)
    except (json.JSONDecodeError, ValueError):
        return last_data


def _extract_result(data: dict) -> dict | list | str:
    """Extract the tool result from a JSON-RPC response."""
    result = data.get("result", data)

    # MCP wraps tool results in content array
    content = result.get("content", []) if isinstance(result, dict) else []
    if content and isinstance(content, list):
        first = content[0]
        if isinstance(first, dict):
            text = first.get("text", "")
            # Try to parse as JSON
            try:
                return json.loads(text)
            except (json.JSONDecodeError, ValueError):
                return text

    return result


# ── High-level functions ──────────────────────────────────────────────────────


async def list_scan_reports(limit: int = 50) -> list[dict]:
    """List all scan reports from the Local Falcon account."""
    try:
        result = await lf_call("listLocalFalconScanReports")
        if isinstance(result, list):
            return result[:limit]
        if isinstance(result, dict):
            return result.get("reports", result.get("data", []))[:limit]
        return []
    except Exception:
        return []


async def get_scan_report(report_key: str) -> dict:
    """
    Get a single scan report with full grid data.

    Returns dict with keys like:
        keyword, grid_size, arp, atrp, solv, scan_date,
        lat, lng, data_points (list of grid point rankings)
    """
    result = await lf_call("getLocalFalconReport", {"report_key": report_key})
    if isinstance(result, dict):
        return result
    return {"raw": result}


async def list_locations() -> list[dict]:
    """List all tracked locations in the Local Falcon account."""
    try:
        result = await lf_call("listAllLocalFalconLocations")
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return result.get("locations", result.get("data", []))
        return []
    except Exception:
        return []


async def list_campaign_reports(limit: int = 20) -> list[dict]:
    """List campaign (recurring scan) reports."""
    try:
        result = await lf_call("listLocalFalconCampaignReports")
        if isinstance(result, list):
            return result[:limit]
        if isinstance(result, dict):
            return result.get("reports", result.get("data", []))[:limit]
        return []
    except Exception:
        return []


async def get_account_info() -> dict:
    """Get Local Falcon account details (credits, subscription info)."""
    try:
        result = await lf_call("viewLocalFalconAccountInformation")
        if isinstance(result, dict):
            return result
        return {}
    except Exception:
        return {}


# ── Data extraction helpers ───────────────────────────────────────────────────


def extract_grid_data(report: dict) -> dict:
    """
    Normalize a scan report into a standard format for the heatmap component.

    Returns:
        {
            "keyword": str,
            "grid_size": int (e.g. 5, 7, 13),
            "arp": float (average rank position),
            "atrp": float (average total rank position),
            "solv": float (share of local voice, 0-100),
            "scan_date": str,
            "center": {"lat": float, "lng": float},
            "grid": [[rank, rank, ...], ...] — 2D array, row-major
        }
    """
    # Handle various key formats Local Falcon might use
    keyword = (
        report.get("keyword")
        or report.get("search_keyword")
        or report.get("kw")
        or ""
    )

    # Grid size — could be "5x5", 5, "7x7", etc.
    raw_size = report.get("grid_size") or report.get("gridSize") or ""
    if isinstance(raw_size, str) and "x" in raw_size:
        grid_size = int(raw_size.split("x")[0])
    elif isinstance(raw_size, (int, float)):
        grid_size = int(raw_size)
    else:
        grid_size = 0

    arp = _float_safe(report.get("arp") or report.get("average_rank_position"))
    atrp = _float_safe(report.get("atrp") or report.get("average_total_rank_position"))
    solv = _float_safe(report.get("solv") or report.get("share_of_local_voice"))

    scan_date = (
        report.get("scan_date")
        or report.get("scanDate")
        or report.get("created_at")
        or ""
    )

    # Center coordinates
    center_lat = _float_safe(report.get("lat") or report.get("latitude"))
    center_lng = _float_safe(report.get("lng") or report.get("longitude"))

    # Extract grid points
    data_points = (
        report.get("data_points")
        or report.get("dataPoints")
        or report.get("grid_data")
        or report.get("points")
        or []
    )

    # Build 2D grid if we have data points
    grid = []
    if data_points and grid_size > 0:
        grid = _build_grid(data_points, grid_size)
    elif data_points:
        # Try to infer grid size from number of points
        import math
        n = len(data_points)
        side = int(math.sqrt(n))
        if side * side == n:
            grid_size = side
            grid = _build_grid(data_points, side)

    return {
        "keyword": keyword,
        "grid_size": grid_size,
        "arp": arp,
        "atrp": atrp,
        "solv": solv,
        "scan_date": scan_date,
        "center": {"lat": center_lat, "lng": center_lng},
        "grid": grid,
    }


def _build_grid(data_points: list, size: int) -> list[list[int]]:
    """Convert a flat list of grid data points into a 2D array of ranks."""
    # Sort by position/order if available
    sorted_points = list(data_points)
    if sorted_points and isinstance(sorted_points[0], dict):
        # Try sorting by grid position fields
        if "row" in sorted_points[0] and "col" in sorted_points[0]:
            sorted_points.sort(key=lambda p: (p.get("row", 0), p.get("col", 0)))
        elif "order" in sorted_points[0]:
            sorted_points.sort(key=lambda p: p.get("order", 0))
        elif "index" in sorted_points[0]:
            sorted_points.sort(key=lambda p: p.get("index", 0))

        # Extract rank from each point
        ranks = []
        for p in sorted_points:
            rank = (
                p.get("rank")
                or p.get("position")
                or p.get("ranking")
                or 21  # 21 = not found
            )
            ranks.append(int(rank) if rank != "Not found" else 21)
    elif sorted_points and isinstance(sorted_points[0], (int, float)):
        ranks = [int(r) for r in sorted_points]
    else:
        ranks = [21] * (size * size)

    # Chunk into rows
    grid = []
    for i in range(0, len(ranks), size):
        grid.append(ranks[i : i + size])

    # Pad if needed
    while len(grid) < size:
        grid.append([21] * size)

    return grid


def _float_safe(val) -> float:
    """Safely convert a value to float, returning 0.0 on failure."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


# ── Formatting for Claude prompts ─────────────────────────────────────────────


def format_scan_for_report(scan_data: dict) -> str:
    """Format a Local Falcon scan report for injection into Claude prompts."""
    grid = extract_grid_data(scan_data)

    lines = [f"### Local Rank Tracking — \"{grid['keyword']}\""]
    lines.append(f"Grid: {grid['grid_size']}x{grid['grid_size']} | Scanned: {grid['scan_date']}")

    if grid["arp"]:
        lines.append(f"Average Rank Position (ARP): {grid['arp']:.1f}")
    if grid["solv"]:
        lines.append(f"Share of Local Voice (SoLV): {grid['solv']:.1f}%")
    if grid["atrp"]:
        lines.append(f"Average Total Rank Position (ATRP): {grid['atrp']:.1f}")

    if grid["grid"]:
        lines.append("")
        lines.append("Grid visualization (rank at each point, 21 = not found):")
        for row in grid["grid"]:
            cells = []
            for r in row:
                if r <= 3:
                    cells.append(f"[{r:2d}]")
                elif r <= 10:
                    cells.append(f" {r:2d} ")
                elif r <= 20:
                    cells.append(f"({r:2d})")
                else:
                    cells.append(" -- ")
            lines.append("  ".join(cells))
        lines.append("")
        lines.append("Legend: [N]=Top 3 (strong), N=4-10 (visible), (N)=11-20 (weak), --=Not found")

        # Summary stats from grid
        flat = [r for row in grid["grid"] for r in row]
        top3 = sum(1 for r in flat if r <= 3)
        top10 = sum(1 for r in flat if r <= 10)
        visible = sum(1 for r in flat if r <= 20)
        total = len(flat)
        lines.append(f"Top 3: {top3}/{total} points ({top3/total*100:.0f}%)")
        lines.append(f"Top 10: {top10}/{total} points ({top10/total*100:.0f}%)")
        lines.append(f"Visible (≤20): {visible}/{total} points ({visible/total*100:.0f}%)")

    return "\n".join(lines)


def format_scans_summary(scans: list[dict]) -> str:
    """Format a list of scan reports into a summary for Claude prompts."""
    if not scans:
        return "No Local Falcon scan data available."

    lines = ["### Local Falcon Scan History\n"]
    for scan in scans[:10]:
        keyword = scan.get("keyword") or scan.get("search_keyword") or "Unknown"
        arp = scan.get("arp") or scan.get("average_rank_position") or "N/A"
        solv = scan.get("solv") or scan.get("share_of_local_voice") or "N/A"
        date = (scan.get("scan_date") or scan.get("created_at") or "")[:10]
        lines.append(f"- {date}: \"{keyword}\" — ARP: {arp}, SoLV: {solv}%")

    return "\n".join(lines)
