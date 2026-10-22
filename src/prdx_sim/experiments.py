"""The numbers behind the figures (paper.py). Pure numpy; every function takes its own rng.

identical tickets      players by payout, the price under a stream of the same ticket
growth against volume  simulated years: the price against the deposits over supply
how much and how       turnover sets the mean multiple exactly, the ladder sets the shape
large numbers          the realised edge against the number of tickets; holders against players
classes                who pays whom, and the outcomes inside each risk class
the loop               static players against players who answer growth and the jackpot L*G
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from prdx_sim import population as pop
from prdx_sim.protocol import Params, draw_payout, entry_for, ladder_max


# ───────────────────────── Q0 the ladder family ─────────────────────────
def single_draw_pmf(outcomes: int) -> tuple[np.ndarray, np.ndarray]:
    """Rungs 1..n and their probabilities; n = 1 is the certain outcome (cancel)."""
    k = np.arange(1, outcomes + 1)
    p = 0.5**k
    p[-1] = 0.5 ** (outcomes - 1)
    return k, p


def ladder_moments(outcomes: int, attempts: int, rtp: float) -> tuple[float, float]:
    """Mean and standard deviation of the payout per unit of deposit."""
    k, p = single_draw_pmf(outcomes)
    pay = entry_for(1.0, outcomes, attempts, rtp) * 2.0 ** (k - 1)
    mean = (p * pay).sum()
    var = (p * (pay - mean) ** 2).sum()
    return attempts * mean, float(np.sqrt(attempts * var))


# ───────────────────────── Q2 law of large numbers ─────────────────────────
def realised_edge(rng, params: Params, outcomes: int, sizes, budget: float = 4e7):
    """1 − ΣX/ΣD for N equal tickets, many repetitions per N. Returns percentiles per N
    (rows 5, 25, 50, 75, 95) and the theoretical standard deviation σ/√N."""
    _, sd = ladder_moments(outcomes, 1, params.rtp)
    e = entry_for(1.0, outcomes, 1, params.rtp)
    q, theory = [], []
    for n_tickets in sizes:
        reps = int(min(4000, max(200, budget / n_tickets)))
        edges = np.empty(reps)
        chunk = max(1, int(2e6 // n_tickets))
        for s in range(0, reps, chunk):
            m = min(chunk, reps - s)
            rungs = np.minimum(rng.geometric(0.5, size=(m, n_tickets)), outcomes)
            edges[s : s + m] = 1 - (e * 2.0 ** (rungs - 1)).mean(axis=1)
        q.append(np.percentile(edges, [5, 25, 50, 75, 95]))
        theory.append(sd / np.sqrt(n_tickets))
    return np.array(q).T, np.array(theory)


# ───────────────────────── Q3 holders against the number of players ─────────────────────────
@dataclass
class YearStats:
    growth: np.ndarray  # price at the end / price at the start, per seed
    trough: np.ndarray  # lowest price of the year / price at the start
    alice: np.ndarray  # Alice's ROI after exit, per seed (pooled over her class)


def holders_vs_players(rng, params: Params, sizes, days: int = 365, seeds=600):
    """`seeds` is a number or a function of the number of players."""
    out = {}
    for n in sizes:
        count = seeds(n) if callable(seeds) else seeds
        g, t, a = [], [], []
        for _ in range(count):
            w = pop.make_world(rng, n, params=params)
            p0 = w.price
            pop.run(w, rng, days)
            prices = np.asarray(w.log["price"])
            g.append(prices[-1] / p0)
            t.append(prices.min() / p0)
            roi = pop.exit_all(w) / w.start - 1
            alice = roi[w.rho == 0]
            if alice.size:
                a.append(alice.mean())
        out[n] = YearStats(np.array(g), np.array(t), np.array(a))
    return out


# ───────────────────────── Q4–Q6 one large population, many years ─────────────────────────
@dataclass
class Pooled:
    rho: np.ndarray
    start: np.ndarray
    final: np.ndarray
    gain_by_class: np.ndarray  # per seed, per class: Σ(final − start), as a share of all money
    fees: np.ndarray  # per seed: mint and burn fees, share of all money
    kept: np.ndarray  # per seed: what stays in the pool (genesis, fee bucket), share
    growth: np.ndarray


def pooled_years(rng, params: Params, players: int = 10_000, seeds: int = 20, days: int = 365):
    rho, start, final = [], [], []
    by_class, fees, kept, growth = [], [], [], []
    for _ in range(seeds):
        w = pop.make_world(rng, players, params=params)
        g0 = w.reserve - (w.start * w.dial.prdx_target * (1 - params.mint_fee)).sum()
        p0 = w.price
        pop.run(w, rng, days)
        growth.append(w.price / p0)
        f = pop.exit_all(w)
        money = w.start.sum()
        cls = pop.class_of(w.rho)
        by_class.append([(f - w.start)[cls == i].sum() / money for i in range(len(pop.CLASSES))])
        fees.append(w.fees_base / money)
        kept.append((w.reserve - g0) / money)
        rho.append(w.rho)
        start.append(w.start)
        final.append(f)
    return Pooled(
        np.concatenate(rho), np.concatenate(start), np.concatenate(final),
        np.array(by_class), np.array(fees), np.array(kept), np.array(growth),
    )


def pooled_loop(rng, params: Params, seeds: int = 20, days: int = 4 * 365, eps: float = 0.8):
    """The same pooling as `pooled_years`, under the loop: players arrive and leave, every player
    who ever took part counts with what they took (or would take leaving at the end)."""
    rho, start, final = [], [], []
    by_class, fees, kept, growth = [], [], [], []
    for _ in range(seeds):
        m = dyn.make_market(rng, params, dyn.Behaviour(eps=eps))
        g0, p0 = 1e-6, m.price
        dyn.run(m, rng, days)
        growth.append(m.price / p0)
        dyn.exit_all(m)
        r, s0, f = dyn.outcomes(m)
        money = s0.sum()
        cls = pop.class_of(r)
        by_class.append([(f - s0)[cls == i].sum() / money for i in range(len(pop.CLASSES))])
        fees.append(m.fees_base / money)
        kept.append((m.reserve - g0) / money)
        rho.append(r)
        start.append(s0)
        final.append(f)
    return Pooled(
        np.concatenate(rho), np.concatenate(start), np.concatenate(final),
        np.array(by_class), np.array(fees), np.array(kept), np.array(growth),
    )


def years_down_loop(rng, params: Params, eps=(0.5, 0.8, 1.2), seeds: int = 10, years: int = 4):
    """Under the loop: the calendar years whose price ends below its start, out of all years run."""
    down = total = 0
    for e in eps:
        for _ in range(seeds):
            m = dyn.make_market(rng, params, dyn.Behaviour(eps=e))
            p0 = m.price
            dyn.run(m, rng, years * 365)
            p = np.r_[p0, m.log["price"]]
            for y in range(years):
                down += p[(y + 1) * 365] < p[y * 365]
                total += 1
    return int(down), int(total)


# ───────────────────────── Q8 growth against volume ─────────────────────────
def growth_vs_volume(rng, params: Params, rates, players: int = 2000, seeds: int = 60,
                     days: int = 365):
    """Per simulated year: tickets' volume over the mean supply, and the price growth."""
    vol, growth, rate_of = [], [], []
    for r in rates:
        dial = pop.Dial(tickets_per_month=r)
        for _ in range(seeds):
            w = pop.make_world(rng, players, params=params, dial=dial)
            p0, s0 = w.price, w.supply
            pop.run(w, rng, days)
            burned = np.asarray(w.log["burned"])
            prices = np.asarray(w.log["price"])
            supply = w.reserve / prices  # G is fixed during the year
            prev = np.r_[s0, supply[:-1]]
            vol.append((burned / prev).sum())
            growth.append(prices[-1] / p0)
            rate_of.append(r)
    return np.array(vol), np.array(growth), np.array(rate_of)


# ───────────────────────── Q9 how much against how ─────────────────────────
@dataclass
class Grid:
    turnover: np.ndarray  # PRDX put through tickets per year, in shares of the holding
    lvls: np.ndarray
    expected: np.ndarray  # per turnover: E[PRDX at the end / at the start], exact
    median: np.ndarray  # [lvl, turnover]
    double: np.ndarray
    half: np.ndarray


def mining_grid(rng, params: Params, turnover, lvls, tickets: int = 24, players: int = 20_000):
    """A player too small to move the price puts turnover/tickets of their PRDX into each of
    `tickets` tickets a year, one draw each. His result in base is the price growth (shared by
    everyone) times this multiple in PRDX, which depends on the player alone."""
    turnover, lvls = np.asarray(turnover, float), np.asarray(lvls)
    edge = 1 - params.rtp
    expected = (1 - edge * turnover / tickets) ** tickets
    med = np.empty((lvls.size, turnover.size))
    dbl, hlf = np.empty_like(med), np.empty_like(med)
    for i, n in enumerate(lvls):
        e = entry_for(1.0, int(n), 1, params.rtp)
        for j, t in enumerate(turnover):
            s = t / tickets
            rungs = np.minimum(rng.geometric(0.5, size=(tickets, players)), n)
            mult = np.prod(1 - s + s * e * 2.0 ** (rungs - 1), axis=0)
            med[i, j] = np.median(mult)
            dbl[i, j] = (mult >= 2).mean()
            hlf[i, j] = (mult <= 0.5).mean()
    return Grid(turnover, lvls, expected, med, dbl, hlf)


# ───────────────────────── Q10–Q13 the feedback loop ─────────────────────────
from prdx_sim import dynamics as dyn  # noqa: E402


def loop_runs(rng, behaviour: "dyn.Behaviour", seeds: int, days: int, params: Params | None = None,
              shock_day: int | None = None, exodus_day: int | None = None) -> dict[str, np.ndarray]:
    """Many runs of one behaviour. Series are relative to day 0: reserve, price; counts as is."""
    keys = ("reserve", "price", "alices", "bobs", "y", "worst")
    out = {k: [] for k in keys}
    for _ in range(seeds):
        m = dyn.make_market(rng, params, behaviour)
        g0, p0 = m.reserve, m.price
        dyn.run(m, rng, days, shock_day, exodus_day)
        price = np.asarray(m.log["price"])
        out["reserve"].append(np.asarray(m.log["reserve"]) / g0)
        out["price"].append(price / p0)
        out["alices"].append(m.log["alices"])
        out["bobs"].append(m.log["bobs"])
        out["y"].append(m.log["y"])
        out["worst"].append(max(0.0, (1 - price[1:] / price[:-1]).max()))
    return {k: np.asarray(v, float) for k, v in out.items()}


@dataclass
class Phase:
    eps: np.ndarray
    r_star: np.ndarray
    growth: np.ndarray  # [r*, eps]: median reserve at the end over the start (at the stop if full)
    trend: np.ndarray  # [r*, eps]: median reserve, last year over the year before (nan: full)
    full: np.ndarray  # [r*, eps]: median year the players reached the capacity (nan: never)
    premium: np.ndarray  # [r*, eps]: median y − r* over the last year


def loop_phase(rng, eps, r_star, seeds: int = 8, days: int = 4 * 365, capacity: int = 200_000,
               log=print) -> Phase:
    eps, r_star = np.asarray(eps, float), np.asarray(r_star, float)
    gr, tr, full, pr = (np.full((r_star.size, eps.size), np.nan) for _ in range(4))
    for i, r in enumerate(r_star):
        for j, e in enumerate(eps):
            b = dyn.Behaviour(eps=e, r_star=r, capacity=capacity)
            trends, years, prem, grows = [], [], [], []
            for _ in range(seeds):
                m = dyn.make_market(rng, None, b)
                g0 = m.reserve
                dyn.run(m, rng, days, stop_full=True)
                res = np.asarray(m.log["reserve"])
                grows.append(res[-1] / g0)
                if res.size < days:
                    years.append(res.size / 365)
                    continue
                trends.append(res[-1] / res[-366])
                prem.append(np.mean(m.log["y"][-365:]) - r)
            gr[i, j] = np.median(grows)
            if len(years) > seeds / 2:
                full[i, j] = np.median(years)
            else:
                tr[i, j], pr[i, j] = np.median(trends), np.median(prem)
            log(f"phase eps={e:g} r*={r:g}: trend {tr[i, j]:.3g} full {full[i, j]:.3g}")
    return Phase(eps, r_star, gr, tr, full, pr)


# ───────────────────────── Q1b, Q8b identical tickets ─────────────────────────
def identical_tickets(rng, params: Params, outcomes: int, players: int):
    """N players, one identical ticket each, no cap (an infinite pool). Returns the payout per
    deposit of each rung, the players on each rung, and the exact shares."""
    k, p = single_draw_pmf(outcomes)
    pay = entry_for(1.0, outcomes, 1, params.rtp) * 2.0 ** (k - 1)
    counts = rng.multinomial(players, p)
    return pay, counts, p


def price_under_identical(rng, params: Params, outcomes: int, volume: float = 2.0,
                          share: float = 1e-7, points: int = 400, paths: int = 2000):
    """The price as a stream of identical tickets is settled. Each ticket's deposit is `share`
    of the starting supply (small enough for every ladder to fit L*P). x is the deposits so far
    over the starting supply. Tickets between points are drawn at once by rung counts."""
    k, p = single_draw_pmf(outcomes)
    pay = entry_for(share, outcomes, 1, params.rtp) * 2.0 ** (k - 1)
    total = int(volume / share)
    per_point = total // points
    supply = np.ones(paths)
    out = [np.ones(paths)]
    for _ in range(points):
        counts = rng.multinomial(per_point, p, size=paths)
        supply = supply - per_point * share + counts @ pay
        out.append(1 / supply)
    x = np.arange(points + 1) * per_point * share
    return x, np.array(out)
