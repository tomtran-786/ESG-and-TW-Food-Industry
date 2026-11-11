"""
deck_lib.py: one slide spec, two renderings.

  live  -> .pptx for the room: action title + chart/table + callouts; narration in the speaker notes.
  read  -> .pptx with a taller page for the PDF: the same slide on top, the takeaway and the narration printed
           beneath it, so the deck still works when it is forwarded without the presenter.

Both renderings call the same `body` function of each Slide, so they cannot drift apart.
Layout: 16:9, one left edge (LM) for kicker, title, body, footnote.
"""
from dataclasses import dataclass
from typing import Callable

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

W, H_LIVE, H_READ = 13.333, 7.5, 10.7
LM = 0.6
CW = W - 2 * LM
BODY_TOP, BODY_BOTTOM = 1.95, 6.8
FONT = "Arial"

INK, GREY, BASE, MUTED = "262626", "595959", "8C8C8C", "BFBFBF"
ACCENT, ACCENT_2, PANEL = "004C6D", "F79545", "F2F2F2"


def _rgb(h):
    return RGBColor.from_string(h.lstrip("#").upper())


@dataclass
class Slide:
    kicker: str
    title: str
    body: Callable      # body(ctx) draws the slide content; used by both renderings
    takeaway: str       # one sentence, printed on the page in the read rendering
    narration: str      # speaker notes (live) and printed under the takeaway (read)
    source: str = ""
    kind: str = "content"   # "title" | "content"
    section: str = ""       # "Introduction" | "Methods" | "Results" | "Discussion" | "Appendix" | "" (summary)


# ----------------------------------------------------------------------------- text primitives
def _fill_paragraph(p, para, size, color, bold, align, line_spacing, space_after, bullet):
    """para: str | list of runs | dict(runs=..., bullet=..., size=..., color=..., bold=..., space_after=...)."""
    if isinstance(para, dict):
        opts = para
        runs = opts.get("runs", opts.get("text", ""))
        size = opts.get("size", size)
        color = opts.get("color", color)
        bold = opts.get("bold", bold)
        space_after = opts.get("space_after", space_after)
        bullet = opts.get("bullet", bullet)
        align = opts.get("align", align)
    else:
        runs = para
    if isinstance(runs, (str, tuple)):
        runs = [runs]
    p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
    p.line_spacing = line_spacing
    p.space_after = Pt(space_after)
    for run in runs:
        text, o = (run, {}) if isinstance(run, str) else run
        if text == "":
            continue
        r = p.add_run()
        r.text = text
        f = r.font
        f.name = FONT
        f.size = Pt(o.get("s", size))
        f.bold = o.get("b", bold)
        f.italic = o.get("i", False)
        f.color.rgb = _rgb(o.get("c", color))
        rPr = r._r.get_or_add_rPr()
        if o.get("sub"):
            rPr.set("baseline", "-25000")
        if o.get("sup"):
            rPr.set("baseline", "30000")
        if o.get("spc"):
            rPr.set("spc", str(o["spc"]))
    if bullet:
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(int(Inches(0.24))))
        pPr.set("indent", str(-int(Inches(0.24))))
        clr = etree.SubElement(pPr, qn("a:buClr"))
        etree.SubElement(clr, qn("a:srgbClr"), val=ACCENT)
        etree.SubElement(pPr, qn("a:buFont"), typeface=FONT)
        etree.SubElement(pPr, qn("a:buChar"), char="•")


def add_text(slide, x, y, w, h, paras, size=14, color=INK, bold=False, align="l", anchor="t",
             line_spacing=1.05, space_after=0, bullet=False):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    if isinstance(paras, (str, tuple)):
        paras = [paras]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        _fill_paragraph(p, para, size, color, bold, align, line_spacing, space_after, bullet)
    return tb


def add_rect(slide, x, y, w, h, fill=None, line=None, line_w=0.75):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    style = s._element.find(qn("p:style"))   # the theme style carries a drop shadow; fill and line are set explicitly
    if style is not None:
        s._element.remove(style)
    if fill:
        s.fill.solid()
        s.fill.fore_color.rgb = _rgb(fill)
    else:
        s.fill.background()
    if line:
        s.line.color.rgb = _rgb(line)
        s.line.width = Pt(line_w)
    else:
        s.line.fill.background()
    return s


def add_picture(slide, path, x, y, w, h, alt):
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(w), height=Inches(h))
    pic._element.nvPicPr.cNvPr.set("descr", alt)
    return pic


def _border(cell, top=None, bottom=None):
    """top/bottom = (hex, pt). Borders go first in tcPr (schema order: lnL lnR lnT lnB ... fill)."""
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnT", "a:lnB"):
        old = tcPr.find(qn(tag))
        if old is not None:
            tcPr.remove(old)
    made = []
    for tag, spec in (("a:lnT", top), ("a:lnB", bottom)):
        if not spec:
            continue
        color, pt = spec
        ln = etree.Element(qn(tag), w=str(int(pt * 12700)), cap="flat", cmpd="sng", algn="ctr")
        sf = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(sf, qn("a:srgbClr"), val=color)
        etree.SubElement(ln, qn("a:prstDash"), val="solid")
        made.append(ln)
    for ln in reversed(made):
        tcPr.insert(0, ln)


def add_table(slide, x, y, col_w, rows, row_h=0.3, size=11, align=None, header_rows=1, bold_rows=(),
              accent_rows=(), muted_rows=(), rule_after=(), panel_rows=(), alt="table"):
    """rows: list of lists; a cell is str or a list of runs. align: per-column 'l'|'c'|'r'.
    rule_after: row indexes that get a thin rule beneath. accent_rows: ACCENT bold text. panel_rows: label rows."""
    nr, nc = len(rows), len(col_w)
    gf = slide.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(sum(col_w)), Inches(row_h * nr))
    gf._element.nvGraphicFramePr.cNvPr.set("descr", alt)
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "0")
    tblPr.set("bandRow", "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = etree.SubElement(tblPr, qn("a:tableStyleId"))
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # No Style, No Grid
    align = align or ["l"] + ["r"] * (nc - 1)
    for j, w in enumerate(col_w):
        tbl.columns[j].width = Inches(w)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(row_h)
        for j in range(nc):
            val = row[j] if j < len(row) else ""
            cell = tbl.cell(i, j)
            cell.fill.background()
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.015)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            is_head = i < header_rows
            color = ACCENT if i in accent_rows else (BASE if i in muted_rows else INK)
            bold = is_head or i in bold_rows or i in accent_rows or i in panel_rows
            _fill_paragraph(cell.text_frame.paragraphs[0], val, size, color, bold, align[j], 1.0, 0, False)
            top = (INK, 1.0) if i == 0 else None
            bottom = None
            if i == header_rows - 1:
                bottom = (INK, 0.75)
            elif i in rule_after:
                bottom = (MUTED, 0.5)
            elif i == nr - 1:
                bottom = (INK, 1.0)
            _border(cell, top, bottom)
    return gf


# ----------------------------------------------------------------------------- drawing context
class Ctx:
    """What a slide body may draw with. Coordinates are in inches on the 13.333 x 7.5 slide."""

    def __init__(self, slide):
        self.slide = slide

    def text(self, x, y, w, h, paras, **kw):
        return add_text(self.slide, x, y, w, h, paras, **kw)

    def pic(self, path, x, y, w, h, alt):
        return add_picture(self.slide, path, x, y, w, h, alt)

    def table(self, x, y, col_w, rows, **kw):
        return add_table(self.slide, x, y, col_w, rows, **kw)

    def rect(self, *a, **kw):
        return add_rect(self.slide, *a, **kw)

    def callout(self, x, y, w, h, big, text, big_size=28, color=ACCENT, text_size=13):
        """Accent bar, one big number or phrase, one caption. Replaces animation: the annotation is always on the slide."""
        add_rect(self.slide, x, y, 0.06, h, fill=color)
        avail = w - 0.25
        while len(big) * big_size / 72 * 0.56 > avail and big_size > 16:   # keep the big phrase on one line
            big_size -= 1
        add_text(self.slide, x + 0.22, y - 0.02, w - 0.22, 0.55, [[(big, {"b": True})]], size=big_size, color=INK,
                 line_spacing=0.95)
        add_text(self.slide, x + 0.22, y + big_size / 72 * 1.25, w - 0.22, h - big_size / 72 * 1.25, text,
                 size=text_size, color=GREY, line_spacing=1.08)

    def card(self, x, y, w, h, head, body, head_color=ACCENT, fill=PANEL, head_size=20, body_size=14, body_dy=0.8):
        add_rect(self.slide, x, y, w, h, fill=fill)
        add_rect(self.slide, x, y, w, 0.07, fill=head_color)
        add_text(self.slide, x + 0.3, y + 0.28, w - 0.6, 0.5, head, size=head_size, color=INK, bold=True,
                 line_spacing=1.0)
        add_text(self.slide, x + 0.3, y + body_dy, w - 0.6, h - body_dy - 0.15, body, size=body_size, color=GREY,
                 line_spacing=1.1, space_after=7)


# ----------------------------------------------------------------------------- rendering
def _title_placeholder(slide, text, x, y, w, h, size, color=INK):
    t = slide.shapes.title
    t.left, t.top, t.width, t.height = Inches(x), Inches(y), Inches(w), Inches(h)
    tf = t.text_frame
    tf.word_wrap = True
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.TOP
    p = tf.paragraphs[0]
    _fill_paragraph(p, [(text, {"b": True})], size, color, True, "l", 0.95, 0, False)


SECTIONS = ["Introduction", "Methods", "Results", "Discussion"]


def _tracker(ctx, current):
    """Where we are in the IMRD sequence: the current section in accent, the others in grey (top right)."""
    if current == "Appendix":
        runs = [("APPENDIX", {"b": True, "c": ACCENT, "spc": 120})]
    else:
        runs = []
        for k, name in enumerate(SECTIONS):
            on = name == current
            runs.append((name.upper(), {"b": on, "c": ACCENT if on else BASE, "spc": 120}))
            if k < len(SECTIONS) - 1:
                runs.append(("    ", {}))
    ctx.text(W - LM - 7.0, 0.38, 7.0, 0.25, [runs], size=10.5, align="r")


def _footer(ctx, s, i, n):
    if s.source:
        ctx.text(LM, 6.98, 10.9, 0.3, s.source, size=10, color=BASE)
    ctx.text(W - LM - 1.0, 6.98, 1.0, 0.3, f"{i} / {n}", size=10, color=BASE, align="r")


def _read_zone(ctx, s):
    ctx.rect(LM, 7.62, CW, 0.012, fill=MUTED)
    ctx.text(LM, 7.8, 3, 0.25, [[("TAKEAWAY", {"b": True, "spc": 120})]], size=10, color=ACCENT)
    ctx.text(LM, 8.08, CW, 0.75, [[(s.takeaway, {"b": True})]], size=16, color=INK, line_spacing=1.05)
    ctx.text(LM, 8.92, CW, 1.6, s.narration, size=12.5, color=GREY, line_spacing=1.12)


def render(slides, path, mode="live", doc_title="", author=""):
    assert mode in ("live", "read")
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H_LIVE if mode == "live" else H_READ)
    n = len(slides)
    for i, s in enumerate(slides, 1):
        slide = prs.slides.add_slide(prs.slide_layouts[5])  # "Title Only": keeps a real title for outline view
        ctx = Ctx(slide)
        if s.kind == "title":
            ctx.rect(LM, 1.55, 0.9, 0.09, fill=ACCENT)
            _title_placeholder(slide, s.title, LM, 1.9, 11.4, 2.2, 40)
            s.body(ctx)
        else:
            ctx.text(LM, 0.38, 9, 0.25, [[(s.kicker.upper(), {"b": True, "spc": 120})]], size=11, color=ACCENT)
            _title_placeholder(slide, s.title, LM, 0.68, CW, 1.15, 24)
            _tracker(ctx, s.section)
            s.body(ctx)
            _footer(ctx, s, i, n)
        if mode == "read":
            _read_zone(ctx, s)
        slide.notes_slide.notes_text_frame.text = s.narration
    prs.core_properties.title = doc_title
    prs.core_properties.author = author
    prs.save(str(path))
    return path
