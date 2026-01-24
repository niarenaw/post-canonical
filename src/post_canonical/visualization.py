"""Visualization and export for derivation proofs.

Provides multiple output formats for rendering derivations, suitable for
documentation, academic papers, and terminal display.
"""

from .system.derivation import Derivation


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
        rule_name = step.rule.name or "rule"
        # For multi-input rules, create edges from each input
        for input_word in step.inputs:
            escaped_input = _escape_dot_string(input_word)
            escaped_output = _escape_dot_string(step.output)
            lines.append(f'  "{escaped_input}" -> "{escaped_output}" [label="{rule_name}"];')

    lines.append("}")
    return "\n".join(lines)


def to_latex(derivation: Derivation) -> str:
    """Export derivation as LaTeX proof format.

    Uses the align* environment with xrightarrow for rule annotations.

    Args:
        derivation: The derivation to export.

    Returns:
        LaTeX formatted string.

    Example output:
        \\begin{align*}
        \\text{MI} &\\xrightarrow{\\text{double}} \\text{MII} \\\\
                  &\\xrightarrow{\\text{double}} \\text{MIIII}
        \\end{align*}
    """
    if derivation.is_axiom:
        return "\\text{(axiom)}"

    lines = ["\\begin{align*}"]

    for i, step in enumerate(derivation.steps):
        rule_name = step.rule.name or "rule"
        escaped_rule = _escape_latex(rule_name)

        # Format inputs (join with comma for multi-antecedent rules)
        inputs_str = ", ".join(f"\\text{{{_escape_latex(w)}}}" for w in step.inputs)
        output_str = f"\\text{{{_escape_latex(step.output)}}}"

        if i == 0:
            lines.append(f"{inputs_str} &\\xrightarrow{{\\text{{{escaped_rule}}}}} {output_str} \\\\")
        else:
            # Continuation lines are indented with &
            lines.append(f"          &\\xrightarrow{{\\text{{{escaped_rule}}}}} {output_str} \\\\")

    # Remove trailing \\ from last line
    lines[-1] = lines[-1].rstrip(" \\")

    lines.append("\\end{align*}")
    return "\n".join(lines)


def to_ascii_tree(derivation: Derivation) -> str:
    """Export derivation as a terminal-friendly ASCII tree.

    Displays the derivation from final word back to axiom, showing
    the tree structure of how words were derived. The label on each
    line indicates what rule was applied to transform that word into
    its parent in the tree.

    Args:
        derivation: The derivation to export.

    Returns:
        ASCII tree representation.

    Example output:
        MIIII
        +-- MII (double)
            +-- MI (axiom)
    """
    if derivation.is_axiom:
        return "(axiom)"

    lines: list[str] = []
    steps = list(derivation.steps)

    # Final word at the top (result of the last derivation step)
    final_word = steps[-1].output
    lines.append(final_word)

    # Build the tree going backwards through the derivation
    # Each step shows input(s) and the rule used to derive the output
    for i in range(len(steps) - 1, -1, -1):
        step = steps[i]
        rule_name = step.rule.name or "rule"
        indent = "    " * (len(steps) - 1 - i)

        for input_word in step.inputs:
            if i == 0:
                # First step's inputs are axioms (the starting points)
                lines.append(f"{indent}+-- {input_word} (axiom)")
            else:
                # This input came from the previous step
                lines.append(f"{indent}+-- {input_word} ({rule_name})")

    return "\n".join(lines)


def to_mermaid(derivation: Derivation) -> str:
    """Export derivation as Mermaid diagram format.

    Produces a top-down graph suitable for rendering in Markdown
    documentation or Mermaid-compatible viewers.

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

    for step in derivation.steps:
        rule_name = step.rule.name or "rule"
        # For multi-input rules, create edges from each input
        for input_word in step.inputs:
            escaped_input = _escape_mermaid_node(input_word)
            escaped_output = _escape_mermaid_node(step.output)
            escaped_rule = _escape_mermaid_label(rule_name)
            lines.append(f"  {escaped_input} -->|{escaped_rule}| {escaped_output}")

    return "\n".join(lines)


def _escape_dot_string(s: str) -> str:
    """Escape special characters for DOT node labels."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _escape_latex(s: str) -> str:
    """Escape special characters for LaTeX."""
    # Order matters: escape backslash first
    replacements = [
        ("\\", "\\textbackslash{}"),
        ("_", "\\_"),
        ("&", "\\&"),
        ("%", "\\%"),
        ("$", "\\$"),
        ("#", "\\#"),
        ("{", "\\{"),
        ("}", "\\}"),
        ("~", "\\textasciitilde{}"),
        ("^", "\\textasciicircum{}"),
    ]
    for old, new in replacements:
        s = s.replace(old, new)
    return s


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


__all__ = [
    "to_ascii_tree",
    "to_dot",
    "to_latex",
    "to_mermaid",
]
