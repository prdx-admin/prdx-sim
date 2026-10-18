# Figures

Made by `python -m prdx_sim.paper`; each figure has its own seed, so any one can be rebuilt alone
(`python -m prdx_sim.paper figures tickets`). PDF for print, PNG for the docs.

| File | Caption |
|------|---------|
| `fig-tickets` | 10 000 players buy the same one-draw ticket, no cap. Bars: share of players on each rung (log scale); circles: exact share 2⁻ᵏ. Orange rungs pay less than the deposit, blue more. The panel title gives the exact P(X > D). |
| `fig-price` | (a) Price as identical tickets are settled, deposits fixed at 10⁻⁷ of supply; dashed: 1 / (1 − 0.125 V/P₀); nested opaque bands: 5–95 % of 2 000 runs for LVL 2, 4, 8, 12, 16, 20, 24, the spread growing with the level. (b) Simulated years of 10 000 players at 0.25–8 tickets a month; dashed: exp(0.125 Σ D/P). |
| `fig-how-much` | A year of 24 one-draw tickets. Turnover T on the horizontal axis, the exact mean multiple (1 − 0.125 T/24)²⁴ in the grey row on top. (a) Median PRDX multiple, (b) P(×2 or more), %, (c) P(half or less), %. |
| `fig-numbers` | (a–c) Burned share 1 − ΣX/ΣD in a round of N identical tickets: median, 25–75 % and 5–95 %; dashed 12.5 % ± 2σ/√N. (d) Share of years the price ends below its start against the number of players (100–100 000), 95 % Wilson band. |
| `fig-classes` | 100 years of 20 000 players. (a) Gains by risk class, mint and burn fees, as shares of all money brought in; the bars sum to zero within 10⁻¹⁵. (b) Distribution of wealth at exit over wealth brought in, by class. |
| `fig-loop` | Entry and exit model, 20 runs of 4 years from 10 000 players: static arrivals against the loop at ε = 0.5, 0.8, 1.2. (a) Reserve, (b) price, (c) holders' growth y (30-day trailing mean) and r* = 5 %, (d) share of Bobs. Median and 25–75 %. |
| `fig-phase` | 8 runs of 4 years per cell. (a) Reserve after 4 years, G/G₀. (b) Holders' premium y − r* in the last year, %. Dashed: ε = 1, the free-entry border. |
| `fig-shock-and-cap` | Paired runs at ε = 0.8, 40 pairs. (a) A win of L·P on day 730: shocked run over its twin. (b, c) Half the Alices leave on day 730: holders' growth and Alices against the twin. (d) Reserve after 4 years against the cap L, 20 runs each; above: median deepest one-day price fall. |
