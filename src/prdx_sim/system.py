"""Core pool state: TON reserve, PRDX supply, and history for analysis."""

from __future__ import annotations

from typing import Any

from prdx_sim.params import SystemParams


class ParadoxMaster:
    """Constant-product style pool: price = TON reserve / PRDX supply."""

    def __init__(self, initial_ton: float = 1, initial_prdx: float = 1000) -> None:
        self.ton_reserve = initial_ton
        self.prdx_supply = initial_prdx
        self.start_price = self.current_price()
        self.params = SystemParams()

        self.history: dict[str, Any] = {
            "ton_reserve": [initial_ton],
            "prdx_supply": [initial_prdx],
            "price": [self.start_price],
            "mine_operations": [],  # (deposit, reward, profit)
        }

    def current_price(self) -> float:
        """Spot PRDX price in TON per PRDX."""
        return self.ton_reserve / self.prdx_supply

    def estimate_mint(self, ton_amount: float) -> tuple[float, float]:
        """Return (prdx_minted, ton_added_to_reserve) for a mint of `ton_amount` TON."""
        ton_to_reserve = ton_amount * (1 - self.params.mint_commission)
        prdx_amount = ton_to_reserve * self.prdx_supply / self.ton_reserve
        return prdx_amount, ton_to_reserve

    def estimate_burn(self, prdx_amount: float) -> tuple[float, float]:
        """Return (ton_received, prdx_burned_after_fee) for burning `prdx_amount` PRDX."""
        prdx_to_burn = prdx_amount * (1 - self.params.burn_commission)
        ton_amount = prdx_to_burn * self.ton_reserve / self.prdx_supply
        return ton_amount, prdx_to_burn

    def estimate_mine(self, prdx_deposit: float, outcomes_count: int) -> list[float]:
        """Possible mine rewards for `outcomes_count` geometric outcomes."""
        min_reward = (2 * prdx_deposit * (1 + self.params.mining_ev)) / (outcomes_count + 1)
        return [min_reward * (2**i) for i in range(outcomes_count)]

    def record_snapshot(self) -> None:
        """Append current reserves, supply, and price to history."""
        self.history["ton_reserve"].append(self.ton_reserve)
        self.history["prdx_supply"].append(self.prdx_supply)
        self.history["price"].append(self.current_price())
