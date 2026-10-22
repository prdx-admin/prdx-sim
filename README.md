# PARADOX (PRDX) protocol simulator

The simulator runs the [PARADOX](https://prdxcoin.com) protocol on the rules of its contracts: PRDX backed by a reserve, MINT and BURN at the price G/P, and tickets for mining PRDX. The simulator's figures appear in the [protocol documentation](https://docs.prdxcoin.com/en/).

[Website](https://prdxcoin.com) · [App](https://app.prdxcoin.com) · [Documentation](https://docs.prdxcoin.com/en/) · [Documentation source](https://github.com/prdx-admin/prdx-docs)

## Protocol documentation

Read the documentation before the simulator: it describes the fees, the PRDX price, mining and the rules of the St. Petersburg game.

| Language | Website | Source |
|----------|---------|--------|
| **English** | [docs.prdxcoin.com/en](https://docs.prdxcoin.com/en/) | [en/docs.md](https://github.com/prdx-admin/prdx-docs/blob/main/en/docs.md) · [raw](https://raw.githubusercontent.com/prdx-admin/prdx-docs/main/en/docs.md) |
| **Russian** | [docs.prdxcoin.com/ru](https://docs.prdxcoin.com/ru/) | [ru/docs.md](https://github.com/prdx-admin/prdx-docs/blob/main/ru/docs.md) · [raw](https://raw.githubusercontent.com/prdx-admin/prdx-docs/main/ru/docs.md) |

## The protocol in the simulator

**Relation to the contracts.** `src/prdx_sim/protocol.py` follows the rules of prdx-contracts in floating point. The treasury holds the reserve G and the supply P; MINT and BURN keep the PRDX price G/P. Buying a ticket debits the deposit D from the participant, but the deposit stays in the supply P. Activation burns the deposit; the payout is minted after the reveal. RESHAPE, CANCEL (RTP · D back) and DRAWS are modelled too. Defaults are the values of the testnet masters deployed on 2026-10-10: fees 16/1024, RTP 896/1024, L 128/1024, smallest MIN 1 PRDX, opening price 1 reserve coin = 100 PRDX.

**Ticket checks.** Mining starts only if the ticket's MIN is at least 1 PRDX and its top payout E · 2^(n−1) · a is at most L · P. The contract checks MIN at purchase and the limit at activation; the simulator runs both checks on the day of purchase. If a ticket fails either check, the participant lowers LVL (RESHAPE) at the same ticket price: MIN grows and the top payout shrinks. If even the LVL 2 ticket fails, the participant keeps the PRDX and tries another day; in the contract such a ticket stays in the INITIAL state.

**Simplifications.** The grace period is not modelled: every ticket is revealed on the day of purchase. Integer rounding is left out.

**Price convention.** The PRDX price is the reserve per 1 PRDX, G/P.

**What exists only in the simulator.** Participants and their risk profile ρ (`population.py`) form a model of behaviour. The contracts have no such layer.

Russian-language description of this repository: [ru.md](ru.md).

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
pytest -q                                   # protocol, conservation, batch-check, loop tests
```

Captions and the numbers they quote: [figures/README.md](figures/README.md).

## What is computed and how

Many quantities of the protocol follow exactly from formulas. The simulation checks those formulas and computes the quantities no formula gives.

| Part | Figure | Question | Method |
|------|--------|----------|--------|
| Mechanics | `fig-tickets` | N participants buy the same one-attempt ticket: the share of participants on each payout rung and the share whose payout exceeds the deposit, for LVL 2…24 | exact shares 2⁻ᵏ and one multinomial sample of 10 000 participants |
| | `fig-price` | How the PRDX price grows as identical tickets are mined | exact law 1/(1 − 0.125·V/P₀); yearly runs of 10 000 participants compared with exp(0.125·Σ D/P) |
| | `fig-how-much` | The yearly turnover T sets a participant's mean PRDX multiple, LVL sets the shape of the distribution | exact mean (1 − 0.125·T/24)^24; Monte Carlo of the distribution |
| | `fig-numbers` | How the burned share 1 − ΣX/ΣD converges to 12.5 % as the number of tickets N grows; how the share of years with a falling PRDX price depends on the number of participants | Monte Carlo, 12.5 % ± 2σ/√N; 100–100 000 participants, Wilson intervals |
| Population | `fig-classes` | Who pays whom: the gains of the risk classes sum to minus the fees; outcomes inside each class | 100 years of 20 000 participants |
| Dynamics | `fig-loop` | In the model, PRDX price growth attracts Alices and the top payout L·G attracts Bobs: a constant inflow of participants compared with the loop | entry and exit model, 20 runs of 4 years |
| | `fig-phase` | For which (ε, r*) the loop settles, grows without bound or fades | 35 cells × 8 runs of 4 years; the free-entry border ε = 1 |
| | `fig-shock-and-cap` | A payout of L·P and half the Alices leaving inside the loop; the limit L compared with the reserve and the deepest one-day price fall | paired runs, 40 pairs; 20 runs per value of L |

## Participants

**Population.** Every participant has a risk profile ρ ∈ [0, 1]. A participant with ρ = 0 is Alice: mints PRDX, holds them and buys no tickets. As ρ grows, a participant puts a larger share of their PRDX into each ticket (up to 25 %), picks a higher LVL (2 → 24) and fewer attempts (8 → 1). A participant with ρ = 1 is Bob. Everything else is common to all participants: 90 % of the wealth goes into MINT at the start, participants with ρ > 0 buy two tickets a month on average, and all participants exit at the end of the year. 30 % of participants have ρ = 0, the rest have ρ uniform. Wealth is log-normal with a median of 100 reserve coins (10 000 PRDX at the opening price). A model step is a day. Tickets of one day are checked against the supply at the start of the day; `tests/test_batch_vs_exact.py` compares this check with checking each ticket one by one.

**Loop.** Alices arrive at the rate a·e^{κ(y−r*)} and leave at the rate h·e^{−κ(y−r*)}. Here y is the 90-day PRDX price growth, annualised, and r* is an outside yield. Bobs arrive at the rate b·(L·G / J₀)^ε, where L·G is the top payout the limit allows, in reserve coins. This dependence comes from an observation: lotto sales grow with the top prize (Cook & Clotfelter 1993); ε is the elasticity of Bob arrivals to the top payout. A Bob leaves when less than 20 % of what they brought remains, and also at a constant rate of 1/180 a day. Each arriving Bob draws a risk profile ρ ∈ (0, 1] and buys tickets by the same rule as the population above, so the loop's outcomes split into the same risk classes. Both arrival streams are scaled by (1 − active participants / capacity): the number of potential participants is finite. Under free entry (κ → ∞) the model gives G^{1−ε} ∝ L^ε / r*: one stable equilibrium for ε < 1, a reserve growing without bound for ε > 1.

The participants' behaviour is set by the model's assumptions. The figures sweep the behaviour parameters over ranges, and the results are stated in dimensionless terms (V/P, T, ε, r*).

## Layout

| Path | Role |
|------|------|
| `src/prdx_sim/protocol.py` | the treasury (master) and the ticket, after prdx-contracts |
| `src/prdx_sim/population.py` | participants with a risk profile, a day of the protocol, exit |
| `src/prdx_sim/dynamics.py` | the loop: entry and exit by price growth and by the top payout |
| `src/prdx_sim/experiments.py` | the numbers behind the figures |
| `src/prdx_sim/paper.py`, `sci.py` | the figures and their journal style |
| `tests/` | protocol, conservation, batch-check and loop tests |
