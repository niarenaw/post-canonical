"""Interactive REPL for exploring Post Canonical Systems.

Provides a command-line interface for building and exploring Post Canonical Systems
without writing Python code. Uses Python's cmd module for a readline-enabled REPL.

Example session:

    $ pcs
    Post Canonical Systems REPL v2.0.0
    Type 'help' for commands.

    pcs> alphabet MIU
    Alphabet set: {I, M, U}

    pcs> axiom MI
    Axiom added: MI

    pcs> var x
    Variable added: x (ANY)

    pcs> rule "$xI -> $xIU"
    Rule added: $xI -> $xIU

    pcs> generate 3
    Generated 4 words:
      MI, MIU, MIIU, MIIIU

    pcs> exit
"""

from __future__ import annotations

import cmd
import shlex
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from . import __version__
from .builder import BuilderError, SystemBuilder
from .core.alphabet import Alphabet
from .core.variable import VariableKind
from .query import ReachabilityQuery
from .serialization.json_codec import PCSJsonCodec

if TYPE_CHECKING:
    from .system.pcs import PostCanonicalSystem


class PCSRepl(cmd.Cmd):
    """Interactive REPL for Post Canonical Systems.

    Provides commands for building systems incrementally, generating words,
    checking reachability, and saving/loading system definitions.
    """

    intro = f"Post Canonical Systems REPL v{__version__}\nType 'help' for commands.\n"
    prompt = "pcs> "

    def __init__(self) -> None:
        super().__init__()
        self._alphabet: Alphabet | None = None
        self._variables: dict[str, VariableKind] = {}
        self._axioms: set[str] = set()
        self._rules: list[str] = []
        self._system: PostCanonicalSystem | None = None
        self._codec = PCSJsonCodec()

    def _invalidate_system(self) -> None:
        """Mark the cached system as stale after a configuration change."""
        self._system = None

    def _build_system(self) -> PostCanonicalSystem | None:
        """Build a system from current configuration, caching the result."""
        if self._system is not None:
            return self._system

        error = self._validate_configuration()
        if error:
            self._print_error(error)
            return None

        try:
            builder = SystemBuilder(self._alphabet)  # type: ignore[arg-type]
            for name, kind in self._variables.items():
                builder.var(name, kind.name.lower())
            for axiom in self._axioms:
                builder.axiom(axiom)
            for rule in self._rules:
                builder.rule(rule)

            self._system = builder.build()
            return self._system
        except BuilderError as e:
            self._print_error(f"Build error: {e}")
            return None
        except ValueError as e:
            self._print_error(f"Validation error: {e}")
            return None

    def _validate_configuration(self) -> str | None:
        """Check if current configuration is complete. Returns error message or None."""
        if self._alphabet is None:
            return "No alphabet set. Use 'alphabet <symbols>' first."
        if not self._axioms:
            return "No axioms defined. Use 'axiom <word>' first."
        if not self._rules:
            return "No rules defined. Use 'rule \"<pattern>\"' first."
        return None

    def _print_error(self, message: str) -> None:
        """Print an error message with consistent formatting."""
        print(f"Error: {message}")

    def _print_success(self, message: str) -> None:
        """Print a success message with consistent formatting."""
        print(message)

    def _parse_args(self, arg: str) -> list[str]:
        """Parse command arguments using shell-style quoting."""
        try:
            return shlex.split(arg)
        except ValueError as e:
            self._print_error(f"Invalid syntax: {e}")
            return []

    # --- Commands ---

    def do_help(self, arg: str) -> None:
        """Show available commands or help for a specific command."""
        if arg:
            super().do_help(arg)
        else:
            print("""
Available Commands:
  alphabet <symbols>          Set alphabet (e.g., 'alphabet MIU')
  var <name> [kind]           Add variable (kind: any, non_empty, single)
  axiom <word>                Add axiom
  rule "<pattern>"            Add rule (e.g., rule "$xI -> $xIU")
  show                        Display current system configuration
  generate <steps>            Generate words up to N derivation steps
  query "<word>"              Check if word is reachable
  trace "<word>"              Show derivation for word
  load <file>                 Load system from JSON file
  save <file>                 Save current system to JSON file
  clear                       Reset system configuration
  exit                        Quit the REPL

Variable Kinds:
  any       - Matches any string including empty (default)
  non_empty - Matches at least one symbol
  single    - Matches exactly one symbol

Rule Syntax:
  Variables are prefixed with $ (e.g., $x, $y)
  Use -> to separate antecedent from consequent
  Example: "$xI -> $xIU" (append U after any string ending in I)
""")

    def do_alphabet(self, arg: str) -> None:
        """Set the alphabet for the system.

        Usage: alphabet <symbols>

        Example:
            pcs> alphabet MIU
            Alphabet set: {I, M, U}
        """
        arg = arg.strip()
        if not arg:
            self._print_error("Usage: alphabet <symbols>")
            return

        try:
            self._alphabet = Alphabet(arg)
            self._invalidate_system()
            symbols = ", ".join(sorted(self._alphabet.symbols))
            self._print_success(f"Alphabet set: {{{symbols}}}")
        except ValueError as e:
            self._print_error(str(e))

    def do_var(self, arg: str) -> None:
        """Add a variable for use in patterns.

        Usage: var <name> [kind]

        Kinds:
            any       - Matches any string including empty (default)
            non_empty - Matches at least one symbol
            single    - Matches exactly one symbol

        Examples:
            pcs> var x
            Variable added: x (ANY)

            pcs> var y non_empty
            Variable added: y (NON_EMPTY)
        """
        args = self._parse_args(arg)
        if not args:
            self._print_error("Usage: var <name> [kind]")
            return

        name = args[0]
        kind_str = args[1] if len(args) > 1 else "any"

        kind_map = {
            "any": VariableKind.ANY,
            "non_empty": VariableKind.NON_EMPTY,
            "nonempty": VariableKind.NON_EMPTY,
            "single": VariableKind.SINGLE,
        }

        kind_str_lower = kind_str.lower()
        if kind_str_lower not in kind_map:
            valid = ", ".join(sorted(set(kind_map.keys()) - {"nonempty"}))
            self._print_error(f"Unknown kind '{kind_str}'. Valid kinds: {valid}")
            return

        if name in self._variables:
            self._print_error(f"Variable '{name}' already defined.")
            return

        kind = kind_map[kind_str_lower]
        self._variables[name] = kind
        self._invalidate_system()
        self._print_success(f"Variable added: {name} ({kind.name})")

    def do_axiom(self, arg: str) -> None:
        """Add an axiom (starting word) to the system.

        Usage: axiom <word>

        Example:
            pcs> axiom MI
            Axiom added: MI
        """
        word = arg.strip()
        if not word:
            self._print_error("Usage: axiom <word>")
            return

        if self._alphabet is None:
            self._print_error("Set alphabet first with 'alphabet <symbols>'.")
            return

        invalid = self._alphabet.validate_word(word)
        if invalid:
            symbols = ", ".join(sorted(invalid))
            self._print_error(f"Invalid symbols for alphabet: {symbols}")
            return

        if word in self._axioms:
            self._print_error(f"Axiom '{word}' already exists.")
            return

        self._axioms.add(word)
        self._invalidate_system()
        self._print_success(f"Axiom added: {word}")

    def do_rule(self, arg: str) -> None:
        """Add a production rule to the system.

        Usage: rule "<pattern>"

        Pattern format: antecedent -> consequent
        Variables are prefixed with $ (e.g., $x, $y)

        Examples:
            pcs> rule "$xI -> $xIU"
            Rule added: $xI -> $xIU

            pcs> rule "M$x -> M$x$x"
            Rule added: M$x -> M$x$x
        """
        args = self._parse_args(arg)
        if not args:
            self._print_error('Usage: rule "<pattern>"')
            return

        pattern = args[0]
        if "->" not in pattern:
            self._print_error("Rule must contain '->' to separate antecedent and consequent.")
            return

        self._rules.append(pattern)
        self._invalidate_system()

        parts = pattern.split("->", 1)
        display = f"{parts[0].strip()} -> {parts[1].strip()}"
        self._print_success(f"Rule added: {display}")

    def do_show(self, arg: str) -> None:
        """Display current system configuration.

        Usage: show

        Shows alphabet, variables, axioms, and rules configured so far.
        """
        print()
        print("Current Configuration")
        print("=" * 40)

        if self._alphabet:
            symbols = ", ".join(sorted(self._alphabet.symbols))
            print(f"Alphabet:  {{{symbols}}}")
        else:
            print("Alphabet:  (not set)")

        if self._variables:
            var_strs = [f"{n} ({k.name})" for n, k in sorted(self._variables.items())]
            print(f"Variables: {', '.join(var_strs)}")
        else:
            print("Variables: (none)")

        if self._axioms:
            print(f"Axioms:    {', '.join(sorted(self._axioms))}")
        else:
            print("Axioms:    (none)")

        if self._rules:
            print("Rules:")
            for i, rule in enumerate(self._rules, 1):
                parts = rule.split("->", 1)
                display = f"{parts[0].strip()} -> {parts[1].strip()}"
                print(f"  {i}. {display}")
        else:
            print("Rules:     (none)")

        print()

    def do_generate(self, arg: str) -> None:
        """Generate all derivable words up to a given number of steps.

        Usage: generate <steps>

        Example:
            pcs> generate 3
            Generated 4 words:
              MI, MIU, MIIU, MIIIU
        """
        arg = arg.strip()
        if not arg:
            self._print_error("Usage: generate <steps>")
            return

        try:
            max_steps = int(arg)
        except ValueError:
            self._print_error("Steps must be a number.")
            return

        if max_steps < 0:
            self._print_error("Steps must be non-negative.")
            return

        system = self._build_system()
        if system is None:
            return

        try:
            words = system.generate_words(max_steps=max_steps)
            sorted_words = sorted(words, key=lambda w: (len(w), w))
            print(f"Generated {len(sorted_words)} words:")
            self._print_word_list(sorted_words)
        except Exception as e:
            self._print_error(f"Generation failed: {e}")

    def _print_word_list(self, words: list[str], indent: int = 2) -> None:
        """Print a list of words in a compact, aligned format."""
        if not words:
            print(" " * indent + "(none)")
            return

        prefix = " " * indent
        max_per_line = 8
        line_words: list[str] = []

        for word in words:
            line_words.append(word)
            if len(line_words) >= max_per_line:
                print(prefix + ", ".join(line_words))
                line_words = []

        if line_words:
            print(prefix + ", ".join(line_words))

    def do_query(self, arg: str) -> None:
        """Check if a word is reachable from the axioms.

        Usage: query "<word>"

        Example:
            pcs> query "MU"
            'MU' NOT_FOUND after exploring 10000 words

            pcs> query "MII"
            'MII' is DERIVABLE in 1 steps
        """
        args = self._parse_args(arg)
        if not args:
            self._print_error('Usage: query "<word>"')
            return

        target = args[0]
        system = self._build_system()
        if system is None:
            return

        query = ReachabilityQuery(system)
        result = query.is_derivable(target, max_words=10000)
        print(str(result))

    def do_trace(self, arg: str) -> None:
        """Show the derivation trace for a word.

        Usage: trace "<word>"

        If the word is reachable, shows the step-by-step derivation from axioms.

        Example:
            pcs> trace "MIU"
            Word: 'MIU'
            Derivation (1 steps):
              1. ('MI',) --[rule]--> MIU
                 bindings: {x: }
        """
        args = self._parse_args(arg)
        if not args:
            self._print_error('Usage: trace "<word>"')
            return

        target = args[0]
        system = self._build_system()
        if system is None:
            return

        query = ReachabilityQuery(system)
        result = query.is_derivable(target, max_words=10000)

        if not result.found:
            print(f"'{target}' is not reachable (explored {result.steps_explored} words)")
            return

        # Find the DerivedWord to get its trace.
        for dw in system.iterate():
            if dw.word == target:
                print(dw.trace())
                return

        # Fallback if axiom (iterate might skip axioms in trace).
        if target in system.axioms:
            print(f"Word: '{target}'")
            print("  (axiom)")

    def do_load(self, arg: str) -> None:
        """Load a system from a JSON file.

        Usage: load <file>

        Example:
            pcs> load examples/mu.json
            System loaded from examples/mu.json
        """
        args = self._parse_args(arg)
        if not args:
            self._print_error("Usage: load <file>")
            return

        filepath = Path(args[0])
        if not filepath.exists():
            self._print_error(f"File not found: {filepath}")
            return

        try:
            system = self._codec.load(str(filepath))
            self._load_from_system(system)
            self._system = system
            self._print_success(f"System loaded from {filepath}")
        except Exception as e:
            self._print_error(f"Failed to load: {e}")

    def _load_from_system(self, system: PostCanonicalSystem) -> None:
        """Populate REPL state from a loaded system."""
        self._alphabet = system.alphabet
        self._variables = {v.name: v.kind for v in system.variables}
        self._axioms = set(system.axioms)
        self._rules = [str(rule).lstrip(f"[{rule.name}] ") if rule.name else str(rule) for rule in system.rules]

    def do_save(self, arg: str) -> None:
        """Save the current system to a JSON file.

        Usage: save <file>

        Example:
            pcs> save my_system.json
            System saved to my_system.json
        """
        args = self._parse_args(arg)
        if not args:
            self._print_error("Usage: save <file>")
            return

        system = self._build_system()
        if system is None:
            return

        filepath = Path(args[0])
        try:
            self._codec.save(system, str(filepath))
            self._print_success(f"System saved to {filepath}")
        except Exception as e:
            self._print_error(f"Failed to save: {e}")

    def do_clear(self, arg: str) -> None:
        """Reset all system configuration.

        Usage: clear

        Clears alphabet, variables, axioms, and rules.
        """
        self._alphabet = None
        self._variables = {}
        self._axioms = set()
        self._rules = []
        self._system = None
        self._print_success("System cleared.")

    def do_exit(self, arg: str) -> bool:
        """Exit the REPL.

        Usage: exit
        """
        print("Goodbye.")
        return True

    def do_quit(self, arg: str) -> bool:
        """Exit the REPL (alias for exit).

        Usage: quit
        """
        return self.do_exit(arg)

    def do_EOF(self, arg: str) -> bool:  # noqa: N802
        """Handle Ctrl-D to exit."""
        print()  # Newline for cleaner output.
        return self.do_exit(arg)

    def emptyline(self) -> bool:
        """Do nothing on empty line (override default repeat behavior)."""
        return False

    def default(self, line: str) -> None:
        """Handle unknown commands."""
        cmd_name = line.split()[0] if line.split() else line
        self._print_error(f"Unknown command: '{cmd_name}'. Type 'help' for available commands.")


def main() -> None:
    """Entry point for the pcs command."""
    try:
        repl = PCSRepl()
        repl.cmdloop()
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
