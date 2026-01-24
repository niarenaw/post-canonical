"""Reachability queries for Post Canonical Systems."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from ..system.derivation import Derivation
from ..system.executor import ExecutionMode

if TYPE_CHECKING:
    from ..system.pcs import PostCanonicalSystem


class QueryResult(Enum):
    """Result of a derivability query."""

    DERIVABLE = auto()  # Word is definitely derivable
    NOT_FOUND = auto()  # Could not find derivation within limits
    # Note: We can never prove NOT_DERIVABLE for infinite systems


@dataclass(frozen=True)
class ReachabilityResult:
    """Full result of a reachability query."""

    status: QueryResult
    derivation: Derivation | None  # If derivable, how
    steps_explored: int  # How many words were explored
    target: str  # The word we were looking for

    def __str__(self) -> str:
        if self.status == QueryResult.DERIVABLE:
            return f"'{self.target}' is DERIVABLE in {self.derivation.length if self.derivation else 0} steps"
        return f"'{self.target}' NOT_FOUND after exploring {self.steps_explored} words"

    @property
    def found(self) -> bool:
        """True if the target word was found to be derivable."""
        return self.status == QueryResult.DERIVABLE


class ReachabilityQuery:
    """Query whether a word is derivable in a Post Canonical System.

    Uses breadth-first exploration from axioms to find derivations.
    """

    def __init__(self, system: "PostCanonicalSystem") -> None:
        self.system = system

    def is_derivable(
        self,
        target: str,
        max_words: int = 10000,
        mode: ExecutionMode = ExecutionMode.NON_DETERMINISTIC,
    ) -> ReachabilityResult:
        """Check if target word is derivable.

        Explores the derivation space breadth-first until either:
        - The target is found (returns DERIVABLE with proof)
        - max_words are explored without finding target (returns NOT_FOUND)

        Args:
            target: The word to search for
            max_words: Maximum number of words to explore
            mode: Execution mode for rule application

        Returns:
            ReachabilityResult with status and derivation if found
        """
        # Check if target is an axiom
        if target in self.system.axioms:
            return ReachabilityResult(
                status=QueryResult.DERIVABLE,
                derivation=Derivation(),
                steps_explored=0,
                target=target,
            )

        # Forward search
        words_explored = 0
        for derived_word in self.system.iterate(mode):
            words_explored += 1

            if derived_word.word == target:
                return ReachabilityResult(
                    status=QueryResult.DERIVABLE,
                    derivation=derived_word.derivation,
                    steps_explored=words_explored,
                    target=target,
                )

            if words_explored >= max_words:
                break

        # Could not find - might still be derivable with more exploration
        return ReachabilityResult(
            status=QueryResult.NOT_FOUND,
            derivation=None,
            steps_explored=words_explored,
            target=target,
        )

    def find_derivation(
        self,
        target: str,
        max_words: int = 10000,
    ) -> Derivation | None:
        """Find a derivation for target, or None if not found.

        Convenience method that just returns the derivation.
        """
        result = self.is_derivable(target, max_words)
        return result.derivation

    def can_reach(
        self,
        target: str,
        max_words: int = 10000,
    ) -> bool:
        """Return True if target is reachable within max_words exploration.

        Convenience method for simple yes/no queries.
        """
        return self.is_derivable(target, max_words).found
