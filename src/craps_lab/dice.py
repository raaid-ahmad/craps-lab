"""Dice primitives: a frozen ``DiceRoll`` dataclass and the ``DIE_FACES`` set.

A craps throw is always the sum of two six-sided dice. ``DiceRoll`` carries
the individual die faces (not just the sum) so that downstream bet-resolution
logic can distinguish, for example, a "hard 8" (4+4) from an "easy 8" (6+2
or 5+3), and so that tests can assert against the underlying dice rather
than only the total.

The dataclass is frozen and slotted. Frozen gives value-object semantics
(two rolls with the same faces compare equal and hash identically, so they
can be used as dict keys or set members). Slots cut per-instance memory
and make attribute access slightly faster, which matters once we are
running millions of rolls per simulation session.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Iterator

DIE_FACES: Final = frozenset(range(1, 7))
"""The six valid faces of a standard six-sided die."""


@dataclass(frozen=True, slots=True)
class DiceRoll:
    """The outcome of rolling two six-sided dice.

    Invariants (enforced in :py:meth:`__post_init__`):

    * ``die1 in DIE_FACES`` and ``die2 in DIE_FACES``
    * ``total == die1 + die2`` by construction
    """

    die1: int
    die2: int

    def __post_init__(self) -> None:
        # ``type(x) is int`` rather than ``isinstance(x, int)``: booleans
        # subclass int in Python (``True == 1``, ``False == 0``), so
        # ``isinstance(True, int)`` is True and ``True in DIE_FACES``
        # silently succeeds. For a project whose whole pitch is rigor,
        # ``DiceRoll(True, 6)`` slipping through would be embarrassing
        # — and ``Fraction(1, 1)`` or ``1.0`` equally so, since both
        # hash and compare equal to 1. Exact-type checks are the right
        # call at this boundary.
        if type(self.die1) is not int:
            msg = f"die1 must be an int, got {type(self.die1).__name__}"
            raise TypeError(msg)
        if type(self.die2) is not int:
            msg = f"die2 must be an int, got {type(self.die2).__name__}"
            raise TypeError(msg)
        if self.die1 not in DIE_FACES:
            msg = f"die1 must be in 1..6, got {self.die1}"
            raise ValueError(msg)
        if self.die2 not in DIE_FACES:
            msg = f"die2 must be in 1..6, got {self.die2}"
            raise ValueError(msg)

    @property
    def total(self) -> int:
        """The sum of the two dice, in ``[2, 12]``."""
        return self.die1 + self.die2

    @property
    def is_doubles(self) -> bool:
        """True iff both dice show the same face (the "hardway" condition)."""
        return self.die1 == self.die2


class DiceRoller:
    """A seedable, deterministic two-dice roller.

    Wraps a :py:class:`numpy.random.Generator` constructed over an
    explicitly pinned :py:class:`numpy.random.PCG64` bit generator, so
    that each call to :py:meth:`roll` consumes one uniform ``(d1, d2)``
    pair in ``{1, ..., 6}`` and returns a :py:class:`DiceRoll`. The
    stream is a pure function of ``seed`` and is stable across NumPy
    versions that keep PCG64 (which NumPy treats as a stable algorithm,
    unlike :py:func:`numpy.random.default_rng` whose default bit
    generator may change in future releases). A golden-sequence test
    pins the first several rolls for a handful of seeds to make that
    stability contract executable.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng: np.random.Generator = np.random.Generator(np.random.PCG64(seed))

    def roll(self) -> DiceRoll:
        """Roll two six-sided dice and return a :py:class:`DiceRoll`."""
        result = self._rng.integers(1, 6, size=2, endpoint=True)
        return DiceRoll(die1=int(result[0]), die2=int(result[1]))

    def rolls(self, count: int) -> Iterator[DiceRoll]:
        """Yield ``count`` independent :py:class:`DiceRoll` instances.

        ``count`` must be non-negative; zero yields an empty iterator.
        """
        if count < 0:
            msg = f"count must be non-negative, got {count}"
            raise ValueError(msg)
        for _ in range(count):
            yield self.roll()
