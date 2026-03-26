"""Global economic parameters for the simulated AMM-style pool."""

from dataclasses import dataclass


@dataclass
class SystemParams:
    """Fee and mining parameters (fractions of amount or supply where noted)."""

    mint_commission: float = 0.015625
    burn_commission: float = 0.015625
    mining_ev: float = -0.125
    mine_limit: float = 0.125
