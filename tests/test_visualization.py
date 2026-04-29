"""Smoke and edge-case tests for the four visualization exporters."""

from post_canonical import (
    Pattern,
    PostCanonicalSystem,
    ProductionRule,
    Variable,
    create_mu_puzzle,
    to_ascii_tree,
    to_dot,
    to_latex,
    to_mermaid,
)
from post_canonical.matching.binding import Binding
from post_canonical.presets import BINARY
from post_canonical.system.derivation import Derivation, DerivationStep


def _two_step_mu_derivation() -> Derivation:
    """Build a real two-step MU-puzzle derivation for testing."""
    mu = create_mu_puzzle()
    derived = mu.generate(max_steps=3)
    # Pick a derivation we know exists at depth >= 2
    target = next(dw for dw in derived if dw.derivation.length >= 2)
    return target.derivation


def _empty_derivation() -> Derivation:
    return Derivation()


def _unicode_word_derivation() -> Derivation:
    """Derivation with non-ASCII symbols to exercise escaping paths."""
    # Use Greek alpha and beta to verify the renderers do not assume ASCII.
    alpha = "α"  # noqa: RUF001 - intentional non-ASCII for test
    beta = "β"
    alphabet = type(BINARY)(alpha + beta)
    x = Variable.any("x")
    rule = ProductionRule([Pattern([x])], Pattern([x, alpha]), name="add_alpha")
    pcs = PostCanonicalSystem(
        alphabet=alphabet,
        axioms=frozenset({beta}),
        rules=frozenset({rule}),
        variables=frozenset({x}),
    )
    derived = pcs.generate(max_steps=2)
    return derived[-1].derivation


# === to_dot ===


class TestToDot:
    def test_axiom_only(self) -> None:
        out = to_dot(_empty_derivation())
        assert out.startswith("digraph derivation")
        assert "axiom" in out

    def test_multi_step(self) -> None:
        out = to_dot(_two_step_mu_derivation())
        assert "digraph derivation" in out
        assert "->" in out

    def test_escapes_double_quotes_in_word(self) -> None:
        # Construct a fake derivation step containing a double-quote in a word
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]), name='quote"rule')
        step = DerivationStep(
            inputs=('a"b',),
            rule=rule,
            binding=Binding({"x": 'a"b'}),
            output='c"d',
        )
        deriv = Derivation([step])
        out = to_dot(deriv)
        # Backslash-escaped quotes should appear in the rendered string
        assert '\\"' in out


# === to_latex ===


class TestToLatex:
    def test_axiom_only(self) -> None:
        assert to_latex(_empty_derivation()) == "\\text{(axiom)}"

    def test_multi_step_uses_align(self) -> None:
        out = to_latex(_two_step_mu_derivation())
        assert out.startswith("\\begin{align*}")
        assert out.endswith("\\end{align*}")
        assert "\\xrightarrow" in out

    def test_escapes_special_chars(self) -> None:
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]), name="rule_$one")
        step = DerivationStep(
            inputs=("a_b",),
            rule=rule,
            binding=Binding({"x": "a_b"}),
            output="c%d",
        )
        out = to_latex(Derivation([step]))
        # Underscore must be escaped, percent must be escaped
        assert "\\_" in out
        assert "\\%" in out
        # Dollar in rule name must be escaped
        assert "\\$" in out


# === to_ascii_tree ===


class TestToAsciiTree:
    def test_axiom_only(self) -> None:
        assert to_ascii_tree(_empty_derivation()) == "(axiom)"

    def test_multi_step_shows_root_word(self) -> None:
        deriv = _two_step_mu_derivation()
        out = to_ascii_tree(deriv)
        # Final word is the first line
        first_line = out.splitlines()[0]
        assert first_line == deriv.steps[-1].output

    def test_unicode_word(self) -> None:
        out = to_ascii_tree(_unicode_word_derivation())
        # Output should contain non-ASCII without crashing
        assert any(ord(c) > 127 for c in out)


# === to_mermaid ===


class TestToMermaid:
    def test_axiom_only(self) -> None:
        assert to_mermaid(_empty_derivation()) == "graph TD\n  axiom"

    def test_multi_step(self) -> None:
        out = to_mermaid(_two_step_mu_derivation())
        assert out.startswith("graph TD")
        assert "-->" in out

    def test_escapes_pipe_in_label(self) -> None:
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]), name="a|b")
        step = DerivationStep(
            inputs=("foo",),
            rule=rule,
            binding=Binding({"x": "foo"}),
            output="foo",
        )
        out = to_mermaid(Derivation([step]))
        # Pipe in rule label must be escaped to avoid breaking mermaid syntax
        assert "\\|" in out

    def test_quotes_node_with_special_chars(self) -> None:
        x = Variable.any("x")
        rule = ProductionRule([Pattern([x])], Pattern([x]), name="r")
        step = DerivationStep(
            inputs=("hello world",),
            rule=rule,
            binding=Binding({"x": "hello world"}),
            output="result",
        )
        out = to_mermaid(Derivation([step]))
        # Space-containing nodes must be wrapped in quotes
        assert '"hello world"' in out


# === Proof-DAG dedup ===


def _multi_antecedent_concat_derivation() -> Derivation:
    """Derive a word via the multi-antecedent concat fixture, exercising shared inputs."""
    x = Variable.any("x")
    y = Variable.any("y")
    rule = ProductionRule(
        antecedents=[Pattern([x]), Pattern([y])],
        consequent=Pattern([x, y]),
        name="concat",
    )
    pcs = PostCanonicalSystem(
        alphabet=BINARY,
        axioms=frozenset({"0", "1"}),
        rules=frozenset({rule}),
        variables=frozenset({x, y}),
    )
    derived = pcs.generate(max_steps=2)
    longest = max(derived, key=lambda dw: dw.derivation.length)
    return longest.derivation


def _derivation_with_duplicate_edge() -> Derivation:
    """Build a derivation whose step list contains the same edge twice."""
    x = Variable.any("x")
    rule = ProductionRule([Pattern([x])], Pattern([x, "0"]), name="append_0")
    step_a = DerivationStep(
        inputs=("1",),
        rule=rule,
        binding=Binding({"x": "1"}),
        output="10",
    )
    return Derivation([step_a, step_a])


class TestProofDagDedup:
    def test_dot_drops_duplicate_edges(self) -> None:
        out = to_dot(_derivation_with_duplicate_edge())
        # The same edge declaration should appear exactly once even though
        # the derivation lists the step twice.
        edge_line = '  "1" -> "10" [label="append_0"];'
        assert out.count(edge_line) == 1

    def test_mermaid_drops_duplicate_edges(self) -> None:
        out = to_mermaid(_derivation_with_duplicate_edge())
        edge_line = "  1 -->|append_0| 10"
        assert out.count(edge_line) == 1

    def test_dot_multi_antecedent_emits_one_edge_per_input(self) -> None:
        derivation = _multi_antecedent_concat_derivation()
        out = to_dot(derivation)
        # Each unique (input, output, rule) triple in the derivation should
        # appear once. We verify the count matches the unique-edge set.
        from post_canonical.visualization._proof_dag import proof_edges

        expected_edges = list(proof_edges(derivation))
        assert out.count("->") == len(expected_edges)
