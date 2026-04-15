"""Unit tests for the multi-bet table state machine."""

from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING

import pytest

from craps_lab.bets import BetType, Outcome
from craps_lab.dice import DiceRoll
from craps_lab.engine import ActiveBet, BetResolution, RollResolution, Table
from craps_lab.probability import pass_line_house_edge

if TYPE_CHECKING:
    from collections.abc import Iterable


class ScriptedRoller:
    """Yields a fixed sequence of :py:class:`DiceRoll` values.

    Satisfies :py:class:`craps_lab.play.RollSource` by structural
    typing — a ``roll()`` method returning a ``DiceRoll`` is all
    the engine needs. Used throughout the resolution tests to
    drive every branch deterministically without relying on a
    particular seed producing a particular sum.
    """

    def __init__(self, rolls: Iterable[DiceRoll]) -> None:
        self._rolls = iter(rolls)

    def roll(self) -> DiceRoll:
        return next(self._rolls)


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


class TestTableRollWithNoBets:
    """``roll()`` with no active bets advances the dice and resolves nothing."""

    def test_roll_returns_a_roll_resolution(self) -> None:
        result = Table(seed=42).roll()
        assert isinstance(result, RollResolution)

    def test_roll_contains_a_valid_dice_roll(self) -> None:
        result = Table(seed=42).roll()
        assert 2 <= result.roll.total <= 12

    def test_roll_returns_empty_resolutions_while_no_bets(self) -> None:
        result = Table(seed=42).roll()
        assert result.resolutions == ()

    def test_point_before_and_after_are_none_on_a_non_point_roll(self) -> None:
        # A come-out roll of 7 (or any natural / craps sum) leaves the table in
        # come-out phase, so point_before and point_after are both None even
        # with no active bets on the table.
        table = Table(roller=ScriptedRoller([DiceRoll(3, 4)]))
        result = table.roll()
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
        # the roller, not a legitimate random event.
        assert first != second

    def test_active_bets_snapshot_is_a_tuple(self) -> None:
        assert isinstance(Table(seed=42).active_bets, tuple)


class TestTableConstructorArguments:
    """Seed / roller are mutually exclusive at the constructor."""

    def test_passing_both_raises(self) -> None:
        with pytest.raises(ValueError, match="pass either seed or roller, not both"):
            Table(seed=1, roller=ScriptedRoller([DiceRoll(1, 1)]))

    def test_scripted_roller_is_accepted(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 4)]))
        assert table.roll().roll.total == 7


class TestPlaceBet:
    """``place_bet`` assigns monotonic ids and enforces phase rules."""

    def test_first_bet_id_is_one(self) -> None:
        table = Table(seed=42)
        assert table.place_bet(BetType.PASS_LINE, 5) == 1

    def test_pass_line_appears_in_active_bets(self) -> None:
        table = Table(seed=42)
        bet_id = table.place_bet(BetType.PASS_LINE, 5)
        (bet,) = table.active_bets
        assert bet.bet_id == bet_id
        assert bet.kind is BetType.PASS_LINE
        assert bet.amount == 5
        assert bet.point is None

    def test_pass_line_rejected_during_point_phase(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))  # come-out 6 → point on
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        with pytest.raises(ValueError, match="pass line can only be placed"):
            table.place_bet(BetType.PASS_LINE, 5)

    def test_pass_odds_rejected_during_come_out(self) -> None:
        table = Table(seed=42)
        with pytest.raises(ValueError, match="pass odds can only be placed"):
            table.place_bet(BetType.PASS_ODDS, 5)

    def test_pass_odds_inherits_table_point(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))  # come-out 6
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        odds_id = table.place_bet(BetType.PASS_ODDS, 10)
        odds_bet = next(b for b in table.active_bets if b.bet_id == odds_id)
        assert odds_bet.point == 6

    def test_unsupported_kind_raises_not_implemented(self) -> None:
        table = Table(seed=42)
        with pytest.raises(NotImplementedError, match="does not yet support"):
            table.place_bet(BetType.COME, 5)


class TestPassLineResolution:
    """Pass-line resolution across all branches of the resolver."""

    @pytest.mark.parametrize(
        ("d1", "d2", "total"),
        [(3, 4, 7), (6, 5, 11)],
    )
    def test_come_out_natural_wins(self, d1: int, d2: int, total: int) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(d1, d2)]))
        table.place_bet(BetType.PASS_LINE, 5)
        result = table.roll()
        assert result.roll.total == total
        (res,) = result.resolutions
        assert res.outcome is Outcome.WIN
        assert res.payout == 5
        assert table.active_bets == ()
        assert table.point is None

    @pytest.mark.parametrize(
        ("d1", "d2", "total"),
        [(1, 1, 2), (1, 2, 3), (6, 6, 12)],
    )
    def test_come_out_craps_loses(self, d1: int, d2: int, total: int) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(d1, d2)]))
        table.place_bet(BetType.PASS_LINE, 5)
        result = table.roll()
        assert result.roll.total == total
        (res,) = result.resolutions
        assert res.outcome is Outcome.LOSE
        assert res.payout == -5
        assert table.active_bets == ()
        assert table.point is None

    @pytest.mark.parametrize("point", [4, 5, 6, 8, 9, 10])
    def test_come_out_point_number_sets_point_and_travels_bet(self, point: int) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(point // 2, point - point // 2)]))
        bet_id = table.place_bet(BetType.PASS_LINE, 5)
        result = table.roll()
        assert result.roll.total == point
        assert result.resolutions == ()
        assert result.point_before is None
        assert result.point_after == point
        assert table.point == point
        (bet,) = table.active_bets
        assert bet.bet_id == bet_id
        assert bet.point == point

    def test_point_phase_point_hit_wins(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 2)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()  # come-out 6 sets point
        result = table.roll()  # point hit
        (res,) = result.resolutions
        assert res.outcome is Outcome.WIN
        assert res.payout == 5
        assert table.point is None
        assert table.active_bets == ()

    def test_point_phase_seven_out_loses(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(1, 6)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        result = table.roll()
        (res,) = result.resolutions
        assert res.outcome is Outcome.LOSE
        assert res.payout == -5
        assert table.point is None
        assert table.active_bets == ()

    def test_point_phase_non_resolving_roll_leaves_state_unchanged(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(2, 2)]))
        bet_id = table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        result = table.roll()
        assert result.resolutions == ()
        assert result.point_before == 6
        assert result.point_after == 6
        assert table.point == 6
        (bet,) = table.active_bets
        assert bet.bet_id == bet_id
        assert bet.point == 6


class TestPassOddsResolution:
    """Pass-odds resolution: true-odds payouts on win, full loss on seven-out."""

    @pytest.mark.parametrize(
        ("point", "come_out_dice", "point_dice", "amount", "expected_payout"),
        [
            # Point 4: 2:1 — $10 odds wins $20
            (4, DiceRoll(2, 2), DiceRoll(1, 3), 10, 20),
            # Point 5: 3:2 — $10 odds wins $15
            (5, DiceRoll(2, 3), DiceRoll(1, 4), 10, 15),
            # Point 6: 6:5 — $10 odds wins $12
            (6, DiceRoll(3, 3), DiceRoll(4, 2), 10, 12),
            # Point 8: 6:5 — $10 odds wins $12
            (8, DiceRoll(4, 4), DiceRoll(3, 5), 10, 12),
            # Point 9: 3:2 — $10 odds wins $15
            (9, DiceRoll(4, 5), DiceRoll(5, 4), 10, 15),
            # Point 10: 2:1 — $10 odds wins $20
            (10, DiceRoll(5, 5), DiceRoll(4, 6), 10, 20),
        ],
    )
    def test_wins_at_true_odds(
        self,
        point: int,
        come_out_dice: DiceRoll,
        point_dice: DiceRoll,
        amount: int,
        expected_payout: int,
    ) -> None:
        table = Table(roller=ScriptedRoller([come_out_dice, point_dice]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        assert table.point == point
        table.place_bet(BetType.PASS_ODDS, amount)
        result = table.roll()
        by_kind = {res.kind: res for res in result.resolutions}
        assert by_kind[BetType.PASS_LINE].outcome is Outcome.WIN
        assert by_kind[BetType.PASS_LINE].payout == 5
        assert by_kind[BetType.PASS_ODDS].outcome is Outcome.WIN
        assert by_kind[BetType.PASS_ODDS].payout == expected_payout

    def test_pass_odds_loses_on_seven_out(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(1, 6)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.PASS_ODDS, 10)
        result = table.roll()
        by_kind = {res.kind: res for res in result.resolutions}
        assert by_kind[BetType.PASS_ODDS].payout == -10

    def test_pass_odds_truncates_fractional_payouts_toward_zero(self) -> None:
        """A $7 pass-odds on point 6 (6:5) would pay $8.4; the casino pays $8."""
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 2)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.PASS_ODDS, 7)
        result = table.roll()
        odds_res = next(r for r in result.resolutions if r.kind is BetType.PASS_ODDS)
        assert odds_res.payout == 8  # int(7 * 6/5) = 8


class TestEngineConvergenceVsClosedForm:
    """Monte Carlo cross-check: engine pass-line edge matches closed-form.

    Runs 100 000 one-unit pass-line bets through the engine, computes
    the empirical mean payout per bet, and checks it against the
    closed-form house edge from :py:func:`pass_line_house_edge`
    (``-7/495 ~ -0.01414``). The tolerance uses the same 5-sigma
    framing as :py:mod:`tests.test_convergence` — a principled bound,
    deterministic under seed.
    """

    _NUM_TRIALS: int = 100_000
    _SEED: int = 0xBE77ED
    _TOLERANCE_SIGMA: float = 5.0

    def test_pass_line_edge_converges(self) -> None:
        table = Table(seed=self._SEED)
        total_payout = 0
        for _ in range(self._NUM_TRIALS):
            table.place_bet(BetType.PASS_LINE, 1)
            while True:
                result = table.roll()
                pass_line_resolutions = [
                    r for r in result.resolutions if r.kind is BetType.PASS_LINE
                ]
                if pass_line_resolutions:
                    total_payout += sum(r.payout for r in pass_line_resolutions)
                    break

        empirical_player_ev = total_payout / self._NUM_TRIALS
        # ``pass_line_house_edge`` is the *house*'s edge by convention — a
        # positive number — so the player's expected payoff per unit wagered
        # is its negation.
        expected_player_ev = -float(pass_line_house_edge())

        # Each one-unit pass-line bet has payoff +1 or -1 with probabilities
        # very close to 1/2, so Var(X) ≈ 1 per bet. The standard error of the
        # sample mean over N trials is ~1/sqrt(N); we allow 5 * SEM.
        sem = 1.0 / (self._NUM_TRIALS**0.5)
        tolerance = self._TOLERANCE_SIGMA * sem
        assert abs(empirical_player_ev - expected_player_ev) < tolerance
