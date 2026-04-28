# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-04-28

A focused release that lands the recommendations from a deep code
review (`docs/CODE_REVIEW_2026-04-28.md`). Roughly half of the user-
facing surface gains direct test coverage; the matcher hot path is
~2x faster on representative workloads; and a small handful of public
API choices change in user-visible ways.

### Breaking

- `PostCanonicalSystem.generate(...)` and `generate_words(...)` now
  return `tuple[DerivedWord, ...]` and `tuple[str, ...]` respectively,
  ordered by `(len(word), word)`. The previous return type was a
  `frozenset` whose lack of ordering forced every caller to wrap
  results in `sorted(...)`. `iterate(...)` is unchanged.
- `ExecutionMode`, `QueryResult`, and `VariableKind` are now
  `StrEnum` subclasses with explicit string values (`"deterministic"`,
  `"non_deterministic"`, `"derivable"`, `"not_found"`, `"any"`,
  `"non_empty"`, `"single"`). Member `.name` access is unchanged, so
  the JSON wire format does not change; code that read `.value` and
  expected an opaque integer must be updated.
- `RuleExecutor` is no longer re-exported from
  `post_canonical.system`; it is an internal implementation detail.
  Reach through `PostCanonicalSystem` instead.

### Added

- Public exports: `SystemBuilder` and the four visualization
  exporters (`to_dot`, `to_latex`, `to_ascii_tree`, `to_mermaid`)
  now live at the top-level package, so the README's quick-start
  imports work without reaching into submodules.
- `core.errors.PatternError` for pattern parse failures, with the
  pattern text, position, and declared-variable context attached.
- `tests/test_visualization.py`, `tests/test_cli.py`,
  `tests/test_builder.py`, and `tests/test_properties.py` (the
  property suite uses `hypothesis`, added as a dev-only dependency).
- `CONTRIBUTING.md` documenting the dev workflow and the two-place
  version invariant in the release process.
- README "Pattern syntax" section with a formal BNF and a note that
  `Pattern.parse` accepts only the canonical `${name}` form while
  the builder accepts both `$x` and `${x}`.

### Changed

- Matcher: replaced per-attempt `Binding` allocations with a mutable
  scratch dict (save/restore on backtrack), swapped slice-equality
  for `str.startswith(elem, pos)`, and added a length-feasibility
  prune before the variable-length loop. Combined with dropping the
  per-BFS-level `frozenset` rebuild and materializing
  `ProductionRule.sort_key` as a regular field, this is roughly 2x
  faster on the MU puzzle and palindrome benchmarks.
- Multi-antecedent unifier now pre-filters word slots by length and
  walks antecedents in descending order of `min_match_length` so the
  most-constrained slot fails fast.
- Validation errors in `PostCanonicalSystem.__post_init__` and
  `Pattern.parse` use `ValidationError` / `PatternError` with
  structured context (rule name, declared variables, alphabet,
  offending characters) instead of one-line `ValueError` messages.
- JSON codec version-mismatch error now lists the supported version
  and the upgrade path.
- `cli.py` REPL: replaced manual chunk loop with `itertools.batched`,
  removed an unnecessary `# type: ignore`, and added a concrete
  example to the "no axioms defined" hint.
- `visualization.py` is now a `visualization/` subpackage with one
  file per output format (dot, latex, ascii_tree, mermaid).
- `presets/{__init__,alphabets,examples}.py` collapses to a single
  `presets.py` module.
- `PostCanonicalSystem` and `ExecutionConfig` now both have
  `slots=True` and (for `ExecutionConfig`) `frozen=True`, matching
  every other core dataclass.

### Fixed

- Removed false claim from the CHANGELOG that v2.0 introduced "BFS
  and DFS execution strategies" (only `DETERMINISTIC` /
  `NON_DETERMINISTIC` modes exist; search order has always been
  BFS only).
- README MU-puzzle example output was wrong (claimed 8 words
  including `MIII`/`MIIIU`); re-pinned to the actual 11-word output.
- README REPL transcript no longer hard-codes the version `v2.0.0`.
- Backfilled missing CHANGELOG entries for v2.1 and v2.2.

### Deferred

- The five-class `object.__setattr__` -> classmethod factory refactor
  (P2-7 in the review). The `__setattr__` pattern is idiomatic for
  frozen dataclasses with input normalization, and the alternative
  would either churn ~400 construction call sites or introduce a
  parallel `.of()` channel that doesn't actually remove the smell.

## [2.2.0] - 2026-03-04

### Changed

- Performance pass on the matcher and rule executor: precomputed suffix-min
  pruning during backtracking, reduced allocations on repeated rule
  application, and trimmed duplicate work in BFS expansion.

### Fixed

- Several small correctness bugs in pattern matching and serialization paths
  surfaced by extended test coverage.

### Documentation

- Trimmed and tightened README. (See PR #3.)

## [2.1.0] - 2026-03-04

### Added

- Interactive REPL (`pcs` command) for exploring systems without writing Python.
- `SystemBuilder` fluent DSL for ergonomic construction with `$name` /
  `${name}` variable syntax.
- Visualization exporters: GraphViz DOT, LaTeX, Mermaid, and ASCII tree.
- Expanded test suite covering builder, REPL, and visualization paths.
- Documentation pass: README quick-start, examples, and architecture diagrams.

### Fixed

- Lint errors after the v2.0 rewrite (import sorting, unused imports,
  per-file `PLR2004` allowances for tests and `example.py`).

(See PR #2.)

## [2.0.0] - 2025-01-24

Complete rewrite of the Post Canonical Systems library with a modern, ergonomic API.

### Added

- **SystemBuilder**: Fluent DSL for constructing systems without manual object creation.
  Supports `$name` and `${name}` variable syntax with method chaining.
- **Interactive CLI (REPL)**: New `pcs` command provides an interactive shell for
  building and exploring systems without writing Python code.
- **Visualization exports**: Export derivation proofs in multiple formats:
  - GraphViz DOT for directed graphs
  - LaTeX with `align*` environment and `\xrightarrow` annotations
  - Mermaid for Markdown-compatible diagrams
  - ASCII trees for terminal display
- **Derivation tracking**: Full provenance tracking with `Derivation`, `DerivationStep`,
  and `DerivedWord` types to trace how words are generated.
- **Reachability queries**: `ReachabilityQuery` class to check if target words are
  derivable from axioms, with configurable search limits.
- **Execution modes**: `ExecutionConfig.mode` controls per-rule match behavior:
  `DETERMINISTIC` (yield first match) or `NON_DETERMINISTIC` (yield all matches).
  Word generation is breadth-first by derivation depth.
- **Preset alphabets**: Built-in alphabets for common use cases (`BINARY`, `DECIMAL`,
  `HEXADECIMAL`, `ENGLISH_LOWERCASE`, `ENGLISH_UPPERCASE`, `ENGLISH_LETTERS`, `MIU`).
- **Example systems**: Ready-to-use systems including `create_mu_puzzle()`,
  `create_binary_doubler()`, and `create_palindrome_generator()`.
- **JSON serialization**: `PCSJsonCodec` for saving and loading system definitions.
- **Type annotations**: Full type hints throughout with PEP 561 `py.typed` marker.

### Changed

- **Pattern matching**: Redesigned pattern system with explicit `Pattern` and `Variable`
  types. Variables now have kinds (`ANY`, `NON_EMPTY`, `SINGLE`) for finer control.
- **Production rules**: Rules now support multiple antecedents for more expressive
  pattern matching. Rule syntax uses `->` separator.
- **API structure**: Modular package structure with clear separation between core types,
  system execution, queries, and serialization.

### Fixed

- Multi-antecedent rules now correctly match multiple input words and bind variables
  consistently across all antecedent patterns.
- Pattern matching handles edge cases with empty strings and single-character variables.
- Variable binding respects variable kind constraints during matching.

## [1.0.0] - 2024-01-01

Initial implementation of Post Canonical Systems.

### Added

- Basic `PostCanonicalSystem` class
- Simple production rules with single-character variables
- Word generation with step limits
