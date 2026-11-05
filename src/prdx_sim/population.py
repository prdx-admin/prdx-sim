"""A population of players on the protocol, vectorised over players.

Each player has a risk profile rho in [0, 1]. rho = 0 is Alice: she mints and holds. As rho grows,
a player puts a larger share of their PRDX into each ticket, on a higher ladder with fewer draws;
rho = 1 is Bob. Everything else is common to all players, so that classes differ by risk alone:
the same starting share in PRDX, the same ticket frequency, no rebalancing, exit at the end.

A step is a day. Tickets bought on a day are admitted against the supply at the start of that day
(the deposits of one day are small next to the supply), activated and revealed the same day.
A ticket refused by the cap L*P is first reshaped down; if even LVL 2 does not fit, the player
keeps their PRDX and tries another day (in the contract the ticket would wait in INITIAL).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from prdx_sim.protocol import MIN_OUTCOMES, OPENING_PRICE, Params, admit, entry_for


@dataclass(frozen=True)
class Dial:
    """How rho maps to a strategy. Alice (rho = 0) never buys a ticket."""

    share_max: float = 0.25  # share of PRDX per ticket at rho = 1
    lvl_min: int = 2
    lvl_max: int = 24
    draws_max: int = 8  # at rho -> 0; one draw at rho = 1
    tickets_per_month: float = 2.0
    prdx_target: float = 0.9  # share of the starting wealth minted into PRDX

    def share(self, rho):
        return self.share_max * rho

    def lvl(self, rho):
        return np.rint(self.lvl_min + (self.lvl_max - self.lvl_min) * rho).astype(int)

    def draws(self, rho):
        return np.maximum(1, np.rint(self.draws_max - (self.draws_max - 1) * rho)).astype(int)


CLASSES = (
    ("Alice  ρ = 0", 0.0, 0.0),
    ("ρ 0–0.25", 1e-12, 0.25),
    ("ρ 0.25–0.5", 0.25, 0.5),
    ("ρ 0.5–0.75", 0.5, 0.75),
    ("Bob  ρ 0.75–1", 0.75, 1.0),
)


def class_of(rho: np.ndarray) -> np.ndarray:
    out = np.zeros(rho.shape, int)
    for i, (_, lo, hi) in enumerate(CLASSES[1:], start=1):
        out[(rho > lo - 1e-12) & (rho <= hi) & (rho > 0)] = i
    return out


def sample_rho(rng, n: int, holders: float = 0.3) -> np.ndarray:
    """A share `holders` of pure holders, the rest uniform on (0, 1]."""
    rho = 1 - rng.random(n)
    rho[rng.random(n) < holders] = 0.0
    return rho


@dataclass
class World:
    params: Params
    dial: Dial
    rho: np.ndarray
    start: np.ndarray  # starting wealth in base
    base: np.ndarray
    prdx: np.ndarray
    reserve: float
    supply: float
    genesis_prdx: float  # held by nobody among the players
    fees_base: float = 0.0
    fees_prdx: float = 0.0
    log: dict[str, list] = field(default_factory=lambda: {
        "price": [], "burned": [], "minted": [], "tickets": [], "refused": [], "reshaped": []})

    @property
    def price(self) -> float:
        return self.reserve / self.supply

    def wealth(self) -> np.ndarray:
        """What each player holds if they leave now: base plus PRDX burned at G/P less the fee."""
        return self.base + self.prdx * (1 - self.params.burn_fee) * self.price


def make_world(
    rng,
    n: int,
    *,
    params: Params | None = None,
    dial: Dial | None = None,
    holders: float = 0.3,
    wealth_sigma: float = 1.0,
    wealth_scale: float = 100.0,
    rho: np.ndarray | None = None,
) -> World:
    """`wealth_scale` is the median starting wealth in base coins (10 000 PRDX at the opening price)."""
    params, dial = params or Params(), dial or Dial()
    rho = sample_rho(rng, n, holders) if rho is None else rho
    start = wealth_scale * rng.lognormal(0.0, wealth_sigma, n)
    # a negligible genesis pool sets the opening price; then every player mints at it
    g0 = 1e-9 * start.sum()
    w = World(params, dial, rho, start, start.copy(), np.zeros(n), g0, g0 / OPENING_PRICE, g0 / OPENING_PRICE)
    spend = dial.prdx_target * start
    net = spend * (1 - params.mint_fee)
    w.prdx = net * w.supply / w.reserve  # every mint is at the same G/P
    w.supply += w.prdx.sum()
    w.reserve += net.sum()
    w.fees_base += (spend - net).sum()
    w.base -= spend
    return w


def day(w: World, rng) -> None:
    p, d = w.params, w.dial
    buy = (w.rho > 0) & (rng.random(w.rho.size) < d.tickets_per_month / 30)
    idx = np.flatnonzero(buy)
    burned = minted = 0.0
    refused = reshaped = 0
    if idx.size:
        rho = w.rho[idx]
        dep = d.share(rho) * w.prdx[idx]
        n, a = d.lvl(rho), d.draws(rho)
        asked = n.copy()
        n, ok = admit(dep, n, a, p.rtp, p.max_yield_rate * w.supply, p.min_entry)
        per_d = 2 * p.rtp / (a * (n + 1))  # E per unit of deposit
        refused = int((~ok).sum())
        reshaped = int(((n < asked) & ok).sum())
        idx, dep, n, a, per_d = idx[ok], dep[ok], n[ok], a[ok], per_d[ok]
        rungs = np.minimum(rng.geometric(0.5, size=(d.draws_max, idx.size)), n)
        used = np.arange(d.draws_max)[:, None] < a
        x = (per_d * dep * 2.0 ** (rungs - 1) * used).sum(axis=0)
        w.prdx[idx] += x - dep
        burned, minted = float(dep.sum()), float(x.sum())
        w.supply += minted - burned
    w.log["price"].append(w.price)
    w.log["burned"].append(burned)
    w.log["minted"].append(minted)
    w.log["tickets"].append(int(idx.size))
    w.log["refused"].append(refused)
    w.log["reshaped"].append(reshaped)


def run(w: World, rng, days: int = 365) -> World:
    for _ in range(days):
        day(w, rng)
    return w


def exit_all(w: World) -> np.ndarray:
    """Every player burns all their PRDX. Burns keep G/P, so the order does not matter."""
    fee = w.prdx * w.params.burn_fee
    net = w.prdx - fee
    out = net * w.price
    w.base = w.base + out
    w.reserve -= out.sum()
    w.supply -= net.sum()
    w.fees_prdx += fee.sum()
    w.prdx = np.zeros_like(w.prdx)
    return w.base


def day_exact(w: World, rng) -> None:
    """Reference for `day`: the same day through `protocol.Master`, one ticket at a time in a
    random order, each admitted against the supply its predecessors left. Slow; for tests."""
    from prdx_sim.protocol import Master

    p, d = w.params, w.dial
    m = Master(w.reserve, w.supply, p)
    buy = np.flatnonzero((w.rho > 0) & (rng.random(w.rho.size) < d.tickets_per_month / 30))
    burned = minted = 0.0
    done = 0
    for i in rng.permutation(buy):
        rho = w.rho[i : i + 1]
        dep = float(d.share(rho)[0] * w.prdx[i])
        n, a = int(d.lvl(rho)[0]), int(d.draws(rho)[0])
        while n > MIN_OUTCOMES and entry_for(dep, n, a, p.rtp) < p.min_entry:
            n -= 1  # RESHAPE up to the entry floor
        if entry_for(dep, n, a, p.rtp) < p.min_entry:
            continue
        t = m.open(dep, n, a)
        x = m.mine(t, rng)
        if x is None:
            continue
        w.prdx[i] += x - dep
        burned, minted, done = burned + dep, minted + x, done + 1
    w.supply = m.supply
    w.log["price"].append(w.price)
    w.log["burned"].append(burned)
    w.log["minted"].append(minted)
    w.log["tickets"].append(done)
    w.log["refused"].append(int(buy.size - done))
    w.log["reshaped"].append(0)
