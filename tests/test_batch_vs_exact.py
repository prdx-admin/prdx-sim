"""The vectorised day admits a day's tickets against the supply at the start of the day; the
contract admits them one by one. Over many years the two must give the same distribution."""

import numpy as np

from prdx_sim.population import day, day_exact, make_world


def years(step, seed: int, n: int = 40, days: int = 120, count: int = 300):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(count):
        w = make_world(rng, n)
        p0 = w.price
        for _ in range(days):
            step(w, rng)
        out.append(w.price / p0)
    return np.log(out)


def test_batch_admission_matches_one_by_one():
    a, b = years(day, 1), years(day_exact, 2)
    # means of log growth within 3 standard errors, quartiles within a tenth of the spread
    se = np.sqrt(a.var() / a.size + b.var() / b.size)
    assert abs(a.mean() - b.mean()) < 3 * se
    spread = np.percentile(a, 75) - np.percentile(a, 25)
    for q in (25, 50, 75):
        assert abs(np.percentile(a, q) - np.percentile(b, q)) < 0.1 * spread + 3 * se
