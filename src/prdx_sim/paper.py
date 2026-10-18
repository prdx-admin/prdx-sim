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


def _mult(v, _=None) -> str:
    if v >= 1e3:
        return rf"$10^{{{int(round(np.log10(v)))}}}$"
    return f"{v:g}"


def _pct(v, _=None) -> str:
    return f"{v * 100:g}%"


def fig_tickets(rng, params: Params, out: Path, players: int = 10_000) -> Path:
    """Players by payout, the same ticket each, no cap."""
    lvls = [2, 4, 8, 12, 16, 24]
    fig, axes = plt.subplots(2, 3, figsize=(sci.TWO_COL, 3.9), sharey=True)
    for i, (ax, n) in enumerate(zip(axes.ravel(), lvls)):
        pay, counts, p = ex.identical_tickets(rng, params, n, players)
        share = counts / players
        colour = np.where(pay > 1 + 1e-9, sci.PROFIT, np.where(pay < 1 - 1e-9, sci.LOSS, sci.EVEN))
        for x, y, c in zip(pay, share, colour):
            if y > 0:
                ax.vlines(x, 1e-5, y, color=c, lw=2.2 if n <= 8 else 1.6)
        ax.plot(pay, p, "o", ms=2.2, mfc="white", mec=sci.INK, mew=0.5, zorder=3)
        ax.axvline(1, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylim(5e-5, 0.8)
        ax.set_xlim(pay[0] / 1.8, pay[-1] * 1.8)
        ax.xaxis.set_major_locator(LogLocator(base=10 if pay[-1] < 1e3 else 100))
        ax.xaxis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10) * 0.1, numticks=50))
        ax.xaxis.set_major_formatter(FuncFormatter(_mult))
        if pay[-1] < 10:
            ax.xaxis.set_major_locator(FixedLocator([0.2, 0.5, 1, 2, 5]))
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_formatter(FuncFormatter(_pct))
        exact = p[pay > 1 + 1e-9].sum()  # the circles are exact, the bars one sample of players
        sci.letter(ax, "abcdef"[i], f"LVL {n}   P(X>D) = {exact * 100:g}%")
    for ax in axes[1]:
        ax.set_xlabel(r"payout per deposit, $X/D$")
    for ax in axes[:, 0]:
        ax.set_ylabel("share of miners")
    fig.tight_layout(pad=0.4, w_pad=0.8, h_pad=0.9)
    return sci.save(fig, out, "fig-tickets")


def fig_price(rng, params: Params, out: Path) -> Path:
    """(a) a stream of identical tickets; (b) simulated years of a mixed population."""
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(sci.TWO_COL, 2.6))
    # the 5-95 % band of every level; the spread grows with the level, so the bands nest and are
    # drawn opaque from the widest (LVL 24, lightest) to the narrowest
    levels = (24, 20, 16, 12, 8, 4, 2)
    shades = plt.get_cmap("Blues")(np.linspace(0.18, 0.95, len(levels)))
    x = None
    for n, c in zip(levels, shades):
        x, paths = ex.price_under_identical(rng, params, n)
        q = np.percentile(paths, [5, 95], axis=1)
        ax.fill_between(x, q[0], q[1], color=c, lw=0, label=f"LVL {n}")
    ax.plot(x, 1 / (1 - (1 - params.rtp) * x), color=sci.INK, lw=0.8, ls=(0, (3, 2)),
            label=r"$1/(1-0.125\,V/P_0)$")
    ax.set_xlim(0, x[-1])
    ax.set_xlabel(r"cumulative deposits, $V/P_0$")
    ax.set_ylabel(r"price, $p/p_0$")
    h, lab = ax.get_legend_handles_labels()
    order = list(range(len(levels) - 1, -1, -1)) + [len(levels)]
    ax.legend([h[i] for i in order], [lab[i] for i in order], loc="upper left", ncol=2,
              columnspacing=0.8, handlelength=1.2)
    sci.letter(ax, "a", "identical tickets, 5–95 %")

    rates = [0.25, 0.5, 1, 2, 4, 8]
    vol, growth, rate = ex.growth_vs_volume(rng, params, rates, players=10_000, seeds=40)
    for i, r in enumerate(rates):
        m = rate == r
        bx.plot(vol[m], growth[m], "o", ms=1.8, color=sci.SERIES[i % 6], alpha=0.7,
                mec="none", label=f"{r:g}")
    v = np.linspace(0, vol.max() * 1.03, 200)
    bx.plot(v, np.exp((1 - params.rtp) * v), color=sci.INK, lw=0.8, ls=(0, (3, 2)))
    bx.text(0.97, 0.06, r"$\exp(0.125\,\sum_t D_t/P_t)$", transform=bx.transAxes, ha="right",
            fontsize=7.5)
    bx.set_xlabel(r"deposits over the year, $\sum_t D_t/P_t$")
    bx.set_ylabel(r"price after a year, $p/p_0$")
    bx.legend(loc="upper left", title="tickets a month", title_fontsize=7, markerscale=2,
              ncol=2, columnspacing=0.8, handletextpad=0.2)
    sci.letter(bx, "b", "simulated years, 10 000 participants")
    fig.tight_layout(pad=0.4, w_pad=1.2)
    return sci.save(fig, out, "fig-price")


def _heat(ax, data, cmap, fmt, norm=None, vmin=None, vmax=None):
    im = ax.imshow(data, cmap=cmap, norm=norm, vmin=vmin, vmax=vmax, aspect="auto", origin="lower")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            r, g, b, _ = im.cmap(im.norm(data[i, j]))
            dark = 0.299 * r + 0.587 * g + 0.114 * b < 0.5
            ax.text(j, i, fmt(data[i, j]), ha="center", va="center", fontsize=6,
                    color="white" if dark else sci.INK)
    ax.tick_params(top=False, right=False, length=0)
    return im


def fig_how_much(rng, params: Params, out: Path) -> Path:
    turnover = [0.25, 0.5, 1, 2, 4, 8]
    lvls = [2, 4, 6, 8, 12, 16, 20, 24]
    g = ex.mining_grid(rng, params, turnover, lvls)
    fig, axes = plt.subplots(1, 3, figsize=(sci.TWO_COL, 2.7), sharey=True)
    panels = (
        (g.median, "median multiple", "Blues_r", lambda v: f"{v:.2f}", -0.15, 1.15),
        (g.double, r"$P(\times 2$ or more$)$", "Blues", lambda v: f"{v * 100:.1f}", 0, None),
        (g.half, r"$P($half or less$)$", "Blues", lambda v: f"{v * 100:.0f}", 0, 1.15),
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
    axes[0].set_yticks(range(len(lvls)))
    axes[0].set_yticklabels([str(n) for n in lvls])
    axes[0].set_ylabel("LVL")
    # the grey row above the cells: the exact mean multiple of each turnover
    axes[0].annotate("mean", (0, 1), xycoords="axes fraction", xytext=(-4, 2), textcoords="offset points",
                     ha="right", va="bottom", fontsize=6, color=sci.GREY)
    fig.tight_layout(pad=0.4, w_pad=0.8)
    return sci.save(fig, out, "fig-how-much")


def fig_numbers(rng, params: Params, out: Path) -> Path:
    sizes = np.unique(np.logspace(1, 5, 13).astype(int))
    fig, axes = plt.subplots(1, 4, figsize=(sci.TWO_COL, 2.2))
    edge = 1 - params.rtp
    for i, (ax, n) in enumerate(zip(axes[:3], (4, 12, 24))):
        q, sd = ex.realised_edge(rng, params, n, sizes)
        ax.fill_between(sizes, q[0], q[4], color=sci.BLUE, alpha=0.15, lw=0)
        ax.fill_between(sizes, q[1], q[3], color=sci.BLUE, alpha=0.3, lw=0)
        ax.plot(sizes, q[2], color=sci.BLUE)
        ax.plot(sizes, edge + 2 * sd, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
        ax.plot(sizes, edge - 2 * sd, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
        ax.axhline(edge, color=sci.INK, lw=0.6)
        ax.set_xscale("log")
        ax.set_ylim(-0.4, 1.0)
        ax.set_xlabel(r"tickets, $N$")
        ax.xaxis.set_major_locator(LogLocator(base=10, numticks=6))
        sci.letter(ax, "abc"[i], f"LVL {n}")
        ax.yaxis.set_major_formatter(FuncFormatter(_pct))
    axes[0].set_ylabel(r"burned share, $1-\sum X/\sum D$")
    for ax in axes[1:3]:
        ax.set_yticklabels([])

    ax = axes[3]
    players = [100, 300, 1000, 3000, 10_000, 30_000, 100_000]
    stats = ex.holders_vs_players(rng, params, players,
                                  seeds=lambda n: 600 if n <= 3000 else 300 if n <= 30_000 else 100)
    k = np.array([(stats[n].growth < 1).sum() for n in players])
    tot = np.array([stats[n].growth.size for n in players])
    lo, hi = np.array([_wilson(a, b) for a, b in zip(k, tot)]).T
    ax.fill_between(players, lo, hi, color=sci.VERMILION, alpha=0.2, lw=0)
    ax.plot(players, k / tot, "o-", color=sci.VERMILION, ms=2.5)
    ax.set_xscale("log")
    ax.set_ylim(0, None)
    ax.yaxis.set_major_formatter(FuncFormatter(_pct))
    ax.set_xlabel(r"participants, $N$")
    ax.set_ylabel("years the price ends lower")
    ax.xaxis.set_major_locator(LogLocator(base=10, numticks=6))
    sci.letter(ax, "d", "holders")
    fig.tight_layout(pad=0.4, w_pad=0.5)
    return sci.save(fig, out, "fig-numbers")


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def fig_classes(rng, params: Params, out: Path) -> Path:
    from prdx_sim.population import CLASSES, class_of

    pooled = ex.pooled_years(rng, params, players=20_000, seeds=100)
    names = [r"Alice, $\rho=0$", r"$\rho\in(0,\,0.25]$", r"$\rho\in(0.25,\,0.5]$",
             r"$\rho\in(0.5,\,0.75]$", r"Bob, $\rho\in(0.75,\,1]$"]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(sci.TWO_COL, 2.6),
                                 gridspec_kw={"width_ratios": [1, 1.5]})
    gains = pooled.gain_by_class.mean(axis=0)
    vals = list(gains) + [-pooled.fees.mean(), -pooled.kept.mean()]
    labels = names + ["mint fee", "burn fee"]
    colours = sci.SERIES[: len(CLASSES)] + [sci.GREY, sci.GREY]
    ys = np.arange(len(vals))[::-1]
    ax.barh(ys, vals, color=colours, height=0.6)
    ax.axvline(0, color=sci.INK, lw=0.6)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels)
    ax.tick_params(axis="y", length=0)
    ax.xaxis.set_major_formatter(FuncFormatter(_pct))
    ax.set_xlabel("gain, share of all money brought in")
    total = np.abs(pooled.gain_by_class.sum(axis=1) + pooled.fees + pooled.kept).max()
    assert total < 1e-12, f"money is not conserved: {total}"
    ax.text(0.98, 0.04, "sum of bars = 0", transform=ax.transAxes, ha="right", fontsize=7)
    sci.letter(ax, "a", "who pays whom")

    mult = pooled.final / pooled.start
    cls = class_of(pooled.rho)
    grid = np.logspace(-1.3, 1.3, 400)
    for i in range(len(CLASSES)):
        m = np.sort(mult[cls == i])
        bx.plot(grid, np.searchsorted(m, grid, side="right") / m.size, color=sci.SERIES[i],
                label=names[i])
    bx.axvline(1, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
    bx.set_xscale("log")
    bx.set_ylim(0, 1)
    bx.xaxis.set_major_formatter(FuncFormatter(_mult))
    bx.yaxis.set_major_formatter(FuncFormatter(_pct))
    bx.set_xlabel("wealth at exit / wealth brought in")
    bx.set_ylabel("share of participants at or below")
    bx.legend(loc="lower right")
    sci.letter(bx, "b", "outcomes by risk class")
    fig.tight_layout(pad=0.4, w_pad=1.2)
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
    regimes = (("static", dyn.Behaviour(static=True), sci.GREY),
               (r"$\varepsilon=0.5$", dyn.Behaviour(eps=0.5), sci.BLUE),
               (r"$\varepsilon=0.8$", dyn.Behaviour(eps=0.8), sci.GREEN),
               (r"$\varepsilon=1.2$", dyn.Behaviour(eps=1.2), sci.VERMILION))
    fig, axes = plt.subplots(1, 4, figsize=(sci.TWO_COL, 2.1), sharex=True)
    for label, b, c in regimes:
        r = ex.loop_runs(rng, b, 20, days, params)
        _iqr(axes[0], x, r["reserve"], c, label)
        _iqr(axes[1], x, r["price"], c)
        ys = np.array([_trailing(v, 30) for v in r["y"]])
        ys[:, : b.window + 30] = np.nan  # y needs a full window of history
        _iqr(axes[2], x, ys, c)
        _iqr(axes[3], x, r["bobs"] / np.maximum(r["alices"] + r["bobs"], 1), c)
    axes[0].set_yscale("log")
    axes[0].set_ylabel(r"reserve, $G/G_0$")
    axes[1].set_ylabel(r"price, $p/p_0$")
    axes[2].axhline(0.05, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
    axes[2].set_ylim(0, 0.6)
    axes[2].set_ylabel(r"holders' growth, $y$")
    axes[2].yaxis.set_major_formatter(FuncFormatter(_pct))
    axes[3].set_ylabel("Bobs among participants")
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

    _heat(axes[0], ph.growth, "Blues", lambda v: "", norm=LogNorm(1, max(np.nanmax(ph.growth), 10)))
    for i in range(len(r_star)):
        for j in range(len(eps)):
            g = ph.growth[i, j]
            txt = f"×{g:.0f}" if g >= 10 else f"×{g:.1f}"
            if not np.isnan(ph.full[i, j]):
                txt += f"\nfull y{ph.full[i, j]:.1f}"
            axes[0].text(j, i, txt, ha="center", va="center", fontsize=5.8,
                         color="white" if g > 8 else sci.INK)
    prem = np.where(np.isnan(ph.premium), 0, ph.premium)
    plim = max(np.nanmax(np.abs(ph.premium)), 0.01)
    _heat(axes[1], prem, "PuOr_r", lambda v: "", norm=TwoSlopeNorm(0, -plim, plim))
    for i in range(len(r_star)):
        for j in range(len(eps)):
            v = ph.premium[i, j]
            axes[1].text(j, i, "—" if np.isnan(v) else f"{v * 100:+.0f}", ha="center",
                         va="center", fontsize=5.8,
                         color="white" if not np.isnan(v) and abs(v) > 0.6 * plim else sci.INK)
    for ax in axes:
        ax.axvline(eps.index(1.0), color=sci.INK, lw=0.8, ls=(0, (3, 2)))
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
    fig, axes = plt.subplots(1, 4, figsize=(sci.TWO_COL, 2.2))
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

    ax = axes[0]
    for k, c in (("price", sci.BLUE), ("reserve", sci.GREEN)):
        _iqr(ax, x, np.array(win[k]), c, k)
    ax.axhline(1, color=sci.INK, lw=0.6)
    ax.set_ylabel("shocked run / its twin")
    ax.legend(loc="lower left")
    sci.letter(ax, "a", r"a payout of $L\cdot P$")

    ax = axes[1]
    _iqr(ax, x, np.array(exo["y_base"]), sci.GREY, "twin")
    _iqr(ax, x, np.array(exo["y_hit"]), sci.VERMILION, "half leave")
    ax.axhline(b.r_star, color=sci.INK, lw=0.6, ls=(0, (3, 2)))
    ax.set_ylim(-0.1, 0.9)
    ax.legend(loc="upper right")
    ax.yaxis.set_major_formatter(FuncFormatter(_pct))
    ax.set_ylabel(r"holders' growth, $y$")
    sci.letter(ax, "b", "Alices leave")

    ax = axes[2]
    _iqr(ax, x, np.array(exo["alices"]), sci.VERMILION)
    ax.axhline(1, color=sci.INK, lw=0.6)
    ax.set_ylim(0, 1.2)
    ax.set_ylabel("Alices / its twin")
    sci.letter(ax, "c", "and come back")
    for ax in axes[:3]:
        ax.axvline(at / 365, color=sci.GREY, lw=0.6, ls=(0, (3, 2)))
        ax.set_xlabel("year")

    rates = [1 / 64, 1 / 32, 1 / 16, 1 / 8, 1 / 4]
    names = ["1/64", "1/32", "1/16", "1/8", "1/4"]
    res = [ex.loop_runs(rng, b, 20, days, Params(max_yield_rate=r)) for r in rates]
    xs = np.arange(len(rates))
    ax = axes[3]
    q = np.array([np.percentile(r["reserve"][:, -1], [5, 25, 50, 75, 95]) for r in res]).T
    w = np.array([np.median(r["worst"]) for r in res])
    ax.vlines(xs, q[0], q[4], color=sci.BLUE, lw=0.8)
    ax.vlines(xs, q[1], q[3], color=sci.BLUE, lw=3)
    ax.plot(xs, q[2], "o", ms=3.5, mfc="white", mec=sci.BLUE, mew=0.9)
    for xi, top, wi in zip(xs, q[4], w):
        ax.annotate(f"{wi * 100:.0f}%", (xi, top), xytext=(0, 2), textcoords="offset points",
                    ha="center", fontsize=6.5, color=sci.VERMILION)
    ax.set_yscale("log")
    ax.set_xticks(xs)
    ax.set_xticklabels(["1.6", "3.1", "6.3", "12.5", "25"], fontsize=6.3)
    ax.set_xlabel(r"cap $L$, % of supply")
    ax.set_ylabel(r"reserve after 4 years, $G/G_0$")
    ax.axvspan(2.6, 3.4, color=sci.LIGHT, lw=0, zorder=0)
    sci.letter(ax, "d", "the cap")
    fig.tight_layout(pad=0.4, w_pad=0.6)
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


def main(outdir: str = "figures", *only: str, seed: int = 777) -> list[Path]:
    sci.apply()
    params = Params()
    made = []
    for i, (name, make) in enumerate(FIGURES.items()):
        if not only or name in only:
            made.append(make(np.random.default_rng([seed, i]), params, Path(outdir)))
    for p in made:
        print(p)
    return made


if __name__ == "__main__":
    main(*sys.argv[1:])
