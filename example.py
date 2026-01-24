#!/usr/bin/env python3
"""Example usage of the Post Canonical Systems library.

Demonstrates the key features:
1. Creating and exploring the MU puzzle
2. Building a custom system
3. Querying derivability
4. Serialization to/from JSON
"""

from post_canonical import (
    PostCanonicalSystem,
    Alphabet,
    Variable,
    Pattern,
    ProductionRule,
    ReachabilityQuery,
    PCSJsonCodec,
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
    rules = frozenset({
        ProductionRule(
            antecedents=[Pattern([x, "+|", y])],
            consequent=Pattern([x, "|+", y]),
            name="move_tally",
        ),
    })

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


def main() -> None:
    """Run all demonstrations."""
    demo_mu_puzzle()
    demo_custom_system()
    demo_palindromes()
    demo_serialization()


if __name__ == "__main__":
    main()
