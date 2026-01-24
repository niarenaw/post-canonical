# Architecture

## Overview

A Post Canonical System (PCS) is a formal system for string manipulation, developed by Emil Post in the 1920s. It consists of an alphabet of symbols, a set of axioms (initial words), and production rules that transform words into new words. This library provides a complete implementation with pattern matching, derivation tracking, and reachability queries.

## Conceptual Model

A Post Canonical System generates words through iterative rule application:

```
                           +-----------------+
                           |     Axioms      |
                           | (Initial Words) |
                           +--------+--------+
                                    |
                                    v
                    +---------------+---------------+
                    |                               |
                    v                               v
            +-------+-------+               +-------+-------+
            | Production    |               | Production    |
            | Rule 1        |               | Rule 2        |
            +-------+-------+               +-------+-------+
                    |                               |
                    v                               v
            +-------+-------+               +-------+-------+
            | Derived       |               | Derived       |
            | Word          |               | Word          |
            +---------------+               +---------------+
                    |                               |
                    +---------------+---------------+
                                    |
                                    v
                            +-------+-------+
                            | Continue      |
                            | Applying      |
                            | Rules...      |
                            +---------------+
```

### Core Concepts

| Component | Description |
|-----------|-------------|
| **Alphabet** | The set of valid symbols (e.g., `{M, I, U}`) |
| **Variable** | A placeholder that matches substrings (e.g., `$x` matches any string) |
| **Pattern** | A sequence of constants and variables (e.g., `M${x}I`) |
| **Production Rule** | Transforms words matching antecedent patterns into new words |
| **Axiom** | Starting words from which all derivations begin |
| **Derivation** | A proof trace showing how a word was derived |

### How Words Are Generated

1. Begin with axioms as the initial set of known words
2. For each known word, attempt to match all production rules
3. When a rule's antecedent pattern matches, substitute the binding into the consequent
4. Add newly derived words to the known set
5. Repeat until no new words are generated (or a limit is reached)

## Module Organization

```
src/post_canonical/
    |
    +-- core/           Fundamental immutable data types
    |   +-- alphabet.py     Symbol set definition
    |   +-- variable.py     Variable declarations (ANY, NON_EMPTY, SINGLE)
    |   +-- pattern.py      Patterns for matching and substitution
    |   +-- rule.py         Production rules (antecedents -> consequent)
    |
    +-- matching/       Pattern matching engine
    |   +-- binding.py      Immutable variable-to-value mappings
    |   +-- matcher.py      Core backtracking pattern matcher
    |   +-- unifier.py      Multi-pattern unification for multi-antecedent rules
    |
    +-- system/         Main PCS implementation
    |   +-- pcs.py          PostCanonicalSystem class
    |   +-- executor.py     Rule execution engine
    |   +-- derivation.py   Derivation tracking and proof traces
    |
    +-- query/          Analysis and search queries
    |   +-- reachability.py Derivability checking via BFS exploration
    |
    +-- presets/        Ready-to-use example systems
    |   +-- alphabets.py    Common alphabets (BINARY, MIU, etc.)
    |   +-- examples.py     Classic systems (MU puzzle, palindromes)
    |
    +-- serialization/  Persistence
        +-- json_codec.py   JSON encode/decode for systems
```

## Key Algorithms

### Pattern Matching (Backtracking)

The pattern matcher uses recursive backtracking to find all ways a pattern can match a word.

```
match(pattern, word, position, bindings):
    if no more pattern elements:
        return SUCCESS if position == end of word

    if current element is CONSTANT:
        if word[position:] starts with constant:
            return match(rest of pattern, word, position + len(constant), bindings)
        else:
            return FAIL

    if current element is VARIABLE:
        if variable already bound:
            if word[position:] starts with bound value:
                return match(rest of pattern, word, position + len(value), bindings)
            else:
                return FAIL
        else:
            for each possible length (respecting variable kind):
                value = word[position : position + length]
                if match(rest of pattern, word, position + length, bindings + {var: value}):
                    yield that binding  # BACKTRACK POINT
```

Variable kinds constrain what can be matched:

| Kind | Matches |
|------|---------|
| `ANY` | Any string, including empty |
| `NON_EMPTY` | At least one character |
| `SINGLE` | Exactly one character |

### Rule Execution

Rules are applied in priority order (higher priority first, then alphabetical by name).

```
+------------------+     +------------------+     +------------------+
|   Input Word     | --> |  Match Against   | --> |   Substitute     |
|   "MIII"         |     |  Antecedent      |     |   Into Consequent|
+------------------+     |  "${x}III${y}"   |     |   "${x}U${y}"    |
                         +------------------+     +------------------+
                                |                         |
                                v                         v
                         +------------------+     +------------------+
                         |   Binding:       |     |   Output Word    |
                         |   x="M", y=""    |     |   "MU"           |
                         +------------------+     +------------------+
```

**Execution modes:**
- **DETERMINISTIC**: First successful match only
- **NON_DETERMINISTIC**: All possible matches (for exhaustive exploration)

### Derivation Tracking

Every derived word carries its complete proof trace:

```
DerivedWord {
    word: "MIUIU"
    derivation: [
        Step 1: "MI" --[add_U]--> "MIU"
        Step 2: "MIU" --[double]--> "MIUIU"
    ]
}
```

### Reachability Search (Breadth-First)

The reachability query uses BFS to find whether a target word is derivable:

```
+----------+     +----------+     +----------+     +----------+
| Axioms   | --> | Level 1  | --> | Level 2  | --> | Level 3  |
| {MI}     |     | {MIU,    |     | {MIUIU,  |     | ...      |
|          |     |  MII}    |     |  MIIU,   |     |          |
|          |     |          |     |  ...}    |     |          |
+----------+     +----------+     +----------+     +----------+
     ^                                                   |
     |                                                   |
     +------------ Continue until target found ----------+
                   or max_words reached
```

## Design Decisions

### Why Frozen Dataclasses (Immutability)

All core types use `@dataclass(frozen=True, slots=True)`:

1. **Thread safety**: Immutable objects can be safely shared across threads
2. **Hashability**: Frozen dataclasses are hashable, enabling use in sets and as dict keys
3. **Predictability**: No unexpected mutations; derivations form clean, traceable chains
4. **Memory efficiency**: `slots=True` reduces memory overhead

### Why Breadth-First Generation

The `generate()` method explores words breadth-first (by derivation depth):

1. **Shortest proofs first**: Finds minimal derivations before longer ones
2. **Fair exploration**: Doesn't get stuck exploring one infinite branch
3. **Termination guarantees**: Combined with step limits, ensures exploration completes

```
BFS Exploration Order:

    Axiom (depth 0)
        |
    +---+---+
    |       |
   d=1     d=1      <- Process all depth-1 words before depth-2
    |       |
  +-+-+   +-+-+
  |   |   |   |
 d=2 d=2 d=2 d=2    <- Process all depth-2 words before depth-3
```

### Why Generators for Lazy Evaluation

The `iterate()` method returns a generator, not a collection:

1. **Memory efficiency**: Don't materialize all words when only searching for one
2. **Early termination**: Stop iteration as soon as target is found
3. **Infinite systems**: Handle systems that generate unbounded word sets
4. **Streaming**: Process words as they're discovered

```python
# Memory-efficient search
for word in system.iterate():
    if is_interesting(word):
        break  # Stop early, no wasted computation
```

## Data Flow

The complete flow when generating words from a Post Canonical System:

```
+-------------------------------------------------------------------+
|                     PostCanonicalSystem                           |
|                                                                   |
|  alphabet   axioms     variables      rules                       |
|  {M,I,U}    {"MI"}     {$x, $y}       [Rule1, Rule2, ...]         |
+------+----------+----------+-------------+-----------+------------+
       |          |          |             |           |
       v          v          v             v           v
+-------------------------------------------------------------------+
|                        RuleExecutor                               |
|                                                                   |
|    +-----------+     +-----------------+     +----------------+   |
|    | Pattern   | <-- | Multi-Pattern   | <-- | Execution      |   |
|    | Matcher   |     | Unifier         |     | Config         |   |
|    +-----------+     +-----------------+     +----------------+   |
|          |                   |                                    |
|          v                   v                                    |
|    +-----------+     +-----------------+                          |
|    | Binding   |     | Derivation      |                          |
|    | {x="M"}   |     | Tracking        |                          |
|    +-----------+     +-----------------+                          |
+-------------------------------------------------------------------+
                               |
                               v
                    +--------------------+
                    | DerivedWord        |
                    |   word: "MIU"      |
                    |   derivation: [...] |
                    +--------------------+
```

## Example: MU Puzzle Flow

```
Input: PostCanonicalSystem with axiom "MI" and 4 rules

Step 1: Initialize
    frontier = {DerivedWord("MI", axiom)}

Step 2: Apply Rules to "MI"
    Rule "add_U":    "MI" matches "${x}I" with x="M"
                     -> substitute into "${x}IU" -> "MIU"
    Rule "double":   "MI" matches "M${x}" with x="I"
                     -> substitute into "M${x}${x}" -> "MII"

Step 3: Update frontier
    frontier = {DerivedWord("MIU", [MI -> MIU]),
                DerivedWord("MII", [MI -> MII])}

Step 4: Continue with new words...
    "MIU" + add_U   -> "MIUU"
    "MIU" + double  -> "MIUIU"
    "MII" + add_U   -> "MIIU"
    "MII" + double  -> "MIIII"
    ...

Result: Expanding tree of derivable words
```
