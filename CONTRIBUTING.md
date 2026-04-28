# Contributing

Thanks for poking at `post-canonical`. This file documents the dev workflow and the release process.

## Setup

```bash
uv sync
```

`uv` resolves dev dependencies (`mypy`, `pytest`, `ruff`) into `.venv/`. The library itself has no runtime dependencies.

## Day-to-day commands

```bash
uv run pytest                # full test suite
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy src              # strict type-check
uv run pcs                   # launch the REPL
uv run python example.py     # run the demo script
```

CI (when present) runs all four of `pytest`, `ruff check`, `ruff format --check`, and `mypy src`. A PR should be green on all four before merge.

## Conventions

- Python 3.12+ only. `match` statements, PEP 695 `type` aliases, and `StrEnum` are all in use.
- Core types are `@dataclass(frozen=True, slots=True)` with classmethod factories for any non-trivial normalization.
- Public methods take `Sequence[T]` (or `Iterable[T]` for single-pass) on input; internal storage is `tuple` for immutable data and `list` for mutable scratch.
- `mypy --strict` must pass with no `# type: ignore` unless there is an inline justification.
- Comments should explain why, not what. No em dashes anywhere; use ` - ` instead.

## Release process

The version string lives in **two places** that must move together:

1. `pyproject.toml` -> `[project] version`
2. `src/post_canonical/__init__.py` -> `__version__`

Forgetting to bump one of them ships a mismatched package. The release flow is:

```bash
# 1. Bump both versions to X.Y.Z.
# 2. Update CHANGELOG.md with a new "## [X.Y.Z] - YYYY-MM-DD" section
#    grouped by Added / Changed / Fixed / Breaking. Keep entries concise
#    and link to PR numbers when relevant.

uv run pytest && uv run ruff check . && uv run mypy src
uv build                                    # wheel + sdist
git commit -am "Release X.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin main --tags
# 3. Publish (uv publish or twine upload, depending on environment).
```

For breaking releases, document the breakage explicitly under a **Breaking** subsection in the changelog; users reading the diff should understand at a glance what to update.

## Filing issues / PRs

- Bug reports: include a minimal `SystemBuilder` snippet that reproduces the issue and the actual vs. expected output.
- Feature ideas: see `docs/RESEARCH_EXTENSIONS_*.md` for the current backlog of known-interesting extensions; if your idea is already there, link to it.
- Code reviews of your own PR are welcome; the latest is captured in `docs/CODE_REVIEW_*.md` and is intentionally specific.
