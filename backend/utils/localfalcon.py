"""
Local Falcon API Client — full local rank tracking suite for ProofPilot.

Calls the Local Falcon MCP server endpoint to pull scan reports, grid data,
competitor analysis, trend tracking, guard alerts, reviews analysis, keyword
reports, location reports, and Google Business Profile locations.

Required env var:
    LOCALFALCON_API_KEY    Your Local Falcon API key (manage at localfalcon.com/api/credentials)

MCP endpoint: https://mcp.localfalcon.com/mcp
Auth: API key passed as query parameter

Available MCP tools (25 total):
  Scans:        listLocalFalconScanReports, getLocalFalconReport, getLocalFalconGrid
  Campaigns:    listLocalFalconCampaignReports, getLocalFalconCampaignReport
  Trends:       listLocalFalconTrendReports, getLocalFalconTrendReport
  Competitors:  getLocalFalconCompetitorReports, getLocalFalconCompetitorReport
  Guards:       listLocalFalconGuardReports, getLocalFalconGuardReport
  Keywords:     listLocalFalconKeywordReports, getLocalFalconKeywordReport,
                getLocalFalconKeywordAtCoordinate
  Locations:    listAllLocalFalconLocations, listLocalFalconLocationReports,
                getLocalFalconLocationReport
  Rankings:     getLocalFalconRankingAtCoordinate
  Reviews:      listLocalFalconReviewsAnalysisReports, getLocalFalconReviewsAnalysisReport
  GBP:          getLocalFalconGoogleBusinessLocations
  Auto-scans:   listLocalFalconAutoScans
  Actions:      runLocalFalconScan, runLocalFalconCampaign
  Account:      viewLocalFalconAccountInformation
"""

import os
import json
import math
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


def _to_list(result, key: str = "data") -> list:
    """Normalize an MCP result to a list."""
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        # Try common wrapper keys
        for k in [key, "reports", "data", "items", "results", "locations"]:
            if k in result and isinstance(result[k], list):
                return result[k]
    return []


def _to_dict(result) -> dict:
    """Normalize an MCP result to a dict."""
    if isinstance(result, dict):
        return result
    return {"raw": result}


# ── High-level functions: Scans ──────────────────────────────────────────────


async def list_scan_reports(limit: int = 50) -> list[dict]:
    """List all scan reports from the Local Falcon account."""
    try:
        result = await lf_call("listLocalFalconScanReports")
        return _to_list(result, "reports")[:limit]
    except Exception:
        return []


async def get_scan_report(report_key: str) -> dict:
    """Get a single scan report with full grid data."""
    result = await lf_call("getLocalFalconReport", {"report_key": report_key})
    return _to_dict(result)


async def get_grid(report_key: str) -> dict:
    """Get grid data for a scan report (alternative endpoint)."""
    try:
        result = await lf_call("getLocalFalconGrid", {"report_key": report_key})
        return _to_dict(result)
    except Exception:
        return {}


# ── High-level functions: Campaigns ──────────────────────────────────────────


async def list_campaign_reports(limit: int = 20) -> list[dict]:
    """List campaign (recurring scan) reports."""
    try:
        result = await lf_call("listLocalFalconCampaignReports")
        return _to_list(result, "reports")[:limit]
    except Exception:
        return []


async def get_campaign_report(campaign_id: str) -> dict:
    """Get a single campaign report with scan history."""
    try:
        result = await lf_call("getLocalFalconCampaignReport", {"campaign_id": campaign_id})
        return _to_dict(result)
    except Exception:
        return {}


# ── High-level functions: Trends ─────────────────────────────────────────────


async def list_trend_reports(limit: int = 50) -> list[dict]:
    """List trend reports showing rank changes over time."""
    try:
        result = await lf_call("listLocalFalconTrendReports")
        return _to_list(result, "reports")[:limit]
    except Exception:
        return []


async def get_trend_report(report_key: str) -> dict:
    """Get a single trend report with historical data points."""
    try:
        result = await lf_call("getLocalFalconTrendReport", {"report_key": report_key})
        return _to_dict(result)
    except Exception:
        return {}


# ── High-level functions: Competitors ────────────────────────────────────────


async def get_competitor_reports(report_key: str) -> list[dict]:
    """Get competitor rankings for a specific scan/keyword."""
    try:
        result = await lf_call("getLocalFalconCompetitorReports", {"report_key": report_key})
        return _to_list(result, "competitors")
    except Exception:
        return []


async def get_competitor_report(report_key: str) -> dict:
    """Get detailed competitor report for a single competitor."""
    try:
        result = await lf_call("getLocalFalconCompetitorReport", {"report_key": report_key})
        return _to_dict(result)
    except Exception:
        return {}


# ── High-level functions: Guard (rank monitoring alerts) ─────────────────────


async def list_guard_reports(limit: int = 50) -> list[dict]:
    """List guard reports (rank change monitoring alerts)."""
    try:
        result = await lf_call("listLocalFalconGuardReports")
        return _to_list(result, "reports")[:limit]
    except Exception:
        return []


async def get_guard_report(report_key: str) -> dict:
    """Get a single guard report with rank change details."""
    try:
        result = await lf_call("getLocalFalconGuardReport", {"report_key": report_key})
        return _to_dict(result)
    except Exception:
        return {}


# ── High-level functions: Keywords ───────────────────────────────────────────


async def list_keyword_reports(limit: int = 50) -> list[dict]:
    """List keyword-level tracking reports."""
    try:
        result = await lf_call("listLocalFalconKeywordReports")
        return _to_list(result, "reports")[:limit]
    except Exception:
        return []


async def get_keyword_report(report_key: str) -> dict:
    """Get detailed keyword tracking report."""
    try:
        result = await lf_call("getLocalFalconKeywordReport", {"report_key": report_key})
        return _to_dict(result)
    except Exception:
        return {}


async def get_keyword_at_coordinate(
    keyword: str, lat: float, lng: float
) -> dict:
    """Check keyword ranking at a specific geographic coordinate."""
    try:
        result = await lf_call("getLocalFalconKeywordAtCoordinate", {
            "keyword": keyword,
            "lat": lat,
            "lng": lng,
        })
        return _to_dict(result)
    except Exception:
        return {}


async def get_ranking_at_coordinate(
    report_key: str, lat: float, lng: float
) -> dict:
    """Get ranking data at a specific coordinate within a scan grid."""
    try:
        result = await lf_call("getLocalFalconRankingAtCoordinate", {
            "report_key": report_key,
            "lat": lat,
            "lng": lng,
        })
        return _to_dict(result)
    except Exception:
        return {}


# ── High-level functions: Locations ──────────────────────────────────────────


async def list_locations() -> list[dict]:
    """List all tracked locations in the Local Falcon account."""
    try:
        result = await lf_call("listAllLocalFalconLocations")
        return _to_list(result, "locations")
    except Exception:
        return []


async def list_location_reports(limit: int = 50) -> list[dict]:
    """List per-location tracking reports."""
    try:
        result = await lf_call("listLocalFalconLocationReports")
        return _to_list(result, "reports")[:limit]
    except Exception:
        return []


async def get_location_report(report_key: str) -> dict:
    """Get detailed location-level report."""
    try:
        result = await lf_call("getLocalFalconLocationReport", {"report_key": report_key})
        return _to_dict(result)
    except Exception:
        return {}


# ── High-level functions: Reviews Analysis ───────────────────────────────────


async def list_reviews_reports(limit: int = 50) -> list[dict]:
    """List reviews analysis reports."""
    try:
        result = await lf_call("listLocalFalconReviewsAnalysisReports")
        return _to_list(result, "reports")[:limit]
    except Exception:
        return []


async def get_reviews_report(report_key: str) -> dict:
    """Get detailed reviews analysis (sentiment, competitor comparison)."""
    try:
        result = await lf_call("getLocalFalconReviewsAnalysisReport", {"report_key": report_key})
        return _to_dict(result)
    except Exception:
        return {}


# ── High-level functions: Google Business ────────────────────────────────────


async def get_gbp_locations() -> list[dict]:
    """Get Google Business Profile locations connected to Local Falcon."""
    try:
        result = await lf_call("getLocalFalconGoogleBusinessLocations")
        return _to_list(result, "locations")
    except Exception:
        return []


# ── High-level functions: Auto-scans ─────────────────────────────────────────


async def list_auto_scans(limit: int = 50) -> list[dict]:
    """List configured automatic/scheduled scans."""
    try:
        result = await lf_call("listLocalFalconAutoScans")
        return _to_list(result, "auto_scans")[:limit]
    except Exception:
        return []


# ── High-level functions: Account ────────────────────────────────────────────


async def get_account_info() -> dict:
    """Get Local Falcon account details (credits, subscription info)."""
    try:
        result = await lf_call("viewLocalFalconAccountInformation")
        return _to_dict(result)
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

    center_lat = _float_safe(report.get("lat") or report.get("latitude"))
    center_lng = _float_safe(report.get("lng") or report.get("longitude"))

    data_points = (
        report.get("data_points")
        or report.get("dataPoints")
        or report.get("grid_data")
        or report.get("points")
        or []
    )

    grid = []
    if data_points and grid_size > 0:
        grid = _build_grid(data_points, grid_size)
    elif data_points:
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


def extract_trend_data(trend_report: dict) -> dict:
    """
    Normalize a trend report into a standard format for trend charts.

    Returns:
        {
            "keyword": str,
            "location": str,
            "data_points": [{"date": str, "arp": float, "solv": float, "atrp": float}, ...]
        }
    """
    keyword = (
        trend_report.get("keyword")
        or trend_report.get("search_keyword")
        or ""
    )
    location = (
        trend_report.get("location")
        or trend_report.get("location_name")
        or trend_report.get("business_name")
        or ""
    )

    # Trend data might be in various formats
    raw_points = (
        trend_report.get("data_points")
        or trend_report.get("dataPoints")
        or trend_report.get("trend_data")
        or trend_report.get("data")
        or trend_report.get("scans")
        or []
    )

    data_points = []
    for pt in raw_points:
        if isinstance(pt, dict):
            data_points.append({
                "date": pt.get("date") or pt.get("scan_date") or pt.get("created_at") or "",
                "arp": _float_safe(pt.get("arp") or pt.get("average_rank_position")),
                "solv": _float_safe(pt.get("solv") or pt.get("share_of_local_voice")),
                "atrp": _float_safe(pt.get("atrp") or pt.get("average_total_rank_position")),
            })

    return {
        "keyword": keyword,
        "location": location,
        "data_points": data_points,
    }


def extract_competitor_data(competitor_report: dict | list) -> list[dict]:
    """
    Normalize competitor report data.

    Returns list of:
        {
            "name": str (business name),
            "rank": int,
            "arp": float,
            "solv": float,
            "reviews": int,
            "rating": float,
        }
    """
    raw = competitor_report if isinstance(competitor_report, list) else [competitor_report]
    competitors = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        competitors.append({
            "name": (
                item.get("name")
                or item.get("business_name")
                or item.get("competitor_name")
                or "Unknown"
            ),
            "rank": int(item.get("rank") or item.get("position") or 0),
            "arp": _float_safe(item.get("arp") or item.get("average_rank_position")),
            "solv": _float_safe(item.get("solv") or item.get("share_of_local_voice")),
            "reviews": int(_float_safe(item.get("reviews") or item.get("review_count"))),
            "rating": _float_safe(item.get("rating") or item.get("star_rating")),
        })
    return competitors


def _build_grid(data_points: list, size: int) -> list[list[int]]:
    """Convert a flat list of grid data points into a 2D array of ranks."""
    sorted_points = list(data_points)
    if sorted_points and isinstance(sorted_points[0], dict):
        if "row" in sorted_points[0] and "col" in sorted_points[0]:
            sorted_points.sort(key=lambda p: (p.get("row", 0), p.get("col", 0)))
        elif "order" in sorted_points[0]:
            sorted_points.sort(key=lambda p: p.get("order", 0))
        elif "index" in sorted_points[0]:
            sorted_points.sort(key=lambda p: p.get("index", 0))

        ranks = []
        for p in sorted_points:
            rank = (
                p.get("rank")
                or p.get("position")
                or p.get("ranking")
                or 21
            )
            ranks.append(int(rank) if rank != "Not found" else 21)
    elif sorted_points and isinstance(sorted_points[0], (int, float)):
        ranks = [int(r) for r in sorted_points]
    else:
        ranks = [21] * (size * size)

    grid = []
    for i in range(0, len(ranks), size):
        grid.append(ranks[i : i + size])

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


def format_trend_for_report(trend_data: dict) -> str:
    """Format trend report data for Claude prompts."""
    td = extract_trend_data(trend_data) if "data_points" not in trend_data else trend_data
    keyword = td.get("keyword", "Unknown")
    points = td.get("data_points", [])

    if not points:
        return ""

    lines = [f"### Rank Trend — \"{keyword}\""]
    lines.append("Date | ARP | SoLV | ATRP")
    lines.append("--- | --- | --- | ---")
    for pt in points[-12:]:  # Last 12 data points
        date = (pt.get("date") or "")[:10]
        arp = pt.get("arp", 0)
        solv = pt.get("solv", 0)
        atrp = pt.get("atrp", 0)
        lines.append(f"{date} | {arp:.1f} | {solv:.0f}% | {atrp:.1f}")

    # Calculate trend direction
    if len(points) >= 2:
        first_arp = points[0].get("arp", 0)
        last_arp = points[-1].get("arp", 0)
        first_solv = points[0].get("solv", 0)
        last_solv = points[-1].get("solv", 0)
        if first_arp and last_arp:
            arp_change = first_arp - last_arp  # lower ARP = better
            direction = "improving" if arp_change > 0 else "declining" if arp_change < 0 else "stable"
            lines.append(f"\nTrend: ARP {direction} ({first_arp:.1f} → {last_arp:.1f})")
        if first_solv and last_solv:
            solv_change = last_solv - first_solv  # higher SoLV = better
            direction = "improving" if solv_change > 0 else "declining" if solv_change < 0 else "stable"
            lines.append(f"SoLV trend: {direction} ({first_solv:.0f}% → {last_solv:.0f}%)")

    return "\n".join(lines)


def format_competitors_for_report(competitors: list[dict]) -> str:
    """Format competitor data for Claude prompts."""
    if not competitors:
        return "No competitor data available from Local Falcon."

    lines = ["### Local Pack Competitors (Local Falcon)\n"]
    lines.append("Rank | Business | ARP | SoLV | Reviews | Rating")
    lines.append("--- | --- | --- | --- | --- | ---")

    for comp in competitors[:10]:
        name = comp.get("name", "Unknown")
        rank = comp.get("rank", "–")
        arp = comp.get("arp", 0)
        solv = comp.get("solv", 0)
        reviews = comp.get("reviews", 0)
        rating = comp.get("rating", 0)
        lines.append(
            f"#{rank} | {name} | {arp:.1f} | {solv:.0f}% | "
            f"{reviews:,} | {'★' + f'{rating:.1f}' if rating else '–'}"
        )

    return "\n".join(lines)


def format_guard_for_report(guard_data: dict) -> str:
    """Format guard (rank monitoring) data for Claude prompts."""
    lines = ["### Rank Guard Alerts (Local Falcon)\n"]

    alerts = (
        guard_data.get("alerts")
        or guard_data.get("changes")
        or guard_data.get("data")
        or []
    )

    if not alerts:
        keyword = guard_data.get("keyword") or guard_data.get("search_keyword") or ""
        if keyword:
            lines.append(f"No rank changes detected for \"{keyword}\".")
        else:
            lines.append("No rank change alerts found.")
        return "\n".join(lines)

    for alert in alerts[:10]:
        if isinstance(alert, dict):
            keyword = alert.get("keyword") or alert.get("search_keyword") or "Unknown"
            old_rank = alert.get("old_rank") or alert.get("previous_rank") or "?"
            new_rank = alert.get("new_rank") or alert.get("current_rank") or "?"
            date = (alert.get("date") or alert.get("detected_at") or "")[:10]
            lines.append(f"- {date}: \"{keyword}\" — rank {old_rank} → {new_rank}")

    return "\n".join(lines)


def format_reviews_for_report(reviews_data: dict) -> str:
    """Format reviews analysis for Claude prompts."""
    lines = ["### Reviews Analysis (Local Falcon)\n"]

    # Extract key metrics
    total = reviews_data.get("total_reviews") or reviews_data.get("review_count") or 0
    rating = reviews_data.get("rating") or reviews_data.get("average_rating") or 0
    sentiment = reviews_data.get("sentiment") or reviews_data.get("sentiment_score") or ""

    if total:
        lines.append(f"- Total reviews: {total}")
    if rating:
        lines.append(f"- Average rating: ★{_float_safe(rating):.1f}")
    if sentiment:
        lines.append(f"- Sentiment: {sentiment}")

    # Competitor review comparison if available
    comp_reviews = (
        reviews_data.get("competitors")
        or reviews_data.get("competitor_reviews")
        or []
    )
    if comp_reviews:
        lines.append("\nCompetitor Review Comparison:")
        for comp in comp_reviews[:5]:
            if isinstance(comp, dict):
                name = comp.get("name") or comp.get("business_name") or "Unknown"
                c_total = comp.get("total_reviews") or comp.get("review_count") or 0
                c_rating = comp.get("rating") or comp.get("average_rating") or 0
                lines.append(f"- {name}: {c_total} reviews, ★{_float_safe(c_rating):.1f}")

    return "\n".join(lines)


# ── Aggregated data gathering for workflows ──────────────────────────────────


async def gather_full_lf_data(limit_scans: int = 5) -> dict:
    """
    Gather comprehensive Local Falcon data for workflows.

    Returns dict with keys:
        scans, detailed_scans, trends, competitors, guards,
        reviews, locations, auto_scans, account
    All values default to empty list/dict on failure.
    """
    import asyncio

    if not os.environ.get("LOCALFALCON_API_KEY"):
        return {}

    async def _safe(coro, default=None):
        try:
            return await coro
        except Exception:
            return default if default is not None else []

    # Fetch everything in parallel
    (
        scans, trends, guards, reviews,
        locations, auto_scans, account
    ) = await asyncio.gather(
        _safe(list_scan_reports(limit=limit_scans * 2)),
        _safe(list_trend_reports(limit=10)),
        _safe(list_guard_reports(limit=10)),
        _safe(list_reviews_reports(limit=5)),
        _safe(list_locations()),
        _safe(list_auto_scans(limit=10)),
        _safe(get_account_info(), default={}),
    )

    # Get detailed grid data for top scans
    detailed_scans = []
    for scan in (scans or [])[:limit_scans]:
        key = (
            scan.get("report_key")
            or scan.get("reportKey")
            or scan.get("key")
            or scan.get("id")
            or ""
        )
        if not key:
            continue
        try:
            report = await get_scan_report(str(key))
            detailed_scans.append(report)
        except Exception:
            pass

    # Get competitor data for the most recent scan
    competitors = []
    if scans:
        first_key = (
            scans[0].get("report_key")
            or scans[0].get("reportKey")
            or scans[0].get("key")
            or scans[0].get("id")
            or ""
        )
        if first_key:
            competitors = await _safe(
                get_competitor_reports(str(first_key))
            )

    # Get detailed trend data for the first trend report
    trend_detail = {}
    if trends:
        first_trend_key = (
            trends[0].get("report_key")
            or trends[0].get("reportKey")
            or trends[0].get("key")
            or trends[0].get("id")
            or ""
        )
        if first_trend_key:
            trend_detail = await _safe(
                get_trend_report(str(first_trend_key)), default={}
            )

    return {
        "scans": scans or [],
        "detailed_scans": detailed_scans,
        "trends": trends or [],
        "trend_detail": trend_detail,
        "competitors": competitors,
        "guards": guards or [],
        "reviews": reviews or [],
        "locations": locations or [],
        "auto_scans": auto_scans or [],
        "account": account or {},
    }


def format_full_lf_context(lf_data: dict) -> str:
    """
    Format all Local Falcon data into a comprehensive context section
    for Claude workflow prompts.
    """
    if not lf_data:
        return ""

    sections = []

    # Detailed scan grids
    for scan in lf_data.get("detailed_scans", [])[:3]:
        text = format_scan_for_report(scan)
        if text:
            sections.append(text)

    # Scan history summary (if we have scans but no detailed)
    if not lf_data.get("detailed_scans") and lf_data.get("scans"):
        sections.append(format_scans_summary(lf_data["scans"]))

    # Trend data
    trend_detail = lf_data.get("trend_detail", {})
    if trend_detail:
        text = format_trend_for_report(trend_detail)
        if text:
            sections.append(text)

    # Competitors
    competitors = lf_data.get("competitors", [])
    if competitors:
        normalized = extract_competitor_data(competitors)
        text = format_competitors_for_report(normalized)
        if text:
            sections.append(text)

    # Guard alerts
    guards = lf_data.get("guards", [])
    if guards and isinstance(guards, list) and len(guards) > 0:
        # Format the first guard report if it has detail
        first_guard = guards[0] if isinstance(guards[0], dict) else {}
        if first_guard:
            text = format_guard_for_report(first_guard)
            if text:
                sections.append(text)

    # Reviews
    reviews = lf_data.get("reviews", [])
    if reviews and isinstance(reviews, list) and len(reviews) > 0:
        first_review = reviews[0] if isinstance(reviews[0], dict) else {}
        if first_review:
            text = format_reviews_for_report(first_review)
            if text:
                sections.append(text)

    # Location overview
    locations = lf_data.get("locations", [])
    if locations:
        loc_lines = ["### Tracked Locations (Local Falcon)\n"]
        for loc in locations[:10]:
            if isinstance(loc, dict):
                name = loc.get("name") or loc.get("business_name") or loc.get("location_name") or "Unknown"
                address = loc.get("address") or loc.get("formatted_address") or ""
                loc_lines.append(f"- {name}" + (f" — {address}" if address else ""))
        if len(loc_lines) > 1:
            sections.append("\n".join(loc_lines))

    if not sections:
        return ""

    return "\n\n".join(sections)
