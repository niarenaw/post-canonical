"""ASCII-tree exporter for derivation proofs."""

from ..system.derivation import Derivation


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
        rule_name = step.rule.display_name
        indent = "    " * (len(steps) - 1 - i)

        for input_word in step.inputs:
            if i == 0:
                # First step's inputs are axioms (the starting points)
                lines.append(f"{indent}+-- {input_word} (axiom)")
            else:
                # This input came from the previous step
                lines.append(f"{indent}+-- {input_word} ({rule_name})")

    return "\n".join(lines)
