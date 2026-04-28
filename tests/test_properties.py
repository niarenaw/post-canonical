"""Property-based tests using ``hypothesis``.

These tests exercise the central invariants of the matcher, the JSON
codec, and the pattern parser. They generate inputs from small finite
domains so they run quickly (under a second on a developer laptop).
"""

from __future__ import annotations

import json

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from post_canonical import (
    Alphabet,
    Pattern,
    PCSJsonCodec,
    PostCanonicalSystem,
    ProductionRule,
    Variable,
    VariableKind,
)
from post_canonical.matching.matcher import PatternMatcher
from post_canonical.presets import BINARY

# === Strategies ===


# A small fixed alphabet keeps the search space tractable.
ALPHA = "ab"
SYMBOLS = st.sampled_from(list(ALPHA))


def words(min_size: int = 0, max_size: int = 6) -> st.SearchStrategy[str]:
    return st.text(alphabet=list(ALPHA), min_size=min_size, max_size=max_size)


@st.composite
def variables(draw: st.DrawFn) -> Variable:
    name = draw(st.sampled_from(["x", "y", "z"]))
    kind = draw(st.sampled_from(list(VariableKind)))
    return Variable(name, kind)


@st.composite
def patterns(draw: st.DrawFn, max_elements: int = 4) -> tuple[Pattern, dict[str, Variable]]:
    """Generate a Pattern using a small declared variable pool."""
    pool: dict[str, Variable] = {}
    elements: list[str | Variable] = []
    n = draw(st.integers(min_value=0, max_value=max_elements))
    for _ in range(n):
        is_var = draw(st.booleans())
        if is_var:
            v = draw(variables())
            pool.setdefault(v.name, v)
            elements.append(pool[v.name])
        else:
            elements.append(draw(words(min_size=1, max_size=3)))
    return Pattern(elements), pool


# === Properties ===


class TestMatcherRoundTrip:
    """Any binding the matcher yields must satisfy substitute(binding) == word."""

    @given(p_and_pool=patterns(), w=words(max_size=8))
    @settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_match_then_substitute_recovers_word(
        self, p_and_pool: tuple[Pattern, dict[str, Variable]], w: str
    ) -> None:
        pattern, _ = p_and_pool
        matcher = PatternMatcher(Alphabet(ALPHA))
        for binding in matcher.match(pattern, w):
            assert pattern.substitute(binding) == w


class TestPatternParseRoundTrip:
    """For a pattern over declared vars, parse(str(p), vars) == p."""

    @given(p_and_pool=patterns())
    @settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_str_then_parse_is_identity(
        self, p_and_pool: tuple[Pattern, dict[str, Variable]]
    ) -> None:
        pattern, pool = p_and_pool
        rendered = str(pattern)
        # str(Pattern) emits the canonical ${name} form, which Pattern.parse
        # accepts. Parse should yield a Pattern equal to the original after
        # normalization (which both sides apply identically).
        reparsed = Pattern.parse(rendered, pool)
        assert reparsed == pattern


class TestJSONRoundTrip:
    """Encoding then decoding preserves a system's value-equality data."""

    @given(axioms=st.sets(words(min_size=1, max_size=4), min_size=1, max_size=3))
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_decode_encode_is_identity(self, axioms: set[str]) -> None:
        # Build a minimal but real system: identity rule over $x.
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]), name="identity")
        system = PostCanonicalSystem(
            alphabet=BINARY if all(c in "01" for ax in axioms for c in ax) else Alphabet(ALPHA),
            axioms=frozenset(axioms),
            rules=frozenset({rule}),
            variables=frozenset({x}),
        )

        codec = PCSJsonCodec()
        encoded = codec.encode(system)

        # Encoded payload must be valid JSON
        json.loads(encoded)

        decoded = codec.decode(encoded)
        assert decoded.axioms == system.axioms
        assert decoded.alphabet == system.alphabet
        assert {r.name for r in decoded.rules} == {r.name for r in system.rules}


# === Single / non-empty boundary tests (P3-7) ===


class TestVariableKindBoundaries:
    def test_single_does_not_match_empty(self) -> None:
        z = Variable.single("z")
        matcher = PatternMatcher(BINARY)
        assert matcher.match_first(Pattern([z]), "") is None

    def test_non_empty_matches_one_char(self) -> None:
        y = Variable.non_empty("y")
        matcher = PatternMatcher(BINARY)
        b = matcher.match_first(Pattern([y]), "0")
        assert b is not None
        assert b["y"] == "0"

    def test_non_empty_does_not_match_empty(self) -> None:
        y = Variable.non_empty("y")
        matcher = PatternMatcher(BINARY)
        assert matcher.match_first(Pattern([y]), "") is None

    def test_any_matches_empty(self) -> None:
        x = Variable.any("x")
        matcher = PatternMatcher(BINARY)
        b = matcher.match_first(Pattern([x]), "")
        assert b is not None
        assert b["x"] == ""


# Silence one known-noisy edge: hypothesis sometimes draws zero-element
# patterns, which only match the empty word. Pin that expected behavior.


def test_empty_pattern_matches_only_empty_word() -> None:
    matcher = PatternMatcher(BINARY)
    empty_pattern = Pattern([])
    assert matcher.match_first(empty_pattern, "") is not None
    assert matcher.match_first(empty_pattern, "0") is None


# A regression sanity check that fast-fails before letting hypothesis
# spend time on patterns guaranteed to be unmatchable.


@pytest.mark.parametrize("word", ["", "0", "1", "01", "10", "0011"])
def test_match_with_no_matches_yields_nothing(word: str) -> None:
    # Pattern requiring a character not in the word will never match.
    pattern = Pattern(["X"])
    matcher = PatternMatcher(Alphabet(ALPHA + "X"))
    assert list(matcher.match(pattern, word)) == []
