"""Multi-agent simulation loop and orchestration."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
import numpy as np
from tqdm import tqdm

from prdx_sim.agent import Agent, AgentProfile
from prdx_sim.system import ParadoxMaster


def generate_ton_balance() -> float:
    """Sample initial TON balance from a log-normal distribution."""
    mean_log = np.log(100)
    sigma_log = 0.8
    balance = np.random.lognormal(mean_log, sigma_log)
    return max(balance, 10.0)


class Simulation:
    """Runs agents for many iterations and records system history."""

    def __init__(
        self,
        profile_counts: Mapping[str, int],
        new_agents_per_iteration: int,
        iterations: int,
        *,
        profiles: Mapping[str, AgentProfile] | None = None,
    ) -> None:
        self.system = ParadoxMaster()
        self.agents: list[Agent] = []
        self.profile_counts = dict(profile_counts)
        self.new_agents_per_iteration = new_agents_per_iteration
        self.iterations = iterations
        self.current_iteration = 0
        if profiles is None:
            from prdx_sim.profiles import DEFAULT_PROFILES

            self.profiles: Mapping[str, AgentProfile] = DEFAULT_PROFILES
        else:
            self.profiles = profiles
        self.action_log: defaultdict[str, int] = defaultdict(int)

        for profile_name, count in self.profile_counts.items():
            for _ in range(count):
                self._create_agent(profile_name)

    def _create_agent(self, profile_name: str) -> None:
        profile = self.profiles[profile_name]
        ton_balance = generate_ton_balance()
        agent = Agent(profile, ton_balance)
        agent.birth_iteration = self.current_iteration
        self.agents.append(agent)

    def run(self) -> None:
        total_agents = sum(self.profile_counts.values())
        new_total = total_agents + self.new_agents_per_iteration * self.iterations

        print("\n" + "=" * 60)
        print("PARADOX SIMULATION")
        print("=" * 60)
        print(f"Initial agents: {total_agents}")
        print(f"New agents per iteration: {self.new_agents_per_iteration}")
        print(f"Expected agents at end: {new_total}")
        print(f"Iterations: {self.iterations}")
        print("\nInitial state:")
        print(f" TON reserve: {self.system.ton_reserve:.2f}")
        print(f" PRDX supply: {self.system.prdx_supply:.2f}")
        print(f" Price: {self.system.start_price:.10f} TON/PRDX")
        print("=" * 60 + "\n")

        for iteration in tqdm(range(self.iterations), desc="Simulation", ncols=80):
            self.current_iteration = iteration
            if self.new_agents_per_iteration > 0:
                profile_name = np.random.choice(list(self.profile_counts.keys()))
                for _ in range(self.new_agents_per_iteration):
                    self._create_agent(profile_name)

            for agent in self.agents:
                if agent.active:
                    action = agent.think(self.system)
                    if action:
                        self.action_log[action] += 1

            self.system.record_snapshot()

        active_count = sum(1 for a in self.agents if a.active)
        print("\n" + "=" * 60)
        print("SIMULATION COMPLETE")
        print("=" * 60)
        print("Final state:")
        print(f" TON reserve: {self.system.ton_reserve:.2f}")
        print(f" PRDX supply: {self.system.prdx_supply:.2f}")
        print(f" Price: {self.system.current_price():.10f} TON/PRDX")
        price_change = (self.system.current_price() / self.system.start_price) - 1
        print(f" Price change: {price_change * 100:+.2f}%")
        print("\nAgents:")
        print(f" Total created: {len(self.agents)}")
        print(f" Active: {active_count}")
        print(f" Exited: {len(self.agents) - active_count}")
        print(f"\nMining operations: {len(self.system.history['mine_operations'])}")
        print("=" * 60 + "\n")

    def plot_results(self) -> None:
        from prdx_sim.plots import plot_simulation_results

        plot_simulation_results(self)
