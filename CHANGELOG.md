# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
