"""Shared walker that flattens a derivation into a deduplicated DAG.

A :class:`~post_canonical.system.derivation.Derivation` is a sequence
of derivation steps; rendering it naively produces one graph edge per
``(input, output)`` pair per step. When the same input appears in
multiple steps - either because the executor merged sub-derivations
for a multi-antecedent rule, or because two distinct paths converge on
the same intermediate word - the naive rendering emits duplicate
edges. Graph viewers dedupe nodes by label but not edges, so the
resulting picture has phantom multi-edges that misrepresent the proof
structure.

This walker collects nodes and edges once each, in derivation order,
and exposes them as plain tuples that the DOT and Mermaid exporters
can consume. ASCII-tree and LaTeX renderings keep their existing
linear behavior because their target formats are inherently sequential.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from ..system.derivation import Derivation


@dataclass(frozen=True, slots=True)
class ProofEdge:
    """One directed edge in the proof DAG.

    ``input_word`` and ``output_word`` are the connected nodes; the
    rule name labels the edge. Edges are uniquely identified by the
    triple ``(input_word, output_word, rule_name)``: two distinct
    steps that share all three are visually identical and rendered
    once.
    """

    input_word: str
    output_word: str
    rule_name: str


def proof_edges(derivation: Derivation) -> Iterator[ProofEdge]:
    """Yield each unique edge in the derivation, in first-seen order.

    A multi-antecedent step contributes one edge per input. Edges that
    repeat (same endpoints, same rule) are collapsed to a single
    yield, preserving the order of their first appearance so the
    rendered output remains stable across runs.
    """
    seen: set[tuple[str, str, str]] = set()
    for step in derivation.steps:
        rule_name = step.rule.display_name
        for input_word in step.inputs:
            key = (input_word, step.output, rule_name)
            if key in seen:
                continue
            seen.add(key)
            yield ProofEdge(input_word=input_word, output_word=step.output, rule_name=rule_name)
