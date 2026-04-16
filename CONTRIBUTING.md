# Contributing to craps-lab

Thanks for taking a look. craps-lab is a practical craps strategy simulator —
the engine is built on exact math so the results are trustworthy, but the
goal is useful visual output, not academic rigor for its own sake. The
standards below apply to any contribution — and to the author.

## Development setup

```bash
git clone https://github.com/raaid-ahmad/craps-lab.git
cd craps-lab
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

Minimum Python version: **3.11**. CI runs against 3.11, 3.12, and 3.13.

## Quality gates

Every commit lands on a green build. Locally, run:

```bash
ruff check .
ruff format --check .
mypy src tests
pytest
```

Pre-commit runs these (plus standard whitespace / YAML / TOML hooks) on every
`git commit`. If a hook fails, fix the issue and re-commit — do not bypass
with `--no-verify`.

## Commit style

Conventional Commits. Each commit message is:

```
<type>(<scope>): <subject>

<body: why, not what, plus anything non-obvious>
```

Accepted types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`,
`build`, `ci`, `style`.

Examples from this repository's history:

- `feat(dice): add seeded roller wrapping numpy.random`
- `chore(ruff): configure lint and format`
- `docs: expand README with project framing and roadmap`

Keep commits **small and atomic** — one logical change per commit. The commit
history is meant to be readable as a narrative; a reviewer should be able to
follow the build-up by scrolling `git log`.

## Code conventions

- **Type hints everywhere.** Strict mypy is enforced. `Any` and bare
  `# type: ignore` without a specific error code are rejected.
- **Public APIs have docstrings.** Private helpers do not need them unless
  the implementation is non-obvious.
- **Derivations go next to the code.** If a function's behavior rests on a
  probability argument, the argument lives in the module docstring or in a
  linked notebook — never as a magic number.
- **Tests are deterministic under seed.** Monte Carlo tests use a fixed
  `numpy.random.Generator` seed and bracket results with tolerances derived
  from the sample size.
- **No magic numbers.** If a constant has a source (a known house edge, a
  payout ratio, a Markov transition probability), name it and cite the
  source in a comment or docstring.

## Test layout

- `tests/` — unit and property tests, mirroring `src/craps_lab/` layout.
- Property-based tests use [Hypothesis](https://hypothesis.readthedocs.io).
- Statistical convergence tests must document the sample size and tolerance
  and must pass deterministically under the pinned seed.

## Notebooks

Notebooks live in `notebooks/` and are numbered by phase. Each notebook:

- is reproducible end-to-end from a fresh kernel,
- uses fixed seeds,
- pins its plot style, and
- cross-references the module docstring whose derivation it illustrates.

## License

By contributing, you agree your contributions are licensed under the MIT
License. See [LICENSE](LICENSE).
