# post-canonical

## Purpose

A pure-Python implementation of Emil Post's canonical string-rewriting systems: an alphabet, axiom strings, and production rules that derive new strings via pattern matching. Turing-complete in theory; an educational toolkit in practice. Personal project, distributed on PyPI as `post-canonical`, console script `pcs`.

For a deep architectural walkthrough (algorithms, data flow, design rationale), read [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md). This file is just the navigational index.

---

## Layout

```
src/post_canonical/
  __init__.py           Public API surface and __version__
  builder.py            SystemBuilder fluent DSL (var / axiom / rule / build)
  cli.py                `pcs` REPL entry point
  visualization.py      DOT, LaTeX, Mermaid, ASCII-tree exporters
  core/                 Frozen dataclasses: Alphabet, Variable, Pattern, ProductionRule, errors
  matching/             Backtracking matcher, Binding, multi-antecedent unifier
  system/               PostCanonicalSystem, executor (BFS, deterministic/non-deterministic), Derivation traces
  query/                ReachabilityQuery (BFS-based derivability checks)
  presets/              Built-in alphabets (BINARY, MIU, ...) and example systems (mu_puzzle, ...)
  serialization/        PCSJsonCodec for save/load
tests/                  pytest suite, fixtures in conftest.py
docs/ARCHITECTURE.md    Diagrams, algorithm pseudocode, design decisions
example.py              Top-level usage demo (lint-exempt for magic numbers)
```

---

## Quick Start

```bash
uv sync                     # install dev deps into .venv
uv run pytest               # run tests
uv run ruff check .         # lint
uv run ruff format .        # format
uv run mypy src             # strict type-check
uv run pcs                  # launch the REPL
uv run python example.py    # run the demo script
```

---

## Conventions

| Rule | Why it matters |
|------|----------------|
| All core types are `@dataclass(frozen=True, slots=True)` | Hashability, thread safety, predictable derivation chains. New core types must follow suit. |
| `mypy --strict` passes | Public APIs are fully typed; `py.typed` is shipped. Don't introduce `Any` without cause. |
| Zero runtime dependencies | Stdlib only. Dev tooling (ruff, mypy, pytest) is fine; runtime deps require strong justification. |
| Python 3.12+ features welcome | `type X = ...` aliases, PEP 695 generics, structural pattern matching are all in use. |
| BFS by default for generation | Shortest-proof-first; lazy via generators so infinite systems remain tractable. |
| Variable syntax in patterns is `${name}` | `Pattern.parse` requires the braced form. The `SystemBuilder` DSL also accepts bare `$name` as a convenience. |
| Tests live in `tests/`, fixtures in `tests/conftest.py` | Reuse existing fixtures (`mu_system`, `binary_alphabet`, `simple_vars`, etc.) before rolling new ones. |

### Lint config (`pyproject.toml`)

- Ruff selects `E,F,I,N,W,B,UP,PL,RUF`, line length 120, target py312
- `RUF022` is ignored so `__all__` can stay grouped semantically rather than alphabetically
- `tests/*` and `example.py` allow `PLR2004` (magic numbers) - don't extend that exemption elsewhere

### Versioning

The version string lives in **two places** that must move together:

- `pyproject.toml` -> `[project] version`
- `src/post_canonical/__init__.py` -> `__version__`

Bumping one without the other ships a mismatched package. CHANGELOG.md follows Keep a Changelog format.

---

## Where Things Live

| Looking for | Go to |
|-------------|-------|
| Public API surface | `src/post_canonical/__init__.py` (`__all__`) |
| How a word is derived | `system/executor.py` -> `system/derivation.py` |
| Pattern-matching algorithm | `matching/matcher.py` (single-pattern), `matching/unifier.py` (multi-antecedent) |
| Adding a new preset system | `presets/examples.py` |
| Adding a new export format | `visualization.py` |
| REPL command handling | `cli.py` |
| Architecture diagrams + rationale | `docs/ARCHITECTURE.md` |
