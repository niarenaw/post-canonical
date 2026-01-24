# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **Execution modes**: `ExecutionConfig` with `BFS` and `DFS` execution strategies.
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
