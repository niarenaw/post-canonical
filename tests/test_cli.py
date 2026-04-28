"""Tests for the `pcs` REPL.

Drives the cmd.Cmd loop directly rather than spawning a subprocess so the
tests stay fast and deterministic. Each test seeds stdin with newline-
separated commands and captures stdout, then asserts on the printed
output and the REPL's internal state.
"""

import io

import pytest

from post_canonical.cli import PCSRepl


def _drive(script: str) -> tuple[PCSRepl, str]:
    """Run a multi-line REPL script. Return the REPL instance and captured stdout."""
    repl = PCSRepl()
    stdin = io.StringIO(script + "\n")
    stdout = io.StringIO()
    repl.use_rawinput = False
    repl.stdin = stdin
    repl.stdout = stdout
    # cmd.Cmd writes intro/prompt to self.stdout when configured, but
    # also uses print() for command implementations; capture sys.stdout
    # via pytest's capfd in tests that need that detail.
    repl.cmdqueue = []
    repl.cmdloop()
    return repl, stdout.getvalue()


# === Configuration ===


class TestConfiguration:
    def test_alphabet_command_sets_alphabet(self, capsys: pytest.CaptureFixture[str]) -> None:
        repl, _ = _drive("alphabet MIU\nexit")
        assert repl._alphabet is not None
        assert "M" in repl._alphabet
        assert "I" in repl._alphabet
        assert "U" in repl._alphabet

    def test_var_command_records_variable(self, capsys: pytest.CaptureFixture[str]) -> None:
        repl, _ = _drive("alphabet MIU\nvar x\nvar y non_empty\nexit")
        assert "x" in repl._variables
        assert "y" in repl._variables
        from post_canonical import VariableKind

        assert repl._variables["x"] == VariableKind.ANY
        assert repl._variables["y"] == VariableKind.NON_EMPTY

    def test_axiom_command_records_axiom(self) -> None:
        repl, _ = _drive("alphabet MIU\naxiom MI\naxiom MII\nexit")
        assert repl._axioms == {"MI", "MII"}

    def test_rule_command_records_rule_string(self) -> None:
        repl, _ = _drive('alphabet MIU\nvar x\nrule "$xI -> $xIU"\nexit')
        assert any("$xI -> $xIU" in r for r in repl._rules)


# === Generation and queries ===


class TestGeneration:
    def test_generate_with_full_config(self, capsys: pytest.CaptureFixture[str]) -> None:
        script = """alphabet MIU
var x
var y
axiom MI
rule "$xI -> $xIU" name=add_U
rule "M$x -> M$x$x" name=double
generate 2
exit"""
        _, out = _drive(script)
        # Combined output (stdout via cmd.Cmd plus print() calls) should
        # mention "Generated" and at least one canonical word.
        full = out + capsys.readouterr().out
        assert "Generated" in full
        assert "MI" in full

    def test_generate_without_axiom_emits_helpful_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        _, _ = _drive("alphabet MIU\ngenerate 2\nexit")
        captured = capsys.readouterr()
        full = captured.out + captured.err
        # The error should mention axioms and include the example we added.
        assert "No axioms defined" in full
        assert "axiom MI" in full

    def test_generate_without_alphabet_emits_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        _, _ = _drive("generate 2\nexit")
        full = capsys.readouterr().out
        assert "No alphabet" in full


# === Robustness ===


class TestRobustness:
    def test_eof_exits_cleanly(self) -> None:
        # Empty script -> immediate EOF. Should not raise.
        _, _ = _drive("")

    def test_unknown_command_does_not_crash(self) -> None:
        _, _ = _drive("totally_made_up_command\nexit")

    def test_malformed_rule_emits_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        script = """alphabet MIU
var x
axiom MI
rule "this is not a valid rule"
generate 1
exit"""
        _, _ = _drive(script)
        full = capsys.readouterr().out
        # Either the rule command itself or generate's build step should
        # surface an error.
        assert "Error" in full or "error" in full
