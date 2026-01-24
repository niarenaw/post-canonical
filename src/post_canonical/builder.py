"""Fluent DSL builder for constructing Post Canonical Systems.

Provides an ergonomic API for building systems without manual object construction.

Example:
    system = (SystemBuilder(alphabet="MIU")
        .var("x")
        .var("y", kind="non_empty")
        .axiom("MI")
        .rule("${x} III ${y} -> ${x} U ${y}", name="replace_III")
        .rule("M ${x} -> M ${x} ${x}", name="double")
        .build())
"""

from __future__ import annotations

from typing import ClassVar, Self

from .core.alphabet import Alphabet
from .core.errors import format_set
from .core.pattern import Pattern
from .core.rule import ProductionRule
from .core.variable import Variable, VariableKind
from .system.pcs import PostCanonicalSystem


class BuilderError(Exception):
    """Raised when builder configuration is invalid."""

    pass


class SystemBuilder:
    """Fluent builder for PostCanonicalSystem instances.

    Allows ergonomic construction of systems using method chaining
    and a compact rule syntax.

    Variable Syntax in Rules:
        - ${name}: Explicit brace syntax (unambiguous)
        - $name: Short syntax (name ends at non-alphanumeric character)

    Rule Syntax:
        - Single antecedent: "pattern -> consequent"
        - Multiple antecedents: "pattern1, pattern2 -> consequent"
        - Whitespace in patterns is ignored (for readability)

    Example:
        system = (SystemBuilder("MIU")
            .var("x")
            .var("y")
            .axiom("MI")
            .rule("${x} III ${y} -> ${x} U ${y}")
            .build())
    """

    # Maps user-friendly kind names to VariableKind enum
    _KIND_MAP: ClassVar[dict[str, VariableKind]] = {
        "any": VariableKind.ANY,
        "non_empty": VariableKind.NON_EMPTY,
        "nonempty": VariableKind.NON_EMPTY,
        "single": VariableKind.SINGLE,
    }

    def __init__(self, alphabet: str | Alphabet) -> None:
        """Initialize builder with an alphabet.

        Args:
            alphabet: Either a string of symbols or an Alphabet instance.
        """
        if isinstance(alphabet, str):
            self._alphabet = Alphabet(alphabet)
        else:
            self._alphabet = alphabet

        self._variables: dict[str, Variable] = {}
        self._axioms: set[str] = set()
        self._rules: list[ProductionRule] = []

    def var(self, name: str, kind: str = "any") -> Self:
        """Declare a variable for use in patterns.

        Args:
            name: Variable name (alphanumeric with underscores).
            kind: One of "any" (default), "non_empty", or "single".

        Returns:
            Self for method chaining.

        Raises:
            BuilderError: If kind is invalid or variable already declared.
        """
        if name in self._variables:
            raise BuilderError(f"Variable '{name}' already declared")

        kind_lower = kind.lower()
        if kind_lower not in self._KIND_MAP:
            valid = ", ".join(sorted(self._KIND_MAP.keys()))
            raise BuilderError(f"Unknown variable kind '{kind}'. Valid: {valid}")

        self._variables[name] = Variable(name, self._KIND_MAP[kind_lower])
        return self

    def axiom(self, word: str) -> Self:
        """Add an axiom (starting word) to the system.

        Args:
            word: A word using only alphabet symbols.

        Returns:
            Self for method chaining.
        """
        self._axioms.add(word)
        return self

    def axioms(self, *words: str) -> Self:
        """Add multiple axioms at once.

        Args:
            *words: Words to add as axioms.

        Returns:
            Self for method chaining.
        """
        self._axioms.update(words)
        return self

    def rule(
        self,
        pattern: str,
        name: str | None = None,
        priority: int = 0,
    ) -> Self:
        """Add a production rule using pattern syntax.

        Args:
            pattern: Rule in format "antecedent -> consequent" or
                     "ant1, ant2 -> consequent" for multiple antecedents.
            name: Optional name for the rule.
            priority: Rule priority (higher = applied first).

        Returns:
            Self for method chaining.

        Raises:
            BuilderError: If pattern syntax is invalid.
        """
        parsed_rule = self._parse_rule(pattern, name, priority)
        self._rules.append(parsed_rule)
        return self

    def build(self) -> PostCanonicalSystem:
        """Build the PostCanonicalSystem.

        Returns:
            A new PostCanonicalSystem instance.

        Raises:
            BuilderError: If configuration is incomplete or invalid.
        """
        if not self._axioms:
            raise BuilderError("At least one axiom is required")

        if not self._rules:
            raise BuilderError("At least one rule is required")

        return PostCanonicalSystem(
            alphabet=self._alphabet,
            axioms=frozenset(self._axioms),
            rules=frozenset(self._rules),
            variables=frozenset(self._variables.values()),
        )

    def _parse_rule(
        self,
        pattern: str,
        name: str | None,
        priority: int,
    ) -> ProductionRule:
        """Parse a rule string into a ProductionRule."""
        if "->" not in pattern:
            raise BuilderError(f"Invalid rule syntax: '{pattern}'. Expected 'antecedent -> consequent'")

        parts = pattern.split("->", 1)
        antecedent_str, consequent_str = parts

        # Parse antecedents, splitting on comma for multi-antecedent rules.
        # Must be careful not to split inside variable references.
        antecedent_strs = self._split_antecedents(antecedent_str)
        antecedents = [self._parse_pattern(a) for a in antecedent_strs]
        consequent = self._parse_pattern(consequent_str)

        return ProductionRule(
            antecedents=antecedents,
            consequent=consequent,
            priority=priority,
            name=name,
        )

    def _split_antecedents(self, antecedent_str: str) -> list[str]:
        """Split antecedent string on commas, respecting variable syntax."""
        # Simple comma split works since variable names cannot contain commas.
        parts = antecedent_str.split(",")
        return [p.strip() for p in parts if p.strip()]

    def _parse_pattern(self, pattern_str: str) -> Pattern:
        """Parse a pattern string, handling both $name and ${name} syntax.

        Whitespace in patterns is stripped for readability, allowing patterns
        like "${x} III ${y}" instead of "${x}III${y}".
        """
        # Normalize the pattern by expanding $name to ${name} syntax,
        # then strip whitespace.
        normalized = self._normalize_pattern_string(pattern_str)
        return Pattern.parse(normalized, self._variables)

    def _normalize_pattern_string(self, pattern_str: str) -> str:
        """Convert $name syntax to ${name} and remove whitespace.

        This allows for more readable patterns like "$x III $y" which
        becomes "${x}III${y}".

        For the short $name format, uses longest-prefix matching against
        declared variables. This means "$xI" will match variable "x" followed
        by literal "I" if "x" is declared but "xI" is not.
        """
        result: list[str] = []
        i = 0
        text = pattern_str

        while i < len(text):
            if text[i] == "$":
                if i + 1 < len(text) and text[i + 1] == "{":
                    # Already in ${name} format, find closing brace.
                    j = i + 2
                    while j < len(text) and text[j] != "}":
                        j += 1
                    if j >= len(text):
                        raise BuilderError(f"Unclosed variable at position {i}")
                    result.append(text[i : j + 1])
                    i = j + 1
                else:
                    # Short $name format: find longest prefix that matches a declared variable.
                    j = i + 1
                    while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                        j += 1
                    if j == i + 1:
                        raise BuilderError(f"Empty variable name at position {i}")

                    # Try to match the longest prefix that is a declared variable.
                    full_name = text[i + 1 : j]
                    var_name = self._find_longest_variable_prefix(full_name)

                    if var_name is None:
                        declared = format_set(self._variables.keys()) if self._variables else "(none)"
                        raise BuilderError(
                            f"Unknown variable '${full_name}' in pattern \"{pattern_str.strip()}\"\n"
                            f"  Declared variables: {declared}\n"
                            f'  Hint: Add the variable with .var("{full_name}") or check spelling'
                        )

                    result.append(f"${{{var_name}}}")
                    # Advance by 1 (for $) + len(var_name)
                    i = i + 1 + len(var_name)
            elif text[i].isspace():
                # Skip whitespace in patterns.
                i += 1
            else:
                # Regular character.
                result.append(text[i])
                i += 1

        return "".join(result)

    def _find_longest_variable_prefix(self, name: str) -> str | None:
        """Find the longest prefix of name that is a declared variable.

        Returns the variable name if found, None otherwise.
        """
        # Try progressively shorter prefixes until we find a match.
        for length in range(len(name), 0, -1):
            prefix = name[:length]
            if prefix in self._variables:
                return prefix
        return None
