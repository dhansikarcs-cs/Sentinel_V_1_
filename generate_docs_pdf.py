"""Generate all three judge prep documents as PDFs."""

from fpdf import FPDF
from fpdf.enums import XPos
import os, re

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__))

def sanitize(t):
    t = t.encode("ascii", "replace").decode("ascii")
    return t

def md_to_pdf(md_path, pdf_path, title, subtitle=""):
    """Convert markdown to styled PDF. Handles headers, bold, code, tables."""
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    pdf = FPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    def mc(w, h, txt, **kw):
        """multi_cell helper that resets X to left margin."""
        pdf.multi_cell(w, h, txt, new_x=XPos.LMARGIN, **kw)

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 30, 80)
    mc(0, 10, title, align="C")
    if subtitle:
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(80, 80, 80)
        for subline in subtitle.split("\n"):
            pdf.cell(0, 7, subline.strip(), align="C")
            pdf.ln(7)
    pdf.ln(4)
    pdf.set_draw_color(30, 30, 80)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)
    pdf.set_text_color(0, 0, 0)

    def write_body(text, size=10, bold=False):
        pdf.set_font("Helvetica", "B" if bold else "", size)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'`(.+?)`', r'\1', text)
        mc(0, 5.5 if size == 10 else 5, text)

    def write_table_row(cols, widths, header=False):
        pdf.set_font("Helvetica", "B" if header else "", 8)
        for i, c in enumerate(cols[:len(widths)]):
            pdf.cell(widths[i], 5, str(c)[:80], border=1, align="L")
        pdf.ln()

    skip_until = None
    in_table = False
    table_cols = []
    table_widths = []

    for i, line in enumerate(lines):
        raw = sanitize(line.rstrip())

        if skip_until:
            if raw.startswith(skip_until):
                skip_until = None
            continue

        # Skip TOC entries (numbered or bulleted links)
        if raw.startswith("- [") or re.match(r'^\d+\.\s*\[', raw):
            continue

        # Heading 1: #
        if raw.startswith("# ") and not raw.startswith("##"):
            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(30, 30, 80)
            pdf.ln(2)
            mc(0, 8, sanitize(raw[2:].replace("**", "").replace("`", "")))
            pdf.set_draw_color(30, 30, 80)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
            pdf.ln(3)
            pdf.set_text_color(0, 0, 0)
            continue

        # Heading 2: ##
        if raw.startswith("## ") and not raw.startswith("###"):
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(50, 50, 50)
            pdf.ln(1)
            mc(0, 7, raw[3:])
            pdf.ln(1)
            pdf.set_text_color(0, 0, 0)
            continue

        # Heading 3: ###
        if raw.startswith("### "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(60, 60, 60)
            pdf.ln(1)
            mc(0, 6, raw[4:])
            pdf.ln(1)
            pdf.set_text_color(0, 0, 0)
            continue

        # Heading 4: ####
        if raw.startswith("#### "):
            pdf.set_font("Helvetica", "BI", 10)
            pdf.set_text_color(70, 70, 70)
            mc(0, 6, raw[5:])
            pdf.ln(1)
            pdf.set_text_color(0, 0, 0)
            continue

        # Table separator
        if "|" in raw and all(c in "|-:" for c in raw.replace(" ", "")):
            in_table = True
            continue

        # Table row
        if in_table and raw.startswith("|"):
            cells = [c.strip() for c in raw.split("|")[1:-1]]
            if not table_widths:
                n = len(cells)
                table_widths = [max(15, int(170 / n)) for _ in range(n)]
            is_header = not in_table
            if not any("---" in c for c in cells):
                write_table_row(cells, table_widths, header=not in_table)
            in_table = False
            continue
        if raw.startswith("---"):
            in_table = False
            continue

        # Bullet point
        if raw.startswith("- "):
            text = raw[2:]
            if text.startswith("**"):
                pdf.set_font("Helvetica", "B", 10)
                text = text[2:-2] if text.endswith("**") else text[2:]
            else:
                pdf.set_font("Helvetica", "", 10)
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'`(.+?)`', r'\1', text)
            x = pdf.get_x()
            pdf.cell(5, 5.5, "-")
            mc(0, 5.5, text)
            continue

        # Numbered list
        if re.match(r'^\d+\.\s', raw):
            pdf.set_font("Helvetica", "", 10)
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', raw)
            text = re.sub(r'`(.+?)`', r'\1', text)
            text = text.strip()
            if text:
                try:
                    mc(0, 5.5, text)
                except Exception as e:
                    print(f"ERROR numbered line {i+1}: full={text!r}")
                    import sys; sys.stdout.flush()
                    raise
            continue

        # Blank line or empty after sanitize
        if not raw or not raw.strip():
            pdf.ln(2)
            continue

        # Regular body text
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', raw)
        text = re.sub(r'`(.+?)`', r'\1', text)
        text = text.strip()
        if text:
            try:
                pdf.set_font("Helvetica", "", 10)
                mc(0, 5.5, text)
            except Exception as e:
                print(f"ERROR line {i+1}: '{text[:100]}' -> {e}")
                raise

    pdf.output(pdf_path)
    return pdf.page_no()


# Generate all PDFs
docs = [
    ("TECHNICAL_DESIGN.md", "sentinel_technical_design.pdf", "Sentinel: Technical Design Document",
     "Engineering Decisions, Alternatives, and Trade-offs\nFor Samsung Solve for Tomorrow  IRIS  ISEF"),
    ("JUDGE_QA.md", "sentinel_judge_qa.pdf", "Sentinel: Judge Q&A Preparation",
     "Every Possible Question  With Answers\nFor Samsung Solve for Tomorrow  IRIS  ISEF"),
    ("ENGINEERING_DECISIONS.md", "sentinel_engineering_decisions.pdf", "Sentinel: Engineering Decisions Log",
     "Every Key Decision, Alternative, and Trade-off\nFor Samsung Solve for Tomorrow  IRIS  ISEF"),
    ("ROADMAP_HARDWARE.md", "sentinel_roadmap_hardware.pdf", "Sentinel: Hardware Roadmap",
     "OEM Ring Procurement + Integration Plan (M1-M3)\nFor Samsung Solve for Tomorrow  IRIS  ISEF"),
    ("ENGINEERING_LOGBOOK.md", os.path.join("docs", "ENGINEERING_LOGBOOK.pdf"), "Sentinel: Engineering Logbook",
     "Build Narrative with Timestamps\nFor Samsung Solve for Tomorrow  IRIS  ISEF"),
]

for md_name, pdf_name, title, subtitle in docs:
    md_path = os.path.join(DOCS_DIR, md_name)
    pdf_path = os.path.join(OUTPUT_DIR, pdf_name)
    if os.path.exists(md_path):
        pages = md_to_pdf(md_path, pdf_path, title, subtitle)
        size = os.path.getsize(pdf_path)
        print(f"{pdf_name}: {size:,} bytes, {pages} pages")
    else:
        print(f"SKIP {md_name}: not found")
