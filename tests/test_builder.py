"""Tests for the SystemBuilder fluent DSL."""

import pytest

from post_canonical import SystemBuilder
from post_canonical.builder import BuilderError

# === Variable declarations ===


class TestVariables:
    def test_default_kind_is_any(self) -> None:
        b = SystemBuilder("ab").var("x")
        v = b._variables["x"]
        assert v.kind.name == "ANY"

    def test_named_kind(self) -> None:
        b = SystemBuilder("ab").var("y", kind="non_empty").var("z", kind="single")
        assert b._variables["y"].kind.name == "NON_EMPTY"
        assert b._variables["z"].kind.name == "SINGLE"

    def test_duplicate_var_name_raises(self) -> None:
        b = SystemBuilder("ab").var("x")
        with pytest.raises(BuilderError, match="already declared"):
            b.var("x")

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(BuilderError):
            SystemBuilder("ab").var("x", kind="banana")


# === Axioms ===


class TestAxioms:
    def test_axiom_added(self) -> None:
        b = SystemBuilder("ab").var("x").axiom("ab")
        assert "ab" in b._axioms

    def test_duplicate_axiom_silently_deduped(self) -> None:
        # Set semantics: adding the same axiom twice is a no-op, not an error.
        b = SystemBuilder("ab").var("x").axiom("ab").axiom("ab")
        assert b._axioms == {"ab"}


# === Rules ===


class TestRules:
    def test_rule_before_var_raises(self) -> None:
        # ${x} is referenced before x is declared. The Pattern parser
        # raises a PatternError (a ValidationError / ValueError subclass);
        # the BuilderError surface is reserved for higher-level builder
        # invariants, not pattern parse failures.
        b = SystemBuilder("ab")
        with pytest.raises(ValueError, match="Unknown variable"):
            b.rule("${x} -> ${x}")

    def test_canonical_brace_syntax_parses(self) -> None:
        b = (
            SystemBuilder("ab")
            .var("x")
            .axiom("a")
            .rule("${x} -> ${x}${x}", name="double")
        )
        assert len(b._rules) == 1

    def test_short_syntax_parses(self) -> None:
        b = (
            SystemBuilder("ab")
            .var("x")
            .axiom("a")
            .rule("$x -> $x$x", name="double_short")
        )
        assert len(b._rules) == 1

    def test_mixed_syntax_in_one_rule(self) -> None:
        # Mixing ${x} and $y in the same pattern should normalize to the same
        # variable references.
        b = (
            SystemBuilder("abc")
            .var("x")
            .var("y")
            .axiom("abc")
            .rule("${x} a $y -> $x b ${y}", name="mixed")
        )
        # The rule should reference both variables.
        rule = b._rules[0]
        all_var_names = {v.name for v in rule.all_variables}
        assert all_var_names == {"x", "y"}

    def test_longest_prefix_match_for_short_syntax(self) -> None:
        # When both $x and $xy are declared, $xy in a pattern should bind
        # to the longer variable rather than $x followed by literal 'y'.
        # Build a self-consistent rule (consequent vars must come from
        # antecedent vars) so we can inspect the parsed structure.
        b = (
            SystemBuilder("ab")
            .var("x")
            .var("xy")
            .axiom("a")
            .rule("$xy -> $xy", name="identity")
        )
        rule = b._rules[0]
        ante_vars = {v.name for v in rule.antecedents[0].variables}
        assert ante_vars == {"xy"}


# === Build ===


class TestBuild:
    def test_full_round_trip(self) -> None:
        system = (
            SystemBuilder("MIU")
            .var("x")
            .var("y")
            .axiom("MI")
            .rule("$xI -> $xIU", name="add_U")
            .rule("M$x -> M$x$x", name="double")
            .build()
        )
        # Building succeeds and the system has the expected pieces.
        assert "M" in system.alphabet
        assert "MI" in system.axioms
        assert len(system.rules) == 2

    def test_build_without_axiom_raises(self) -> None:
        # The builder requires at least one axiom for a buildable system.
        b = SystemBuilder("ab").var("x").rule("$x -> $x$x", name="double")
        with pytest.raises(BuilderError, match="axiom"):
            b.build()
