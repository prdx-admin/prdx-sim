import numpy as np

from prdx_sim.dynamics import Behaviour, exit_all, make_market, run


def test_the_loop_makes_and_loses_no_base_coin():
    rng = np.random.default_rng(9)
    m = make_market(rng, b=Behaviour(eps=0.8))
    g_start = 1e-6  # the genesis reserve
    run(m, rng, 400, shock_day=200)
    gain = exit_all(m)
    # all players' gain + fees + what stays in the pool (genesis and its growth) = 0
    assert np.isclose(gain + m.fees_base + (m.reserve - g_start), 0.0,
                      atol=1e-9 * (m.start[: m.n].sum() + abs(gain) + m.fees_base))


def test_elasticity_one_is_the_border():
    # Bobs with risk profiles spread one run widely, so the border is read off the median of six runs
    def growth(eps, seed):
        rng = np.random.default_rng(seed)
        m = make_market(rng, b=Behaviour(eps=eps))
        run(m, rng, 3 * 365)
        r = np.asarray(m.log["reserve"])
        return r[-1] / r[-366]  # last year over the year before

    def median(eps):
        return float(np.median([growth(eps, s) for s in range(6)]))

    assert median(0.5) < 1.3 < median(1.3)


def test_bobs_carry_risk_profiles_and_every_player_is_accounted_for():
    from prdx_sim.dynamics import outcomes
    from prdx_sim.population import class_of

    rng = np.random.default_rng(5)
    m = make_market(rng, b=Behaviour(eps=0.8))
    run(m, rng, 400)
    rho, start, final = outcomes(m)
    assert rho.size == start.size == final.size == m.gone_count.sum() + m.n
    assert set(np.unique(class_of(rho))) == {0, 1, 2, 3, 4}
    # what all players ever take or would take, plus the fees, plus what stays in the pool = what they brought
    burn_fees = m.prdx[: m.n].sum() * m.params.burn_fee * m.price
    kept = m.reserve - m.prdx[: m.n].sum() * m.price  # genesis and the PRDX of past burn fees
    assert np.isclose(final.sum() + m.fees_base + burn_fees + kept, start.sum(), rtol=1e-9)


def test_one_strategy_without_profiles():
    rng = np.random.default_rng(6)
    m = make_market(rng, b=Behaviour(profile=False))
    run(m, rng, 60)
    assert np.all(m.rho[: m.n][m.kind[: m.n] == 1] == 1.0)
