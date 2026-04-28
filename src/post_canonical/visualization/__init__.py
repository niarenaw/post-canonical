"""Visualization and export for derivation proofs.

Each output format lives in its own submodule. This package re-exports
the four user-facing functions so existing imports
(``from post_canonical.visualization import to_dot``) keep working.
"""

from .ascii_tree import to_ascii_tree
from .dot import to_dot
from .latex import to_latex
from .mermaid import to_mermaid

__all__ = [
    "to_ascii_tree",
    "to_dot",
    "to_latex",
    "to_mermaid",
]
