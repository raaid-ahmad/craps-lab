# craps-lab

[![CI](https://github.com/raaid-ahmad/craps-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/raaid-ahmad/craps-lab/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

> See what your craps strategy actually does to your bankroll — before you bring it to the table.

## What this is

Most craps resources tell you the house edge on each bet. That's useful, but it doesn't answer the questions you actually have: *if I play Iron Cross for four hours with $500, how often do I walk away up? How often do I bust? How bad do the drawdowns get?*

craps-lab lets you define a strategy in Python, run it through thousands of realistic sessions, and see the distribution of outcomes — not just the theoretical edge, but the practical shape of what happens to your money.

- **Define a strategy** — conditional logic like "press after two hits" or "regress on the first win."
- **Run realistic sessions** — bankroll, hours of play, stop-win, stop-loss.
- **Compare head-to-head** — same dice sequence, different strategies, clear winner.
- **Explore visually** — P&L distributions, drawdown charts, risk-of-ruin curves.

The engine underneath is built on exact probability math so the simulator's answers are trustworthy, but the point of the project is the practical output, not the math itself.

## Quickstart

```bash
# Run a preset against a realistic session
craps-lab run --strategy pass-line-with-odds \
              --bankroll 500 --hours 4 --stop-win 200 --stop-loss 300 \
              --sessions 10000

# Compare strategies head-to-head on the same seed
craps-lab compare --strategies pass-line-with-odds,iron-cross \
                  --bankroll 500 --hours 4 --sessions 10000

# Or explore interactively
streamlit run app/streamlit_app.py
```

*CLI and UI are coming — see the roadmap below.*

## Built-in strategies

| Strategy | What it does |
|----------|-------------|
| **Pass Line with Odds** | Pass line on come-out, 3-4-5x odds behind the point. The textbook low-edge play. |
| **Iron Cross** | Field + place 5/6/8. Wins on every number except 7. Feels great until it doesn't. |
| **Three Point Molly** | Pass line + two come bets, all with max odds. Three points working at all times. |

Write your own by subclassing `Strategy` and implementing `get_actions()`.

## Status

All phases are complete. `main` is always green.

## Roadmap

| Phase | What lands |
|-------|------------|
| ✅ 0 — Scaffolding | `pyproject.toml`, ruff, mypy (strict), pytest, pre-commit, GitHub Actions |
| ✅ 1 — Dice primitives | Seeded RNG wrapper, 2d6 sum PMF, convergence tests, notebook |
| ✅ 2 — Bets & edges | Line bets, come bets, place bets, field, free odds; closed-form house edges |
| ✅ 3 — Multi-bet engine | Table state machine: per-roll resolution of multiple simultaneous bets |
| ✅ 4 — Strategy layer | `Strategy` base class, `BetAction` / `Context` primitives, three presets |
| ✅ 5 — Session runner | Bankroll tracking, stop rules, real-world time parameterization, equity curves |
| ✅ 6 — Campaign runner | Many sessions aggregated; head-to-head strategy comparison on a shared seed |
| ✅ 7 — Reporting | Risk of ruin, hit-target rate, drawdown distribution, P&L histograms |
| ✅ 8 — CLI | Typer-based `run` / `compare` / `list-presets` with rich table output |
| ✅ 9 — Streamlit UI | Interactive strategy picker, session config, results dashboard |

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

Every commit lands on a green build:

```bash
ruff check .
ruff format --check .
mypy src tests
pytest
```

### Notebooks

Math derivations and visualizations live in `notebooks/`. They back up the engine — not the other way around.

## License

MIT — see [LICENSE](LICENSE).
