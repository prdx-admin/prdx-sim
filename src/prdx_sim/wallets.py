"""Wallets and ROI accounting for TON and PRDX positions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prdx_sim.system import ParadoxMaster


class TonWallet:
    def __init__(self, balance: float) -> None:
        self.balance = balance
        self.initial_balance = balance


class InvestmentTracker:
    """Tracks TON in, TON out, and mark-to-market PRDX position for ROI."""

    def __init__(self) -> None:
        self.total_ton_invested: float = 0.0
        self.total_ton_withdrawn: float = 0.0
        self.current_ton_in_system: float = 0.0

    def record_investment(self, ton_amount: float) -> None:
        self.total_ton_invested += ton_amount
        self.current_ton_in_system += ton_amount

    def record_withdrawal(self, ton_amount: float) -> None:
        self.total_ton_withdrawn += ton_amount
        if self.current_ton_in_system > 0:
            withdrawal_ratio = min(ton_amount / self.current_ton_in_system, 1.0)
            self.current_ton_in_system *= 1 - withdrawal_ratio

    def update_current_value(self, current_value_ton: float) -> None:
        self.current_ton_in_system = current_value_ton

    def get_roi(self) -> float:
        if self.total_ton_invested <= 0:
            return 0.0
        total_value = self.total_ton_withdrawn + self.current_ton_in_system
        net_profit = total_value - self.total_ton_invested
        return net_profit / self.total_ton_invested

    def get_funds_ratio_in_system(self) -> float:
        """Share of originally invested TON still marked in the system (0 = fully exited)."""
        if self.total_ton_invested <= 0:
            return 0.0
        return self.current_ton_in_system / self.total_ton_invested


class ParadoxWallet:
    def __init__(self) -> None:
        self.balance = 0.0
        self.investment_tracker = InvestmentTracker()

    def get_current_roi(self, system: ParadoxMaster) -> float:
        if self.balance > 0:
            current_ton_value, _ = system.estimate_burn(self.balance)
            self.investment_tracker.update_current_value(current_ton_value)
        return self.investment_tracker.get_roi()

    def get_funds_ratio_in_system(self, system: ParadoxMaster) -> float:
        if self.balance > 0:
            current_ton_value, _ = system.estimate_burn(self.balance)
            self.investment_tracker.update_current_value(current_ton_value)
        return self.investment_tracker.get_funds_ratio_in_system()
