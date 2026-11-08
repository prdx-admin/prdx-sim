import numpy as np
import pytest

from prdx_sim.protocol import Master, Params, admit, draw_payout, entry_for


def test_mint_and_burn_keep_the_price():
    m = Master(reserve=1000.0, supply=1_000_000.0)
    p0 = m.price
    m.mint(50.0)
    assert m.price == pytest.approx(p0)
    m.burn(10_000.0)
    assert m.price == pytest.approx(p0)


def test_open_parks_the_deposit_and_activation_burns_it_except_the_bottom_rungs():
    m = Master(reserve=1000.0, supply=1_000_000.0)
    t = m.open(100.0, 6, 2)
    assert m.supply == 1_000_000.0
    assert m.activate(t)
    assert m.supply == pytest.approx(1_000_000.0 - 100.0 + t.minimum)


@pytest.mark.parametrize("end", ["settle", "abort"])
def test_every_mined_ticket_ends_as_burn_d_mint_x(end):
    m = Master(reserve=1000.0, supply=1_000_000.0)
    t = m.open(100.0, 6, 3)
    assert m.activate(t)
    x = m.settle(t, np.random.default_rng(3)) if end == "settle" else m.abort(t)
    assert m.supply == pytest.approx(1_000_000.0 - 100.0 + x)


def test_cancel_is_the_ladder_with_one_outcome():
    params = Params()
    m = Master(reserve=1000.0, supply=1_000_000.0, params=params)
    t = m.open(100.0, 6)
    refund = m.cancel(t)
    assert refund == pytest.approx(entry_for(100.0, 1, 1, params.rtp))
    assert m.supply == pytest.approx(1_000_000.0 - 100.0 * (1 - params.rtp))


@pytest.mark.parametrize("n,a", [(2, 1), (6, 1), (6, 8), (12, 3)])
def test_every_ladder_returns_rtp_on_average(n, a):
    rng = np.random.default_rng(1)
    params = Params()
    x = draw_payout(rng, entry_for(1.0, n, a, params.rtp), n, a, size=400_000)
    assert x.mean() == pytest.approx(params.rtp, rel=0.02 if n < 10 else 0.1)


def test_the_gate_refuses_a_ceiling_above_the_cap_and_reshape_lets_it_in():
    m = Master(reserve=1000.0, supply=1000.0)
    t = m.open(100.0, 8)  # ceiling = 100 * 2*0.875/9 * 128 ≈ 2489 > 125
    assert not m.activate(t)
    assert t.state == "INITIAL"
    m.reshape(t, 2)
    assert t.deposit == 100.0
    assert m.activate(t)


def test_reshape_only_lowers_the_level_and_terms_hold_from_the_purchase():
    m = Master(1000.0, 100_000.0, Params(max_outcomes=8))
    with pytest.raises(ValueError):
        m.open(100.0, 9)
    t = m.open(100.0, 8)
    with pytest.raises(ValueError):
        m.reshape(t, 9)
    entry = t.entry
    m.reshape(t, 4)
    assert t.outcomes == 4 and t.entry > entry
    # a floor raised after the purchase does not touch the activation
    m.params = Params(max_outcomes=8, min_entry=t.entry * 2)
    assert m.activate(t)


def test_the_gate_measures_one_draw_whatever_the_number_of_draws():
    # one draw tops at E·2^(n−1); eight draws of the same terms meet the gate as eight tickets do
    m = Master(reserve=1000.0, supply=1000.0)
    one = m.open(10.0, 4, 1)
    eight = m.open(80.0, 4, 8)
    assert eight.entry == pytest.approx(one.entry)
    assert eight.max_yield == pytest.approx(one.max_yield)
    assert eight.total_max_yield == pytest.approx(8 * one.max_yield)
    assert m.fits(one) == m.fits(eight)
    n, ok = admit(np.array([80.0]), np.array([4]), np.array([8]), m.params.rtp, m.cap, m.params.min_entry)
    n1, ok1 = admit(np.array([10.0]), np.array([4]), np.array([1]), m.params.rtp, m.cap, m.params.min_entry)
    assert (n == n1).all() and (ok == ok1).all()
