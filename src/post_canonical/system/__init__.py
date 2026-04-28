"""Post Canonical System implementation with derivation tracking."""

from .derivation import Derivation, DerivationStep, DerivedWord
from .executor import ExecutionConfig, ExecutionMode
from .pcs import PostCanonicalSystem

# RuleExecutor is intentionally not re-exported. It is an internal
# implementation detail; callers should reach through PostCanonicalSystem.
__all__ = [
    "Derivation",
    "DerivationStep",
    "DerivedWord",
    "ExecutionConfig",
    "ExecutionMode",
    "PostCanonicalSystem",
]
