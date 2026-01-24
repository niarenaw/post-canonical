#!/usr/bin/env python3
"""Example usage of the Post Canonical Systems library.

Demonstrates the key features:
1. Creating and exploring the MU puzzle
2. Building a custom system
3. Querying derivability
4. Serialization to/from JSON
"""

from post_canonical import (
    Alphabet,
    ExecutionMode,
    Pattern,
    PCSJsonCodec,
    PostCanonicalSystem,
    ProductionRule,
    ReachabilityQuery,
    Variable,
    create_mu_puzzle,
    create_palindrome_generator,
)


def demo_mu_puzzle() -> None:
    """Demonstrate the famous MU puzzle from Gödel, Escher, Bach."""
    print("=" * 60)
    print("MU PUZZLE")
    print("=" * 60)

    # Create the MU puzzle
    mu = create_mu_puzzle()
    print(mu.describe())
    print()

    # Generate some words
    print("Generating words (3 steps)...")
    derived = mu.generate(max_steps=3)

    print(f"Found {len(derived)} unique words:\n")
    for dw in sorted(derived, key=lambda d: (d.derivation.length, d.word)):
        print(f"  '{dw.word}' ({dw.derivation.length} steps)")

    # Show a derivation trace
    print("\nExample derivation trace:")
    for dw in derived:
        if dw.word == "MIUIU" or (dw.derivation.length == 2 and not dw.is_axiom):
            print(dw.trace())
            break

    # Query: is MU derivable?
    print("\nQuerying: Is 'MU' derivable?")
    query = ReachabilityQuery(mu)
    result = query.is_derivable("MU", max_words=500)
    print(f"Result: {result}")
    print("(Spoiler: MU is NOT derivable - the number of I's is never divisible by 3)")


def demo_custom_system() -> None:
    """Demonstrate building a custom Post Canonical System."""
    print("\n" + "=" * 60)
    print("CUSTOM SYSTEM: Simple Arithmetic")
    print("=" * 60)

    # A system that models unary addition
    # Alphabet: | (tally mark), + (plus), = (equals)
    alphabet = Alphabet("|+=")

    # Variables
    x = Variable.any("x")
    y = Variable.any("y")

    # Rule: x + | y = z  ->  x | + y = z
    # (Move a tally from right side of + to left side)
    rules = frozenset(
        {
            ProductionRule(
                antecedents=[Pattern([x, "+|", y])],
                consequent=Pattern([x, "|+", y]),
                name="move_tally",
            ),
        }
    )

    system = PostCanonicalSystem(
        alphabet=alphabet,
        axioms=frozenset({"|+||", "||+|||"}),  # 1+2, 2+3
        rules=rules,
        variables=frozenset({x, y}),
    )

    print(system.describe())
    print()

    # Generate words
    print("Generating derivations...")
    for dw in system.generate(max_steps=5):
        print(f"  '{dw.word}' - {dw.derivation.length} steps")


def demo_palindromes() -> None:
    """Demonstrate the palindrome generator."""
    print("\n" + "=" * 60)
    print("PALINDROME GENERATOR")
    print("=" * 60)

    system = create_palindrome_generator()
    print(system.describe())
    print()

    # Generate palindromes
    print("Binary palindromes (up to 4 steps):")
    words = system.generate_words(max_steps=4)
    for w in sorted(words, key=lambda x: (len(x), x)):
        if w:  # Skip empty string for display
            print(f"  {w}")


def demo_serialization() -> None:
    """Demonstrate JSON serialization."""
    print("\n" + "=" * 60)
    print("SERIALIZATION")
    print("=" * 60)

    # Create a system
    original = create_mu_puzzle()

    # Serialize to JSON
    codec = PCSJsonCodec()
    json_str = codec.encode(original)

    print("JSON representation:")
    print(json_str)

    # Deserialize back
    restored = codec.decode(json_str)

    # Verify they produce the same words
    original_words = original.generate_words(max_steps=2)
    restored_words = restored.generate_words(max_steps=2)

    print(f"\nOriginal generates {len(original_words)} words")
    print(f"Restored generates {len(restored_words)} words")
    print(f"Match: {original_words == restored_words}")


def demo_multi_antecedent() -> None:
    """Demonstrate rules with multiple antecedents.

    Multi-antecedent rules match against multiple words simultaneously
    and combine them. This example shows a simple concatenation system
    where two existing words can be joined together.
    """
    print("\n" + "=" * 60)
    print("MULTI-ANTECEDENT RULES")
    print("=" * 60)

    # Create an alphabet for simple word building
    alphabet = Alphabet("ab.")

    # Variables that will unify across multiple antecedents
    x = Variable.any("x")
    y = Variable.any("y")

    # Multi-antecedent rule: given two words, produce their concatenation
    # separated by a dot. This rule takes TWO input words and combines them.
    #
    # If we have words "a" and "b", the rule matches:
    #   - First antecedent: "a" with x=""
    #   - Second antecedent: "b" with y=""
    # And produces: "a.b"
    concat_rule = ProductionRule(
        antecedents=[
            Pattern(["a", x]),  # Match word starting with 'a'
            Pattern(["b", y]),  # Match word starting with 'b'
        ],
        consequent=Pattern(["a", x, ".b", y]),  # Combine them with a dot
        name="concat",
    )

    system = PostCanonicalSystem(
        alphabet=alphabet,
        axioms=frozenset({"a", "b", "aa", "bb"}),
        rules=frozenset({concat_rule}),
        variables=frozenset({x, y}),
    )

    print(system.describe())
    print()

    # Generate and show results
    print("Derived words:")
    for dw in sorted(system.generate(max_steps=2), key=lambda d: (d.derivation.length, d.word)):
        if dw.derivation.length > 0:  # Only show derived (non-axiom) words
            print(f"  '{dw.word}'")
            # Show the inputs that were combined
            if dw.derivation.steps:
                step = dw.derivation.steps[-1]
                print(f"    Combined: {step.inputs} -> '{step.output}'")

    print("\n  Note: Each derived word comes from combining TWO input words.")
    print("  The rule requires both antecedent patterns to match simultaneously.")


def demo_variable_kinds() -> None:
    """Demonstrate the three variable kinds: ANY, NON_EMPTY, and SINGLE.

    Variable kinds control what strings a variable can match:
    - ANY: Matches any string, including empty string
    - NON_EMPTY: Matches at least one character
    - SINGLE: Matches exactly one character
    """
    print("\n" + "=" * 60)
    print("VARIABLE KINDS")
    print("=" * 60)

    alphabet = Alphabet("ab")

    # Create variables of each kind
    any_var = Variable.any("any")  # Can match "", "a", "ab", etc.
    nonempty = Variable.non_empty("nonempty")  # Must match at least one char
    single = Variable.single("single")  # Must match exactly one char

    print("Variable kinds:")
    print(f"  {any_var} (ANY) - matches any string including empty")
    print(f"  {nonempty} (NON_EMPTY) - matches one or more characters")
    print(f"  {single} (SINGLE) - matches exactly one character")
    print()

    # Demo 1: ANY variable allows empty match
    # Rule: aXb -> Xb (remove leading 'a' before any content)
    any_rule = ProductionRule(
        antecedents=[Pattern(["a", any_var, "b"])],
        consequent=Pattern([any_var, "b"]),
        name="strip_a",
    )
    any_system = PostCanonicalSystem(
        alphabet=alphabet,
        axioms=frozenset({"ab", "aab", "abb"}),
        rules=frozenset({any_rule}),
        variables=frozenset({any_var}),
    )

    print("System with ANY variable (can match empty):")
    print("  Rule: a${any}b -> ${any}b")
    print("  Axioms: ab, aab, abb")
    print("  Results:", sorted(any_system.generate_words(max_steps=2)))
    print("  'ab' matches with ${any}='' (empty), producing 'b'")
    print()

    # Demo 2: NON_EMPTY variable requires at least one char
    nonempty_rule = ProductionRule(
        antecedents=[Pattern(["a", nonempty, "b"])],
        consequent=Pattern([nonempty, "b"]),
        name="strip_a_nonempty",
    )
    nonempty_system = PostCanonicalSystem(
        alphabet=alphabet,
        axioms=frozenset({"ab", "aab", "abb"}),
        rules=frozenset({nonempty_rule}),
        variables=frozenset({nonempty}),
    )

    print("System with NON_EMPTY variable (must match at least one char):")
    print("  Rule: a${nonempty}b -> ${nonempty}b")
    print("  Axioms: ab, aab, abb")
    print("  Results:", sorted(nonempty_system.generate_words(max_steps=2)))
    print("  'ab' does NOT match (nothing between a and b for variable)")
    print()

    # Demo 3: SINGLE variable matches exactly one char
    single_rule = ProductionRule(
        antecedents=[Pattern(["a", single, "b"])],
        consequent=Pattern([single, "b"]),
        name="strip_a_single",
    )
    single_system = PostCanonicalSystem(
        alphabet=alphabet,
        axioms=frozenset({"ab", "aab", "abb", "aaab"}),
        rules=frozenset({single_rule}),
        variables=frozenset({single}),
    )

    print("System with SINGLE variable (exactly one character):")
    print("  Rule: a${single}b -> ${single}b")
    print("  Axioms: ab, aab, abb, aaab")
    print("  Results:", sorted(single_system.generate_words(max_steps=2)))
    print("  Only 'aab' and 'abb' match (exactly one char between a and b)")


def demo_execution_modes() -> None:
    """Demonstrate DETERMINISTIC vs NON_DETERMINISTIC execution modes.

    Execution modes control how many rule applications are explored:
    - DETERMINISTIC: Only the first matching rule/binding is applied
    - NON_DETERMINISTIC: All possible rule applications are explored

    This affects both which words are generated and system performance.
    """
    print("\n" + "=" * 60)
    print("EXECUTION MODES")
    print("=" * 60)

    alphabet = Alphabet("ab")
    x = Variable.any("x")

    # Two rules that can both apply to some words
    rule_a = ProductionRule(
        antecedents=[Pattern([x, "a"])],
        consequent=Pattern([x, "aa"]),  # Double trailing 'a'
        name="double_a",
        priority=1,
    )
    rule_b = ProductionRule(
        antecedents=[Pattern([x, "b"])],
        consequent=Pattern([x, "bb"]),  # Double trailing 'b'
        name="double_b",
        priority=0,
    )

    system = PostCanonicalSystem(
        alphabet=alphabet,
        axioms=frozenset({"a", "b", "ab"}),
        rules=frozenset({rule_a, rule_b}),
        variables=frozenset({x}),
    )

    print(system.describe())
    print()

    # Deterministic mode: only first match per rule application
    print("DETERMINISTIC mode (first match only, respects priority):")
    det_words = system.generate_words(max_steps=2, mode=ExecutionMode.DETERMINISTIC)
    print(f"  Words found: {sorted(det_words)}")
    print("  Explores one path through the derivation tree")
    print()

    # Non-deterministic mode: all possible matches
    print("NON_DETERMINISTIC mode (all possible matches):")
    nondet_words = system.generate_words(max_steps=2, mode=ExecutionMode.NON_DETERMINISTIC)
    print(f"  Words found: {sorted(nondet_words)}")
    print("  Explores all paths through the derivation tree")
    print()

    print("Comparison:")
    print(f"  Deterministic found {len(det_words)} words")
    print(f"  Non-deterministic found {len(nondet_words)} words")
    print()
    print("  Use DETERMINISTIC for:")
    print("    - Predictable, reproducible behavior")
    print("    - Performance when you only need one derivation")
    print()
    print("  Use NON_DETERMINISTIC for:")
    print("    - Exhaustive exploration of all possibilities")
    print("    - Finding all derivable words")
    print("    - Proving properties about the system")


def main() -> None:
    """Run all demonstrations."""
    demo_mu_puzzle()
    demo_custom_system()
    demo_palindromes()
    demo_serialization()
    demo_multi_antecedent()
    demo_variable_kinds()
    demo_execution_modes()


if __name__ == "__main__":
    main()
