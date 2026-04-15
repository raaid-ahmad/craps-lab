# craps-lab

[![CI](https://github.com/raaid-ahmad/craps-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/raaid-ahmad/craps-lab/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

> A craps strategy simulator: define a betting strategy, run it across thousands of realistic sessions, and see the actual distribution of what you'd take home — not just the house edge.

## Why craps-lab?

Most craps tools answer *what* the house edge is. They rarely answer the questions a player actually cares about: *if I play this strategy for four hours tonight starting with $500, how often do I go home up $200? How often do I bust? How deep do my drawdowns get along the way?*

craps-lab treats the simulator as the primary product and the probability engine as the foundation it stands on:

- **Define a strategy** as a Python class — including conditional logic like "press after two hits" or "regress on win."
- **Run it through realistic sessions** — bankroll, hours at a user-set pace (default ~100 rolls/hr), stop-win, stop-loss, target, number of sessions.
- **Compare strategies** head-to-head on the same seed — P&L distribution, risk of ruin, drawdowns, hit-target rate, expected time played.
- **Explore interactively** via a Streamlit UI, or batch from a Typer CLI.

Under the hood sits a probability-first engine built commit-by-commit to be trustworthy:

- Every bet type ships with a closed-form derivation of its expected value in the module docstring.
- Every Monte Carlo result is cross-checked against the analytical answer, and the convergence rate itself is a tested property.
- Every math artifact — the dice PMF, shooter-length distribution, gambler's ruin — has a companion Jupyter notebook.
- Strict type checking, property-based tests on the state machine, 100% deterministic under seed, zero magic numbers without a source.

The simulator's answers are only as trustworthy as the engine underneath it; this one is built to be trusted.

## Quickstart

```bash
# Run a preset against a realistic session
craps-lab run --strategy pass-line-with-odds \
              --bankroll 500 --hours 4 --stop-win 200 --stop-loss 500 \
              --sessions 10000

# Compare strategies head-to-head on the same seed
craps-lab compare --strategies pass-line-with-odds,iron-cross \
                  --bankroll 500 --hours 4 --sessions 10000

# Or explore interactively
streamlit run app/streamlit_app.py
```

*These commands land in Phases 8–9 of the roadmap — see status below.*

## Status

Early development. The probability engine and line-bet derivations are done; the multi-bet engine, strategy layer, session runner, CLI, and UI are being built atomic-commit-by-atomic-commit on top. `main` is always green. The commit history *is* the story — each commit is a small, atomic step.

## Roadmap

| Phase | What lands |
|-------|------------|
| ✅ 0 — Scaffolding | `pyproject.toml`, ruff, mypy (strict), pytest, pre-commit, GitHub Actions |
| ✅ 1 — Dice primitives | Seeded RNG wrapper, 2d6 sum PMF, convergence tests, notebook |
| ✅ 2 — Bets & closed-form edges | Line bets, come bets, free odds; derivations in docstrings and notebooks |
| 🛠 3 — Multi-bet engine | Table state machine with per-roll resolution of multiple simultaneous bets |
| 🛠 4 — Strategy layer | `Strategy` base class, `Context` / `BetAction` primitives, and presets (PassLineWithOdds, IronCross, ThreePointMolly, ...) |
| 🛠 5 — Session runner | Bankroll tracking, stop rules, real-world time parameterization, equity curves, drawdown tracking |
| 🛠 6 — Campaign runner | Many sessions aggregated; head-to-head strategy comparison on a shared seed |
| 🛠 7 — Reporting | Risk of ruin, hit-target rate, drawdown distribution, P&L histograms, matplotlib figures |
| 🛠 8 — CLI | Typer-based `run` / `compare` / `list-presets` with rich table output |
| 🛠 9 — Streamlit UI | Config inputs, strategy picker, results tabs |
| 🕒 Later | Shooter-length Markov chain, closed-form gambler's ruin, variance decomposition |

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

Math derivations and visualizations live in `notebooks/`. They are companions to the code, not a replacement for it.

## License

MIT — see [LICENSE](LICENSE).
