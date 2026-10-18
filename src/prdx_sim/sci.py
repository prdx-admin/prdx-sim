"""Figure style for the docs: a journal figure, not a dashboard.

The app's monospace (Atkinson Hyperlegible Mono, fonts/), Greek from DejaVu Sans Mono and STIX
Sans, thin frames with inward ticks on all four sides, no titles inside the
figure (captions live in figures/README.md), panel letters, a colour-blind-safe palette
(Okabe & Ito 2008), widths of one and two journal columns, PDF and PNG.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager

FONTS = Path(__file__).resolve().parents[2] / "fonts"
MONO = "Atkinson Hyperlegible Mono"

ONE_COL = 3.4  # inches
TWO_COL = 7.0

INK = "#1a1a1a"
GREY = "#8c8c8c"
LIGHT = "#d9d9d9"
# Okabe–Ito
BLUE = "#0072B2"
VERMILION = "#D55E00"
GREEN = "#009E73"
ORANGE = "#E69F00"
SKY = "#56B4E9"
PURPLE = "#CC79A7"
YELLOW = "#F0E442"
SERIES = [BLUE, VERMILION, GREEN, ORANGE, PURPLE, SKY, INK]
PROFIT, LOSS, EVEN = BLUE, VERMILION, GREY


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
    ax.annotate(f"({text})", (0, 1), xycoords="axes fraction", xytext=(0, pad),
                textcoords="offset points", fontweight="bold", fontsize=fs, va="bottom")
    if title:
        ax.annotate(title, (0, 1), xycoords="axes fraction", xytext=(5 * 0.6 * fs, pad),
                    textcoords="offset points", fontsize=fs, va="bottom")


def save(fig, out: Path, name: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight")
    path = out / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    return path
