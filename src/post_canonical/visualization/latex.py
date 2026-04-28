"""LaTeX exporter for derivation proofs."""

from ..system.derivation import Derivation


def to_latex(derivation: Derivation) -> str:
    """Export derivation as LaTeX proof format.

    Uses the ``align*`` environment with ``\\xrightarrow`` for rule annotations.

    Args:
        derivation: The derivation to export.

    Returns:
        LaTeX formatted string.

    Example output::

        \\begin{align*}
        \\text{MI} &\\xrightarrow{\\text{double}} \\text{MII} \\\\
                  &\\xrightarrow{\\text{double}} \\text{MIIII}
        \\end{align*}
    """
    if derivation.is_axiom:
        return "\\text{(axiom)}"

    lines = ["\\begin{align*}"]

    for i, step in enumerate(derivation.steps):
        rule_name = step.rule.display_name
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
