"""GraphViz DOT exporter for derivation proofs."""

from ..system.derivation import Derivation
from ._proof_dag import proof_edges


def to_dot(derivation: Derivation) -> str:
    """Export derivation as GraphViz DOT format.

    Produces a directed graph where nodes are derived words and edges
    are labeled with the production rule applied. Repeated edges
    (same endpoints and rule) are deduplicated so the output is a
    proper DAG rather than a multigraph, which matches how proof
    structure is usually read.

    Args:
        derivation: The derivation to export.

    Returns:
        GraphViz DOT format string.

    Example output:
        digraph derivation {
          "MI" -> "MII" [label="double"];
          "MII" -> "MIIII" [label="double"];
        }
    """
    if derivation.is_axiom:
        return 'digraph derivation {\n  "axiom";\n}'

    lines = ["digraph derivation {"]
    for edge in proof_edges(derivation):
        escaped_input = _escape_dot_string(edge.input_word)
        escaped_output = _escape_dot_string(edge.output_word)
        lines.append(f'  "{escaped_input}" -> "{escaped_output}" [label="{edge.rule_name}"];')
    lines.append("}")
    return "\n".join(lines)


def _escape_dot_string(s: str) -> str:
    """Escape special characters for DOT node labels."""
    return s.replace("\\", "\\\\").replace('"', '\\"')
