# Paradox ecosystem simulator

Simulation of the [PARADOX](https://github.com/prdx-admin/prdx-docs) protocol on the contracts' own rules: PRDX backed by a reserve, MINT and BURN at G/P, and tickets — the right to mine. This repository is the simulation linked from the official docs.

## Official documentation

Read the protocol specification first (fees, pricing, Mine mechanics, St. Petersburg paradox adaptation):

| Language | Source |
|----------|--------|
| **English** | [en/docs.md](https://github.com/prdx-admin/prdx-docs/blob/main/en/docs.md) · [raw](https://raw.githubusercontent.com/prdx-admin/prdx-docs/main/en/docs.md) |
| **Russian** | [ru/docs.md](https://github.com/prdx-admin/prdx-docs/blob/main/ru/docs.md) · [raw](https://raw.githubusercontent.com/prdx-admin/prdx-docs/main/ru/docs.md) |

Repository: [github.com/prdx-admin/prdx-docs](https://github.com/prdx-admin/prdx-docs).

**How this repo relates to the contracts.** `src/prdx_sim/protocol.py` follows prdx-contracts in floating point: the pool moves the reserve G and the supply P, MINT and BURN keep G/P, and a ticket (a position) parks its deposit at open, burns it at activation and mints its payout at settlement. Admission is MAX ≤ L·P; RESHAPE, CANCEL (RTP · D back) and DRAWS are modelled. Defaults are the values of the testnet masters deployed on 2026-10-10: fees 16/1024, RTP 896/1024, L 128/1024, minimum entry 1 PRDX, opening price 1 base coin = 100 PRDX. A ticket whose entry falls under 1 PRDX steps its LVL down until it clears the floor (RESHAPE), or is not bought. The 24-hour grace period is not modelled: every ticket is revealed. Integer floors are left out.

**Price convention.** Price is base per PRDX, G/P.

**What is extra here.** Players and their risk profile ρ (`population.py`) are a model of behaviour; they are not part of the contracts.

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

## Make the figures

```bash
python -m prdx_sim.paper                    # all figures into figures/, PDF and PNG
python -m prdx_sim.paper figures tickets    # only the named ones
pytest -q                                   # protocol, conservation, batch-vs-exact, loop tests
```

Captions and the numbers they quote: [figures/README.md](figures/README.md).

## What is computed and how

Most answers about the protocol are exact; the simulation checks them and goes where no formula does.

| Part | Figure | Question | Method |
|------|--------|----------|--------|
| Mechanics | `fig-tickets` | N players buy the same ticket: who ends above the deposit, for LVL 2…24 | exact shares, one multinomial draw of 10 000 players |
| | `fig-price` | How the price grows as tickets are settled | exact law 1/(1 − 0.125·V/P₀); simulated years of 10 000 players against exp(0.125·Σ D/P) |
| | `fig-how-much` | How much one mines sets the mean, how one mines sets the shape | exact mean (1 − 0.125·T/24)^24; Monte Carlo of the distribution |
| | `fig-numbers` | How the realised edge converges with the number of tickets; holders against the number of players | Monte Carlo, ±2σ/√N; 100–100 000 players, Wilson intervals |
| Population | `fig-classes` | Who pays whom (sums to minus the fees), and outcomes inside each risk class | 100 years of 20 000 players |
| Dynamics | `fig-loop` | Growth brings Alices, the jackpot L·G brings Bobs: static players against the loop | entry and exit model, 20 runs of 4 years |
| | `fig-phase` | Where the loop settles, grows without bound or fades over (ε, r*) | 35 cells × 4 runs; the free-entry border ε = 1 |
| | `fig-shock-and-cap` | A win of L·P inside the loop; the cap L against the reserve and the tail | paired runs; 20 runs per L |

## Players

**Population.** Every player has a risk profile ρ ∈ [0, 1]. ρ = 0 is Alice: she mints and holds. As ρ grows, a player puts more of their PRDX into each ticket (up to 25 %), on a higher ladder (LVL 2 → 24) with fewer draws (8 → 1); ρ = 1 is Bob. Everything else is common: 90 % of the wealth minted at the start, two tickets a month for ρ > 0, exit at the end of the year. 30 % holders, the rest uniform in ρ; wealth is log-normal with a median of 100 base coins (10 000 PRDX at the opening price). A step is a day; tickets of one day are admitted against the supply at the start of the day (checked against one-by-one admission in `tests/test_batch_vs_exact.py`).

**Loop.** Alices arrive at a·e^{κ(y−r*)} and leave at h·e^{−κ(y−r*)}, where y is the 90-day price growth, annualised, and r* an outside yield. Bobs arrive at b·(L·G / J₀)^ε: lotto sales grow with the jackpot (Cook & Clotfelter 1993), ε is that elasticity. A Bob leaves under 20 % of what they brought. Free entry (κ → ∞) gives G^{1−ε} ∝ L^ε / r*: one stable size for ε < 1, growth without bound for ε > 1.

These behaviours are assumptions; the figures show them over ranges, and results are stated in dimensionless terms (V/P, T, ε, r*).

## Layout

| Path | Role |
|------|------|
| `src/prdx_sim/protocol.py` | the master's pool and the ticket, after prdx-contracts |
| `src/prdx_sim/population.py` | players on a risk profile, a day of the protocol, exit |
| `src/prdx_sim/dynamics.py` | the loop: entry and exit by growth and by the jackpot |
| `src/prdx_sim/experiments.py` | the numbers behind the figures |
| `src/prdx_sim/paper.py`, `sci.py` | the figures and their journal style |
| `tests/` | protocol, conservation, batch-vs-exact and loop tests |
