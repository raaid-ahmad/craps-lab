"""Unit tests for the ``DiceRoll`` dataclass and ``DIE_FACES`` constant."""

from __future__ import annotations

from fractions import Fraction

import pytest

from craps_lab.dice import DIE_FACES, DiceRoll, DiceRoller


def test_die_faces_is_one_through_six() -> None:
    assert set(DIE_FACES) == set(range(1, 7))
    assert len(DIE_FACES) == 6


def test_total_is_sum_of_two_faces() -> None:
    assert DiceRoll(1, 1).total == 2
    assert DiceRoll(1, 6).total == 7
    assert DiceRoll(4, 3).total == 7
    assert DiceRoll(6, 6).total == 12


def test_is_doubles_true_when_faces_match() -> None:
    for face in DIE_FACES:
        assert DiceRoll(face, face).is_doubles


def test_is_doubles_false_when_faces_differ() -> None:
    assert not DiceRoll(1, 2).is_doubles
    assert not DiceRoll(3, 5).is_doubles
    assert not DiceRoll(6, 5).is_doubles


def test_equal_rolls_are_equal_and_hashable() -> None:
    a = DiceRoll(3, 4)
    b = DiceRoll(3, 4)
    assert a == b
    assert hash(a) == hash(b)
    assert {a, b} == {a}


def test_dice_roll_is_frozen() -> None:
    roll = DiceRoll(2, 3)
    with pytest.raises(AttributeError):
        roll.die1 = 6  # type: ignore[misc]


@pytest.mark.parametrize("die", [0, 7, -1, 10, 100])
def test_invalid_die1_raises(die: int) -> None:
    with pytest.raises(ValueError, match="die1"):
        DiceRoll(die, 1)


@pytest.mark.parametrize("die", [0, 7, -1, 10, 100])
def test_invalid_die2_raises(die: int) -> None:
    with pytest.raises(ValueError, match="die2"):
        DiceRoll(1, die)


# ``bool`` subclasses ``int`` in Python and ``True == 1``; without an
# exact-type check ``DiceRoll(True, 6)`` would slip through value
# validation and produce nonsense totals downstream. Same story for
# ``Fraction(1, 1)`` and ``1.0``, both of which compare equal to 1 and
# hash to the same bucket. These tests pin the rejection at the
# boundary where it belongs.
@pytest.mark.parametrize("bad", [True, False, Fraction(1, 1), 1.0])
def test_dice_roll_rejects_non_int_die1(bad: object) -> None:
    with pytest.raises(TypeError, match="die1 must be an int"):
        DiceRoll(bad, 1)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [True, False, Fraction(1, 1), 1.0])
def test_dice_roll_rejects_non_int_die2(bad: object) -> None:
    with pytest.raises(TypeError, match="die2 must be an int"):
        DiceRoll(1, bad)  # type: ignore[arg-type]


def test_roller_returns_valid_dice_rolls() -> None:
    roller = DiceRoller(seed=42)
    for _ in range(500):
        roll = roller.roll()
        assert roll.die1 in DIE_FACES
        assert roll.die2 in DIE_FACES


def test_roller_is_deterministic_under_seed() -> None:
    a = DiceRoller(seed=0xC0DE)
    b = DiceRoller(seed=0xC0DE)
    for _ in range(100):
        assert a.roll() == b.roll()


def test_different_seeds_yield_different_streams() -> None:
    a_roller = DiceRoller(seed=1)
    b_roller = DiceRoller(seed=2)
    a_stream = [a_roller.roll() for _ in range(30)]
    b_stream = [b_roller.roll() for _ in range(30)]
    assert a_stream != b_stream


def test_rolls_generator_yields_requested_count() -> None:
    roller = DiceRoller(seed=7)
    assert len(list(roller.rolls(50))) == 50


def test_rolls_zero_count_yields_empty() -> None:
    roller = DiceRoller(seed=7)
    assert list(roller.rolls(0)) == []


def test_rolls_negative_count_raises() -> None:
    roller = DiceRoller(seed=7)
    with pytest.raises(ValueError, match="non-negative"):
        list(roller.rolls(-1))


# Golden sequences — first ten rolls for a handful of seeds, pinned
# against the explicit PCG64 bit generator. Makes the "stable across
# NumPy versions" docstring contract executable: if a future NumPy
# silently changes PCG64's algorithm these assertions fail loudly,
# rather than downstream simulations drifting away from the values
# cited in notebooks and README examples.
_GOLDEN_ROLLS: dict[int, list[tuple[int, int]]] = {
    0: [(6, 4), (4, 2), (2, 1), (1, 1), (2, 5), (4, 6), (4, 4), (6, 5), (4, 4), (4, 6)],
    1: [(3, 4), (5, 6), (1, 1), (5, 6), (2, 2), (6, 3), (2, 5), (2, 3), (4, 4), (1, 1)],
    42: [(1, 5), (4, 3), (3, 6), (1, 5), (2, 1), (4, 6), (5, 5), (5, 5), (4, 1), (6, 3)],
    0xC0DE: [(6, 2), (3, 4), (1, 5), (5, 3), (6, 5), (3, 5), (2, 6), (4, 6), (3, 6), (2, 6)],
}


@pytest.mark.parametrize(("seed", "expected"), list(_GOLDEN_ROLLS.items()))
def test_roller_golden_sequence(seed: int, expected: list[tuple[int, int]]) -> None:
    roller = DiceRoller(seed=seed)
    actual = [(roll.die1, roll.die2) for roll in roller.rolls(len(expected))]
    assert actual == expected
