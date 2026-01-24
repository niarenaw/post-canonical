"""Shared pytest fixtures for Post Canonical Systems tests."""

import pytest

from post_canonical import (
    Alphabet,
    ExecutionConfig,
    ExecutionMode,
    Pattern,
    PostCanonicalSystem,
    ProductionRule,
    Variable,
)
from post_canonical.presets import create_binary_doubler, create_mu_puzzle, create_palindrome_generator
from post_canonical.presets.alphabets import BINARY, MIU


@pytest.fixture
def mu_system() -> PostCanonicalSystem:
    """The classic MU puzzle from Godel, Escher, Bach."""
    return create_mu_puzzle()


@pytest.fixture
def binary_doubler() -> PostCanonicalSystem:
    """A system that doubles binary strings."""
    return create_binary_doubler()


@pytest.fixture
def palindrome_generator() -> PostCanonicalSystem:
    """A system that generates binary palindromes."""
    return create_palindrome_generator()


@pytest.fixture
def binary_alphabet() -> Alphabet:
    """Binary alphabet: {0, 1}."""
    return BINARY


@pytest.fixture
def miu_alphabet() -> Alphabet:
    """MIU alphabet: {M, I, U}."""
    return MIU


@pytest.fixture
def simple_vars() -> dict[str, Variable]:
    """Standard variable set for testing."""
    return {
        "x": Variable.any("x"),
        "y": Variable.non_empty("y"),
        "z": Variable.single("z"),
    }


@pytest.fixture
def any_var() -> Variable:
    """A variable that matches any string including empty."""
    return Variable.any("x")


@pytest.fixture
def non_empty_var() -> Variable:
    """A variable that matches at least one character."""
    return Variable.non_empty("y")


@pytest.fixture
def single_var() -> Variable:
    """A variable that matches exactly one character."""
    return Variable.single("z")


@pytest.fixture
def deterministic_config() -> ExecutionConfig:
    """Configuration for deterministic execution mode."""
    return ExecutionConfig(mode=ExecutionMode.DETERMINISTIC)


@pytest.fixture
def non_deterministic_config() -> ExecutionConfig:
    """Configuration for non-deterministic execution mode."""
    return ExecutionConfig(mode=ExecutionMode.NON_DETERMINISTIC)


@pytest.fixture
def multi_antecedent_system() -> PostCanonicalSystem:
    """A system with a multi-antecedent rule for testing.

    This system concatenates two strings when both are present.
    Rule: x, y -> xy (combine two words into one)
    """
    x = Variable.any("x")
    y = Variable.any("y")

    # Multi-antecedent rule: if we have words matching x and y, produce xy
    concat_rule = ProductionRule(
        antecedents=[Pattern([x]), Pattern([y])],
        consequent=Pattern([x, y]),
        name="concat",
    )

    return PostCanonicalSystem(
        alphabet=BINARY,
        axioms=frozenset({"0", "1"}),
        rules=frozenset({concat_rule}),
        variables=frozenset({x, y}),
    )
