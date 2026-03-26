"""Matplotlib charts and printed statistics for a finished simulation."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression

if TYPE_CHECKING:
    from prdx_sim.simulation import Simulation


def plot_simulation_results(simulation: Simulation) -> None:
    """Save system/ROI figures and print action and profile statistics."""
    system = simulation.system
    profile_rois: dict[str, list[float]] = defaultdict(list)
    profile_ages: dict[str, list[int]] = defaultdict(list)

    funds_ratios: list[float] = []

    for agent in simulation.agents:
        roi = agent.user.get_roi(system)
        funds_ratio = agent.user.get_funds_ratio_in_system(system)

        funds_ratios.append(funds_ratio)

        tracker = agent.user.prdx_wallet.investment_tracker
        if tracker.total_ton_invested > 0 or tracker.get_roi() != 0:
            profile_rois[agent.profile.name].append(roi)
            age = simulation.iterations - agent.birth_iteration
            profile_ages[agent.profile.name].append(age)

    plt.figure(figsize=(20, 12))

    ax1 = plt.subplot(2, 3, 1)
    ax1_twin = ax1.twinx()

    line1 = ax1.plot(system.history["ton_reserve"], linewidth=2, color="#2ecc71", label="TON Reserve")
    ax1.set_xlabel("Iteration")
    ax1.set_ylabel("TON Reserve", color="#2ecc71")
    ax1.tick_params(axis="y", labelcolor="#2ecc71")
    ax1.grid(True, alpha=0.3)

    line2 = ax1_twin.plot(
        system.history["prdx_supply"], linewidth=2, color="#e74c3c", label="PRDX Supply"
    )
    ax1_twin.set_ylabel("PRDX Supply", color="#e74c3c")
    ax1_twin.tick_params(axis="y", labelcolor="#e74c3c")

    ax1.set_title("TON Reserve & PRDX Supply", fontsize=14, fontweight="bold")

    lines = line1 + line2
    labels = [ln.get_label() for ln in lines]
    ax1.legend(lines, labels, loc="upper left")

    ax2 = plt.subplot(2, 3, 2)
    price_data = system.history["price"]
    iterations = range(len(price_data))

    ax2.plot(price_data, linewidth=2, color="#3498db", alpha=0.7, label="Price")

    if len(price_data) > 1:
        x = np.array(iterations).reshape(-1, 1)
        y = np.array(price_data)
        model = LinearRegression()
        model.fit(x, y)
        trend_line = model.predict(x)
        ax2.plot(
            iterations,
            trend_line,
            linewidth=3,
            color="#e74c3c",
            linestyle="--",
            alpha=0.8,
            label="Linear Trend",
        )

    ax2.set_title("Price (TON/PRDX) with Trend", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Iteration")
    ax2.set_ylabel("Price")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="best")

    ax3 = plt.subplot(2, 3, 3)
    mine_ops = system.history["mine_operations"]
    if len(mine_ops) > 0:
        successful = sum(1 for _, _, profit in mine_ops if profit > 0)
        failed = len(mine_ops) - successful
        colors = ["#2ecc71", "#e74c3c"]
        explode = (0.05, 0)
        ax3.pie(
            [successful, failed],
            labels=[f"Successful\n({successful})", f"Failed\n({failed})"],
            autopct="%1.1f%%",
            colors=colors,
            explode=explode,
            startangle=90,
            textprops={"fontsize": 10, "weight": "bold"},
        )
        ax3.set_title("Mining Operations", fontsize=14, fontweight="bold")
    else:
        ax3.text(
            0.5,
            0.5,
            "No mining\noperations",
            ha="center",
            va="center",
            fontsize=12,
            transform=ax3.transAxes,
        )
        ax3.set_title("Mining Operations", fontsize=14, fontweight="bold")

    ax4 = plt.subplot(2, 3, 4)
    if len(mine_ops) > 0:
        profits = [profit for _, _, profit in mine_ops]
        ax4.hist(profits, bins=100, color="#9b59b6", alpha=0.7, edgecolor="black", log=True)
        ax4.axvline(0, color="red", linestyle="--", linewidth=2, label="Break-even")
        ax4.axvline(
            np.mean(profits),
            color="orange",
            linestyle="--",
            linewidth=2,
            label=f"Mean: {np.mean(profits):.2f}",
        )
        ax4.set_title("Mining Profit Distribution (Log Scale)", fontsize=14, fontweight="bold")
        ax4.set_xlabel("Profit (PRDX)")
        ax4.set_ylabel("Frequency (Log)")
        ax4.legend()
        ax4.grid(True, alpha=0.3, axis="y")
    else:
        ax4.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12, transform=ax4.transAxes)
        ax4.set_title("Mining Profit Distribution", fontsize=14, fontweight="bold")

    ax5 = plt.subplot(2, 3, 5)
    if len(mine_ops) > 0:
        cumulative_ev: list[float] = []
        cumulative_deposit = 0.0
        cumulative_profit = 0.0
        for deposit, _reward, profit in mine_ops:
            cumulative_deposit += deposit
            cumulative_profit += profit
            if cumulative_deposit > 0:
                ev = cumulative_profit / cumulative_deposit
                cumulative_ev.append(ev)

        ax5.plot(cumulative_ev, linewidth=2, color="#e67e22", alpha=0.8)
        ax5.axhline(
            system.params.mining_ev,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Theoretical EV: {system.params.mining_ev:.1%}",
        )
        if len(cumulative_ev) > 50:
            window = 50
            smoothed = np.convolve(cumulative_ev, np.ones(window) / window, mode="valid")
            ax5.plot(
                range(window - 1, len(cumulative_ev)),
                smoothed,
                linewidth=3,
                color="#c0392b",
                label="Smoothed (50)",
            )

        ax5.set_ylim(system.params.mining_ev - 0.5, system.params.mining_ev + 0.5)
        ax5.set_title("Mining EV Convergence", fontsize=14, fontweight="bold")
        ax5.set_xlabel("Mining Operation #")
        ax5.set_ylabel("Cumulative EV")
        ax5.legend()
        ax5.grid(True, alpha=0.3)
    else:
        ax5.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12, transform=ax5.transAxes)
        ax5.set_title("Mining EV Convergence", fontsize=14, fontweight="bold")

    ax6 = plt.subplot(2, 3, 6)
    ax6.hist(funds_ratios, bins=50, alpha=0.7, color="#3498db", edgecolor="black", linewidth=0.5)
    ax6.set_xlabel("Share of funds still in system (of amount invested)")
    ax6.set_ylabel("Number of agents")
    ax6.set_title("Distribution of agents by share of funds in system", fontsize=14, fontweight="bold")
    ax6.grid(True, alpha=0.3)
    ax6.axvline(0, color="red", linestyle="--", alpha=0.7, label="Fully exited")
    ax6.axvline(1, color="green", linestyle="--", alpha=0.7, label="All funds in system")
    ax6.axvline(
        np.median(funds_ratios),
        color="orange",
        linestyle="--",
        alpha=0.7,
        label=f"Median: {np.median(funds_ratios):.2f}",
    )
    ax6.legend()

    plt.tight_layout()
    plt.savefig("paradox_system_results.png", dpi=300, bbox_inches="tight")
    plt.show()

    if profile_rois:
        num_roi_plots = len(profile_rois)
        cols_roi = 3
        rows_roi = (num_roi_plots + cols_roi - 1) // cols_roi

        fig_roi = plt.figure(figsize=(20, 5 * rows_roi))
        fig_roi.suptitle("ROI Analysis by Agent Profile", fontsize=16, fontweight="bold", y=0.98)

        for idx, (profile_name, rois) in enumerate(sorted(profile_rois.items())):
            ax = plt.subplot(rows_roi, cols_roi, idx + 1)

            if len(rois) > 0:
                ages = profile_ages[profile_name]
                parts = ax.violinplot([rois], positions=[0], widths=0.7, showmeans=True, showextrema=True)
                for pc in parts["bodies"]:
                    pc.set_facecolor("#3498db")
                    pc.set_alpha(0.7)

                y = rois
                x = np.random.normal(0, 0.04, size=len(y))
                ax.scatter(x, y, c=ages, cmap="viridis", alpha=0.3, s=15)

                mean_roi = np.mean(rois)
                median_roi = np.median(rois)
                std_roi = np.std(rois)

                ax.axhline(
                    mean_roi, color="red", linestyle="--", linewidth=2, label=f"Mean: {mean_roi:.2%}"
                )
                ax.axhline(
                    median_roi,
                    color="orange",
                    linestyle="--",
                    linewidth=1.5,
                    label=f"Median: {median_roi:.2%}",
                )
                ax.axhline(0, color="black", linestyle="-", linewidth=1, alpha=0.5)

                ax.set_title(f"{profile_name}\n(n={len(rois)}, σ={std_roi:.2%})", fontsize=11, fontweight="bold")
                ax.set_ylabel("ROI")
                ax.set_xticks([])
                ax.legend(loc="best", fontsize=8)
                ax.grid(True, alpha=0.3, axis="y")

                sm = plt.cm.ScalarMappable(
                    cmap="viridis", norm=plt.Normalize(vmin=0, vmax=simulation.iterations)
                )
                fig_roi.colorbar(sm, ax=ax, label="Agent Age (iterations)", shrink=0.5, aspect=10)
            else:
                ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes, fontsize=12)
                ax.set_title(profile_name, fontsize=11, fontweight="bold")

        plt.tight_layout()
        plt.savefig("paradox_roi_results.png", dpi=300, bbox_inches="tight")
        plt.show()

    print("\n" + "=" * 60)
    print("DETAILED STATISTICS")
    print("=" * 60)

    print("\nAgent actions:")
    for action, count in sorted(simulation.action_log.items(), key=lambda x: -x[1]):
        print(f" {action:20s}: {count:6d}")

    print("\nROI by profile:")
    for profile_name, rois in sorted(profile_rois.items()):
        if len(rois) > 0:
            print(f"\n {profile_name}:")
            print(f" Agents: {len(rois)}")
            print(f" Mean:   {np.mean(rois):8.2%}")
            print(f" Median: {np.median(rois):8.2%}")
            print(f" Std:    {np.std(rois):8.2%}")
            print(f" Min:    {np.min(rois):8.2%}")
            print(f" Max:    {np.max(rois):8.2%}")
            print(f" Q25:    {np.percentile(rois, 25):8.2%}")
            print(f" Q75:    {np.percentile(rois, 75):8.2%}")

    print("\nFunds-in-system ratio (all agents):")
    print(f" Count:  {len(funds_ratios)}")
    print(f" Mean:   {np.mean(funds_ratios):.3f}")
    print(f" Median: {np.median(funds_ratios):.3f}")
    print(f" Std:    {np.std(funds_ratios):.3f}")
    print(f" Min:    {np.min(funds_ratios):.3f}")
    print(f" Max:    {np.max(funds_ratios):.3f}")

    fr = np.array(funds_ratios)
    fully_exited = int(np.sum(fr == 0))
    partially_invested = int(np.sum((fr > 0) & (fr < 1)))
    fully_invested = int(np.sum(fr >= 1))

    print("\nDistribution by funds share:")
    print(f" Fully exited:        {fully_exited} ({fully_exited / len(funds_ratios) * 100:.1f}%)")
    print(f" Partially in system: {partially_invested} ({partially_invested / len(funds_ratios) * 100:.1f}%)")
    print(f" All funds in system: {fully_invested} ({fully_invested / len(funds_ratios) * 100:.1f}%)")

    mine_ops = system.history["mine_operations"]
    if len(mine_ops) > 0:
        print("\nMining statistics:")
        print(f" Total operations: {len(mine_ops)}")
        successful = [profit for _, _, profit in mine_ops if profit > 0]
        failed = [profit for _, _, profit in mine_ops if profit < 0]
        print(f" Profitable: {len(successful)} ({len(successful) / len(mine_ops) * 100:.1f}%)")
        print(f" Unprofitable: {len(failed)} ({len(failed) / len(mine_ops) * 100:.1f}%)")

        all_profits = [profit for _, _, profit in mine_ops]
        print(f"\n Profit mean:   {np.mean(all_profits):.2f} PRDX")
        print(f" Profit median: {np.median(all_profits):.2f} PRDX")
        print(f" Profit std:    {np.std(all_profits):.2f} PRDX")
        print(f" Profit min:    {np.min(all_profits):.2f} PRDX")
        print(f" Profit max:    {np.max(all_profits):.2f} PRDX")

        total_deposit = sum(deposit for deposit, _, _ in mine_ops)
        total_profit = sum(profit for _, _, profit in mine_ops)
        observed_ev = total_profit / total_deposit if total_deposit > 0 else 0.0

        print(f"\n Observed EV:    {observed_ev:.4f} ({observed_ev * 100:.2f}%)")
        print(f" Theoretical EV: {system.params.mining_ev:.4f} ({system.params.mining_ev * 100:.2f}%)")
        print(f" Abs. deviation: {abs(observed_ev - system.params.mining_ev):.4f}")

    print("\n" + "=" * 60 + "\n")
