"""Unit tests for the multi-bet table state machine scaffolding."""

from __future__ import annotations

from fractions import Fraction

import pytest

from craps_lab.bets import BetType, Outcome
from craps_lab.engine import ActiveBet, BetResolution, RollResolution, Table


class TestActiveBet:
    """Construction and validation of :py:class:`ActiveBet`."""

    def test_minimal_construction(self) -> None:
        bet = ActiveBet(bet_id=1, kind=BetType.PASS_LINE, amount=5)
        assert bet.bet_id == 1
        assert bet.kind is BetType.PASS_LINE
        assert bet.amount == 5
        assert bet.point is None

    def test_with_point(self) -> None:
        bet = ActiveBet(bet_id=2, kind=BetType.PASS_ODDS, amount=10, point=6)
        assert bet.point == 6

    def test_equal_bets_are_equal_and_hashable(self) -> None:
        a = ActiveBet(bet_id=1, kind=BetType.PASS_LINE, amount=5)
        b = ActiveBet(bet_id=1, kind=BetType.PASS_LINE, amount=5)
        assert a == b
        assert hash(a) == hash(b)

    def test_is_frozen(self) -> None:
        bet = ActiveBet(bet_id=1, kind=BetType.PASS_LINE, amount=5)
        with pytest.raises(AttributeError):
            bet.amount = 10  # type: ignore[misc]

    @pytest.mark.parametrize("bad", [True, False, 1.0, Fraction(1, 1), "1"])
    def test_rejects_non_int_bet_id(self, bad: object) -> None:
        with pytest.raises(TypeError, match="bet_id must be an int"):
            ActiveBet(bet_id=bad, kind=BetType.PASS_LINE, amount=5)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [0, -1])
    def test_rejects_non_positive_bet_id(self, bad: int) -> None:
        with pytest.raises(ValueError, match="bet_id must be positive"):
            ActiveBet(bet_id=bad, kind=BetType.PASS_LINE, amount=5)

    @pytest.mark.parametrize("bad", [True, 1.0, Fraction(5, 1), "5"])
    def test_rejects_non_int_amount(self, bad: object) -> None:
        with pytest.raises(TypeError, match="amount must be an int"):
            ActiveBet(bet_id=1, kind=BetType.PASS_LINE, amount=bad)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [0, -5])
    def test_rejects_non_positive_amount(self, bad: int) -> None:
        with pytest.raises(ValueError, match="amount must be positive"):
            ActiveBet(bet_id=1, kind=BetType.PASS_LINE, amount=bad)

    @pytest.mark.parametrize("bad_point", [2, 3, 7, 11, 12])
    def test_rejects_non_point_number(self, bad_point: int) -> None:
        with pytest.raises(ValueError, match="point must be one of"):
            ActiveBet(bet_id=1, kind=BetType.PASS_LINE, amount=5, point=bad_point)

    def test_rejects_non_int_point(self) -> None:
        with pytest.raises(TypeError, match="point must be an int or None"):
            ActiveBet(bet_id=1, kind=BetType.PASS_LINE, amount=5, point=True)


class TestBetResolution:
    """Shape and immutability of :py:class:`BetResolution`."""

    def test_construction(self) -> None:
        res = BetResolution(
            bet_id=1,
            kind=BetType.PASS_LINE,
            amount=5,
            outcome=Outcome.WIN,
            payout=5,
        )
        assert res.bet_id == 1
        assert res.kind is BetType.PASS_LINE
        assert res.outcome is Outcome.WIN
        assert res.payout == 5

    def test_is_frozen(self) -> None:
        res = BetResolution(
            bet_id=1,
            kind=BetType.PASS_LINE,
            amount=5,
            outcome=Outcome.WIN,
            payout=5,
        )
        with pytest.raises(AttributeError):
            res.payout = 10  # type: ignore[misc]


class TestTableInitialState:
    """A fresh Table starts in come-out phase with no bets."""

    def test_point_is_none(self) -> None:
        assert Table(seed=42).point is None

    def test_active_bets_is_empty(self) -> None:
        assert Table(seed=42).active_bets == ()


class TestTableRollScaffolding:
    """Scaffolding: ``roll()`` advances the dice but does not yet resolve bets."""

    def test_roll_returns_a_roll_resolution(self) -> None:
        result = Table(seed=42).roll()
        assert isinstance(result, RollResolution)

    def test_roll_contains_a_valid_dice_roll(self) -> None:
        result = Table(seed=42).roll()
        assert 2 <= result.roll.total <= 12

    def test_roll_returns_empty_resolutions_while_no_bets(self) -> None:
        result = Table(seed=42).roll()
        assert result.resolutions == ()

    def test_point_before_and_after_are_none_initially(self) -> None:
        result = Table(seed=42).roll()
        assert result.point_before is None
        assert result.point_after is None

    def test_roll_is_deterministic_under_seed(self) -> None:
        a = Table(seed=42).roll()
        b = Table(seed=42).roll()
        assert a.roll == b.roll

    def test_successive_rolls_advance_the_stream(self) -> None:
        table = Table(seed=42)
        first = table.roll().roll
        second = table.roll().roll
        # The PCG64 stream over two consecutive draws is overwhelmingly
        # unlikely to repeat the exact same (die1, die2) pair. Two back-
        # to-back identical rolls with this seed would indicate a bug in
        # the roller, not a legitimate random event, so asserting they
        # differ is safe under the golden-sequence contract.
        assert first != second

    def test_active_bets_snapshot_is_isolated_from_internal_list(self) -> None:
        """``active_bets`` returns a tuple so external callers cannot mutate state."""
        table = Table(seed=42)
        snapshot = table.active_bets
        assert isinstance(snapshot, tuple)
