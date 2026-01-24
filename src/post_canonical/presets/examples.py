"""Example Post Canonical Systems."""

from ..core.pattern import Pattern
from ..core.rule import ProductionRule
from ..core.variable import Variable
from ..system.pcs import PostCanonicalSystem
from .alphabets import BINARY, MIU


def create_mu_puzzle() -> PostCanonicalSystem:
    """Create the famous MU puzzle from Gödel, Escher, Bach.

    The MU puzzle is a formal system with these rules:
    1. xI -> xIU       (add U after I at the end)
    2. Mx -> Mxx       (double the string after M)
    3. xIIIy -> xUy    (replace III with U)
    4. xUUy -> xy      (delete UU)

    Starting from "MI", the puzzle asks: can you derive "MU"?

    Spoiler: No! The number of I's is never divisible by 3.
    """
    # Declare variables
    x = Variable.any("x")
    y = Variable.any("y")

    # Create rules
    rules = frozenset(
        {
            ProductionRule(
                antecedents=[Pattern([x, "I"])],
                consequent=Pattern([x, "I", "U"]),
                name="add_U",
                priority=1,
            ),
            ProductionRule(
                antecedents=[Pattern(["M", x])],
                consequent=Pattern(["M", x, x]),
                name="double",
                priority=2,
            ),
            ProductionRule(
                antecedents=[Pattern([x, "III", y])],
                consequent=Pattern([x, "U", y]),
                name="III_to_U",
                priority=3,
            ),
            ProductionRule(
                antecedents=[Pattern([x, "UU", y])],
                consequent=Pattern([x, y]),
                name="delete_UU",
                priority=4,
            ),
        }
    )

    return PostCanonicalSystem(
        alphabet=MIU,
        axioms=frozenset({"MI"}),
        rules=rules,
        variables=frozenset({x, y}),
    )


def create_binary_doubler() -> PostCanonicalSystem:
    """Create a system that generates binary strings by doubling.

    Starting from "1", repeatedly doubles the string.
    Generates: 1, 11, 1111, 11111111, ...
    """
    x = Variable.any("x")

    rules = frozenset(
        {
            ProductionRule(
                antecedents=[Pattern([x])],
                consequent=Pattern([x, x]),
                name="double",
            ),
        }
    )

    return PostCanonicalSystem(
        alphabet=BINARY,
        axioms=frozenset({"1"}),
        rules=rules,
        variables=frozenset({x}),
    )


def create_palindrome_generator() -> PostCanonicalSystem:
    """Create a system that generates binary palindromes.

    Rules:
    - x -> 0x0    (wrap with 0s)
    - x -> 1x1    (wrap with 1s)

    Starting from "", generates all binary palindromes.
    """
    x = Variable.any("x")

    rules = frozenset(
        {
            ProductionRule(
                antecedents=[Pattern([x])],
                consequent=Pattern(["0", x, "0"]),
                name="wrap_0",
                priority=1,
            ),
            ProductionRule(
                antecedents=[Pattern([x])],
                consequent=Pattern(["1", x, "1"]),
                name="wrap_1",
                priority=2,
            ),
        }
    )

    # Start with empty string and single characters
    return PostCanonicalSystem(
        alphabet=BINARY,
        axioms=frozenset({"", "0", "1"}),
        rules=rules,
        variables=frozenset({x}),
    )
