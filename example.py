from src.post_canonical import (
    PostCanonicalSystem,
    ProductionRule,
    Alphabet,
    create_mu_puzzle,
    BINARY,
)


def main():
    # Example 1: MU Puzzle
    print("MU Puzzle Example:")
    print("-" * 50)
    mu_system = create_mu_puzzle()
    print(f"Initial word: {mu_system.initial_words}")
    print("\nRules:")
    for rule in mu_system.rules:
        print(f"  {rule}")

    print("\nGenerating words (max 5 steps):")
    words = mu_system.generate_words(max_steps=5)
    for word in sorted(words):
        print(f"  {word}")

    # Example 2: Binary number system
    print("\nBinary Number System Example:")
    print("-" * 50)

    initial_words = {'0', '1'}
    rules = {
        ProductionRule(('x',), 'x0'),  # Append 0
        ProductionRule(('x',), 'x1'),  # Append 1
    }

    binary_system = PostCanonicalSystem(BINARY, initial_words, rules)
    print(f"Initial words: {binary_system.initial_words}")
    print("\nRules:")
    for rule in binary_system.rules:
        print(f"  {rule}")

    print("\nGenerating binary numbers (max 3 steps):")
    words = binary_system.generate_words(max_steps=3)
    for word in sorted(words):
        print(f"  {word}")

    # Example 3: Custom alphabet
    print("\nCustom Alphabet Example:")
    print("-" * 50)

    # Create a system that generates words with only vowels
    vowel_alphabet = Alphabet('aeiou')
    initial_words = {'a', 'e', 'i', 'o', 'u'}
    rules = {
        ProductionRule(('x',), 'xa'),  # Append 'a'
        ProductionRule(('x',), 'xe'),  # Append 'e'
        ProductionRule(('x',), 'xi'),  # Append 'i'
    }

    vowel_system = PostCanonicalSystem(vowel_alphabet, initial_words, rules)
    print(f"Initial words: {vowel_system.initial_words}")
    print("\nRules:")
    for rule in vowel_system.rules:
        print(f"  {rule}")

    print("\nGenerating vowel words (max 2 steps):")
    words = vowel_system.generate_words(max_steps=2)
    for word in sorted(words):
        print(f"  {word}")


if __name__ == "__main__":
    main()
