"""Error formatting utilities for actionable, contextual error messages."""

from collections.abc import Iterable


def format_set(items: Iterable[str], max_display: int = 10) -> str:
    """Format a collection of items as a set-like string.

    Sorts items alphabetically and truncates if there are too many.
    """
    sorted_items = sorted(items)
    if len(sorted_items) > max_display:
        displayed = sorted_items[:max_display]
        return "{" + ", ".join(displayed) + f", ... (+{len(sorted_items) - max_display} more)}}"
    return "{" + ", ".join(sorted_items) + "}"


class ValidationError(ValueError):
    """A validation error with structured context and hints.

    Extends ValueError to provide multi-line, contextual error messages that
    help users understand what went wrong and how to fix it.
    """

    def __init__(
        self,
        summary: str,
        *,
        context: dict[str, str] | None = None,
        hint: str | None = None,
    ) -> None:
        self.summary = summary
        self.context = context or {}
        self.hint = hint

        lines = [summary]
        for key, value in self.context.items():
            lines.append(f"  {key}: {value}")
        if hint:
            lines.append(f"  Hint: {hint}")

        super().__init__("\n".join(lines))
