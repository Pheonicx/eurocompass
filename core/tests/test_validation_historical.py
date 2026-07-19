from core.models import Confidence, Observation, SourceType, utc_now
from core.validation.historical import check_against_recent_history


def _obs(buy, sell=None):
    return Observation(
        bank_id="BRAC",
        currency="EUR",
        product_id="TT",
        buy=buy,
        sell=sell if sell is not None else buy + 3,
        collected_at=utc_now(),
        source_type=SourceType.PDF,
        confidence=Confidence.MEDIUM,
    )


def test_no_history_always_passes():
    """A brand-new bank/currency must be able to get its first data point."""
    assert check_against_recent_history(_obs(139.0), recent=[]) is None


def test_small_change_passes():
    recent = [_obs(139.0)]
    assert check_against_recent_history(_obs(139.5), recent) is None


def test_large_jump_is_rejected():
    recent = [_obs(139.0)]
    # ~14% jump — well beyond the 5% default threshold
    reason = check_against_recent_history(_obs(159.0), recent)
    assert reason is not None
    assert "%" in reason


def test_only_most_recent_entry_is_used():
    # recent[0] is what matters; a big change from an older entry further
    # back should not matter if the most recent one is close.
    recent = [_obs(139.0), _obs(100.0)]
    assert check_against_recent_history(_obs(139.5), recent) is None


def test_custom_threshold_is_respected():
    recent = [_obs(139.0)]
    # ~1.4% change: passes a loose 5% threshold, fails a strict 1% one
    assert check_against_recent_history(_obs(141.0), recent, max_change_pct=5.0) is None
    assert check_against_recent_history(_obs(141.0), recent, max_change_pct=1.0) is not None


def test_sell_spike_is_caught_even_when_buy_looks_normal():
    """
    Regression test for a real coverage gap: the check previously only
    compared `buy` against history, never `sell` — but the recommendation
    engine's cost math is built entirely on `sell`. A collector bug that
    corrupts sell while buy happens to look normal must be caught here,
    not sail through silently.
    """
    recent = [_obs(139.0, sell=142.0)]
    # buy barely moves (139.0 -> 139.2, ~0.1%), but sell jumps ~13%
    suspicious = _obs(139.2, sell=160.0)

    reason = check_against_recent_history(suspicious, recent)

    assert reason is not None
    assert "sell" in reason


def test_buy_spike_still_caught_when_sell_looks_normal():
    """The reverse case, for symmetry: a buy-only spike must still be caught."""
    recent = [_obs(139.0, sell=142.0)]
    # buy jumps ~5.4% (139.0 -> 146.5), sell only ~3.5% (142.0 -> 147.0,
    # still >= buy as Observation requires) — isolates a buy-only spike.
    suspicious = _obs(146.5, sell=147.0)

    reason = check_against_recent_history(suspicious, recent)

    assert reason is not None
    assert "buy" in reason
