from .alphabet import Alphabet
from .production_rule import ProductionRule


class PostCanonicalSystem:
    """Implements a Post Canonical System as defined by Emil Post."""

    def __init__(self, alphabet: Alphabet, initial_words: set[str], rules: set[ProductionRule]):
        """Initialize a Post Canonical System.

        Args:
            alphabet: The alphabet of the system
            initial_words: Set of initial words
            rules: Set of production rules
        """
        self.alphabet = alphabet
        self.initial_words = frozenset(initial_words)
        self.rules = frozenset(rules)

        # Validate that all words and rules use only symbols from the alphabet
        self._validate_words()
        self._validate_rules()

    def _validate_words(self):
        """Validate that all initial words use only symbols from the alphabet."""
        for word in self.initial_words:
            if not all(symbol in self.alphabet for symbol in word):
                raise ValueError(f"Word '{word}' contains symbols not in alphabet {self.alphabet}")

    def _validate_rules(self):
        """Validate that all rules use only symbols from the alphabet for constants."""
        for rule in self.rules:
            # Check antecedents
            for antecedent in rule.antecedents:
                # Only validate constants (characters in the alphabet)
                if not all(symbol in self.alphabet or symbol not in self.alphabet for symbol in antecedent):
                    raise ValueError(f"Antecedent '{antecedent}' contains invalid symbols")
            # Check consequent
            if not all(symbol in self.alphabet or symbol not in self.alphabet for symbol in rule.consequent):
                raise ValueError(f"Consequent '{rule.consequent}' contains invalid symbols")

    def apply_rule(self, word: str, rule: ProductionRule) -> str | None:
        """Try to apply a production rule to a word.

        Args:
            word: The word to apply the rule to
            rule: The production rule to apply

        Returns:
            The resulting word if the rule can be applied, None otherwise
        """
        match len(rule.antecedents):
            case 1:
                antecedent = rule.antecedents[0]
                # Find all variables in the antecedent (any character not in the alphabet)
                variables = {c for c in antecedent if c not in self.alphabet}

                # For each possible position in the word
                for i in range(len(word) + 1):
                    # Try to match the pattern
                    var_values = {}  # Map of variable names to their matched values
                    match_pos = 0
                    word_pos = i

                    # Try to match the pattern
                    while match_pos < len(antecedent):
                        if antecedent[match_pos] in variables:
                            # Find the next constant or end of pattern
                            next_const_pos = match_pos + 1
                            while next_const_pos < len(antecedent) and antecedent[next_const_pos] in variables:
                                next_const_pos += 1

                            if next_const_pos == len(antecedent):
                                # Variable at end of pattern
                                var_values[antecedent[match_pos]] = word[word_pos:]
                                match_pos = next_const_pos
                                word_pos = len(word)
                            else:
                                # Find the next occurrence of the constant
                                const = antecedent[next_const_pos]
                                next_word_pos = word.find(const, word_pos)
                                if next_word_pos == -1:
                                    break  # No match
                                var_values[antecedent[match_pos]] = word[word_pos:next_word_pos]
                                word_pos = next_word_pos
                                match_pos = next_const_pos
                        else:
                            # Match constant
                            if word_pos >= len(word) or word[word_pos] != antecedent[match_pos]:
                                break  # No match
                            word_pos += 1
                            match_pos += 1

                    # If we matched the entire pattern
                    if match_pos == len(antecedent) and word_pos == len(word):
                        # Substitute variables in the consequent
                        result = rule.consequent
                        for var, value in var_values.items():
                            result = result.replace(var, value)
                        return result

            case _:
                raise NotImplementedError("Multiple antecedents not yet supported")
        return None

    def generate_words(self, max_steps: int = 10) -> set[str]:
        """Generate words by applying production rules to initial words.

        Args:
            max_steps: Maximum number of derivation steps to perform

        Returns:
            Set of all words that can be generated within max_steps
        """
        current_words = set(self.initial_words)
        all_words = set(current_words)

        for _ in range(max_steps):
            new_words = set()
            for word in current_words:
                for rule in self.rules:
                    if result := self.apply_rule(word, rule):
                        new_words.add(result)

            if not new_words or new_words.issubset(all_words):
                break

            current_words = new_words
            all_words.update(new_words)

        return all_words


def create_mu_puzzle() -> PostCanonicalSystem:
    """Create the MU puzzle as a Post Canonical System."""
    from .alphabet import MU_PUZZLE

    # Initial word
    initial_words = {"MI"}

    # Production rules
    rules = {
        ProductionRule(["xI"], "xIU"),  # Rule 1: Add U to end if string ends in I
        ProductionRule(["Mx"], "Mxx"),  # Rule 2: Double everything after M
        ProductionRule(["xIIIy"], "xUy"),  # Rule 3: Replace III with U
        ProductionRule(["xUUy"], "xy"),  # Rule 4: Remove UU
    }

    return PostCanonicalSystem(MU_PUZZLE, initial_words, rules)
