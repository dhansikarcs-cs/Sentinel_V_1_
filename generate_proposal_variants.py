"""Render proposal markdown variants (250/500/1000 words) to clean PDFs."""

import os
import re
import sys

from fpdf import FPDF

OUTDIR = os.path.join(os.path.dirname(__file__), "docs")


def _ascii(text: str) -> str:
    return (
        text.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2082", "2")
        .replace("\u2265", ">=")
        .replace("\u2248", "~")
        .replace("\u00d7", "x")
        .replace("\u00b0", " deg ")
    )


class ProposalPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, "Sentinel Ecosystem - Proposal", align="C")
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def title_block(self, title, subtitle, wordcount):
        self.set_font("Helvetica", "B", 20)
        self.set_text_color(30, 30, 80)
        self.multi_cell(0, 11, title, align="C")
        self.ln(2)
        self.set_font("Helvetica", "", 12)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 7, subtitle, align="C")
        self.ln(2)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, f"Word count: {wordcount}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def section(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(30, 30, 80)
        self.multi_cell(0, 7, title)
        self.set_draw_color(30, 30, 80)
        self.line(self.l_margin, self.get_y() + 0.5, self.w - self.r_margin, self.get_y() + 0.5)
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def para(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(20, 20, 20)
        self.multi_cell(0, 5.6, text)
        self.ln(2)


def render(md_path: str, pdf_path: str, subtitle: str) -> int:
    text = open(md_path, encoding="utf-8").read()
    words = re.findall(r"[A-Za-z0-9]+[A-Za-z0-9'\-\u2019]*", text)
    pdf = ProposalPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    title = words_title = "The Sentinel Ecosystem"
    lines = text.splitlines()
    first = lines[0].strip()
    if first.startswith("# "):
        title = first[2:].strip()

    pdf.title_block(_ascii(title), subtitle, len(words))

    for line in lines[1:]:
        s = line.strip()
        if not s:
            continue
        if s.startswith("### "):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 5.6, _ascii(s[4:]))
            pdf.ln(1)
        elif s.startswith("## "):
            pdf.section(_ascii(s[3:]))
        elif s.startswith("# "):
            continue
        else:
            clean = re.sub(r"\*\*(.+?)\*\*\.", r"\1 - ", s)
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", clean)
            pdf.para(_ascii(clean))

    pdf.output(pdf_path)
    return len(words)


if __name__ == "__main__":
    md, out, sub = sys.argv[1], sys.argv[2], sys.argv[3]
    n = render(md, out, sub)
    print(f"{out} | words={n} | size={os.path.getsize(out)} bytes | pages={1}")
