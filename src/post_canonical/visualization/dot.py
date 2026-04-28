"""GraphViz DOT exporter for derivation proofs."""

from ..system.derivation import Derivation


def to_dot(derivation: Derivation) -> str:
    """Export derivation as GraphViz DOT format.

    Produces a directed graph where nodes are derived words and edges
    are labeled with the production rule applied.

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

    for step in derivation.steps:
        rule_name = step.rule.display_name
        # For multi-input rules, create edges from each input
        for input_word in step.inputs:
            escaped_input = _escape_dot_string(input_word)
            escaped_output = _escape_dot_string(step.output)
            lines.append(f'  "{escaped_input}" -> "{escaped_output}" [label="{rule_name}"];')

    lines.append("}")
    return "\n".join(lines)


def _escape_dot_string(s: str) -> str:
    """Escape special characters for DOT node labels."""
    return s.replace("\\", "\\\\").replace('"', '\\"')
