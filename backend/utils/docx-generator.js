/**
 * ProofPilot DOCX Generator — Node.js
 *
 * Based on the official ProofPilot brand boilerplate (proofpilot-brand.skill).
 * Converts markdown content from workflows into branded .docx files.
 *
 * Usage: node utils/docx-generator.js <input.json> <output.docx>
 *
 * Input JSON: { content, client_name, workflow_title, job_id }
 *
 * Markdown patterns handled:
 *   [COVER_END]       — page break, exits cover mode
 *   # H1              — cover title (2-line split at " & ") or body H1
 *   ## H2             — section heading, alternates Dark Blue / Electric Blue
 *   ### H3            — sub-heading (Black Bebas Neue)
 *   > **HEADER**      — callout box header (Dark Blue bg, Neon Green text)
 *   > - bullet        — callout box bullet
 *   > plain text      — callout box body
 *   | col | col |     — brand table (or info table if headers are empty)
 *   - bullet          — bullet list
 *   1. item           — numbered list
 *   ---               — horizontal rule
 *   **bold**          — bold inline
 *   *italic*          — italic inline
 */

'use strict';

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, PageNumber, LevelFormat, BorderStyle,
  WidthType, ShadingType, PageBreak, UnderlineType,
} = require('docx');
const fs = require('fs');

// ═══════════════════════════════════════════════════════════════════════
// BRAND COLORS
// ═══════════════════════════════════════════════════════════════════════
const ELECTRIC_BLUE = "0051FF";
const DARK_BLUE     = "00184D";
const NEON_GREEN    = "C8FF00";
const BLACK         = "000000";
const LIGHT_GRAY    = "F4F4F4";
const MEDIUM_GRAY   = "666666";
const WHITE         = "FFFFFF";

// ═══════════════════════════════════════════════════════════════════════
// TABLE STYLING
// ═══════════════════════════════════════════════════════════════════════
const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };

// ═══════════════════════════════════════════════════════════════════════
// STATUS PREFIXES — skip these lines from workflow progress output
// ═══════════════════════════════════════════════════════════════════════
const STATUS_PREFIXES = [
  'Pulling', 'Fetching', 'Researching', 'Building', 'Loading',
  'Analyzing', 'Computing', 'Gathering', 'Checking',
];

// ═══════════════════════════════════════════════════════════════════════
// INLINE TEXT FORMATTING
// Parses **bold** and *italic* in a string, returns array of TextRun
// ═══════════════════════════════════════════════════════════════════════
function parseInline(text, opts = {}) {
  const { color = BLACK, size = 22, font = "Calibri", bold = false, italic = false } = opts;
  const runs = [];

  // Split on **bold** first
  const boldParts = text.split(/(\*\*[^*]+\*\*)/);
  for (const part of boldParts) {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      runs.push(new TextRun({
        text: part.slice(2, -2),
        bold: true,
        italics: italic,
        color,
        size,
        font: { name: font },
      }));
    } else {
      // Split on *italic*
      const italicParts = part.split(/(\*[^*]+\*)/);
      for (const sub of italicParts) {
        if (sub.startsWith('*') && sub.endsWith('*') && sub.length > 2) {
          runs.push(new TextRun({
            text: sub.slice(1, -1),
            bold,
            italics: true,
            color,
            size,
            font: { name: font },
          }));
        } else if (sub) {
          runs.push(new TextRun({
            text: sub,
            bold,
            italics: italic,
            color,
            size,
            font: { name: font },
          }));
        }
      }
    }
  }
  return runs;
}

// ═══════════════════════════════════════════════════════════════════════
// HELPER: createHeaderRow (from boilerplate)
// ═══════════════════════════════════════════════════════════════════════
function createHeaderRow(headers, colWidths, bgColor) {
  return new TableRow({
    children: headers.map((h, i) => new TableCell({
      borders: cellBorders,
      shading: { fill: bgColor, type: ShadingType.CLEAR },
      width: { size: colWidths[i], type: WidthType.DXA },
      children: [new Paragraph({
        spacing: { before: 80, after: 80 },
        children: [new TextRun({ text: stripMd(h), bold: true, color: WHITE, size: 20, font: { name: "Calibri" } })],
      })],
    })),
  });
}

// ═══════════════════════════════════════════════════════════════════════
// HELPER: createDataRow (from boilerplate)
// ═══════════════════════════════════════════════════════════════════════
function createDataRow(cells, colWidths, options = {}) {
  const { bgColor = WHITE, textColor = BLACK } = options;
  return new TableRow({
    children: cells.map((cell, i) => new TableCell({
      borders: cellBorders,
      shading: { fill: bgColor, type: ShadingType.CLEAR },
      width: { size: colWidths[i] || 2000, type: WidthType.DXA },
      children: [new Paragraph({
        spacing: { before: 60, after: 60 },
        children: parseInline(stripMd(cell), { color: textColor, size: 20 }),
      })],
    })),
  });
}

// ═══════════════════════════════════════════════════════════════════════
// HELPER: createCTABox — dark blue callout box (from boilerplate, extended)
// ═══════════════════════════════════════════════════════════════════════
function createCTABox(headline, bodyLines) {
  const children = [];

  if (headline) {
    children.push(new Paragraph({
      alignment: AlignmentType.LEFT,
      spacing: { before: 160, after: 80 },
      children: [new TextRun({
        text: headline,
        bold: true,
        color: NEON_GREEN,
        size: 26,
        font: { name: "Bebas Neue" },
      })],
    }));
  }

  for (const line of bodyLines) {
    if (!line.trim()) continue;
    const isBullet = line.startsWith('- ');
    const raw = isBullet ? line.slice(2) : line;

    const lineRuns = [];
    if (isBullet) {
      lineRuns.push(new TextRun({ text: '• ', color: NEON_GREEN, size: 20, font: { name: "Calibri" } }));
    }
    // Parse inline bold in callout — bold becomes Neon Green
    const boldParts = raw.split(/(\*\*[^*]+\*\*)/);
    for (const part of boldParts) {
      if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
        lineRuns.push(new TextRun({ text: part.slice(2, -2), bold: true, color: NEON_GREEN, size: 20, font: { name: "Calibri" } }));
      } else if (part) {
        lineRuns.push(new TextRun({ text: part, color: WHITE, size: 20, font: { name: "Calibri" } }));
      }
    }

    children.push(new Paragraph({
      spacing: { before: 40, after: 40 },
      indent: isBullet ? { left: 180 } : undefined,
      children: lineRuns,
    }));
  }

  if (children.length === 0) return null;

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [9360],
    rows: [
      new TableRow({
        children: [new TableCell({
          borders: cellBorders,
          shading: { fill: DARK_BLUE, type: ShadingType.CLEAR },
          width: { size: 9360, type: WidthType.DXA },
          margins: { top: 120, bottom: 120, left: 160, right: 160 },
          children,
        })],
      }),
    ],
  });
}

// ═══════════════════════════════════════════════════════════════════════
// HELPER: stripMd — remove ** and * from text for table cells
// ═══════════════════════════════════════════════════════════════════════
function stripMd(text) {
  return (text || '').replace(/\*\*([^*]+)\*\*/g, '$1').replace(/\*([^*]+)\*/g, '$1').trim();
}

// ═══════════════════════════════════════════════════════════════════════
// MARKDOWN TABLE PARSER
// Returns { headers, rows, isInfoTable }
// ═══════════════════════════════════════════════════════════════════════
function parseMarkdownTable(tableLines) {
  const headers = [];
  const rows = [];

  for (const line of tableLines) {
    const trimmed = line.trim();
    if (!trimmed.startsWith('|')) continue;
    if (/^\|[-:\s|]+\|$/.test(trimmed)) continue; // separator row

    const cells = trimmed
      .split('|')
      .slice(1, -1)  // remove outer empty strings
      .map(c => c.trim());

    if (headers.length === 0) {
      headers.push(...cells);
    } else {
      rows.push(cells);
    }
  }

  const isInfoTable = headers.length === 2 && headers.every(h => h === '');
  return { headers, rows, isInfoTable };
}

// ═══════════════════════════════════════════════════════════════════════
// BUILD INFO TABLE (company metadata — label / value, no header row)
// ═══════════════════════════════════════════════════════════════════════
function buildInfoTable(rows) {
  const tableRows = rows.map(row => {
    const label = stripMd(row[0] || '');
    const value = stripMd(row[1] || '');
    return new TableRow({
      children: [
        new TableCell({
          borders: cellBorders,
          shading: { fill: LIGHT_GRAY, type: ShadingType.CLEAR },
          width: { size: 2500, type: WidthType.DXA },
          margins: { top: 60, bottom: 60, left: 80, right: 80 },
          children: [new Paragraph({
            children: [new TextRun({ text: label, bold: true, size: 22, color: BLACK, font: { name: "Calibri" } })],
          })],
        }),
        new TableCell({
          borders: cellBorders,
          shading: { fill: WHITE, type: ShadingType.CLEAR },
          width: { size: 6860, type: WidthType.DXA },
          margins: { top: 60, bottom: 60, left: 80, right: 80 },
          children: [new Paragraph({
            children: [new TextRun({ text: value, size: 22, color: BLACK, font: { name: "Calibri" } })],
          })],
        }),
      ],
    });
  });

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: [2500, 6860],
    rows: tableRows,
  });
}

// ═══════════════════════════════════════════════════════════════════════
// BUILD BRAND DATA TABLE
// ═══════════════════════════════════════════════════════════════════════
function buildBrandTable(headers, rows, headerColor) {
  if (!headers || headers.length === 0) return null;

  // Distribute width across columns
  const totalWidth = 9360;
  const colWidth = Math.floor(totalWidth / headers.length);
  const colWidths = headers.map((_, i) =>
    i === headers.length - 1 ? totalWidth - colWidth * (headers.length - 1) : colWidth
  );

  const tableRows = [];

  // Header row
  tableRows.push(createHeaderRow(headers, colWidths, headerColor));

  // Data rows with alternating background
  rows.forEach((row, idx) => {
    const bg = idx % 2 === 1 ? LIGHT_GRAY : WHITE;
    // Pad to header count
    const paddedRow = [...row];
    while (paddedRow.length < headers.length) paddedRow.push('');
    tableRows.push(createDataRow(paddedRow, colWidths, { bgColor: bg }));
  });

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths: colWidths,
    rows: tableRows,
  });
}

// ═══════════════════════════════════════════════════════════════════════
// MAIN MARKDOWN RENDERER
// Returns array of Document children (paragraphs, tables, etc.)
// ═══════════════════════════════════════════════════════════════════════
function renderMarkdown(content) {
  const elements = [];
  const lines = content.split('\n');
  let i = 0;
  let h2Count = 0;

  // Cover state
  let inCover = true;
  let coverH1Done = false;
  let coverSubtitleDone = false;

  const addSpacer = (before = 0, after = 100) => {
    elements.push(new Paragraph({ spacing: { before, after }, children: [] }));
  };

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // ── [COVER_END]: page break ─────────────────────────────────────
    if (trimmed === '[COVER_END]') {
      inCover = false;
      elements.push(new Paragraph({
        children: [new PageBreak()],
        spacing: { before: 0, after: 0 },
      }));
      i++;
      continue;
    }

    // ── Blockquote: callout box ─────────────────────────────────────
    if (trimmed.startsWith('> ')) {
      const rawContent = trimmed.slice(2).trim();
      // Skip status lines
      if (STATUS_PREFIXES.some(pfx => rawContent.startsWith(pfx))) {
        i++;
        continue;
      }

      // Collect all consecutive > lines
      const calloutLines = [];
      while (i < lines.length && lines[i].trim().startsWith('> ')) {
        calloutLines.push(lines[i].trim().slice(2).trim());
        i++;
      }

      // First line is the header if it's **BOLD**
      let headline = '';
      const bodyLines = [];
      if (calloutLines.length > 0 && /^\*\*[^*]+\*\*$/.test(calloutLines[0])) {
        headline = calloutLines[0].replace(/^\*\*([^*]+)\*\*$/, '$1');
        bodyLines.push(...calloutLines.slice(1));
      } else {
        bodyLines.push(...calloutLines);
      }

      addSpacer(80, 0);
      const box = createCTABox(headline, bodyLines);
      if (box) elements.push(box);
      addSpacer(0, 120);
      continue;
    }

    // ── Markdown table ──────────────────────────────────────────────
    if (trimmed.startsWith('|') && !/^\|[-:\s|]+\|$/.test(trimmed)) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }

      const { headers, rows, isInfoTable } = parseMarkdownTable(tableLines);

      if (isInfoTable) {
        elements.push(buildInfoTable(rows));
        addSpacer(0, 120);
      } else if (headers.length > 0) {
        const headerColor = h2Count % 2 === 1 ? DARK_BLUE : ELECTRIC_BLUE;
        const tbl = buildBrandTable(headers, rows, headerColor);
        if (tbl) {
          elements.push(tbl);
          addSpacer(0, 120);
        }
      }
      continue;
    }

    // ── H1 ──────────────────────────────────────────────────────────
    if (line.startsWith('# ')) {
      const title = line.slice(2).trim();

      if (inCover && !coverH1Done && title.includes(' & ')) {
        // Cover: two-line split
        coverH1Done = true;
        const [preAmp, postAmp] = title.split(' & ', 2);

        // Line 1: Electric Blue 24pt
        elements.push(new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 480, after: 0 },
          children: [new TextRun({
            text: preAmp,
            bold: true,
            color: ELECTRIC_BLUE,
            size: 48,
            font: { name: "Bebas Neue" },
          })],
        }));

        // Line 2: Dark Blue 38pt
        elements.push(new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 120 },
          children: [new TextRun({
            text: '& ' + postAmp,
            bold: true,
            color: DARK_BLUE,
            size: 76,
            font: { name: "Bebas Neue" },
          })],
        }));
      } else {
        // Body H1: Dark Blue 40pt Bebas
        elements.push(new Paragraph({
          heading: 'Heading1',
          spacing: { before: 360, after: 160 },
          children: [new TextRun({
            text: title,
            bold: true,
            color: DARK_BLUE,
            size: 40,
            font: { name: "Bebas Neue" },
          })],
        }));
      }
      i++;
      continue;
    }

    // ── H2 ──────────────────────────────────────────────────────────
    if (line.startsWith('## ')) {
      h2Count++;
      inCover = false;
      const color = h2Count % 2 === 1 ? DARK_BLUE : ELECTRIC_BLUE;
      elements.push(new Paragraph({
        heading: 'Heading2',
        spacing: { before: 300, after: 100 },
        children: [new TextRun({
          text: line.slice(3).trim(),
          bold: true,
          color,
          size: 36,
          font: { name: "Bebas Neue" },
        })],
      }));
      i++;
      continue;
    }

    // ── H3 ──────────────────────────────────────────────────────────
    if (line.startsWith('### ')) {
      elements.push(new Paragraph({
        heading: 'Heading3',
        spacing: { before: 200, after: 80 },
        children: [new TextRun({
          text: line.slice(4).trim(),
          bold: true,
          color: BLACK,
          size: 26,
          font: { name: "Bebas Neue" },
        })],
      }));
      i++;
      continue;
    }

    // ── Bullet list ─────────────────────────────────────────────────
    if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(new Paragraph({
        bullet: { level: 0 },
        spacing: { before: 40, after: 40 },
        indent: { left: 360 },
        children: parseInline(line.slice(2).trim(), { size: 22 }),
      }));
      i++;
      continue;
    }

    // ── Numbered list ───────────────────────────────────────────────
    const numMatch = line.match(/^(\d+)\.\s/);
    if (numMatch) {
      elements.push(new Paragraph({
        numbering: { reference: 'num-list-1', level: 0 },
        spacing: { before: 40, after: 40 },
        indent: { left: 360 },
        children: parseInline(line.replace(/^\d+\.\s/, '').trim(), { size: 22 }),
      }));
      i++;
      continue;
    }

    // ── Horizontal rule ─────────────────────────────────────────────
    if (trimmed === '---') {
      elements.push(new Paragraph({
        spacing: { before: 120, after: 120 },
        border: {
          bottom: { color: ELECTRIC_BLUE, space: 1, style: BorderStyle.SINGLE, size: 6 },
        },
        children: [],
      }));
      i++;
      continue;
    }

    // ── Empty line ──────────────────────────────────────────────────
    if (trimmed === '') {
      elements.push(new Paragraph({ spacing: { before: 0, after: 60 }, children: [] }));
      i++;
      continue;
    }

    // ── Body text / cover subtitle ──────────────────────────────────
    if (inCover && coverH1Done && !coverSubtitleDone) {
      // First plain text after cover H1 → italic gray subtitle
      coverSubtitleDone = true;
      elements.push(new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 200 },
        children: [new TextRun({
          text: trimmed,
          italics: true,
          color: MEDIUM_GRAY,
          size: 26,
          font: { name: "Calibri" },
        })],
      }));
    } else {
      // Regular body paragraph
      elements.push(new Paragraph({
        spacing: { before: 0, after: 80 },
        children: parseInline(trimmed, { size: 22 }),
      }));
    }
    i++;
  }

  return elements;
}

// ═══════════════════════════════════════════════════════════════════════
// DOCUMENT BUILDER
// ═══════════════════════════════════════════════════════════════════════
function buildDocument(content, clientName, workflowTitle) {
  const children = renderMarkdown(content);

  const doc = new Document({
    styles: {
      default: {
        document: { run: { font: "Calibri", size: 22 } },
      },
      paragraphStyles: [
        {
          id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 40, bold: true, color: DARK_BLUE, font: "Bebas Neue" },
          paragraph: { spacing: { before: 350, after: 150 }, outlineLevel: 0 },
        },
        {
          id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 36, bold: true, color: ELECTRIC_BLUE, font: "Bebas Neue" },
          paragraph: { spacing: { before: 300, after: 100 }, outlineLevel: 1 },
        },
        {
          id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 26, bold: true, color: BLACK, font: "Bebas Neue" },
          paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 },
        },
      ],
    },
    numbering: {
      config: [
        {
          reference: "bullet-list",
          levels: [{
            level: 0, format: LevelFormat.BULLET, text: "\u2022",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 360, hanging: 180 } } },
          }],
        },
        {
          reference: "num-list-1",
          levels: [{
            level: 0, format: LevelFormat.DECIMAL, text: "%1.",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 360, hanging: 180 } } },
          }],
        },
      ],
    },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 },
        },
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              alignment: AlignmentType.RIGHT,
              spacing: { before: 0, after: 60 },
              children: [
                new TextRun({ text: "PROOFPILOT", bold: true, color: DARK_BLUE, size: 20, font: { name: "Bebas Neue" } }),
                new TextRun({ text: "  |  ", color: ELECTRIC_BLUE, size: 18, font: { name: "Calibri" } }),
                new TextRun({ text: workflowTitle.toUpperCase(), color: ELECTRIC_BLUE, size: 18, font: { name: "Calibri" } }),
              ],
            }),
            new Paragraph({
              spacing: { before: 0, after: 0 },
              border: {
                bottom: { color: ELECTRIC_BLUE, space: 1, style: BorderStyle.SINGLE, size: 6 },
              },
              children: [],
            }),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "ProofPilot  \u00b7  " + clientName + "  \u00b7  Page ", size: 16, color: MEDIUM_GRAY, font: { name: "Calibri" } }),
              new TextRun({ children: [PageNumber.CURRENT], size: 16, color: MEDIUM_GRAY, font: { name: "Calibri" } }),
              new TextRun({ text: " of ", size: 16, color: MEDIUM_GRAY, font: { name: "Calibri" } }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, color: MEDIUM_GRAY, font: { name: "Calibri" } }),
            ],
          })],
        }),
      },
      children,
    }],
  });

  return doc;
}

// ═══════════════════════════════════════════════════════════════════════
// ENTRY POINT
// ═══════════════════════════════════════════════════════════════════════
async function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error('Usage: node docx-generator.js <input.json> <output.docx>');
    process.exit(1);
  }

  const inputPath  = args[0];
  const outputPath = args[1];

  let jobData;
  try {
    jobData = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  } catch (err) {
    console.error('Failed to read input JSON:', err.message);
    process.exit(1);
  }

  const { content, client_name, workflow_title } = jobData;

  if (!content || !client_name || !workflow_title) {
    console.error('Input JSON must have content, client_name, workflow_title');
    process.exit(1);
  }

  try {
    const doc    = buildDocument(content, client_name, workflow_title);
    const buffer = await Packer.toBuffer(doc);
    fs.writeFileSync(outputPath, buffer);
    console.log('OK:' + outputPath);
  } catch (err) {
    console.error('DOCX generation failed:', err.message, err.stack);
    process.exit(1);
  }
}

main();
