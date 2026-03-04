# Post Canonical Systems

A Python implementation of Emil Post's formal string rewriting systems for computation and formal language exploration.

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

## What is this?

Post Canonical Systems are a foundational model of computation developed by mathematician Emil Post in the 1920s. They define formal languages through string rewriting: starting from initial words (axioms) and repeatedly applying production rules to generate new strings. Despite their simplicity, Post systems are Turing-complete and serve as an elegant framework for exploring computability, formal grammars, and proof derivations.

## Features

| Feature | Description |
|---------|-------------|
| Pattern Matching | Variable kinds: `ANY` (empty or more), `NON_EMPTY` (1+), `SINGLE` (exactly 1) |
| Multi-Antecedent Rules | Combine multiple words in a single production |
| Derivation Tracking | Full proof traces showing how each word was derived |
| Visualization Exports | DOT/GraphViz, LaTeX, Mermaid diagrams, ASCII trees |
| Interactive CLI | REPL interface via the `pcs` command |
| JSON Serialization | Save and load system definitions |
| SystemBuilder DSL | Ergonomic fluent API for system construction |
| Preset Systems | MU Puzzle, Binary Doubler, Palindrome Generator |

## Installation

```bash
pip install post-canonical
```

Or with uv:

```bash
uv add post-canonical
```

## Quick Start

```python
from post_canonical.builder import SystemBuilder

# Build the MU puzzle from Godel, Escher, Bach
system = (SystemBuilder("MIU")
    .var("x")
    .var("y")
    .axiom("MI")
    .rule("$xI -> $xIU", name="add_U")
    .rule("M$x -> M$x$x", name="double")
    .rule("$x III $y -> $x U $y", name="III_to_U")
    .rule("$x UU $y -> $x$y", name="delete_UU")
    .build())

# Generate all derivable words up to 3 steps
words = system.generate_words(max_steps=3)
print(sorted(words, key=lambda w: (len(w), w)))
# ['MI', 'MII', 'MIU', 'MIII', 'MIIU', 'MIIII', 'MIIIU', 'MIUIU']

# Check if a word is reachable
from post_canonical.query import ReachabilityQuery

query = ReachabilityQuery(system)
print(query.is_derivable("MU", max_words=10000))
# 'MU' NOT_FOUND after exploring 10000 words
```

Variables use `$` prefix in patterns (`$x`, `${x}`). Whitespace is ignored, so `$x III $y` reads cleanly. Three variable kinds are available:

```python
builder = (SystemBuilder("abc")
    .var("x")                      # ANY: matches "" or "a" or "abc"...
    .var("y", kind="non_empty")    # NON_EMPTY: matches "a" or "abc"...
    .var("z", kind="single")       # SINGLE: matches exactly one symbol
)
```

## CLI

The package includes an interactive REPL for exploring systems without writing code:

```
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

pcs> rule "M$x -> M$x$x"
Rule added: M$x -> M$x$x

pcs> generate 3
Generated 8 words:
  MI, MII, MIU, MIII, MIIU, MIIII, MIIIU, MIUIU

pcs> query "MU"
'MU' NOT_FOUND after exploring 10000 words

pcs> exit
Goodbye.
```

## Visualization

Export derivations as DOT/GraphViz, LaTeX, Mermaid, or ASCII trees:

```python
from post_canonical import create_mu_puzzle
from post_canonical.visualization import to_ascii_tree

system = create_mu_puzzle()
for dw in system.generate(max_steps=3):
    if dw.word == "MIIII":
        print(to_ascii_tree(dw.derivation))
        break
```

```
MIIII
+-- MII (double)
    +-- MI (axiom)
```

## Preset Systems

| System | Import | Description |
|--------|--------|-------------|
| MU Puzzle | `create_mu_puzzle()` | Hofstadter's famous puzzle from GEB |
| Binary Doubler | `create_binary_doubler()` | Doubles binary strings: 1 -> 11 -> 1111 |
| Palindrome Generator | `create_palindrome_generator()` | Generates all binary palindromes |

## Requirements

- Python 3.12+
- No external dependencies

## License

MIT
