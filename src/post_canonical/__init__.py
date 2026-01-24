"""Post Canonical Systems - A Python implementation.

A Post Canonical System is a formal system for string manipulation,
developed by Emil Post in the 1920s. It consists of:
- An alphabet of symbols
- A set of axioms (initial words)
- A set of production rules

The system generates all words derivable from the axioms by
repeatedly applying the production rules.

Example usage:

    from post_canonical import (
        PostCanonicalSystem,
        Alphabet,
        Variable,
        Pattern,
        ProductionRule,
    )
    from post_canonical.presets import create_mu_puzzle
    from post_canonical.query import ReachabilityQuery

    # Create the MU puzzle
    mu = create_mu_puzzle()
    print(mu.describe())

    # Generate words
    words = mu.generate_words(max_steps=3)
    print(f"Generated {len(words)} words")

    # Check if MU is derivable
    query = ReachabilityQuery(mu)
    result = query.is_derivable("MU", max_words=1000)
    print(result)
"""

# Core types
from .core.alphabet import Alphabet
from .core.pattern import Pattern
from .core.rule import ProductionRule
from .core.variable import Variable, VariableKind

# Presets
from .presets.alphabets import (
    BINARY,
    DECIMAL,
    ENGLISH_LETTERS,
    ENGLISH_LOWERCASE,
    ENGLISH_UPPERCASE,
    HEXADECIMAL,
    MIU,
)
from .presets.examples import (
    create_binary_doubler,
    create_mu_puzzle,
    create_palindrome_generator,
)

# Query
from .query.reachability import QueryResult, ReachabilityQuery, ReachabilityResult

# Serialization
from .serialization.json_codec import PCSJsonCodec
from .system.derivation import Derivation, DerivationStep, DerivedWord
from .system.executor import ExecutionConfig, ExecutionMode

# System
from .system.pcs import PostCanonicalSystem

__version__ = "2.0.0"

__all__ = [
    # Preset alphabets
    "BINARY",
    "DECIMAL",
    "ENGLISH_LETTERS",
    "ENGLISH_LOWERCASE",
    "ENGLISH_UPPERCASE",
    "HEXADECIMAL",
    "MIU",
    # Core
    "Alphabet",
    "Derivation",
    "DerivationStep",
    "DerivedWord",
    "ExecutionConfig",
    "ExecutionMode",
    # Serialization
    "PCSJsonCodec",
    "Pattern",
    # System
    "PostCanonicalSystem",
    "ProductionRule",
    # Query
    "QueryResult",
    "ReachabilityQuery",
    "ReachabilityResult",
    "Variable",
    "VariableKind",
    "create_binary_doubler",
    # Preset examples
    "create_mu_puzzle",
    "create_palindrome_generator",
]
