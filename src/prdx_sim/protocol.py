"""Contract-faithful core: the master's pool (G, P) and the ticket (a position NFT).

Mirrors prdx-contracts `contracts/master/pool.tolk`, `master/collection.tolk` and
`position/mining.tolk` in floating point; the contracts' integer floors are left out.

The whole protocol moves two numbers, the reserve G and the supply P:

    mint    G + dG,  P + dG * P / G       price G/P unchanged (fee in base goes aside)
    burn    G - dG,  P - dP               price unchanged (fee in PRDX stays in P, set aside)
    ticket  G,       P - D + X            D burned at activation, X minted at settlement

A ticket is the right to mine: the deposit D is debited from the owner's wallet at open and
parked inside P; nothing is burned until activation. Every way a ticket ends is "burn D, mint X":
reveal pays the drawn ladder, abort pays the bottom rung, cancel pays RTP * D.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

MAX_FRACTION = 1024
MIN_OUTCOMES = 2
MAX_OUTCOMES = 32
MAX_ATTEMPTS = 8


# The testnet masters of 2026-10-10 opened at 1 base coin = 100 PRDX; their grace period is 24 hours.
# The model does not run the grace window: every ticket is revealed.
OPENING_PRICE = 0.01  # base per PRDX


@dataclass(frozen=True)
class Params:
    """Collection and pool parameters, as fractions of 1 (the contracts store x/1024); min_entry in PRDX.
    min_entry and max_outcomes are terms of the purchase: open checks them and nothing after it does."""

    mint_fee: float = 16 / MAX_FRACTION
    burn_fee: float = 16 / MAX_FRACTION
    rtp: float = 896 / MAX_FRACTION
    max_yield_rate: float = 128 / MAX_FRACTION
    min_entry: float = 1.0
    max_outcomes: int = MAX_OUTCOMES


def entry_for(deposit: float, outcomes: int, attempts: int, rtp: float) -> float:
    """E = 2 * D * RTP / (a * (n + 1)): the bottom rung of one draw (docs §6.2)."""
    return 2 * deposit * rtp / (attempts * (outcomes + 1))


def admit(deposit, outcomes, attempts, rtp: float, cap: float, min_entry: float):
    """Batch RESHAPE before activation: each ladder steps down while its entry is under min_entry or
    its ceiling E·2^(n-1)·a is over the cap; a lower n raises E and lowers the ceiling. Returns the
    outcomes and the mask of tickets that then pass both checks."""
    n = np.array(outcomes, copy=True)
    while True:
        e = 2 * rtp * deposit / (attempts * (n + 1))
        bad = ((e < min_entry) | (e * 2.0 ** (n - 1) * attempts > cap)) & (n > MIN_OUTCOMES)
        if not bad.any():
            break
        n = np.where(bad, n - 1, n)
    e = 2 * rtp * deposit / (attempts * (n + 1))
    return n, (e >= min_entry) & (e * 2.0 ** (n - 1) * attempts <= cap)


def ladder_max(entry: float, outcomes: int, attempts: int) -> float:
    """The ladder's ceiling, E * 2^(n-1) * a: what the admission gate compares with L * P."""
    return entry * 2 ** (outcomes - 1) * attempts


def draw_rungs(rng: np.random.Generator, outcomes: int, size) -> np.ndarray:
    """Rung index k in 1..n per draw: P(k) = 1/2^k for k < n, the top takes 1/2^(n-1)."""
    return np.minimum(rng.geometric(0.5, size=size), outcomes)


def draw_payout(
    rng: np.random.Generator, entry: float, outcomes: int, attempts: int, size=None
) -> np.ndarray:
    """Sum of `attempts` independent draws of the ladder, in PRDX."""
    shape = (attempts,) if size is None else (*np.atleast_1d(size), attempts)
    rungs = draw_rungs(rng, outcomes, shape)
    return (entry * 2.0 ** (rungs - 1)).sum(axis=-1)


@dataclass
class Ticket:
    """A position: deposit, ladder and the RTP frozen when it was bought."""

    deposit: float
    entry: float
    outcomes: int
    attempts: int
    rtp: float
    state: str = "INITIAL"  # INITIAL -> ACTIVATED -> COMPLETED | CANCELED
    payout: float = 0.0

    @property
    def maximum(self) -> float:
        return ladder_max(self.entry, self.outcomes, self.attempts)

    @property
    def minimum(self) -> float:
        return self.entry * self.attempts


@dataclass
class Master:
    """The master contract's pool: reserve G, supply P, and the two fee buckets."""

    reserve: float
    supply: float
    params: Params = field(default_factory=Params)
    fees_base: float = 0.0
    fees_prdx: float = 0.0  # a bucket inside `supply`, as in pool.tolk

    @property
    def price(self) -> float:
        """Base per PRDX: G / P."""
        return self.reserve / self.supply

    @property
    def cap(self) -> float:
        """The payout cap L * P that a ladder's ceiling must fit to activate."""
        return self.params.max_yield_rate * self.supply

    def mint(self, base: float) -> float:
        fee = base * self.params.mint_fee
        prdx = (base - fee) * self.supply / self.reserve
        self.reserve += base - fee
        self.supply += prdx
        self.fees_base += fee
        return prdx

    def burn(self, prdx: float) -> float:
        fee = prdx * self.params.burn_fee
        net = prdx - fee
        base = net * self.reserve / self.supply
        self.supply -= net
        self.reserve -= base
        self.fees_prdx += fee
        return base

    def open(self, deposit: float, outcomes: int, attempts: int = 1) -> Ticket:
        """Buy a ticket. The deposit stays in P until activation."""
        if not (MIN_OUTCOMES <= outcomes <= MAX_OUTCOMES and 1 <= attempts <= MAX_ATTEMPTS):
            raise ValueError("ladder out of range")
        if outcomes > self.params.max_outcomes:
            raise ValueError("outcomes above maxOutcomes")
        entry = entry_for(deposit, outcomes, attempts, self.params.rtp)
        if entry < self.params.min_entry:
            raise ValueError("entry below minEntryPrdx")
        return Ticket(deposit, entry, outcomes, attempts, self.params.rtp)

    def fits(self, ticket: Ticket) -> bool:
        return ticket.maximum <= self.cap

    def activate(self, ticket: Ticket) -> bool:
        """Admission: the ceiling fits L * P; then D is burned. The floor and the outcome limit were
        checked at open, and a reshape cannot leave them."""
        if ticket.state != "INITIAL" or not self.fits(ticket):
            return False
        self.supply -= ticket.deposit
        ticket.state = "ACTIVATED"
        return True

    def settle(self, ticket: Ticket, rng: np.random.Generator) -> float:
        """Reveal: the drawn ladder is minted whole."""
        if ticket.state != "ACTIVATED":
            raise ValueError("not activated")
        x = float(draw_payout(rng, ticket.entry, ticket.outcomes, ticket.attempts))
        self.supply += x
        ticket.state, ticket.payout = "COMPLETED", x
        return x

    def abort(self, ticket: Ticket) -> float:
        """Grace missed: the bottom rung of every draw."""
        if ticket.state != "ACTIVATED":
            raise ValueError("not activated")
        x = ticket.minimum
        self.supply += x
        ticket.state, ticket.payout = "COMPLETED", x
        return x

    def cancel(self, ticket: Ticket) -> float:
        """Before activation: RTP * D back, the rest burned. The same as a ladder with n = 1."""
        if ticket.state != "INITIAL":
            raise ValueError("cancel is pre-activation only")
        refund = ticket.deposit * ticket.rtp
        self.supply -= ticket.deposit - refund
        ticket.state, ticket.payout = "CANCELED", refund
        return refund

    def reshape(self, ticket: Ticket, outcomes: int) -> None:
        """Re-cut the ladder at the same deposit, attempts and frozen RTP, to a lower level. A lower
        level raises the entry, so the ticket stays inside the terms open checked."""
        if ticket.state != "INITIAL":
            raise ValueError("reshape is pre-activation only")
        if not MIN_OUTCOMES <= outcomes <= ticket.outcomes:
            raise ValueError("reshape only lowers the level")
        ticket.entry = entry_for(ticket.deposit, outcomes, ticket.attempts, ticket.rtp)
        ticket.outcomes = outcomes

    def mine(self, ticket: Ticket, rng: np.random.Generator) -> float | None:
        """Activate and reveal; a ticket refused by the gate is reshaped down until it fits."""
        while not self.fits(ticket) and ticket.outcomes > MIN_OUTCOMES:
            self.reshape(ticket, ticket.outcomes - 1)
        if not self.activate(ticket):
            return None
        return self.settle(ticket, rng)
