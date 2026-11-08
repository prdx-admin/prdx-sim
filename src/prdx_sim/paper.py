# SPDX-License-Identifier: MIT
# Copyright (c) 2025-2026 prdx-admin
"""Figures in the journal style (`sci.py`). Captions: figures/README.md.

python -m prdx_sim.paper [outdir] [names...]
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FixedLocator, FuncFormatter, LogLocator, NullFormatter

from prdx_sim import experiments as ex
from prdx_sim import sci
from prdx_sim.protocol import Params


# The numbers the docs quote, by figure: each figure stores what its caption and text cite, and main
# writes them to figures/numbers.json, so a sentence is checked against the run that drew the figure.
QUOTES: dict[str, object] = {}


def quote(key: str, value) -> None:
    """Store a cited value, rounded to four significant digits."""
    def r(v):
        if isinstance(v, (list, tuple, np.ndarray)):
            return [r(x) for x in v]
        if isinstance(v, dict):
            return {k: r(x) for k, x in v.items()}
        v = float(v)
        return float(f"{v:.4g}") if np.isfinite(v) else None
    QUOTES[key] = r(value)


def _mult(v, _=None) -> str:
    if v >= 1e3:
        return rf"$10^{{{int(round(np.log10(v)))}}}$"
    return f"{v:g}"


def _mult_down(v) -> str:
    """A power of ten below one: 10^-2, 10^-4."""
    return rf"$10^{{{int(round(np.log10(v)))}}}$"


def _pct(v, _=None) -> str:
    return f"{v * 100:g}%"


def _share(v: float) -> str:
    """A share as a percent, two significant digits under 10 %, none under 0.1 %."""
    if v == 0:
        return "0"
    if v < 0.001:
        return "<0.1%"
    return f"{v * 100:.1f}%" if v < 0.1 else f"{v * 100:.0f}%"


def fig_tickets(rng, params: Params, out: Path) -> Path:
    """The exact chance of every rung of a one-draw ticket, by level. The law is exact (2^-k, the top
    rung as often as the one below it), so no sample is drawn: a sample of any size shows the rare
    rungs of a high level as noise."""
    lvls = [2, 4, 8, 12, 16, 24]
    fig, axes = plt.subplots(2, 3, figsize=(sci.TWO_COL, 3.9), sharey=True)
    for i, (ax, n) in enumerate(zip(axes.ravel(), lvls)):
        k, p = ex.single_draw_pmf(n)
        pay = ex.entry_for(1.0, n, 1, params.rtp) * 2.0 ** (k - 1)
        # a payout above the deposit in the accent, below it grey
        colour = np.where(pay > 1 + 1e-9, sci.MINE, sci.GREY)
        ax.vlines(pay, 1e-9, p, color=colour, lw=2.2 if n <= 8 else 1.4)
        ax.axvline(1, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylim(3e-8, 1.5)
        ax.set_xlim(pay[0] / 1.8, pay[-1] * 1.8)
        ax.xaxis.set_major_locator(LogLocator(base=10 if pay[-1] < 1e3 else 100))
        ax.xaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10) * 0.1, numticks=50))
        ax.xaxis.set_major_formatter(FuncFormatter(_mult))
        if pay[-1] < 10:
            ax.xaxis.set_major_locator(FixedLocator([0.2, 0.5, 1, 2, 5]))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_locator(FixedLocator([1e-6, 1e-4, 1e-2, 1]))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: "1" if v == 1 else _mult_down(v)))
        ax.yaxis.set_minor_formatter(NullFormatter())
        above = p[pay > 1 + 1e-9].sum()
        quote(f"lvl{n}", {"p_above_deposit": above, "max_per_deposit": pay[-1], "p_max": p[-1]})
        sci.letter(ax, "abcdef"[i], f"LVL {n}   P(X>D) = {above * 100:g}%")
    for ax in axes[1]:
        ax.set_xlabel(r"payout per deposit, $X/D$")
    for ax in axes[:, 0]:
        ax.set_ylabel("chance")
    fig.tight_layout(pad=0.4, w_pad=0.8, h_pad=0.9)
    return sci.save(fig, out, "fig-tickets")


# fig-price (a): the example of docs section 6, a supply of 100 000 PRDX and tickets of 10 PRDX, until
# the tickets have taken twice the supply. The cap admits
# LVL 14 at the start and LVL 13 at the end of the stream; it is enforced ticket by ticket.
PRICE_SUPPLY = 100_000
PRICE_TICKET = 10
PRICE_LEVELS = (4, 8, 12)
PRICE_VOLUME = 2.0


def _count(v, _=None) -> str:
    """A ticket count, compact: 66, 333, 3.3k, 50k, 1M, 20M."""
    for div, unit in ((1e6, "M"), (1e3, "k"), (1, "")):
        if v >= div or div == 1:
            g = v / div
            return (f"{g:.0f}" if g >= 10 or g == int(g) else f"{g:.2g}") + unit
    return ""


def _prdx(v: float) -> str:
    """An amount of PRDX, compact: 7, 167, 2.1k, 40k, 584k, 10.5M."""
    for div, unit in ((1e9, "B"), (1e6, "M"), (1e3, "k"), (1, "")):
        if v >= div or div == 1:
            g = v / div
            return (f"{g:.0f}" if g >= 100 or div == 1 else f"{g:.3g}") + unit
    return ""


def fig_price(rng, params: Params, out: Path) -> Path:
    """(a) the price against the number of tickets settled, one panel per level on one price scale,
    labelled on every panel; (b) simulated years of a mixed population."""
    fig = plt.figure(figsize=(sci.TWO_COL, 5.0))
    grid = fig.add_gridspec(2, 3, height_ratios=[1, 1.1], hspace=0.62, wspace=0.28)
    share = PRICE_TICKET / PRICE_SUPPLY
    panels, top = [], 1.0
    for n in PRICE_LEVELS:
        x, paths, stopped = ex.price_under_identical(rng, params, n, volume=PRICE_VOLUME, share=share)
        q = np.percentile(paths, [5, 50, 95], axis=1)
        tickets = x / share
        formula = 1 / (1 - (1 - params.rtp) * x)
        e = ex.entry_for(PRICE_TICKET, n, 1, params.rtp)
        quote(f"a.lvl{n}", {"min": e, "max": e * 2.0 ** (n - 1), "tickets": tickets[-1],
                            "p5": q[0][-1], "median": q[1][-1], "p95": q[2][-1],
                            "formula": formula[-1], "stopped_by_cap": stopped})
        panels.append((n, e, tickets, q, formula))
        top = max(top, q[2].max())
    for k, (n, e, tickets, q, formula) in enumerate(panels):
        ax = fig.add_subplot(grid[0, k])
        c = sci.BURN
        ax.fill_between(tickets, q[0], q[2], color=c, alpha=0.22, lw=0)
        ax.plot(tickets, q[1], color=c, lw=1.4)
        ax.plot(tickets, formula, color=sci.INK, lw=0.7, ls=(0, (3, 2)))
        ax.set_xlim(0, tickets[-1])
        ax.set_ylim(0.95, top * 1.04)
        ax.xaxis.set_major_locator(FixedLocator([0, 5000, 10000, 15000, 20000]))
        ax.xaxis.set_major_formatter(FuncFormatter(_count))
        # the top axis: what the tickets have taken, as a share of the starting supply
        sec = ax.secondary_xaxis("top", functions=(lambda t: t * share, lambda v: v / share))
        sec.xaxis.set_major_locator(FixedLocator([0.5, 1, 1.5]))
        sec.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:g}%"))
        sec.tick_params(labelsize=6, labelcolor=sci.GREY, pad=1)
        if k == 1:
            ax.set_xlabel(f"tickets of {PRICE_TICKET} PRDX")
            sec.set_xlabel(f"deposits / supply of {_prdx(PRICE_SUPPLY)} PRDX", fontsize=6,
                           color=sci.GREY, labelpad=2)
        if k == 0:
            ax.set_ylabel(r"price, $p/p_0$")
        ax.text(0.04, 0.95, f"MIN {e:.3g}\nMAX {_prdx(e * 2.0 ** (n - 1))}", transform=ax.transAxes,
                ha="left", va="top", fontsize=6.5, linespacing=1.3)
        sci.letter(ax, "a" if k == 0 else "", f"LVL {n}", pad=20)

    bx = fig.add_subplot(grid[1, :])
    rates = [0.25, 0.5, 1, 2, 4, 8]
    vol, growth, rate = ex.growth_vs_volume(rng, params, rates, players=10_000, seeds=40)
    ramp = sci.ramp(len(rates), 0.35, 1.0, sci.BURN)
    for i, r in enumerate(rates):
        m = rate == r
        bx.plot(vol[m], growth[m], "o", ms=2.0, color=ramp[i], mec="none", label=f"{r:g}")
    quote("b.share_above_formula", np.mean(growth > np.exp((1 - params.rtp) * vol)))
    v = np.linspace(0, vol.max() * 1.03, 200)
    bx.plot(v, np.exp((1 - params.rtp) * v), color=sci.INK, lw=0.8, ls=(0, (3, 2)))
    bx.text(0.97, 0.06, r"$\exp(0.125\,\sum_t D_t/P_t)$", transform=bx.transAxes, ha="right",
            fontsize=7.5)
    bx.set_xlabel(r"deposits over the year, $\sum_t D_t/P_t$")
    bx.set_ylabel(r"price after a year, $p/p_0$")
    bx.legend(loc="upper left", title="tickets a month", title_fontsize=7, markerscale=2,
              ncol=2, columnspacing=0.8, handletextpad=0.2)
    sci.letter(bx, "b", "simulated years, 10 000 participants")
    return sci.save(fig, out, "fig-price")


def _luminance(rgb) -> float:
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb[:3]]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _ink_on(rgb) -> str:
    """White or ink, whichever has the higher contrast ratio on the cell (WCAG)."""
    bg = _luminance(rgb)
    on_white = 1.05 / (bg + 0.05)
    on_ink = (bg + 0.05) / (_luminance((0.102, 0.102, 0.102)) + 0.05)
    return "white" if on_white > on_ink else sci.INK


def _heat(ax, data, cmap, fmt, norm=None, vmin=None, vmax=None):
    im = ax.imshow(data, cmap=cmap, norm=norm, vmin=vmin, vmax=vmax, aspect="auto", origin="lower")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, fmt(data[i, j]), ha="center", va="center", fontsize=6,
                    color=_ink_on(im.cmap(im.norm(data[i, j]))))
    ax.tick_params(top=False, right=False, length=0)
    return im


def fig_how_much(rng, params: Params, out: Path) -> Path:
    turnover = [0.25, 0.5, 1, 2, 4, 8]
    lvls = [2, 4, 6, 8, 12, 16, 20, 24]
    g = ex.mining_grid(rng, params, turnover, lvls)
    fig, axes = plt.subplots(1, 3, figsize=(sci.TWO_COL, 2.7), sharey=True)
    panels = (
        (g.median, "median multiple", sci.heat(sci.MINE), lambda v: f"{v:.2f}", -0.15, 1.15),
        (g.double, r"$P(\times 2$ or more$)$", sci.heat(sci.MINE), lambda v: f"{v * 100:.1f}", 0, None),
        (g.half, r"$P($half or less$)$", sci.heat(sci.MINE), lambda v: f"{v * 100:.0f}", 0, 1.15),
    )
    for i, (ax, (data, title, cmap, fmt, lo, hi)) in enumerate(zip(axes, panels)):
        _heat(ax, data, cmap, fmt, vmin=lo, vmax=hi if hi is not None else data.max())
        ax.set_xticks(range(len(turnover)))
        ax.set_xticklabels([f"{t:g}" for t in turnover])
        ax.set_xlabel(r"turnover per year, $T$")
        sci.letter(ax, "abc"[i], title + ("" if i == 0 else ", %"), pad=13)
        sec = ax.secondary_xaxis("top")
        sec.set_xticks(range(len(turnover)))
        sec.set_xticklabels([f"{e:.2f}" for e in g.expected], fontsize=6, color=sci.GREY)
        sec.tick_params(length=0, pad=2)
    i, j = np.unravel_index(np.argmax(g.double), g.double.shape)
    quote("b.best_double", {"lvl": lvls[i], "turnover": turnover[j], "p": g.double[i, j]})
    quote("expected", g.expected)
    axes[0].set_yticks(range(len(lvls)))
    axes[0].set_yticklabels([str(n) for n in lvls])
    axes[0].set_ylabel("LVL")
    # the grey row above the cells: the exact mean multiple of each turnover
    axes[0].annotate("mean", (0, 1), xycoords="axes fraction", xytext=(-4, 2), textcoords="offset points",
                     ha="right", va="bottom", fontsize=6, color=sci.GREY)
    fig.tight_layout(pad=0.4, w_pad=0.8)
    return sci.save(fig, out, "fig-how-much")


def fig_numbers(rng, params: Params, out: Path) -> Path:
    sizes = np.unique(np.logspace(1, 10, 37).astype(np.int64))
    fig, axes = plt.subplots(1, 4, figsize=(sci.TWO_COL, 2.2))
    edge = 1 - params.rtp
    # Panels (a–c) and (d) draw from separate generators, so a change to one leaves the other as it was.
    rng_edge, rng_years = rng.spawn(2)
    for i, (ax, n) in enumerate(zip(axes[:3], (4, 12, 24))):
        q, sd = ex.realised_edge(rng_edge, params, n, sizes)
        for at in (1_000, 2 ** n):
            k = int(np.argmin(np.abs(np.log(sizes / at))))
            quote(f"lvl{n}.at_{int(sizes[k])}", {"p5": q[0][k], "median": q[2][k], "p95": q[4][k]})
        c = sci.BURN
        ax.fill_between(sizes, q[0], q[4], color=c, alpha=0.15, lw=0)
        ax.fill_between(sizes, q[1], q[3], color=c, alpha=0.3, lw=0)
        ax.plot(sizes, q[2], color=c)
        ax.plot(sizes, edge + 2 * sd, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
        ax.plot(sizes, edge - 2 * sd, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
        ax.axhline(edge, color=sci.INK, lw=0.6)
        ax.set_xscale("log")
        ax.set_ylim(-0.4, 1.0)
        ax.set_xlabel(r"tickets, $N$")
        ax.xaxis.set_major_locator(FixedLocator([1e1, 1e4, 1e7, 1e10]))
        ax.xaxis.set_minor_locator(LogLocator(base=10, subs=(1.0,), numticks=12))
        ax.xaxis.set_minor_formatter(NullFormatter())
        sci.letter(ax, "abc"[i], f"LVL {n}")
        ax.yaxis.set_major_formatter(FuncFormatter(_pct))
    axes[0].set_ylabel(r"burned share, $1-\sum X/\sum D$")

    ax = axes[3]
    players = [100, 300, 1000, 3000, 10_000, 30_000, 100_000]
    stats = ex.holders_vs_players(rng_years, params, players,
                                  seeds=lambda n: 600 if n <= 3000 else 300 if n <= 30_000 else 100)
    k = np.array([(stats[n].growth < 1).sum() for n in players])
    tot = np.array([stats[n].growth.size for n in players])
    quote("d.years_lower", dict(zip(map(str, players), k / tot)))
    quote("d.years", dict(zip(map(str, players), tot)))
    lo, hi = np.array([_wilson(a, b) for a, b in zip(k, tot)]).T
    ax.fill_between(players, lo, hi, color=sci.BURN, alpha=0.18, lw=0)
    ax.plot(players, k / tot, "o-", color=sci.BURN, ms=2.5)
    ax.set_xscale("log")
    ax.set_ylim(0, None)
    ax.yaxis.set_major_formatter(FuncFormatter(_pct))
    ax.set_xlabel(r"participants, $N$")
    ax.set_ylabel("share of years")
    ax.xaxis.set_major_locator(LogLocator(base=10, numticks=6))
    sci.letter(ax, "d", "years the price fell")
    fig.tight_layout(pad=0.4, w_pad=0.9)
    return sci.save(fig, out, "fig-numbers")


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def _strip_key(bx, y: float, x0: float) -> None:
    """The key of the outcome strips, drawn in a spare row from x0 rightwards (log axis)."""
    k = lambda d: x0 * 10 ** d  # noqa: E731
    bx.plot([k(0.25), k(1.25)], [y, y], color=sci.GREY, lw=1.2, solid_capstyle="butt")
    bx.plot([k(0.5), k(1.0)], [y, y], color=sci.GREY, lw=6, solid_capstyle="butt")
    bx.plot([k(0.75), k(0.75)], [y - 0.24, y + 0.24], color=sci.INK, lw=1.2)
    bx.plot([k(1.6)], [y], "o", ms=5, mfc="white", mec=sci.GREY, mew=1.2)
    bx.text(k(1.85), y, "5–95 %, 25–75 %, median, max", va="center", fontsize=6.5)


# the five risk classes: Alice (rho = 0) holds and wears gold; the four classes that mine, up to Bob
# (rho in (0.75, 1]), wear the mine steps, light to dark
RISK = [sci.GOLD] + sci.ramp(4, 0.4, 1.0)


def fig_classes(rng, params: Params, out: Path) -> Path:
    """Two models in two rows: the closed population of one year (statics) and the loop of four
    years, where players arrive and leave (dynamics)."""
    from prdx_sim.population import CLASSES, class_of

    rows = (
        ("statics, one year", ex.pooled_years(rng, params, players=20_000, seeds=100)),
        (r"loop, four years", ex.pooled_loop(rng, params, seeds=20)),
    )
    names = [r"Alice, $\rho=0$", r"$\rho\in(0,\,0.25]$", r"$\rho\in(0.25,\,0.5]$",
             r"$\rho\in(0.5,\,0.75]$", r"Bob, $\rho\in(0.75,\,1]$"]
    fig, axes = plt.subplots(2, 2, figsize=(sci.TWO_COL, 5.0),
                             gridspec_kw={"width_ratios": [1, 1.5]})
    for r, (title, pooled) in enumerate(rows):
        ax, bx = axes[r]
        gains = pooled.gain_by_class.mean(axis=0)
        vals = list(gains) + [-pooled.fees.mean(), -pooled.kept.mean()]
        labels = names + ["mint fee", "burn fee"]
        colours = list(RISK) + [sci.MINT, sci.BURN]
        ys = np.arange(len(vals))[::-1]
        ax.barh(ys, vals, color=colours, height=0.6)
        ax.axvline(0, color=sci.INK, lw=0.6)
        ax.set_yticks(ys)
        ax.set_yticklabels(labels)
        ax.tick_params(axis="y", length=0)
        ax.xaxis.set_major_formatter(FuncFormatter(_pct))
        ax.set_xlabel("gain, share of all money brought in")
        ax.text(0.98, 0.03, "sum of bars = 0", transform=ax.transAxes, ha="right", va="bottom", fontsize=6.5)
        total = np.abs(pooled.gain_by_class.sum(axis=1) + pooled.fees + pooled.kept).max()
        assert total < 1e-9, f"money is not conserved: {total}"
        sci.letter(ax, "ac"[r], f"gains · {title}")

        mult = pooled.final / pooled.start
        cls = class_of(pooled.rho)
        lo = max(mult.min(), 1e-3) / 1.6
        # one row per class, level with its bar in (a): 5-95 % thin, 25-75 % thick, the median a tick,
        # a ring the largest. Right: the share that ended below what it brought, and at x10 or more.
        # A fee row of (a) holds the key.
        for i in range(len(CLASSES)):
            y, m, c = ys[i], mult[cls == i], RISK[i]
            q = np.quantile(m, [0.05, 0.25, 0.5, 0.75, 0.95])
            quote(f"{'bd'[r]}.class{i}", {"loss": (m < 1).mean(), "x10": (m >= 10).mean(),
                                         "p5": q[0], "median": q[2], "p95": q[4], "min": m.min(),
                                         "max": m.max(), "gain": gains[i]})
            bx.plot([q[0], q[4]], [y, y], color=c, lw=1.2, solid_capstyle="butt")
            bx.plot([q[1], q[3]], [y, y], color=c, lw=6, solid_capstyle="butt")
            bx.plot([q[2], q[2]], [y - 0.24, y + 0.24], color=sci.INK, lw=1.2)
            bx.plot([m.max()], [y], "o", ms=5, mfc="white", mec=c, mew=1.2)
            for x, v in ((1.03, (m < 1).mean()), (1.17, (m >= 10).mean())):
                bx.text(x, y, _share(v), transform=bx.get_yaxis_transform(), ha="left", va="center",
                        fontsize=7, clip_on=False)
        for x, head in ((1.03, "loss"), (1.17, "×10+")):
            bx.text(x, ys[0] + 0.55, head, transform=bx.get_yaxis_transform(), ha="left",
                    va="center", fontsize=7, color=sci.GREY, clip_on=False)
        _strip_key(bx, ys[len(CLASSES) + 1], lo)
        bx.axvline(1, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
        bx.set_xscale("log")
        bx.set_xlim(lo, mult.max() * 2.5)
        bx.set_ylim(ax.get_ylim())
        bx.set_yticks([])
        bx.xaxis.set_major_formatter(FuncFormatter(_mult))
        bx.set_xlabel("wealth at exit / brought in")
        sci.letter(bx, "bd"[r], "outcomes by risk class")
    fig.tight_layout(pad=0.4, w_pad=1.2, h_pad=1.0)
    return sci.save(fig, out, "fig-classes")


YEARS = 4


def _trailing(v, w: int) -> np.ndarray:
    """Mean of the last `w` values at each day (fewer at the start)."""
    c = np.cumsum(np.r_[0.0, v])
    i = np.arange(1, len(v) + 1)
    return (c[i] - c[np.maximum(i - w, 0)]) / np.minimum(i, w)


def _iqr(ax, x, runs, colour, label=None, lw=1.0):
    q = np.nanpercentile(runs, [25, 50, 75], axis=0)
    ax.fill_between(x, q[0], q[2], color=colour, alpha=0.18, lw=0)
    ax.plot(x, q[1], color=colour, lw=lw, label=label)
    return q[1]


def fig_loop(rng, params: Params, out: Path) -> Path:
    from prdx_sim import dynamics as dyn

    days = YEARS * 365
    x = np.arange(1, days + 1) / 365
    # each panel wears the tone of its quantity (reserve mint, price burn, holders gold, miners mine); the
    # regimes are the steps of that tone, light to dark as epsilon grows, the static model grey
    tones = (sci.MINT, sci.BURN, sci.GOLD, sci.MINE)
    steps = [sci.ramp(3, 0.45, 0.95, t) for t in tones]
    regimes = (("static", dyn.Behaviour(static=True), None),
               (r"$\varepsilon=0.5$", dyn.Behaviour(eps=0.5), 0),
               (r"$\varepsilon=0.8$", dyn.Behaviour(eps=0.8), 1),
               (r"$\varepsilon=1.2$", dyn.Behaviour(eps=1.2), 2))
    fig, axes = plt.subplots(1, 4, figsize=(sci.TWO_COL, 2.1), sharex=True)
    for label, b, j in regimes:
        c = [sci.GREY if j is None else s[j] for s in steps]
        r = ex.loop_runs(rng, b, 20, days, params)
        yearly = r["price"][:, 364::365]
        lower = (np.diff(np.hstack([np.ones((yearly.shape[0], 1)), yearly]), axis=1) < 0)
        quote(label.strip("$").replace("\\varepsilon", "eps"),
              {"reserve": np.median(r["reserve"][:, -1]), "price": np.median(r["price"][:, -1]),
               "reserve_p25_p75": np.percentile(r["reserve"][:, -1], [25, 75]),
               "price_p25_p75": np.percentile(r["price"][:, -1], [25, 75]),
               "years_lower": int(lower.sum()), "years": int(lower.size)})
        _iqr(axes[0], x, r["reserve"], c[0], label)
        _iqr(axes[1], x, r["price"], c[1])
        ys = np.array([_trailing(v, 30) for v in r["y"]])
        ys[:, : b.window + 30] = np.nan  # y needs a full window of history
        _iqr(axes[2], x, ys, c[2])
        _iqr(axes[3], x, r["bobs"] / np.maximum(r["alices"] + r["bobs"], 1), c[3])
    axes[0].set_yscale("log")
    axes[0].set_ylabel(r"reserve, $G/G_0$")
    axes[1].set_ylabel(r"price, $p/p_0$")
    axes[2].axhline(0.05, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
    axes[2].set_ylim(0, 0.6)
    axes[2].set_ylabel(r"holders' growth, $y$")
    axes[2].yaxis.set_major_formatter(FuncFormatter(_pct))
    axes[3].set_ylabel("miners among participants")
    axes[3].yaxis.set_major_formatter(FuncFormatter(_pct))
    for i, ax in enumerate(axes):
        ax.set_xlabel("year")
        sci.letter(ax, "abcd"[i])
    axes[0].legend(loc="lower right", handlelength=1.2)
    fig.tight_layout(pad=0.4, w_pad=0.6)
    return sci.save(fig, out, "fig-loop")


def fig_phase(rng, params: Params, out: Path) -> Path:
    from matplotlib.colors import TwoSlopeNorm

    eps = [0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
    r_star = [0.02, 0.05, 0.1, 0.2, 0.4]
    ph = ex.loop_phase(rng, eps, r_star, log=lambda m: print(m, flush=True))
    fig, axes = plt.subplots(1, 2, figsize=(sci.TWO_COL, 2.5), sharey=True)
    from matplotlib.colors import LogNorm

    _heat(axes[0], ph.growth, sci.heat(sci.MINT), lambda v: "", norm=LogNorm(1, max(np.nanmax(ph.growth), 10)))
    for i in range(len(r_star)):
        for j in range(len(eps)):
            g = ph.growth[i, j]
            txt = f"×{g:.0f}" if g >= 10 else f"×{g:.1f}"
            if not np.isnan(ph.full[i, j]):
                txt += f"\nfull y{ph.full[i, j]:.1f}"
            axes[0].text(j, i, txt, ha="center", va="center", fontsize=5.8,
                         color=_ink_on(axes[0].images[0].cmap(axes[0].images[0].norm(g))))
    prem = np.where(np.isnan(ph.premium), 0, ph.premium)
    plim = max(np.nanmax(np.abs(ph.premium)), 0.01)
    _heat(axes[1], prem, sci.SIGNED_CMAP, lambda v: "", norm=TwoSlopeNorm(0, -plim, plim))
    for i in range(len(r_star)):
        for j in range(len(eps)):
            v = ph.premium[i, j]
            axes[1].text(j, i, "—" if np.isnan(v) else f"{v * 100:+.0f}", ha="center",
                         va="center", fontsize=5.8,
                         color=_ink_on(axes[1].images[0].cmap(axes[1].images[0].norm(prem[i, j]))))
    quote("a.reserve_range", [np.nanmin(ph.growth), np.nanmax(ph.growth)])
    quote("b.premium", {f"eps{e:g}": dict(zip([f"r{r:g}" for r in r_star], ph.premium[:, j]))
                        for j, e in enumerate(eps)})
    from matplotlib.patches import Rectangle

    for ax in axes:
        j = eps.index(1.0)
        ax.add_patch(Rectangle((j - 0.5, -0.5), 1, len(r_star), fill=False, ec=sci.INK, lw=1.0,
                               clip_on=False, zorder=3))
        ax.set_xticks(range(len(eps)))
        ax.set_xticklabels([f"{e:g}" for e in eps])
        ax.set_xlabel(r"top-payout elasticity, $\varepsilon$")
    axes[0].set_yticks(range(len(r_star)))
    axes[0].set_yticklabels([f"{r * 100:g}%" for r in r_star])
    axes[0].set_ylabel(r"outside yield, $r^*$")
    sci.letter(axes[0], "a", r"reserve after 4 years, $G/G_0$")
    sci.letter(axes[1], "b", r"holders' premium $y-r^*$, %")
    fig.tight_layout(pad=0.4, w_pad=1.0)
    return sci.save(fig, out, "fig-phase")


def fig_shock(rng, params: Params, out: Path, pairs: int = 40) -> Path:
    from prdx_sim import dynamics as dyn

    days, at = YEARS * 365, 2 * 365
    b = dyn.Behaviour(eps=0.8)
    x = np.arange(1, days + 1) / 365
    fig, axes = plt.subplots(2, 2, figsize=(sci.TWO_COL, 4.6))
    axes = axes.ravel()
    win = {"price": [], "reserve": []}
    exo = {"y_base": [], "y_hit": [], "alices": []}
    for _ in range(pairs):
        s = int(rng.integers(1 << 31))
        base = ex.loop_runs(np.random.default_rng(s), b, 1, days, params)
        hit = ex.loop_runs(np.random.default_rng(s), b, 1, days, params, shock_day=at)
        gone = ex.loop_runs(np.random.default_rng(s), b, 1, days, params, exodus_day=at)
        for k in win:
            win[k].append((hit[k] / base[k])[0])
        exo["y_base"].append(_trailing(base["y"][0], 30))
        exo["y_hit"].append(_trailing(gone["y"][0], 30))
        exo["alices"].append(gone["alices"][0] / np.maximum(base["alices"][0], 1))

    for k in win:
        med = np.median(np.array(win[k]), axis=0)
        quote(f"a.{k}", {"lowest": med[at:].min(), "end": med[-1]})
    alices = np.median(np.array(exo["alices"]), axis=0)
    quote("c.alices", {"half_year": alices[at + 182], "end": alices[-1]})
    ax = axes[0]
    for k, c in (("price", sci.BURN), ("reserve", sci.MINT)):
        _iqr(ax, x, np.array(win[k]), c, k)
    ax.axhline(1, color=sci.INK, lw=0.6)
    ax.set_ylabel("shocked run / its twin")
    ax.legend(loc="upper left", ncol=2)
    ax.set_ylim(0, 2.0)
    sci.letter(ax, "a", r"one payout of $L\cdot P$ on day 730")

    ax = axes[1]
    _iqr(ax, x, np.array(exo["y_base"]), sci.GREY, "twin")
    _iqr(ax, x, np.array(exo["y_hit"]), sci.GOLD, "half leave")
    ax.axhline(b.r_star, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
    ax.set_ylim(-0.1, 0.9)
    ax.legend(loc="upper right", ncol=2)
    ax.yaxis.set_major_formatter(FuncFormatter(_pct))
    ax.set_ylabel(r"holders' growth, $y$")
    sci.letter(ax, "b", "half the holders leave on day 730")

    ax = axes[2]
    _iqr(ax, x, np.array(exo["alices"]), sci.GOLD)
    ax.axhline(1, color=sci.INK, lw=0.6)
    ax.set_ylim(0, 1.2)
    ax.set_ylabel("holders / its twin")
    sci.letter(ax, "c", "holders come back")
    for ax in axes[:3]:
        ax.axvline(at / 365, color=sci.GREY, lw=0.6, ls=(0, (3, 2)))
        ax.set_xlabel("year")

    rates = [1 / 64, 1 / 32, 1 / 16, 1 / 8, 1 / 4]
    res = [ex.loop_runs(rng, b, 20, days, Params(max_yield_rate=r)) for r in rates]
    xs = np.arange(len(rates))
    ax = axes[3]
    q = np.array([np.percentile(r["reserve"][:, -1], [5, 25, 50, 75, 95]) for r in res]).T
    w = np.array([np.median(r["worst"]) for r in res])
    ax.vlines(xs, q[0], q[4], color=sci.MINT, lw=0.8)
    ax.vlines(xs, q[1], q[3], color=sci.MINT, lw=3)
    ax.plot(xs, q[2], "o", ms=3.5, mfc="white", mec=sci.MINT, mew=0.9)
    quote("d.reserve", dict(zip(["1.6", "3.1", "6.3", "12.5", "25"], q[2])))
    quote("d.worst_day", dict(zip(["1.6", "3.1", "6.3", "12.5", "25"], w)))
    for xi, top, wi in zip(xs, q[4], w):
        ax.annotate(f"{wi * 100:.0f}%", (xi, top), xytext=(0, 2), textcoords="offset points",
                    ha="center", fontsize=6.5, color=sci.INK)
    ax.set_yscale("log")
    ax.set_ylim(q[0].min() / 1.5, q[4].max() * 2.2)
    ax.set_xlim(-0.5, len(rates) - 0.5)
    ax.set_xticks(xs)
    ax.set_xticklabels(["1.6", "3.1", "6.3", "12.5", "25"])
    ax.set_xlabel(r"cap $L$, % of supply")
    ax.set_ylabel(r"reserve after 4 years, $G/G_0$")
    ax.axvspan(2.6, 3.4, color=sci.LIGHT, lw=0, zorder=0)
    sci.letter(ax, "d", "the cap; worst day of the price above")
    fig.tight_layout(pad=0.4, w_pad=1.2, h_pad=1.2)
    return sci.save(fig, out, "fig-shock-and-cap")


FIGURES = {
    "tickets": fig_tickets,
    "price": fig_price,
    "how-much": fig_how_much,
    "numbers": fig_numbers,
    "classes": fig_classes,
    "loop": fig_loop,
    "phase": fig_phase,
    "shock": fig_shock,
}


def _build(job):
    """One figure in its own process: its own seed, so the order of the processes changes nothing."""
    name, i, outdir, seed = job
    sci.apply()
    QUOTES.clear()
    path = FIGURES[name](np.random.default_rng([seed, i]), Params(), Path(outdir))
    return name, path, dict(QUOTES)


def main(outdir: str = "figures", *only: str, seed: int = 777, workers: int = 6) -> list[Path]:
    import json
    import os
    from concurrent.futures import ProcessPoolExecutor

    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ.setdefault(var, "1")
    jobs = [(name, i, outdir, seed) for i, name in enumerate(FIGURES) if not only or name in only]
    with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as pool:
        done = list(pool.map(_build, jobs))
    numbers = Path(outdir) / "numbers.json"
    cited = json.loads(numbers.read_text()) if numbers.exists() else {}
    for name, path, quotes in done:
        cited[name] = quotes
        print(path)
    numbers.write_text(json.dumps(cited, indent=1, ensure_ascii=False) + "\n")
    return [path for _, path, _ in done]


if __name__ == "__main__":
    main(*sys.argv[1:])
