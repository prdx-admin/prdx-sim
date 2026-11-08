# Figures

Made by `python -m prdx_sim.paper`; each figure has its own seed, so any one can be rebuilt alone
(`python -m prdx_sim.paper figures tickets`). The figures are built in up to six processes, one per
figure. PDF for print, PNG for the docs. `numbers.json` holds every value the docs cite, by figure, from
the run that drew the figure.

Colours are the app's five tones (prdx-front `src/styles.css`) at a lightness that reads on white, one
quantity each, in every figure: mine for tickets and miners, mint for the reserve and the mint fee, burn
for the price, the burned share and the burn fee, gold for holders, coral below zero. An ordered series
takes the steps of its tone, light to dark. Ink and grey carry the rest: a twin, the model without
feedback, a formula.

| File | Caption |
|------|---------|
| `fig-tickets` | The exact law of a one-draw ticket by level, no sample. Payout per deposit on the horizontal axis, its chance 2⁻ᵏ on the vertical (the top rung as often as the one below it). Payouts above the deposit in colour, below it in grey. The panel title gives P(X > D). |
| `fig-price` | (a) The example of docs section 6: a supply of 100 000 PRDX, tickets of 10 PRDX with one draw, no Mint or Burn, 2 000 runs, until the deposits reach twice the supply (20 000 tickets). One panel per level (4, 8, 12) on one price scale; MIN and MAX in the corner; top scale: deposits over the starting supply. Median, 5–95 %, dashed 1 / (1 − 0.125 V/P₀). The cap is enforced ticket by ticket. (b) Simulated years of 10 000 players at 0.25–8 tickets a month; dashed: exp(0.125 Σ D/P). |
| `fig-how-much` | A year of 24 one-draw tickets. Turnover T on the horizontal axis, the exact mean multiple (1 − 0.125 T/24)²⁴ in the grey row on top. (a) Median PRDX multiple, (b) P(×2 or more), %, (c) P(half or less), %. |
| `fig-numbers` | (a–c) Burned share 1 − ΣX/ΣD in a round of N identical tickets, N from 10 to 10¹⁰ (multinomial counts per rung): median, 25–75 % and 5–95 %; dashed 12.5 % ± 2σ/√N. (d) Share of years the price fell, against the number of players (100–100 000): 600 years per point up to 3 000 players, 300 at 10 000 and 30 000, 100 at 100 000; 95 % Wilson band. |
| `fig-classes` | Two models in two rows. Top: the closed population, 100 years of 20 000 players. Bottom: the loop, 20 runs of 4 years at ε = 0.8, every player who ever took part. (a, c) Gains by risk class, mint and burn fees, as shares of all money brought in; the bars sum to zero. (b, d) Wealth at exit over wealth brought in, by class: 5–95 %, 25–75 %, median, max; the key is in a fee row. Right: the share of the class that ended with a loss and at ×10 or more. |
| `fig-loop` | Entry and exit model, 20 runs of 4 years from 10 000 players: static arrivals (grey) against the loop at ε = 0.5, 0.8, 1.2 (light to dark in every panel). (a) Reserve, (b) price, (c) holders' growth y (30-day trailing mean) and r* = 5 %, (d) share of miners among participants. Median and 25–75 %. |
| `fig-phase` | The median of 8 runs of 4 years per cell. (a) Reserve after 4 years, G/G₀. (b) Holders' premium y − r* in the last year, %. Frame: ε = 1, the free-entry border. |
| `fig-shock-and-cap` | Paired runs at ε = 0.8, 40 pairs. (a) A win of L·P on day 730: shocked run over its twin, price and reserve. (b, c) Half the holders leave on day 730: holders' growth and holders against the twin. (d) Reserve after 4 years against the cap L, 20 runs each; above: median deepest one-day price fall. |
