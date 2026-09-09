"""Regenerate docs/sentinel_paper.pdf from docs/sentinel_paper.md.

Uses reportlab (platypus). Run from the repo root:
    python scripts/generate_paper_pdf.py
"""

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "sentinel_paper.md"
OUT = ROOT / "docs" / "sentinel_paper.pdf"


INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
    (re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)"), r"<i>\1</i>"),
    (re.compile(r"`([^`]+?)`"), r'<font face="Courier">\1</font>'),
]


def inline(text: str) -> str:
    for pattern, repl in INLINE:
        text = pattern.sub(repl, text)
    return text


def build_styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "SentinelTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        alignment=1,
        textColor=colors.HexColor("#1a232e"),
        spaceAfter=6,
    )
    subtitle = ParagraphStyle(
        "SentinelSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10.5,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#444444"),
    )
    h1 = ParagraphStyle(
        "SentinelH1",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=15,
        spaceBefore=16,
        spaceAfter=6,
        textColor=colors.HexColor("#123a2e"),
    )
    h2 = ParagraphStyle(
        "SentinelH2",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        spaceBefore=10,
        spaceAfter=4,
        textColor=colors.HexColor("#1e6f57"),
    )
    body = ParagraphStyle(
        "SentinelBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=12.6,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
    bullet = ParagraphStyle(
        "SentinelBullet",
        parent=body,
        leftIndent=14,
        firstLineIndent=0,
        bulletIndent=2,
        spaceAfter=3,
    )
    quote = ParagraphStyle(
        "SentinelQuote",
        parent=body,
        fontName="Helvetica-Oblique",
        leftIndent=16,
        textColor=colors.HexColor("#333333"),
    )
    small = ParagraphStyle("SentinelSmall", parent=body, fontSize=8.4, leading=11)
    return {
        "title": title,
        "subtitle": subtitle,
        "h1": h1,
        "h2": h2,
        "body": body,
        "bullet": bullet,
        "quote": quote,
        "small": small,
    }


def parse_table(rows):
    data = []
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        data.append(cells)
    return data


def main():
    text = SRC.read_text(encoding="utf-8")
    lines = text.splitlines()

    styles = build_styles()
    story = []

    def add_paragraph(text, style_name="body"):
        story.append(Paragraph(inline(text), styles[style_name]))

    # Title page: consume up to the first blank line after metadata.
    i = 0
    assert lines[i].startswith("# "), "expected title line"
    title_text = lines[i][2:].strip()
    i += 1
    meta = []
    while i < len(lines) and lines[i].strip() and not lines[i].startswith("---"):
        meta.append(lines[i].strip())
        i += 1
    story.append(Spacer(1, 2.5 * cm))
    story.append(Paragraph(title_text, styles["title"]))
    for m in meta:
        story.append(Paragraph(m, styles["subtitle"]))
    story.append(Spacer(1, 1.2 * cm))
    story.append(PageBreak())
    if i < len(lines) and lines[i].startswith("---"):
        i += 1

    table_start = None

    def flush_table():
        nonlocal table_start
        if table_start is None:
            return
        data = parse_table(table_start)
        ncols = max(len(r) for r in data)
        width = 16.8 * cm
        col_w = [width / ncols] * ncols
        t = Table(data, colWidths=col_w, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f1ec")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#123a2e")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9ab3a8")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(Spacer(1, 4))
        story.append(t)
        story.append(Spacer(1, 8))
        table_start = None

    for line in lines[i:]:
        line = line.rstrip()
        stripped = line.strip()
        if stripped.startswith("|"):
            if table_start is None:
                table_start = []
                # skip separator row like "|---|"
            if not set(
                stripped.replace("|", "").replace("-", "").replace(":", "").strip()
            ):
                continue
            table_start.append(stripped)
            continue
        flush_table()
        if not stripped or stripped == "---":
            continue
        if stripped == "<!-- pagebreak -->":
            story.append(PageBreak())
            continue
        if stripped.startswith("# "):
            story.append(PageBreak())
            story.append(Paragraph(inline(stripped[2:].strip()), styles["h1"]))
            continue
        if stripped.startswith("## "):
            name = stripped[3:].strip()
            story.append(Paragraph(inline(name), styles["h1"]))
            continue
        if stripped.startswith("### "):
            story.append(Paragraph(inline(stripped[4:].strip()), styles["h2"]))
            continue
        if stripped.startswith("- "):
            story.append(Paragraph(inline(stripped[2:]), styles["bullet"]))
            continue
        if stripped.startswith("> "):
            add_paragraph(stripped[2:], "quote")
            continue
        add_paragraph(stripped)  # body or small auto? keep body

    # Keep body styling throughout; disclosure/references render as body text.

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        title="Sentinel: An On-Premises Psychophysiological Triage Node",
        author="Sentinel Engineering Team",
        subject="Biomedical Engineering, 2026",
        leftMargin=1.9 * cm,
        rightMargin=1.9 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
    )

    def footer(canvas, docobj):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawCentredString(
            A4[0] / 2,
            0.9 * cm,
            "Sentinel — On-Premises Psychophysiological Triage Node",
        )
        canvas.drawRightString(A4[0] - 1.9 * cm, 0.9 * cm, str(docobj.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {doc.page} pages)")


if __name__ == "__main__":
    sys.exit(main())
