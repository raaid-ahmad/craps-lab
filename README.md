# craps-lab

[![CI](https://github.com/raaid-ahmad/craps-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/raaid-ahmad/craps-lab/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

> A probability-first craps simulator. Closed-form house-edge derivations, Monte Carlo convergence, shooter-length Markov chains, and risk-of-ruin analysis — built commit by commit.

## Why another craps simulator?

Most open-source craps engines tell you *what* the house edge is; they do not show *why*. `craps-lab` treats the math as a first-class citizen:

- Every bet type ships with a closed-form derivation of its expected value in the module docstring and a companion notebook cell.
- Every Monte Carlo result is cross-checked against the analytical answer, and the convergence rate itself is a tested property.
- Every advanced artifact — the shooter-length distribution as a Markov chain, the gambler's-ruin survival curve, a variance decomposition across bet mixes — has a Jupyter notebook companion.

The engine is rigorously built: strict type checking, property-based tests for the state machine, 100% deterministic under seed, and zero magic numbers without a source.

## Status

Early development. See the [roadmap](#roadmap) below. The commit history *is* the story — each commit is a small, atomic step, and `main` is always green.

## Roadmap

| Phase | What lands |
|-------|------------|
| 0 — Scaffolding | `pyproject.toml`, ruff, mypy (strict), pytest, pre-commit, GitHub Actions, README, CONTRIBUTING |
| 1 — Dice primitives | Seeded RNG wrapper, 2d6 sum PMF derivation, convergence tests, first notebook |
| 2 — Bets & house edges | All bet types with closed-form edge derivations in docstrings |
| 3 — Table state machine | Per-bet resolver classes, property tests for round-resolution invariants |
| 4 — Session runner | Bankroll tracking, bust detection, deterministic under seed |
| 5 — Monte Carlo | Batch runner, bootstrap confidence intervals, analytical-vs-simulated convergence notebook |
| 6 — Advanced statistics | Shooter-length Markov chain, gambler's-ruin solution, risk-of-ruin heatmaps, variance decomposition |
| 7 — CLI | Typer-based CLI with rich reporting |
| 8 — Optional | YAML strategies, web UI |

## Development

### Install

```bash
git clone https://github.com/raaid-ahmad/craps-lab.git
cd craps-lab
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

### Quality gates

Every commit lands on a green build. The full pipeline, run locally:

```bash
ruff check .
ruff format --check .
mypy src tests
pytest
```

Pre-commit runs ruff, ruff-format, mypy, and the standard whitespace / YAML / TOML checks automatically on every commit.

### Notebooks

Math derivations and visualizations live in `notebooks/`, each accompanying a specific phase. They are companions to the code, not a replacement for it.

## License

MIT — see [LICENSE](LICENSE).
