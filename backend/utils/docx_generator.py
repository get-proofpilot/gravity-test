"""
ProofPilot branded .docx generator — Node.js backend

Calls utils/docx-generator.js (Node.js + docx npm) to produce fully branded
Word documents. Python handles font embedding post-processing since the docx
npm package doesn't support TTF embedding natively.

DO NOT use python-docx for ProofPilot documents — use this module instead.
"""

import json
import os
import subprocess
import zipfile
from pathlib import Path

UTILS_DIR = Path(__file__).parent
BACKEND_DIR = UTILS_DIR.parent
NODE_SCRIPT = UTILS_DIR / "docx-generator.js"
FONTS_DIR = UTILS_DIR / "fonts"
BEBAS_NEUE_TTF = FONTS_DIR / "BebasNeue-regular.ttf"
TEMP_DIR = Path(os.environ.get("DOCS_DIR", str(BACKEND_DIR / "temp_docs")))


# ═══════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════

def generate_docx(job_id: str, job_data: dict) -> Path:
    """Generate a branded ProofPilot .docx and return its path."""
    TEMP_DIR.mkdir(exist_ok=True)

    content        = job_data["content"]
    client_name    = job_data["client_name"]
    workflow_title = job_data["workflow_title"]

    # Write input JSON for Node.js script
    json_path = TEMP_DIR / f"{job_id}_input.json"
    out_path  = TEMP_DIR / f"{job_id}.docx"

    json_path.write_text(json.dumps({
        "content":        content,
        "client_name":    client_name,
        "workflow_title": workflow_title,
        "job_id":         job_id,
    }, ensure_ascii=False))

    try:
        result = subprocess.run(
            ["node", str(NODE_SCRIPT), str(json_path), str(out_path)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(BACKEND_DIR),
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"docx-generator.js failed (exit {result.returncode}):\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
    finally:
        # Clean up temp JSON
        try:
            json_path.unlink(missing_ok=True)
        except Exception:
            pass

    # Post-process: embed Bebas Neue TTF (docx npm doesn't do font embedding)
    _embed_fonts(out_path)

    return out_path


# ═══════════════════════════════════════════════════════════════════════
# Font embedding (post-process the DOCX zip)
# ═══════════════════════════════════════════════════════════════════════

def _embed_fonts(docx_path: Path) -> None:
    """
    Inject BebasNeue-regular.ttf into the DOCX zip so the font renders
    correctly on any machine without Bebas Neue installed.
    """
    if not BEBAS_NEUE_TTF.exists():
        return  # Font file not available — skip silently

    font_bytes = BEBAS_NEUE_TTF.read_bytes()
    tmp = docx_path.with_suffix(".tmp.docx")

    FONT_DECL = (
        '<w:font w:name="Bebas Neue">'
        '<w:embedRegular'
        ' w:fontKey="{00000000-0000-0000-0000-000000000000}"'
        ' r:id="rId10" w:subsetted="0"/>'
        "</w:font>"
    )
    FONT_REL = (
        '<Relationship Id="rId10"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"'
        ' Target="fonts/BebasNeue-regular.ttf"/>'
    )
    FONT_RELS_NEW = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + FONT_REL
        + "</Relationships>"
    )

    with zipfile.ZipFile(docx_path, "r") as zin:
        existing = {item.filename for item in zin.infolist()}

        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)

                if item.filename == "word/fontTable.xml":
                    text = data.decode("utf-8")
                    if "Bebas Neue" not in text:
                        # Handle both self-closing (<w:fonts .../>) and with body (</w:fonts>)
                        if "</w:fonts>" in text:
                            text = text.replace("</w:fonts>", FONT_DECL + "</w:fonts>")
                        else:
                            # Self-closing — replace with open/close tag containing declaration
                            import re as _re
                            text = _re.sub(
                                r"(<w:fonts\b[^>]*)/\s*>",
                                lambda m: m.group(1) + ">" + FONT_DECL + "</w:fonts>",
                                text,
                            )
                    data = text.encode("utf-8")

                elif item.filename == "word/_rels/fontTable.xml.rels":
                    text = data.decode("utf-8")
                    if "rId10" not in text:
                        text = text.replace("</Relationships>", FONT_REL + "</Relationships>")
                    data = text.encode("utf-8")

                zout.writestr(item, data)

            # Embed font binary
            if "word/fonts/BebasNeue-regular.ttf" not in existing:
                zout.writestr("word/fonts/BebasNeue-regular.ttf", font_bytes)

            # Create fontTable.xml.rels if not present
            if "word/_rels/fontTable.xml.rels" not in existing:
                zout.writestr(
                    "word/_rels/fontTable.xml.rels",
                    FONT_RELS_NEW.encode("utf-8"),
                )

    tmp.replace(docx_path)
