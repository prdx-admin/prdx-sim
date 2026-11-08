"""Figure style for the docs: a journal figure, not a dashboard.

The app's monospace (Atkinson Hyperlegible Mono, fonts/), Greek from DejaVu Sans Mono and STIX
Sans, thin frames with inward ticks on all four sides, no titles inside the
figure (captions live in figures/README.md), panel letters, the app's five tones (prdx-front
src/styles.css), one quantity each, with ink and grey, widths of one and two journal columns, PDF and PNG.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap

FONTS = Path(__file__).resolve().parents[2] / "fonts"
MONO = "Atkinson Hyperlegible Mono"

ONE_COL = 3.4  # inches
TWO_COL = 7.0

INK = "#1a1a1a"
GREY = "#8c8c8c"
LIGHT = "#d9d9d9"
# The five tones of the app (prdx-front src/styles.css), at a lightness that reads on white. A tone names
# one quantity in every figure, as the app names an operation:
#   mine  tickets and miners (Bob)           mint  the reserve G, the mint fee
#   burn  the price and the burned share     gold  holders (Alice): their growth y and premium
#   coral below zero
# Ink and grey carry the rest: a twin, a model without feedback, a formula.
MINE = "#573bab"
MINT = "#007141"
BURN = "#0096af"
GOLD = "#958000"
CORAL = "#ed756e"

# The steps of each tone, highlight to deep (the app's highlight, light, shadow and deep; gold's deep end is
# the olive of its line, not the app's green, so that it does not meet mint).
STEPS = {
    MINE: ["#eae6ff", "#ada0fe", "#695ae0", "#221b66"],
    MINT: ["#c8fae1", "#89ecb9", "#239f6f", "#123e33"],
    BURN: ["#c0f7f9", "#80e8ed", "#0a82aa", "#0c2b46"],
    GOLD: ["#f4ecc2", "#e5d68b", "#958000", "#3d3500"],
}


def cmap(tone: str) -> LinearSegmentedColormap:
    """An ordered scale in one tone, highlight to deep."""
    return LinearSegmentedColormap.from_list(f"prdx-{tone}", STEPS[tone])


# A heat map with a number in every cell: the light half of a tone, so ink reads on every cell at a
# contrast of 5:1 or more.
HEAT = {
    MINE: ["#f6f4ff", "#d0c9fe", "#ada0fe", "#8a7bf2"],
    MINT: ["#f3fdf8", "#c8fae1", "#89ecb9", "#4fc98e"],
    BURN: ["#f2fdfd", "#c0f7f9", "#80e8ed", "#3fc6d6"],
}


def heat(tone: str) -> LinearSegmentedColormap:
    return LinearSegmentedColormap.from_list(f"prdx-heat-{tone}", HEAT[tone])


# A signed quantity of holders: coral below zero, gold above, near-white at zero.
SIGNED_CMAP = LinearSegmentedColormap.from_list(
    "prdx-signed", ["#cd2a48", "#ffbeba", "#f6f6f6", "#e5d68b", "#958000"])


def ramp(k: int, lo: float = 0.3, hi: float = 1.0, tone: str = MINE) -> list:
    """k colours of one tone, light to dark; `lo` keeps the lightest visible on white."""
    import numpy as np
    return list(cmap(tone)(np.linspace(lo, hi, k)))


def apply() -> None:
    for f in FONTS.glob("*.ttf"):
        font_manager.fontManager.addfont(str(f))
    mpl.rcParams.update({
        "font.family": [MONO, "DejaVu Sans Mono"],
        "font.weight": "light",
        "mathtext.fontset": "custom",
        "mathtext.rm": MONO,
        "mathtext.it": MONO,
        "mathtext.bf": f"{MONO}:bold",
        "mathtext.fallback": "stixsans",
        "font.size": 7.5,
        "axes.labelsize": 7.5,
        "axes.titlesize": 7.5,
        "axes.titleweight": "light",
        "legend.fontsize": 6.8,
        "xtick.labelsize": 6.8,
        "ytick.labelsize": 6.8,
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.edgecolor": INK,
        "axes.linewidth": 0.6,
        "axes.spines.top": True,
        "axes.spines.right": True,
        "axes.grid": False,
        "axes.titlelocation": "left",
        "axes.titlepad": 4,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.minor.size": 1.6,
        "ytick.minor.size": 1.6,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.minor.width": 0.4,
        "ytick.minor.width": 0.4,
        "xtick.color": INK,
        "ytick.color": INK,
        "lines.linewidth": 1.1,
        "lines.markersize": 3,
        "legend.frameon": False,
        "legend.handlelength": 1.8,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": 300,
        "pdf.fonttype": 42,
    })


def letter(ax, text: str, title: str | None = None, pad: float = 3) -> None:
    """Panel letter in bold and an optional subtitle after it: (a)  LVL 4. The font is
    monospaced, so the subtitle starts five character widths after the letter. `pad` lifts both
    above the frame, in points: a panel with tick labels on top needs it above them."""
    fs = mpl.rcParams["axes.titlesize"]
    if text:
        ax.annotate(f"({text})", (0, 1), xycoords="axes fraction", xytext=(0, pad),
                    textcoords="offset points", fontweight="bold", fontsize=fs, va="bottom")
    if title:
        # a panel without a letter (a later panel of a row of small multiples) starts its title at the frame
        ax.annotate(title, (0, 1), xycoords="axes fraction", xytext=(5 * 0.6 * fs if text else 0, pad),
                    textcoords="offset points", fontsize=fs, va="bottom")


def save(fig, out: Path, name: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight")
    path = out / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    return path
