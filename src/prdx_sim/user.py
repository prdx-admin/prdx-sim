"""User actions: mint, burn, mine."""

from __future__ import annotations

import numpy as np

from prdx_sim.system import ParadoxMaster
from prdx_sim.wallets import ParadoxWallet, TonWallet


class User:
    def __init__(self, ton_balance: float) -> None:
        self.ton_wallet = TonWallet(ton_balance)
        self.prdx_wallet = ParadoxWallet()
        self.initial_ton_balance = ton_balance

    def mint(self, system: ParadoxMaster, ton_amount: float) -> bool:
        if ton_amount > self.ton_wallet.balance or ton_amount <= 0:
            return False

        prdx_amount, ton_to_reserve = system.estimate_mint(ton_amount)

        self.ton_wallet.balance -= ton_amount
        self.prdx_wallet.balance += prdx_amount
        self.prdx_wallet.investment_tracker.record_investment(ton_amount)

        system.ton_reserve += ton_to_reserve
        system.prdx_supply += prdx_amount

        return True

    def burn(self, system: ParadoxMaster, prdx_amount: float) -> bool:
        if prdx_amount > self.prdx_wallet.balance or prdx_amount <= 0:
            return False

        ton_amount, prdx_to_burn = system.estimate_burn(prdx_amount)

        self.ton_wallet.balance += ton_amount
        self.prdx_wallet.balance -= prdx_amount
        self.prdx_wallet.investment_tracker.record_withdrawal(ton_amount)

        system.ton_reserve -= ton_amount
        system.prdx_supply -= prdx_to_burn

        return True

    def mine(self, system: ParadoxMaster, prdx_deposit: float, outcomes_count: int) -> bool:
        if prdx_deposit > self.prdx_wallet.balance or prdx_deposit <= 0:
            return False

        outcomes = system.estimate_mine(prdx_deposit, outcomes_count)

        if outcomes[-1] > system.params.mine_limit * system.prdx_supply:
            return False

        rand = np.random.randint(0, 2**53)
        index = 0
        while (rand & 1) and (index < outcomes_count - 1):
            rand >>= 1
            index += 1

        reward = outcomes[index]
        profit = reward - prdx_deposit

        system.history["mine_operations"].append((prdx_deposit, reward, profit))

        self.prdx_wallet.balance += profit
        system.prdx_supply += profit

        return True

    def get_roi(self, system: ParadoxMaster) -> float:
        return self.prdx_wallet.get_current_roi(system)

    def get_net_profit(self) -> float:
        """Net TON P&L vs initial wallet (excluding PRDX mark)."""
        return self.ton_wallet.balance - self.initial_ton_balance

    def get_funds_ratio_in_system(self, system: ParadoxMaster) -> float:
        return self.prdx_wallet.get_funds_ratio_in_system(system)
