"""The protocol with the feedback loop: players come and go by what the protocol shows them.

Alices compare the trailing price growth y with an outside yield r*. They arrive faster and
leave slower while y > r*:  arrivals = a0 * exp(k * (y - r*)),  exit hazard = h0 * exp(-k * (y - r*)).

Bobs respond to the jackpot, the largest payout one ticket may reach in the reserve coin,
J = L * P * (G / P) = L * G:  arrivals = b0 * (J / J0) ** eps. Lotto sales grow with the advertised
jackpot (Cook & Clotfelter 1993); eps is that elasticity. A Bob leaves when their wealth falls under
a share of what they brought, or by a constant hazard.

Both arrival streams are scaled by (1 - active / capacity): the pool of potential players is finite.
Every arrival mints 90 % of their wealth; every departure burns all their PRDX. Tickets follow the same
day as `population.day`: admission against the supply at the start of the day, reshape down, settle.

Bobs carry a risk profile rho in (0, 1] and buy their tickets by `population.Dial`: a larger share
of their PRDX, a higher ladder and fewer draws as rho grows. So the outcomes of the loop split into
the same risk classes as `population.CLASSES`. `Behaviour(profile=False)` gives every Bob the one
strategy of `ticket_share` and `lvl` with a single draw.

The loop: y > r* -> Alices mint -> G grows -> J = L*G grows -> Bobs arrive and mint -> their tickets
burn the edge -> y grows. The way back: a large win mints PRDX, y falls, Alices leave, G and J fall.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from prdx_sim.population import Dial
from prdx_sim.protocol import OPENING_PRICE, Params, admit

ALICE, BOB = 0, 1


@dataclass(frozen=True)
class Behaviour:
    r_star: float = 0.05  # Alice's outside yield, per year
    alice_rate: float = 25.0  # Alice arrivals a day at y = r*
    kappa: float = 8.0  # Alice's sensitivity to y - r*
    alice_hazard: float = 1 / 365  # her daily exit hazard at y = r*
    bob_rate: float = 25.0  # Bob arrivals a day at J = J0
    eps: float = 0.8  # jackpot elasticity of Bob arrivals
    bob_hazard: float = 1 / 180
    bob_ruin: float = 0.2  # a Bob leaves under this share of what they brought
    tickets_per_month: float = 4.0
    ticket_share: float = 0.15
    lvl: tuple[int, int] = (4, 16)
    capacity: int = 500_000  # potential players
    window: int = 90  # days of trailing growth
    wealth_sigma: float = 1.0
    wealth_scale: float = 100.0  # median starting wealth, base coins
    static: bool = False  # True: arrivals and hazards ignore y and J (no loop)
    profile: bool = True  # Bobs draw rho in (0, 1] and buy by Dial; False: one strategy for all
    dial: Dial = field(default_factory=Dial)


@dataclass
class Market:
    params: Params
    b: Behaviour
    kind: np.ndarray
    start: np.ndarray
    base: np.ndarray
    prdx: np.ndarray
    active: np.ndarray
    reserve: float
    supply: float
    j0: float
    n: int = 0
    fees_base: float = 0.0
    gone_gain: np.ndarray = field(default_factory=lambda: np.zeros(2))  # Σ(final − start) by kind
    gone_count: np.ndarray = field(default_factory=lambda: np.zeros(2, int))
    rho: np.ndarray = field(default_factory=lambda: np.zeros(0))  # 0 for Alices
    # every departed player, kept per player so that outcomes split by risk class
    gone_rho: list = field(default_factory=list)
    gone_start: list = field(default_factory=list)
    gone_final: list = field(default_factory=list)
    log: dict[str, list] = field(default_factory=lambda: {
        k: [] for k in ("price", "reserve", "alices", "bobs", "y", "jackpot", "burned", "minted")})

    @property
    def price(self) -> float:
        return self.reserve / self.supply


def _grow(m: Market, k: int) -> None:
    if m.n + k <= m.kind.size:
        return
    size = max(2 * m.kind.size, m.n + k)
    for name in ("kind", "start", "base", "prdx", "active", "rho"):
        old = getattr(m, name)
        new = np.zeros(size, old.dtype)
        new[: old.size] = old
        setattr(m, name, new)


def _compact(m: Market) -> None:
    """Fold departed players into per-kind sums, keep the arrays to the active ones."""
    act = m.active[: m.n]
    if act.sum() > 0.5 * m.n:
        return
    gone = ~act
    for k in (ALICE, BOB):
        sel = gone & (m.kind[: m.n] == k)
        m.gone_gain[k] += (m.base[: m.n][sel] - m.start[: m.n][sel]).sum()
        m.gone_count[k] += int(sel.sum())
    m.gone_rho.append(m.rho[: m.n][gone])
    m.gone_start.append(m.start[: m.n][gone])
    m.gone_final.append(m.base[: m.n][gone])
    keep = np.flatnonzero(act)
    for name in ("kind", "start", "base", "prdx", "active", "rho"):
        arr = getattr(m, name)
        new = np.zeros_like(arr)
        new[: keep.size] = arr[keep]
        setattr(m, name, new)
    m.n = keep.size


def _arrive(m: Market, rng, k: int, kind: int) -> None:
    if k <= 0:
        return
    _grow(m, k)
    s = slice(m.n, m.n + k)
    wealth = m.b.wealth_scale * rng.lognormal(0.0, m.b.wealth_sigma, k)
    spend = 0.9 * wealth
    net = spend * (1 - m.params.mint_fee)
    prdx = net * m.supply / m.reserve
    m.kind[s], m.start[s], m.base[s], m.prdx[s], m.active[s] = kind, wealth, wealth - spend, prdx, True
    m.rho[s] = 0.0 if kind == ALICE else (1 - rng.random(k) if m.b.profile else 1.0)
    m.supply += prdx.sum()
    m.reserve += net.sum()
    m.fees_base += (spend - net).sum()
    m.n += k


def _leave(m: Market, idx: np.ndarray) -> None:
    if idx.size == 0:
        return
    net = m.prdx[idx] * (1 - m.params.burn_fee)
    out = net * m.price
    m.base[idx] += out
    m.reserve -= out.sum()
    m.supply -= net.sum()
    m.prdx[idx] = 0.0
    m.active[idx] = False


def make_market(rng, params: Params | None = None, b: Behaviour | None = None,
                alices: int = 7_500, bobs: int = 2_500) -> Market:
    params, b = params or Params(), b or Behaviour()
    m = Market(params, b, np.zeros(0, int), np.zeros(0), np.zeros(0), np.zeros(0),
               np.zeros(0, bool), reserve=1e-6, supply=1e-6 / OPENING_PRICE, j0=1.0)
    _arrive(m, rng, alices, ALICE)
    _arrive(m, rng, bobs, BOB)
    m.j0 = 0.125 * m.reserve  # the reference jackpot is the default cap, whatever L the run uses
    return m


def trailing_growth(m: Market) -> float:
    """Annualised price growth over the last `window` days (0 before the window fills)."""
    p = m.log["price"]
    w = m.b.window
    if len(p) <= w:
        return m.b.r_star  # no history yet: neither pull nor push
    return (p[-1] / p[-1 - w]) ** (365 / w) - 1


def day(m: Market, rng, *, shock: bool = False, exodus: bool = False) -> None:
    p, b = m.params, m.b
    y = trailing_growth(m)
    jackpot = p.max_yield_rate * m.reserve
    act = m.active[: m.n]
    room = max(0.0, 1 - act.sum() / b.capacity)
    if b.static:
        ra, rb, ha = b.alice_rate, b.bob_rate, b.alice_hazard
    else:
        pull = float(np.clip(b.kappa * (y - b.r_star), -4.0, 4.0))
        ra = b.alice_rate * np.exp(pull)
        rb = b.bob_rate * (jackpot / m.j0) ** b.eps
        ha = b.alice_hazard * np.exp(-pull)
    ra, rb = min(ra, b.capacity / 30), min(rb, b.capacity / 30)
    _arrive(m, rng, rng.poisson(ra * room), ALICE)
    _arrive(m, rng, rng.poisson(rb * room), BOB)

    n = m.n
    kind, act = m.kind[:n], m.active[:n]
    # departures: Alices by hazard, Bobs by hazard or ruin
    wealth = m.base[:n] + m.prdx[:n] * m.price
    go_a = act & (kind == ALICE) & (rng.random(n) < min(ha, 1.0))
    go_b = act & (kind == BOB) & ((rng.random(n) < b.bob_hazard) | (wealth < b.bob_ruin * m.start[:n]))
    _leave(m, np.flatnonzero(go_a | go_b))

    if exodus:
        # half of the active Alices leave at once, everything else unchanged
        alices = np.flatnonzero(m.active[:n] & (kind == ALICE))
        _leave(m, rng.choice(alices, size=alices.size // 2, replace=False))

    if shock:
        # a win the size of the cap, L * P, paid to one active Bob (a top rung at the cap)
        bobs = np.flatnonzero(m.active[:n] & (kind == BOB))
        if bobs.size:
            win = p.max_yield_rate * m.supply
            m.prdx[rng.choice(bobs)] += win
            m.supply += win

    # tickets
    act = m.active[:n]
    idx = np.flatnonzero(act & (kind == BOB) & (rng.random(n) < b.tickets_per_month / 30))
    burned = minted = 0.0
    if idx.size:
        if b.profile:
            rho = m.rho[idx]
            dep = b.dial.share(rho) * m.prdx[idx]
            lvl, a = b.dial.lvl(rho), b.dial.draws(rho)
        else:
            dep = b.ticket_share * m.prdx[idx]
            lvl = rng.integers(b.lvl[0], b.lvl[1] + 1, size=idx.size)
            a = np.ones(idx.size, int)
        lvl, ok = admit(dep, lvl, a, p.rtp, p.max_yield_rate * m.supply, p.min_entry)
        per_d = 2 * p.rtp / (a * (lvl + 1))
        idx, dep, lvl, a, per_d = idx[ok], dep[ok], lvl[ok], a[ok], per_d[ok]
        draws = b.dial.draws_max
        rungs = np.minimum(rng.geometric(0.5, size=(draws, idx.size)), lvl)
        used = np.arange(draws)[:, None] < a
        x = (per_d * dep * 2.0 ** (rungs - 1) * used).sum(axis=0)
        m.prdx[idx] += x - dep
        burned, minted = float(dep.sum()), float(x.sum())
        m.supply += minted - burned

    act = m.active[:n]
    _compact_due = (len(m.log["price"]) % 30) == 0
    m.log["price"].append(m.price)
    m.log["reserve"].append(m.reserve)
    m.log["alices"].append(int((act & (kind == ALICE)).sum()))
    m.log["bobs"].append(int((act & (kind == BOB)).sum()))
    m.log["y"].append(y)
    m.log["jackpot"].append(jackpot)
    m.log["burned"].append(burned)
    m.log["minted"].append(minted)
    if _compact_due:
        _compact(m)


def run(m: Market, rng, days: int, shock_day: int | None = None,
        exodus_day: int | None = None, stop_full: bool = False) -> Market:
    """`stop_full`: end the run once the active players reach 90 % of the capacity."""
    for t in range(days):
        day(m, rng, shock=(t == shock_day), exodus=(t == exodus_day))
        if stop_full and m.log["alices"][-1] + m.log["bobs"][-1] >= 0.9 * m.b.capacity:
            break
    return m


def outcomes(m: Market) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """rho, wealth brought and wealth at exit of every player ever: the departed with what they took,
    the active with what they would take leaving now (PRDX burned at G/P less the fee)."""
    n = m.n
    now = m.base[:n] + m.prdx[:n] * (1 - m.params.burn_fee) * m.price
    rho = np.concatenate([*m.gone_rho, m.rho[:n]])
    start = np.concatenate([*m.gone_start, m.start[:n]])
    final = np.concatenate([*m.gone_final, now])
    return rho, start, final


def exit_all(m: Market) -> float:
    """Everyone still in burns their PRDX. Returns Σ(final − start) over all players ever."""
    _leave(m, np.flatnonzero(m.active[: m.n]))
    return float(m.gone_gain.sum() + (m.base[: m.n] - m.start[: m.n]).sum())
