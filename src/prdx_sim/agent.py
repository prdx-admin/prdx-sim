"""Agent profile and hybrid decision logic (mint / burn / mine / hold)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from prdx_sim.system import ParadoxMaster
from prdx_sim.user import User


@dataclass
class AgentProfile:
    """Psychological and strategy parameters for an agent."""

    name: str

    understanding: float  # [0, 1]
    risk: float  # [0, 1]
    patience: float  # [0, 1]
    emotional: float  # [0, 1]

    follow_trend: float  # [0, 1]
    buy_dip: float  # [0, 1]

    mine_willingness: float  # [0, 1]
    mine_range: tuple[int, int]

    panic_at: float  # negative ROI threshold for panic
    exit_at: float  # positive ROI threshold to consider exit

    target_position: float  # [0, 1] PRDX share of portfolio
    exit_strategy: str  # "full", "partial", "gradual"


class Agent:
    def __init__(self, profile: AgentProfile, initial_ton: float) -> None:
        self.profile = profile
        self.user = User(initial_ton)
        self.active = True
        self.birth_iteration = 0
        self.exit_progress = 0.0

    def think(self, system: ParadoxMaster) -> Optional[str]:
        """One decision step: returns action label or None if agent exited."""
        if not self.active:
            return None

        current_roi = self.user.get_roi(system)
        has_position = self.user.prdx_wallet.balance > 0

        price_trend = (system.current_price() / system.start_price) - 1

        if has_position:
            my_prdx_value = self.user.prdx_wallet.balance * system.current_price()
            my_total_value = my_prdx_value + self.user.ton_wallet.balance
            current_allocation = my_prdx_value / my_total_value if my_total_value > 0 else 0
        else:
            current_allocation = 0.0

        panic_level = 0.0
        if current_roi < self.profile.panic_at:
            loss_magnitude = abs(current_roi - self.profile.panic_at) / abs(self.profile.panic_at)
            panic_level = (
                self.profile.emotional * (1 - self.profile.understanding) * min(loss_magnitude, 1)
            )

        greed_level = 0.0
        if current_roi > self.profile.exit_at:
            profit_magnitude = (current_roi - self.profile.exit_at) / self.profile.exit_at
            greed_level = (1 - self.profile.patience) * (1 - self.profile.understanding) * min(
                profit_magnitude, 1
            )

        trend_signal = price_trend * self.profile.follow_trend

        dip_signal = 0.0
        if current_roi < 0 and self.profile.understanding > 0.3:
            dip_signal = self.profile.buy_dip * self.profile.understanding * abs(current_roi)

        if panic_level > 0.5 and has_position:
            if self.user.burn(system, self.user.prdx_wallet.balance):
                self.active = False
                return None

        if has_position and current_roi > self.profile.exit_at:
            exit_action = self._execute_exit_strategy(system, current_roi)
            if exit_action:
                return None

        weights = {"mint": 0.0, "burn": 0.0, "mine": 0.0, "hold": 0.0}

        if not has_position:
            weights["mint"] = self.profile.risk + max(trend_signal, 0)
        else:
            gap = self.profile.target_position - current_allocation
            if gap > 0:
                weights["mint"] = gap + dip_signal + max(trend_signal, 0)
                if dip_signal > 0 and self.profile.understanding > 0.6:
                    understanding_boost = self.profile.understanding * dip_signal
                    weights["mint"] += understanding_boost

        if has_position:
            excess = current_allocation - self.profile.target_position
            if excess > 0:
                weights["burn"] = excess

            weights["burn"] += panic_level + greed_level

            if trend_signal < 0 and self.profile.understanding < 0.5:
                weights["burn"] += abs(trend_signal) * self.profile.follow_trend

        if has_position and self.profile.mine_willingness > 0:
            base_mine_weight = self.profile.mine_willingness * self.profile.risk

            if current_roi < 0:
                if self.profile.understanding > 0.6:
                    understanding_penalty = 1.0 - abs(current_roi) * 0.4
                    weights["mine"] = base_mine_weight * understanding_penalty
                else:
                    desperation_boost = 1.0 + abs(current_roi) * 0.5
                    weights["mine"] = base_mine_weight * desperation_boost
            else:
                weights["mine"] = base_mine_weight

        weights["hold"] = self.profile.patience

        if has_position:
            distance = abs(current_allocation - self.profile.target_position)
            if distance < 0.1:
                weights["hold"] += self.profile.understanding

        if self.profile.understanding > 0.7:
            weights["hold"] += self.profile.understanding

        action = self._weighted_choice(weights)

        if action == "mint":
            return self._do_mint(system, has_position, current_allocation, dip_signal)
        if action == "burn":
            return self._do_burn(system, panic_level, greed_level, current_allocation)
        if action == "mine":
            return self._do_mine(system)
        return "HOLD"

    def _execute_exit_strategy(
        self, system: ParadoxMaster, current_roi: float
    ) -> Optional[str]:
        if not self.user.prdx_wallet.balance > 0:
            return None

        excess_roi = current_roi - self.profile.exit_at
        exit_probability = min(0.8, excess_roi * 2)

        if np.random.random() < exit_probability:
            if self.profile.exit_strategy == "full":
                if self.user.burn(system, self.user.prdx_wallet.balance):
                    self.active = False
                    return "EXIT"

            elif self.profile.exit_strategy == "partial":
                exit_ratio = 0.3 + 0.4 * (excess_roi / (1 + excess_roi))
                burn_amount = self.user.prdx_wallet.balance * exit_ratio
                if self.user.burn(system, burn_amount):
                    return "PARTIAL_EXIT"

            elif self.profile.exit_strategy == "gradual":
                self.exit_progress += 0.1 + 0.2 * excess_roi
                if self.exit_progress >= 1.0:
                    if self.user.burn(system, self.user.prdx_wallet.balance):
                        self.active = False
                        return "EXIT"
                else:
                    burn_amount = self.user.prdx_wallet.balance * 0.2
                    if self.user.burn(system, burn_amount):
                        return "PARTIAL_EXIT"

        return None

    def _weighted_choice(self, weights: dict[str, float]) -> str:
        total = sum(weights.values())
        if total == 0:
            return "hold"

        rand = np.random.random() * total
        for action, weight in weights.items():
            rand -= weight
            if rand <= 0:
                return action
        return "hold"

    def _do_mint(
        self,
        system: ParadoxMaster,
        has_position: bool,
        current_allocation: float,
        dip_signal: float,
    ) -> str:
        available = self.user.ton_wallet.balance
        if available <= 0:
            return "MINT_FAILED"

        if not has_position:
            amount = available * self.profile.risk * 0.5
        else:
            gap = self.profile.target_position - current_allocation
            base_ratio = max(gap, 0.05)

            if dip_signal > 0 and self.profile.understanding > 0.6:
                dip_boost = min(dip_signal * 0.2, 0.2)
                base_ratio += dip_boost

            amount = available * min(base_ratio, 0.3)

        amount = min(amount, available)
        if self.user.mint(system, amount):
            return "MINT"
        return "MINT_FAILED"

    def _do_burn(
        self,
        system: ParadoxMaster,
        panic_level: float,
        greed_level: float,
        current_allocation: float,
    ) -> str:
        available = self.user.prdx_wallet.balance
        if available <= 0:
            return "BURN_FAILED"

        if panic_level > 0.5:
            ratio = 0.3 + panic_level * 0.5
        elif greed_level > 0.5:
            ratio = 0.2 + greed_level * 0.3
        else:
            excess = current_allocation - self.profile.target_position
            ratio = min(max(excess, 0.1), 0.5)

        ratio = min(ratio, 0.9)
        amount = available * ratio
        if self.user.burn(system, amount):
            return "BURN"
        return "BURN_FAILED"

    def _do_mine(self, system: ParadoxMaster) -> str:
        available = self.user.prdx_wallet.balance
        if available <= 0:
            return "MINE_FAILED"

        min_n, max_n = self.profile.mine_range
        n = int(min_n + self.profile.risk * (max_n - min_n))

        base_ratio = 0.15
        n_penalty = (n - min_n) / (max_n - min_n) if max_n > min_n else 0
        ratio = base_ratio * (1 - 0.6 * n_penalty)

        deposit = available * ratio

        if self.user.mine(system, deposit, n):
            return "MINE"
        return "MINE_FAILED"
