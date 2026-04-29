"""Mermaid diagram exporter for derivation proofs."""

from ..system.derivation import Derivation
from ._proof_dag import proof_edges


def to_mermaid(derivation: Derivation) -> str:
    """Export derivation as Mermaid diagram format.

    Produces a top-down graph suitable for rendering in Markdown
    documentation or Mermaid-compatible viewers. Repeated edges
    (same endpoints and rule) are deduplicated so the output is a
    proper DAG rather than a multigraph.

    Args:
        derivation: The derivation to export.

    Returns:
        Mermaid diagram format string.

    Example output:
        graph TD
          MI -->|double| MII
          MII -->|double| MIIII
    """
    if derivation.is_axiom:
        return "graph TD\n  axiom"

    lines = ["graph TD"]
    for edge in proof_edges(derivation):
        escaped_input = _escape_mermaid_node(edge.input_word)
        escaped_output = _escape_mermaid_node(edge.output_word)
        escaped_rule = _escape_mermaid_label(edge.rule_name)
        lines.append(f"  {escaped_input} -->|{escaped_rule}| {escaped_output}")
    return "\n".join(lines)


def _escape_mermaid_node(s: str) -> str:
    """Escape/transform a string to be a valid Mermaid node ID.

    Empty strings and strings with special characters need quoting.
    """
    if not s:
        return 'empty[""]'
    # If the string contains special characters, wrap in quotes
    if any(c in s for c in " |[]{}()<>"):
        escaped = s.replace('"', '\\"')
        return f'"{escaped}"'
    return s


def _escape_mermaid_label(s: str) -> str:
    """Escape special characters in Mermaid edge labels."""
    # Pipe characters need escaping in labels
    return s.replace("|", "\\|")
