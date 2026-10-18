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
    def growth(eps):
        rng = np.random.default_rng(4)
        m = make_market(rng, b=Behaviour(eps=eps))
        run(m, rng, 3 * 365)
        r = np.asarray(m.log["reserve"])
        return r[-1] / r[-366]  # last year over the year before

    assert growth(0.5) < 1.3 < growth(1.3)
