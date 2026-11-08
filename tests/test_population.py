import numpy as np

from prdx_sim.population import CLASSES, class_of, exit_all, make_world, run


def test_no_base_coin_is_made_or_lost():
    """Players' total gain plus what stays in the pool equals minus the fees."""
    rng = np.random.default_rng(5)
    w = make_world(rng, 2000)
    g0 = w.reserve - (w.start * w.dial.prdx_target * (1 - w.params.mint_fee)).sum()
    run(w, rng, 120)
    final = exit_all(w)
    gain = (final - w.start).sum()
    kept = w.reserve - g0  # genesis' gain and the value of the burn-fee bucket
    assert np.isclose(gain + kept + w.fees_base, 0.0, atol=1e-9 * w.start.sum())
    # the fee bucket and genesis are all that is left in the pool
    assert np.isclose(w.reserve, (w.genesis_prdx + w.fees_prdx) * w.price)


def test_mining_moves_value_from_risk_to_holders():
    rng = np.random.default_rng(6)
    w = make_world(rng, 5000)
    run(w, rng, 365)
    roi = exit_all(w) / w.start - 1
    cls = class_of(w.rho)
    alice = roi[cls == 0].mean()
    bob = roi[cls == len(CLASSES) - 1].mean()
    assert alice > 0 > bob
