"""
swd_charts.py: matplotlib chart helpers for the slide deck.

Rules follow Knaflic, Storytelling with Data (2015): grey base with one accent colour, direct labels,
no gridlines, no value axis when every mark is labelled, no pie/3-D/secondary axis, bars start at zero.
Charts carry no title: the slide's native action title does that job ("headerless twin").
Each figure is built at the size of its slide box, so font sizes are real points on the slide.
Labels are left-aligned at the figure's left edge so they line up with the slide margin.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager as fm
from matplotlib.colors import LinearSegmentedColormap

INK = "#262626"      # titles and text that must be read
GREY = "#595959"     # secondary text
BASE = "#8c8c8c"     # context data
MUTED = "#bfbfbf"    # axis lines, de-emphasised data
ACCENT = "#004c6d"   # the one "look here" colour
ACCENT_2 = "#f79545"  # adverse pole (fill/mark only: text next to it stays INK)

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
MIN_FONT_PT = 10


def use():
    """Install the font stack and strip gridlines/spines. Call once before any figure."""
    for f in ("Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf"):
        p = FONT_DIR / f
        if p.exists():
            fm.fontManager.addfont(str(p))
    plt.rcParams.update({
        "font.family": ["Arial", "DejaVu Sans"],
        "axes.grid": False,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.spines.bottom": False,
        "text.color": INK, "axes.labelcolor": GREY,
        "xtick.color": GREY, "ytick.color": GREY,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "font.size": 13,
    })


def minus(s):
    """Typographic minus sign for negative numbers."""
    return s.replace("-", "−")


def _measure(fig, labels, size, weights):
    """Width in inches of the widest label."""
    r = fig.canvas.get_renderer()
    w = 0.0
    for s, wt in zip(labels, weights):
        t = fig.text(0, 0, s, fontsize=size, fontweight=wt)
        w = max(w, t.get_window_extent(r).width)
        t.remove()
    return w / fig.dpi


def _new(w, h):
    fig = plt.figure(figsize=(w, h), dpi=100)
    fig.canvas.draw()
    return fig


def _place_axes(fig, label_w, right_pad=0.1, top=0.05, bottom=0.05, gap=0.2):
    """Axes start after the label column; labels sit at the figure's left edge."""
    W, H = fig.get_size_inches()
    left = (label_w + gap) / W if label_w > 0 else 0.0
    ax = fig.add_axes([left, bottom / H, 1 - left - right_pad / W, 1 - (top + bottom) / H])
    ax.set_facecolor("white")
    return ax


def check(fig):
    """Minimal lint: gridlines, tiny fonts, secondary axes. Returns a list of problems."""
    problems = []
    for ax in fig.axes:
        if any(g.get_visible() for g in ax.xaxis.get_gridlines() + ax.yaxis.get_gridlines()):
            problems.append("gridlines visible")
        for t in ax.texts:
            if t.get_fontsize() < MIN_FONT_PT:
                problems.append(f"font {t.get_fontsize()}pt < {MIN_FONT_PT}pt: {t.get_text()[:30]!r}")
    if len(fig.axes) > 1:
        problems.append("more than one axes (secondary axis?)")
    return problems


def save(fig, path):
    problems = check(fig)
    if problems:
        raise ValueError(f"{Path(path).name}: " + "; ".join(sorted(set(problems))))
    fig.savefig(path, dpi=200, facecolor="white")  # no bbox_inches: geometry must match the slide box
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------------------------
def hbar(path, size, labels, values, texts, highlight=(), xlim=None, label_size=13, text_size=13):
    """Horizontal bars, zero baseline, direct value labels, labels flush left. Top-to-bottom order = input order.

    highlight: labels drawn in ACCENT (others MUTED, with grey text). texts: value label per bar.
    """
    use()
    fig = _new(*size)
    hi = set(highlight)
    weights = ["bold" if (not hi or l in hi) else "normal" for l in labels]
    lw = _measure(fig, labels, label_size, weights)
    ax = _place_axes(fig, lw, right_pad=0.1)
    n = len(values)
    y = np.arange(n)[::-1]
    lo, hi_x = xlim
    span = hi_x - lo
    pad = 0.015 * span
    for yi, lab, v, tx in zip(y, labels, values, texts):
        on = (not hi) or lab in hi
        ax.barh(yi, v, height=0.56, color=ACCENT if on else MUTED, zorder=2)
        if v >= 0:
            ax.text(v + pad, yi, tx, ha="left", va="center", fontsize=text_size,
                    color=INK if on else BASE, fontweight="bold" if on else "normal")
        else:
            ax.text(v - pad, yi, tx, ha="right", va="center", fontsize=text_size,
                    color=INK if on else BASE, fontweight="bold" if on else "normal")
    ax.set_xlim(lo, hi_x)
    ax.set_ylim(-0.6, n - 0.4)
    ax.axvline(0, color=MUTED, lw=1.2, zorder=1)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.canvas.draw()
    for yi, lab in zip(y, labels):  # category labels flush left, after the final limits are set
        on = (not hi) or lab in hi
        yfig = ax.transData.transform((0, yi))[1] / (fig.dpi * fig.get_size_inches()[1])
        fig.text(0, yfig, lab, ha="left", va="center", fontsize=label_size,
                 fontweight="bold" if on else "normal", color=INK if on else GREY)
    return save(fig, path)


def rangeplot(path, size, labels, est, lo, hi, texts, highlight=(), xlim=(-12, 16), ticks=(-10, 0, 10),
              label_size=13, text_size=13, note=None):
    """Dot with whisker per row (estimate and interval), direct labels above each dot."""
    use()
    fig = _new(*size)
    hl = set(highlight)
    weights = ["bold" if l in hl else "normal" for l in labels]
    lw = _measure(fig, labels, label_size, weights)
    ax = _place_axes(fig, lw, right_pad=0.2, bottom=0.55 if note else 0.45, top=0.1)
    n = len(est)
    y = np.arange(n)[::-1]
    for yi, lab, e, a, b, tx in zip(y, labels, est, lo, hi, texts):
        on = lab in hl
        col = ACCENT if on else BASE
        ax.plot([a, b], [yi, yi], color=col, lw=4, solid_capstyle="butt", zorder=2)
        ax.plot([e], [yi], "o", color=col, ms=15, zorder=3, mec="white", mew=2)
        ax.text(e, yi + 0.3, tx, ha="center", va="bottom", fontsize=text_size, zorder=5,
                color=INK, fontweight="bold" if on else "normal",
                bbox=dict(facecolor="white", edgecolor="none", pad=2))
    ax.axvline(0, color=MUTED, lw=1.2, zorder=1)
    ax.set_xlim(*xlim)
    ax.set_ylim(-0.6, n - 0.2)
    ax.set_yticks([])
    ax.set_xticks(list(ticks))
    ax.tick_params(axis="x", length=0, labelsize=11, colors=BASE, pad=6)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(MUTED)
    fig.canvas.draw()
    if note:   # flush left with the labels, on the figure's bottom edge
        fig.text(0, 0.04 / fig.get_size_inches()[1], note, ha="left", va="bottom", fontsize=11, color=BASE)
    for yi, lab in zip(y, labels):
        on = lab in hl
        yfig = ax.transData.transform((0, yi))[1] / (fig.dpi * fig.get_size_inches()[1])
        fig.text(0, yfig, lab, ha="left", va="center", fontsize=label_size,
                 fontweight="bold" if on else "normal", color=INK if on else GREY)
    return save(fig, path)


def threshold_bars(path, size, labels, values, texts, thresholds, passing, xlim, text_x,
                   label_size=13, text_size=12, note=None):
    """Horizontal bars of a test statistic with reference lines; a text column to the right of the plot.

    thresholds: [(value, label, ha)]. passing: bool per bar (ACCENT when True, MUTED otherwise).
    """
    use()
    fig = _new(*size)
    weights = ["bold" if p else "normal" for p in passing]
    lw = _measure(fig, labels, label_size, weights)
    ax = _place_axes(fig, lw, right_pad=0.1, top=0.55, bottom=0.5 if note else 0.05)
    n = len(values)
    y = np.arange(n)[::-1]
    for yi, v, tx, p in zip(y, values, texts, passing):
        ax.barh(yi, v, height=0.5, color=ACCENT if p else MUTED, zorder=2)
        ax.text(text_x, yi, tx, ha="left", va="center", fontsize=text_size,
                color=INK if p else BASE, fontweight="bold" if p else "normal")
    for val, lab, ha in thresholds:
        ax.axvline(val, ymax=0.93, color=BASE, lw=1.3, zorder=1)
    ax.set_xlim(*xlim)
    ax.set_ylim(-0.6, n - 0.2)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axvline(0, color=MUTED, lw=1.2, zorder=1)
    fig.canvas.draw()
    for val, lab, ha in thresholds:
        off = -0.03 * (xlim[1] - xlim[0]) if ha == "right" else 0.03 * (xlim[1] - xlim[0])
        ax.text(val + off, n - 0.2 + 0.05, lab, ha=ha, va="bottom", fontsize=11, color=GREY, clip_on=False)
    if note:
        ax.text(xlim[0], -0.6 - 0.2, note, ha="left", va="top", fontsize=11, color=BASE, clip_on=False)
    for yi, p, lab in zip(y, passing, labels):
        yfig = ax.transData.transform((0, yi))[1] / (fig.dpi * fig.get_size_inches()[1])
        fig.text(0, yfig, lab, ha="left", va="center", fontsize=label_size,
                 fontweight="bold" if p else "normal", color=INK if p else GREY)
    return save(fig, path)


def waterfall(path, size, labels, values, kinds, colors, texts, ylim, label_size=12, text_size=14):
    """Vertical waterfall: 'total' bars stand on zero, 'step' bars float. One text label above each bar."""
    use()
    fig = _new(*size)
    ax = _place_axes(fig, 0, right_pad=0.1, top=0.1, bottom=0.95)
    run = 0.0
    tops = []
    for i, (v, k, c, tx) in enumerate(zip(values, kinds, colors, texts)):
        if k == "total":
            bottom, height = 0, v
            run = v
        else:
            bottom, height = run + v, -v  # v negative: bar spans [run+v, run]
            run = run + v
        top = bottom + height
        ax.bar(i, height if height != 0 else 0.0001, bottom=bottom, width=0.62, color=c, zorder=2)
        tops.append((top, bottom))
        ax.text(i, top + 0.012 * (ylim[1] - ylim[0]), tx, ha="center", va="bottom", fontsize=text_size,
                fontweight="bold", color=INK)
    for i in range(len(values) - 1):  # connectors
        level = tops[i][1] if kinds[i] == "step" else tops[i][0]
        ax.plot([i + 0.31, i + 1 - 0.31], [level, level], color=MUTED, lw=1.1, zorder=1)
    ax.set_xlim(-0.55, len(values) - 0.45)
    ax.set_ylim(*ylim)
    ax.set_yticks([])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=label_size, color=GREY)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.axhline(0, color=MUTED, lw=1.2, zorder=1)
    return save(fig, path)


def lineplot(path, size, x, y, split_after, end_labels, ylim, note=None, label_size=12, text_size=13):
    """One line, first segment (retrospective data) in MUTED dashes, the rest in ACCENT, labelled points.

    split_after: index of the last point of the first segment. end_labels: {index: text}.
    """
    use()
    fig = _new(*size)
    ax = _place_axes(fig, 0, right_pad=0.2, top=0.2, bottom=0.55)
    k = split_after
    ax.plot(x[: k + 1], y[: k + 1], color=BASE, lw=2.5, ls=(0, (4, 3)), zorder=2)
    ax.plot(x[k:], y[k:], color=ACCENT, lw=3, zorder=3)
    ax.plot(x, y, "o", color="white", mec=BASE, mew=1.5, ms=7, zorder=4)
    ax.plot(x[k + 1:], y[k + 1:], "o", color="white", mec=ACCENT, mew=2, ms=7, zorder=5)
    for i, tx in end_labels.items():
        dy = 0.35
        ax.text(x[i], y[i] + dy, tx, ha="center", va="bottom", fontsize=text_size, fontweight="bold", color=INK)
    ax.set_ylim(*ylim)
    ax.set_xlim(min(x) - 0.4, max(x) + 0.4)
    ax.set_yticks([])
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(v) for v in x], fontsize=label_size, color=GREY)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(MUTED)
    if note:
        for xi, yi, tx, ha in note:
            ax.text(xi, yi, tx, ha=ha, va="center", fontsize=11, color=GREY)
    return save(fig, path)


def heatmap(path, size, names, mat, texts, label_size=12, text_size=12):
    """Lower-triangle matrix, one hue by |value|, signed values printed in each cell."""
    use()
    fig = _new(*size)
    n = len(names)
    lw = _measure(fig, names, label_size, ["normal"] * n)
    ax = _place_axes(fig, lw, right_pad=0.1, top=0.1, bottom=0.45)
    cmap = LinearSegmentedColormap.from_list("one_hue", ["#ffffff", "#c1e7ff", "#7aa6c2", "#004c6d"])
    for i in range(n):
        for j in range(n):
            if j > i:
                continue
            v = mat[i][j]
            c = cmap(min(abs(v), 1.0)) if i != j else "#f2f2f2"
            ax.add_patch(plt.Rectangle((j, n - 1 - i), 1, 1, facecolor=c, edgecolor="white", lw=2))
            dark = abs(v) >= 0.5 and i != j
            ax.text(j + 0.5, n - 1 - i + 0.5, texts[i][j], ha="center", va="center", fontsize=text_size,
                    color="white" if dark else INK, fontweight="bold" if abs(v) >= 0.5 else "normal")
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_xticks([j + 0.5 for j in range(n)])
    ax.set_xticklabels(names, fontsize=label_size, color=GREY)
    ax.tick_params(axis="x", length=0, pad=6)
    ax.set_yticks([])
    fig.canvas.draw()
    for i, nm in enumerate(names):
        yfig = ax.transData.transform((0, n - 1 - i + 0.5))[1] / (fig.dpi * fig.get_size_inches()[1])
        fig.text(0, yfig, nm, ha="left", va="center", fontsize=label_size, color=GREY)
    return save(fig, path)
