"""Unit tests for the multi-bet table state machine."""

from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING

import pytest

from craps_lab.bets import BetType, Outcome
from craps_lab.dice import DiceRoll
from craps_lab.engine import ActiveBet, BetResolution, RollResolution, Table
from craps_lab.probability import dont_pass_house_edge, pass_line_house_edge

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


class TestPlaceBetPhaseRules:
    """``place_bet`` enforces per-kind phase rules and linked-bet rules."""

    def test_first_bet_id_is_one(self) -> None:
        table = Table(seed=42)
        assert table.place_bet(BetType.PASS_LINE, 5) == 1

    def test_bet_ids_increment_across_placements(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        first = table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        second = table.place_bet(BetType.PASS_ODDS, 10)
        assert second == first + 1

    @pytest.mark.parametrize("kind", [BetType.PASS_LINE, BetType.DONT_PASS])
    def test_line_bets_rejected_during_point_phase(self, kind: BetType) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        with pytest.raises(ValueError, match="come-out phase"):
            table.place_bet(kind, 5)

    @pytest.mark.parametrize("kind", [BetType.COME, BetType.DONT_COME])
    def test_come_bets_rejected_during_come_out(self, kind: BetType) -> None:
        table = Table(seed=42)
        with pytest.raises(ValueError, match="point is established"):
            table.place_bet(kind, 5)

    def test_pass_odds_rejected_during_come_out(self) -> None:
        table = Table(seed=42)
        with pytest.raises(ValueError, match="point is established"):
            table.place_bet(BetType.PASS_ODDS, 5)

    def test_pass_odds_rejected_without_pass_line(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        table.place_bet(BetType.DONT_PASS, 5)  # has a don't pass but not a pass line
        table.roll()
        with pytest.raises(ValueError, match="existing pass line bet"):
            table.place_bet(BetType.PASS_ODDS, 5)

    def test_dont_pass_odds_rejected_without_dont_pass(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        with pytest.raises(ValueError, match="existing dont pass bet"):
            table.place_bet(BetType.DONT_PASS_ODDS, 5)

    def test_pass_odds_auto_inherits_point(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        odds_id = table.place_bet(BetType.PASS_ODDS, 10)
        odds_bet = next(b for b in table.active_bets if b.bet_id == odds_id)
        assert odds_bet.point == 6

    def test_dont_pass_odds_auto_inherits_point(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        table.place_bet(BetType.DONT_PASS, 5)
        table.roll()
        odds_id = table.place_bet(BetType.DONT_PASS_ODDS, 12)
        odds_bet = next(b for b in table.active_bets if b.bet_id == odds_id)
        assert odds_bet.point == 6

    def test_pass_odds_rejects_explicit_linked_bet_id(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        pass_id = table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        with pytest.raises(ValueError, match="does not accept linked_bet_id"):
            table.place_bet(BetType.PASS_ODDS, 10, linked_bet_id=pass_id)

    def test_come_odds_requires_linked_bet_id(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 4)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()  # point 6
        table.place_bet(BetType.COME, 5)
        table.roll()  # come bet travels to 8
        with pytest.raises(ValueError, match="requires linked_bet_id"):
            table.place_bet(BetType.COME_ODDS, 10)

    def test_come_odds_rejects_id_of_wrong_kind(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        pass_id = table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        with pytest.raises(ValueError, match="must link to a come bet"):
            table.place_bet(BetType.COME_ODDS, 10, linked_bet_id=pass_id)

    def test_come_odds_rejects_linked_come_without_point(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        come_id = table.place_bet(BetType.COME, 5)
        # Do not roll — the come bet has no come point yet.
        with pytest.raises(ValueError, match="have a point"):
            table.place_bet(BetType.COME_ODDS, 10, linked_bet_id=come_id)

    def test_come_odds_inherits_linked_bet_point(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 4)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()  # point 6
        come_id = table.place_bet(BetType.COME, 5)
        table.roll()  # come bet travels to 8
        odds_id = table.place_bet(BetType.COME_ODDS, 20, linked_bet_id=come_id)
        odds_bet = next(b for b in table.active_bets if b.bet_id == odds_id)
        assert odds_bet.point == 8


class TestPlacementUniqueness:
    """At most one contract of each kind may be stacked at a time.

    Come / don't-come are the exception: multiple are explicitly
    allowed (they each track their own come point). Everything else
    — pass line, don't pass, pass odds, don't-pass odds, come odds
    behind a specific come bet — is one-at-a-time. "Add more money"
    is the press operation, not a second :py:class:`ActiveBet`.
    """

    def test_rejects_second_pass_line(self) -> None:
        table = Table(seed=42)
        table.place_bet(BetType.PASS_LINE, 5)
        with pytest.raises(ValueError, match="already active"):
            table.place_bet(BetType.PASS_LINE, 5)

    def test_rejects_second_dont_pass(self) -> None:
        table = Table(seed=42)
        table.place_bet(BetType.DONT_PASS, 5)
        with pytest.raises(ValueError, match="already active"):
            table.place_bet(BetType.DONT_PASS, 5)

    def test_allows_both_pass_line_and_dont_pass_simultaneously(self) -> None:
        table = Table(seed=42)
        table.place_bet(BetType.PASS_LINE, 5)
        table.place_bet(BetType.DONT_PASS, 5)
        kinds = {bet.kind for bet in table.active_bets}
        assert kinds == {BetType.PASS_LINE, BetType.DONT_PASS}

    def test_rejects_second_pass_odds(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.PASS_ODDS, 10)
        with pytest.raises(ValueError, match="already attached"):
            table.place_bet(BetType.PASS_ODDS, 10)

    def test_rejects_second_dont_pass_odds(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        table.place_bet(BetType.DONT_PASS, 5)
        table.roll()
        table.place_bet(BetType.DONT_PASS_ODDS, 12)
        with pytest.raises(ValueError, match="already attached"):
            table.place_bet(BetType.DONT_PASS_ODDS, 12)

    def test_rejects_second_come_odds_on_same_parent(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 4)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        come_id = table.place_bet(BetType.COME, 5)
        table.roll()  # travels to 8
        table.place_bet(BetType.COME_ODDS, 10, linked_bet_id=come_id)
        with pytest.raises(ValueError, match="already attached"):
            table.place_bet(BetType.COME_ODDS, 10, linked_bet_id=come_id)

    def test_allows_come_odds_on_different_parent_come_bets(self) -> None:
        table = Table(
            roller=ScriptedRoller(
                [DiceRoll(3, 3), DiceRoll(4, 4), DiceRoll(2, 3)],
            )
        )
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()  # point 6
        a = table.place_bet(BetType.COME, 5)
        table.roll()  # come a → point 8
        b = table.place_bet(BetType.COME, 5)
        table.roll()  # come b → point 5
        table.place_bet(BetType.COME_ODDS, 10, linked_bet_id=a)
        table.place_bet(BetType.COME_ODDS, 10, linked_bet_id=b)
        odds_parents = {
            bet.parent_bet_id for bet in table.active_bets if bet.kind is BetType.COME_ODDS
        }
        assert odds_parents == {a, b}


class TestLinkedBetIdTypeSafety:
    """``linked_bet_id`` must be an exact ``int``: booleans are rejected.

    Booleans subclass ``int`` in Python, so ``linked_bet_id=True`` would
    otherwise silently attach an odds bet to ``bet_id == 1`` and silently
    corrupt parentage. The same exact-type discipline :py:class:`DiceRoll`
    applies to dice faces is enforced here.
    """

    def _table_with_travelled_come(self, come_amount: int = 5) -> tuple[Table, int]:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 4)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        come_id = table.place_bet(BetType.COME, come_amount)
        table.roll()  # travels to 8
        return table, come_id

    @pytest.mark.parametrize("bad", [True, False, 1.0, Fraction(1, 1), "1"])
    def test_come_odds_rejects_non_int_linked_id(self, bad: object) -> None:
        table, _ = self._table_with_travelled_come()
        with pytest.raises(TypeError, match="linked_bet_id must be an int"):
            table.place_bet(BetType.COME_ODDS, 10, linked_bet_id=bad)  # type: ignore[arg-type]

    @pytest.mark.parametrize("bad", [True, False, 1.0, Fraction(1, 1), "1"])
    def test_dont_come_odds_rejects_non_int_linked_id(self, bad: object) -> None:
        # Establish table point and a travelled don't-come bet.
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 4)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.DONT_COME, 5)
        table.roll()
        with pytest.raises(TypeError, match="linked_bet_id must be an int"):
            table.place_bet(BetType.DONT_COME_ODDS, 10, linked_bet_id=bad)  # type: ignore[arg-type]


class TestActiveBetParentField:
    """Odds bets expose their parent bet id via ``parent_bet_id``."""

    def test_pass_line_has_no_parent(self) -> None:
        table = Table(seed=42)
        table.place_bet(BetType.PASS_LINE, 5)
        (bet,) = table.active_bets
        assert bet.parent_bet_id is None

    def test_pass_odds_parent_is_pass_line(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3)]))
        pass_id = table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        odds_id = table.place_bet(BetType.PASS_ODDS, 10)
        odds_bet = next(b for b in table.active_bets if b.bet_id == odds_id)
        assert odds_bet.parent_bet_id == pass_id

    def test_come_odds_parent_is_linked_come(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 4)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        come_id = table.place_bet(BetType.COME, 5)
        table.roll()
        odds_id = table.place_bet(BetType.COME_ODDS, 10, linked_bet_id=come_id)
        odds_bet = next(b for b in table.active_bets if b.bet_id == odds_id)
        assert odds_bet.parent_bet_id == come_id


class TestPassLineResolution:
    """Pass-line resolution across every branch."""

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
        table.roll()
        result = table.roll()
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


class TestDontPassResolution:
    """Don't-pass resolution across every branch."""

    @pytest.mark.parametrize(
        ("d1", "d2", "total"),
        [(1, 1, 2), (1, 2, 3)],
    )
    def test_come_out_craps_wins_for_dont_pass(self, d1: int, d2: int, total: int) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(d1, d2)]))
        table.place_bet(BetType.DONT_PASS, 5)
        result = table.roll()
        assert result.roll.total == total
        (res,) = result.resolutions
        assert res.outcome is Outcome.WIN
        assert res.payout == 5

    @pytest.mark.parametrize(
        ("d1", "d2", "total"),
        [(3, 4, 7), (6, 5, 11)],
    )
    def test_come_out_natural_loses_for_dont_pass(self, d1: int, d2: int, total: int) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(d1, d2)]))
        table.place_bet(BetType.DONT_PASS, 5)
        result = table.roll()
        assert result.roll.total == total
        (res,) = result.resolutions
        assert res.outcome is Outcome.LOSE
        assert res.payout == -5

    def test_come_out_twelve_pushes_bar_12(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(6, 6)]))
        bet_id = table.place_bet(BetType.DONT_PASS, 5)
        result = table.roll()
        (res,) = result.resolutions
        assert res.bet_id == bet_id
        assert res.outcome is Outcome.PUSH
        assert res.payout == 0
        assert table.active_bets == ()

    def test_point_phase_seven_wins_for_dont_pass(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(1, 6)]))
        table.place_bet(BetType.DONT_PASS, 5)
        table.roll()  # point 6
        result = table.roll()  # seven-out
        (res,) = result.resolutions
        assert res.outcome is Outcome.WIN
        assert res.payout == 5

    def test_point_phase_point_hit_loses_for_dont_pass(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 2)]))
        table.place_bet(BetType.DONT_PASS, 5)
        table.roll()
        result = table.roll()
        (res,) = result.resolutions
        assert res.outcome is Outcome.LOSE
        assert res.payout == -5


class TestComeBetResolution:
    """Come bet resolution: its own come-out, its own travel, and seven-out."""

    @pytest.mark.parametrize(
        ("d1", "d2", "total"),
        [(3, 4, 7), (6, 5, 11)],
    )
    def test_come_bet_own_come_out_natural_wins(self, d1: int, d2: int, total: int) -> None:
        # Establish the table point, then place a come bet; on the next
        # roll, if the shooter rolls a natural, the come bet wins.
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(d1, d2)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()  # point 6
        table.place_bet(BetType.COME, 5)
        result = table.roll()
        assert result.roll.total == total
        come_res = next(r for r in result.resolutions if r.kind is BetType.COME)
        assert come_res.outcome is Outcome.WIN
        assert come_res.payout == 5

    def test_come_bet_own_come_out_craps_loses(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(1, 1)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.COME, 5)
        result = table.roll()
        come_res = next(r for r in result.resolutions if r.kind is BetType.COME)
        assert come_res.outcome is Outcome.LOSE
        assert come_res.payout == -5

    def test_come_bet_travels_to_come_point(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 4)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        come_id = table.place_bet(BetType.COME, 5)
        result = table.roll()
        # Come bet travelled, so it does not resolve — no come resolution.
        assert not any(r.kind is BetType.COME for r in result.resolutions)
        come_bet = next(b for b in table.active_bets if b.bet_id == come_id)
        assert come_bet.point == 8

    def test_come_point_hit_wins(self) -> None:
        table = Table(
            roller=ScriptedRoller(
                [DiceRoll(3, 3), DiceRoll(4, 4), DiceRoll(3, 5)],
            )
        )
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.COME, 5)
        table.roll()  # come travels to 8
        result = table.roll()  # 8 again → come wins
        come_res = next(r for r in result.resolutions if r.kind is BetType.COME)
        assert come_res.outcome is Outcome.WIN
        assert come_res.payout == 5

    def test_seven_out_takes_all_come_points_but_pass_line(self) -> None:
        # Establish table point 6. Place three come bets on three different
        # come-outs, each travelling to its own point. Then seven-out.
        table = Table(
            roller=ScriptedRoller(
                [
                    DiceRoll(3, 3),  # come-out 6: table point 6
                    DiceRoll(2, 2),  # come bet A travels to 4
                    DiceRoll(2, 3),  # come bet B travels to 5
                    DiceRoll(4, 5),  # come bet C travels to 9
                    DiceRoll(1, 6),  # seven-out
                ]
            )
        )
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        a = table.place_bet(BetType.COME, 5)
        table.roll()
        b = table.place_bet(BetType.COME, 5)
        table.roll()
        c = table.place_bet(BetType.COME, 5)
        table.roll()
        assert {bet.bet_id for bet in table.active_bets} == {
            1,  # pass line
            a,
            b,
            c,
        }
        result = table.roll()  # seven-out
        resolved_ids = {r.bet_id for r in result.resolutions}
        assert resolved_ids == {1, a, b, c}  # pass + all three come bets
        for res in result.resolutions:
            assert res.outcome is Outcome.LOSE
            assert res.payout == -5
        assert table.active_bets == ()
        assert table.point is None

    def test_fresh_come_on_seven_is_a_natural_win(self) -> None:
        # Subtle craps rule: a come bet placed on the roll *before* a 7 is
        # on its own come-out when that 7 arrives — so the come bet wins
        # (as a natural) while the pass line and any travelled come bets
        # seven-out. A fresh come and an existing pass line see the same
        # roll oppositely.
        table = Table(
            roller=ScriptedRoller(
                [DiceRoll(3, 3), DiceRoll(1, 6)],  # come-out 6, then 7
            )
        )
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        come_id = table.place_bet(BetType.COME, 5)
        result = table.roll()
        by_id = {r.bet_id: r for r in result.resolutions}
        # Pass line loses on seven-out.
        assert by_id[1].kind is BetType.PASS_LINE
        assert by_id[1].outcome is Outcome.LOSE
        # Fresh come bet wins as a natural.
        assert by_id[come_id].kind is BetType.COME
        assert by_id[come_id].outcome is Outcome.WIN


class TestDontComeBetResolution:
    """Don't-come resolution mirrors don't-pass against its own come-out."""

    def test_dont_come_own_come_out_two_wins(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(1, 1)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.DONT_COME, 5)
        result = table.roll()
        dc_res = next(r for r in result.resolutions if r.kind is BetType.DONT_COME)
        assert dc_res.outcome is Outcome.WIN
        assert dc_res.payout == 5

    def test_dont_come_own_come_out_twelve_pushes(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(6, 6)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.DONT_COME, 5)
        result = table.roll()
        dc_res = next(r for r in result.resolutions if r.kind is BetType.DONT_COME)
        assert dc_res.outcome is Outcome.PUSH
        assert dc_res.payout == 0

    def test_dont_come_seven_on_come_out_loses(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(3, 4)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.DONT_COME, 5)
        result = table.roll()
        dc_res = next(r for r in result.resolutions if r.kind is BetType.DONT_COME)
        assert dc_res.outcome is Outcome.LOSE
        assert dc_res.payout == -5

    def test_dont_come_travels_and_seven_out_wins(self) -> None:
        table = Table(
            roller=ScriptedRoller(
                [DiceRoll(3, 3), DiceRoll(4, 4), DiceRoll(1, 6)],
            )
        )
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.DONT_COME, 5)
        table.roll()  # don't-come travels to 8
        result = table.roll()  # seven-out → don't-come wins
        dc_res = next(r for r in result.resolutions if r.kind is BetType.DONT_COME)
        assert dc_res.outcome is Outcome.WIN
        assert dc_res.payout == 5


class TestPassOddsResolution:
    """Pass-odds payouts at true odds for every point."""

    @pytest.mark.parametrize(
        ("point", "come_out_dice", "point_dice", "amount", "expected_payout"),
        [
            (4, DiceRoll(2, 2), DiceRoll(1, 3), 10, 20),
            (5, DiceRoll(2, 3), DiceRoll(1, 4), 10, 15),
            (6, DiceRoll(3, 3), DiceRoll(4, 2), 10, 12),
            (8, DiceRoll(4, 4), DiceRoll(3, 5), 10, 12),
            (9, DiceRoll(4, 5), DiceRoll(5, 4), 10, 15),
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
        assert by_kind[BetType.PASS_LINE].payout == 5
        assert by_kind[BetType.PASS_ODDS].payout == expected_payout

    def test_pass_odds_loses_on_seven_out(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(1, 6)]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        table.place_bet(BetType.PASS_ODDS, 10)
        result = table.roll()
        by_kind = {res.kind: res for res in result.resolutions}
        assert by_kind[BetType.PASS_ODDS].payout == -10

    @pytest.mark.parametrize(
        ("point", "come_out_dice", "bad_amount", "denom"),
        [
            # Pass-odds ratios: 2:1 on 4/10, 3:2 on 5/9, 6:5 on 6/8.
            (5, DiceRoll(2, 3), 5, 2),  # 5 % 2 != 0
            (6, DiceRoll(3, 3), 7, 5),  # 7 % 5 != 0 (the old truncate example)
            (8, DiceRoll(4, 4), 11, 5),
            (9, DiceRoll(4, 5), 3, 2),
        ],
    )
    def test_pass_odds_rejects_amounts_that_would_truncate(
        self,
        point: int,
        come_out_dice: DiceRoll,
        bad_amount: int,
        denom: int,
    ) -> None:
        table = Table(roller=ScriptedRoller([come_out_dice]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        assert table.point == point
        with pytest.raises(ValueError, match=f"multiple of {denom}"):
            table.place_bet(BetType.PASS_ODDS, bad_amount)

    @pytest.mark.parametrize(
        ("point", "come_out_dice", "any_integer_amount"),
        [
            (4, DiceRoll(2, 2), 7),  # 2:1 — denom 1 — any amount pays a whole win
            (10, DiceRoll(5, 5), 13),
        ],
    )
    def test_pass_odds_accepts_any_amount_on_2_to_1_points(
        self,
        point: int,
        come_out_dice: DiceRoll,
        any_integer_amount: int,
    ) -> None:
        table = Table(roller=ScriptedRoller([come_out_dice]))
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        assert table.point == point
        odds_id = table.place_bet(BetType.PASS_ODDS, any_integer_amount)
        assert odds_id > 0


class TestLayOddsResolution:
    """Don't-pass lay-odds payouts at true odds for every point."""

    @pytest.mark.parametrize(
        ("point", "come_out_dice", "amount", "expected_payout"),
        [
            # Lay payout ratios are inverses of take odds:
            (4, DiceRoll(2, 2), 20, 10),  # 1:2 — $20 risk, $10 win
            (5, DiceRoll(2, 3), 30, 20),  # 2:3 — $30 risk, $20 win
            (6, DiceRoll(3, 3), 30, 25),  # 5:6 — $30 risk, $25 win
            (8, DiceRoll(4, 4), 30, 25),  # 5:6
            (9, DiceRoll(4, 5), 30, 20),  # 2:3
            (10, DiceRoll(5, 5), 20, 10),  # 1:2
        ],
    )
    def test_lay_odds_wins_on_seven(
        self,
        point: int,
        come_out_dice: DiceRoll,
        amount: int,
        expected_payout: int,
    ) -> None:
        table = Table(roller=ScriptedRoller([come_out_dice, DiceRoll(1, 6)]))
        table.place_bet(BetType.DONT_PASS, 5)
        table.roll()
        assert table.point == point
        table.place_bet(BetType.DONT_PASS_ODDS, amount)
        result = table.roll()
        by_kind = {res.kind: res for res in result.resolutions}
        assert by_kind[BetType.DONT_PASS].outcome is Outcome.WIN
        assert by_kind[BetType.DONT_PASS_ODDS].outcome is Outcome.WIN
        assert by_kind[BetType.DONT_PASS_ODDS].payout == expected_payout

    def test_lay_odds_loses_on_point_hit(self) -> None:
        table = Table(roller=ScriptedRoller([DiceRoll(3, 3), DiceRoll(4, 2)]))
        table.place_bet(BetType.DONT_PASS, 5)
        table.roll()
        table.place_bet(BetType.DONT_PASS_ODDS, 30)
        result = table.roll()
        by_kind = {res.kind: res for res in result.resolutions}
        assert by_kind[BetType.DONT_PASS_ODDS].payout == -30

    @pytest.mark.parametrize(
        ("point", "come_out_dice", "bad_amount", "denom"),
        [
            # Lay ratios: 1:2 on 4/10, 2:3 on 5/9, 5:6 on 6/8.
            (4, DiceRoll(2, 2), 5, 2),
            (10, DiceRoll(5, 5), 7, 2),
            (5, DiceRoll(2, 3), 5, 3),
            (9, DiceRoll(4, 5), 7, 3),
            (6, DiceRoll(3, 3), 7, 6),
            (8, DiceRoll(4, 4), 11, 6),
        ],
    )
    def test_lay_odds_rejects_amounts_that_would_truncate(
        self,
        point: int,
        come_out_dice: DiceRoll,
        bad_amount: int,
        denom: int,
    ) -> None:
        table = Table(roller=ScriptedRoller([come_out_dice]))
        table.place_bet(BetType.DONT_PASS, 5)
        table.roll()
        assert table.point == point
        with pytest.raises(ValueError, match=f"multiple of {denom}"):
            table.place_bet(BetType.DONT_PASS_ODDS, bad_amount)


class TestComeOddsResolution:
    """Come-odds follows its linked come bet's point."""

    def test_come_odds_wins_when_come_point_hit(self) -> None:
        table = Table(
            roller=ScriptedRoller(
                [DiceRoll(3, 3), DiceRoll(4, 4), DiceRoll(3, 5)],
            )
        )
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()  # table point 6
        come_id = table.place_bet(BetType.COME, 5)
        table.roll()  # come travels to 8
        table.place_bet(BetType.COME_ODDS, 10, linked_bet_id=come_id)
        result = table.roll()  # rolls 8 → come wins; come-odds wins at 6:5
        by_kind = {res.kind: res for res in result.resolutions}
        assert by_kind[BetType.COME].payout == 5
        assert by_kind[BetType.COME_ODDS].payout == 12  # (10 * 6) // 5

    def test_come_odds_loses_on_seven_out(self) -> None:
        table = Table(
            roller=ScriptedRoller(
                [DiceRoll(3, 3), DiceRoll(4, 4), DiceRoll(1, 6)],
            )
        )
        table.place_bet(BetType.PASS_LINE, 5)
        table.roll()
        come_id = table.place_bet(BetType.COME, 5)
        table.roll()
        table.place_bet(BetType.COME_ODDS, 10, linked_bet_id=come_id)
        result = table.roll()
        by_kind = {res.kind: res for res in result.resolutions}
        assert by_kind[BetType.COME_ODDS].payout == -10


class TestEngineConvergenceVsClosedForm:
    """Monte Carlo cross-checks: engine edges match closed-form values.

    Uses the same 5-sigma framing as :py:mod:`tests.test_convergence` —
    each one-unit line bet pays +/-/0 with near-coin variance, so the
    standard error of the sample mean over N trials is ~1/sqrt(N).
    """

    _NUM_TRIALS: int = 100_000
    _TOLERANCE_SIGMA: float = 5.0

    def test_pass_line_edge_converges(self) -> None:
        table = Table(seed=0xBE77ED)
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
        expected_player_ev = -float(pass_line_house_edge())
        sem = 1.0 / (self._NUM_TRIALS**0.5)
        tolerance = self._TOLERANCE_SIGMA * sem
        assert abs(empirical_player_ev - expected_player_ev) < tolerance

    def test_dont_pass_edge_converges(self) -> None:
        table = Table(seed=0xDECAF)
        total_payout = 0
        for _ in range(self._NUM_TRIALS):
            table.place_bet(BetType.DONT_PASS, 1)
            while True:
                result = table.roll()
                dp_resolutions = [r for r in result.resolutions if r.kind is BetType.DONT_PASS]
                if dp_resolutions:
                    total_payout += sum(r.payout for r in dp_resolutions)
                    break

        empirical_player_ev = total_payout / self._NUM_TRIALS
        expected_player_ev = -float(dont_pass_house_edge())
        # Don't pass variance is slightly lower than pass line because of
        # the ~1/36 push branch; 1/sqrt(N) remains a conservative bound.
        sem = 1.0 / (self._NUM_TRIALS**0.5)
        tolerance = self._TOLERANCE_SIGMA * sem
        assert abs(empirical_player_ev - expected_player_ev) < tolerance
