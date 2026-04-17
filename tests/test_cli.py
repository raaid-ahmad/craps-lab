"""Tests for the CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from craps_lab.cli import app

runner = CliRunner()


class TestListPresets:
    """The list-presets command."""

    def test_exit_code_zero(self) -> None:
        result = runner.invoke(app, ["list-presets"])
        assert result.exit_code == 0

    def test_lists_all_presets(self) -> None:
        result = runner.invoke(app, ["list-presets"])
        assert "pass-line-with-odds" in result.output
        assert "iron-cross" in result.output
        assert "three-point-molly" in result.output


class TestRun:
    """The run command."""

    def test_basic_run(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "--strategy",
                "pass-line-with-odds",
                "--bankroll",
                "500",
                "--hours",
                "1",
                "--sessions",
                "10",
            ],
        )
        assert result.exit_code == 0

    def test_output_contains_stats(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "--strategy",
                "pass-line-with-odds",
                "--bankroll",
                "500",
                "--hours",
                "1",
                "--sessions",
                "10",
            ],
        )
        assert "Win Rate" in result.output
        assert "Mean P&L" in result.output

    def test_invalid_strategy_shows_error(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "--strategy",
                "does-not-exist",
                "--bankroll",
                "500",
                "--hours",
                "1",
                "--sessions",
                "10",
            ],
        )
        assert result.exit_code == 1
        assert "Unknown strategy" in result.output

    def test_stop_options_accepted(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "--strategy",
                "pass-line-with-odds",
                "--bankroll",
                "500",
                "--hours",
                "1",
                "--sessions",
                "10",
                "--stop-win",
                "100",
                "--stop-loss",
                "200",
            ],
        )
        assert result.exit_code == 0


class TestCompare:
    """The compare command."""

    def test_basic_compare(self) -> None:
        result = runner.invoke(
            app,
            [
                "compare",
                "--strategies",
                "pass-line-with-odds,iron-cross",
                "--bankroll",
                "500",
                "--hours",
                "1",
                "--sessions",
                "10",
            ],
        )
        assert result.exit_code == 0

    def test_output_contains_both_strategy_names(self) -> None:
        result = runner.invoke(
            app,
            [
                "compare",
                "--strategies",
                "pass-line-with-odds,iron-cross",
                "--bankroll",
                "500",
                "--hours",
                "1",
                "--sessions",
                "10",
            ],
        )
        assert "PassLineWithOdds" in result.output
        assert "IronCross" in result.output

    def test_invalid_strategy_in_list_shows_error(self) -> None:
        result = runner.invoke(
            app,
            [
                "compare",
                "--strategies",
                "pass-line-with-odds,bogus",
                "--bankroll",
                "500",
                "--hours",
                "1",
                "--sessions",
                "10",
            ],
        )
        assert result.exit_code == 1
