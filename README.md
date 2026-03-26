# Paradox ecosystem simulator

Agent-based simulation of the [PARADOX](https://github.com/prdx-admin/prdx-docs) protocol economy: a PRDX token backed by a TON reserve with Mint, Burn, and Mine. This repository is the simulation linked from the official docs.

## Official documentation

Read the protocol specification first (fees, pricing, Mine mechanics, St. Petersburg paradox adaptation):

| Language | Source |
|----------|--------|
| **English** | [en/docs.md](https://github.com/prdx-admin/prdx-docs/blob/main/en/docs.md) · [raw](https://raw.githubusercontent.com/prdx-admin/prdx-docs/main/en/docs.md) |
| **Russian** | [ru/docs.md](https://github.com/prdx-admin/prdx-docs/blob/main/ru/docs.md) · [raw](https://raw.githubusercontent.com/prdx-admin/prdx-docs/main/ru/docs.md) |

Repository: [github.com/prdx-admin/prdx-docs](https://github.com/prdx-admin/prdx-docs).

**How this repo relates to the docs.** The math for Mint and Burn follows the documented formulas (commission on TON for Mint, on PRDX for Burn; pool updates). Mine uses the documented minimum reward, geometric rewards, outcome probabilities, negative EV, and the maximum-reward cap vs supply. Default parameters match the protocol table: \(\phi_{\text{mint}}=\phi_{\text{burn}}=0.015625\), \(EV_{\text{mine}}=-0.125\), \(L_{\text{mine}}=0.125\).

**Price convention.** The documentation sometimes expresses the spot as \(P_{\text{base}}=S/R\) (PRDX per TON in the worked examples). The code reports **TON per PRDX** as `ton_reserve / prdx_supply`, i.e. \(R/S\) — the same pool state, inverse units.

**What is extra here.** On top of the on-chain rules, the simulator adds heuristic *agents* (profiles, emotions, trends) to study aggregate behaviour; that layer is not part of the smart contracts.

Russian-language overview of this repo: [ru.md](ru.md).

---

## Setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Optional dev tools:

```bash
pip install -e ".[dev]"
```

## Run the notebook

```bash
jupyter notebook paradox_model.ipynb
```

The import cell adds `src` to `sys.path` when working from the repo root, or use `pip install -e .` as above.

## What this package models

- **Mint / burn** with protocol-aligned fees  
- **Mine** with negative expected value and the emission cap check  
- **Nine preset agent profiles** (risk, patience, mining appetite, exit rules, etc.)  
- **Outputs**: console summary, `paradox_system_results.png`, `paradox_roi_results.png`

## Layout

| Path | Role |
|------|------|
| `src/prdx_sim/` | Library code (pool, agents, simulation, plotting) |
| `paradox_model.ipynb` | Parameters, run, plots |
