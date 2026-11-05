# Contributing to prdx-sim

prdx-sim runs the PARADOX protocol on the rules of its contracts and draws the figures of the
[protocol documentation](https://docs.prdxcoin.com/en/). Its model of participants also drives the
TRIAL market in the [app](https://app.prdxcoin.com). Patches that make the model more accurate are
welcome.

## What a patch can change

| Part | Files | What a patch does |
|------|-------|-------------------|
| Protocol | `src/prdx_sim/protocol.py` | fixes a place where the simulator differs from the contracts, with a link to the section of the documentation |
| Participants | `src/prdx_sim/population.py`, `src/prdx_sim/dynamics.py` | changes how participants arrive, leave, pick a risk profile and spend their wealth |
| Experiments and figures | `src/prdx_sim/experiments.py`, `src/prdx_sim/paper.py` | adds a question the figures do not answer yet, or a better method for an existing one |

The model of participants needs the most work: the contracts have no such layer, and every rule in
it is an assumption.

Simplifications listed in the README, each a task of its own:

- the grace period: every ticket is revealed on the day of purchase;
- integer rounding: amounts are floats;
- the step: a model step is a day, while the app's TRIAL market splits a day into hours.

## What stays as it is

- **The protocol's rules.** `protocol.py` follows the contracts. A change to the rules themselves
  is proposed in the issues of [prdx-docs](https://github.com/prdx-admin/prdx-docs), not here.
- **The defaults.** `Params` holds the values of the testnet masters. A figure may sweep other
  values; the defaults stay.

## Changing the model of participants

- State the assumption: what participants do and what it rests on, data or a publication. For
  example, Bob arrivals grow with the top payout after Cook & Clotfelter (1993).
- State results in dimensionless terms (V/P, T, ε, r*), as the figures do.
- Draw every random number from the `numpy.random.Generator` the caller passes in. A run with the
  same seed gives the same numbers.

## Checks before a pull request

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
python -m prdx_sim.paper <figure>   # every figure the change touches
```

- GitHub runs `ruff check src tests` and `pytest -q` on every pull request; both must pass.
- Commit the regenerated PNG files in `figures/`: the documentation embeds them. PDF files stay
  out of the repository.
- Update the numbers that `figures/README.md` quotes from the regenerated figures.

## The pull request

The description states:

- which rule or assumption changed, and its source;
- which figures changed, with images before and after;
- which test covers the change.

## The app's TRIAL market

The app's TRIAL mode runs a port of this model. A parity test compares the port with prdx-sim
runs: the number of Alices, the number of Bobs and the 90-day price growth. We port merged changes
of the model to the app ourselves.

## License of contributions

The Work is under the [PRDX License 1.0](LICENSE). Its section 3 covers contributions: a patch
you send may be used by prdx-admin, the copyright holder, for any purpose. There is nothing to
sign.

## Discussion

- [Issues](https://github.com/prdx-admin/prdx-sim/issues) of this repository: bugs, proposals,
  questions.
- The project's chat in Telegram: [t.me/prdxcoinchat](https://t.me/prdxcoinchat).

Issues and pull requests are written in English.
