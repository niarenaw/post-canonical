# Code Review - post-canonical v2.2.0

_Date: 2026-04-28_

## Executive Summary

- **One real correctness-of-claims bug:** the `CHANGELOG.md` advertises "BFS and DFS execution strategies" that do not exist in code. `ExecutionMode` only has `DETERMINISTIC` / `NON_DETERMINISTIC`. This is the only P0.
- **Hot-path waste in the matcher is the biggest engineering win.** The backtracking loop slices the input string and reallocates immutable `Binding` objects per attempt. A save / restore mutable scratch binding plus `str.startswith(elem, pos)` should yield 30 - 50% on typical workloads with negligible API surface change.
- **The public API silently hides documented features.** `SystemBuilder` and `to_ascii_tree` are referenced by the README but not in the top-level `__all__`. Quick-start users hit a wall.
- **Two frozen-dataclass invariants are violated:** `PostCanonicalSystem` is frozen but missing `slots=True`; `ExecutionConfig` is plain mutable. Both are one-line fixes.
- **Three sibling modules (visualization, REPL, builder) have zero direct tests.** That is roughly half the surface area. Property-based tests on the matcher round-trip would catch a class of regressions that no current test would.

## Findings by Severity

---

### P0 - Correctness or contract bugs

#### [P0-1] CHANGELOG advertises a `DFS` execution strategy that does not exist
- **File:** `CHANGELOG.md:27`
- **Category:** Docs
- **Problem:** The v2.0.0 entry claims `ExecutionConfig` has "`BFS` and `DFS` execution strategies." `ExecutionMode` in `src/post_canonical/system/executor.py:15-19` only defines `DETERMINISTIC` and `NON_DETERMINISTIC`. There is no DFS code path anywhere in the executor; `pcs.generate` and `pcs.iterate` are both BFS-only. Anyone reading the changelog and reaching for `ExecutionMode.DFS` gets an `AttributeError`. (The same myth was unintentionally propagated into the just-written `CLAUDE.md`; see [P1-7].)
- **Recommendation:** Rewrite the bullet to describe what actually exists:
  ```markdown
  - **Execution modes**: `ExecutionConfig.mode` selects per-rule match behavior:
    `DETERMINISTIC` (yield first match) or `NON_DETERMINISTIC` (yield all matches).
    Search order is breadth-first by derivation depth.
  ```
- **Effort:** S

---

### P1 - Significant performance, ergonomic, or maintainability wins

#### [P1-1] `Binding.extend` reallocates a `dict` per backtrack attempt
- **File:** `src/post_canonical/matching/matcher.py:145-149`, `src/post_canonical/matching/binding.py:70-80`
- **Category:** Performance
- **Problem:** Inside the matcher's variable-length loop, every candidate length calls `binding.extend(name, value)`, which does `dict(self._data)` and re-sorts to construct a new immutable `Binding`. With N consecutive variables and average M attempted lengths each, the matcher allocates O(N * M) bindings per word, plus one dict copy per allocation. For non-trivial backtracking depths this dominates wall-clock time.
- **Recommendation:** Introduce a mutable scratch binding (a plain `dict[str, str]`) inside the matcher, paired with a save / restore stack: push on assign, pop on backtrack, only freeze into an immutable `Binding` at the yield boundary. The public `Binding` API stays unchanged. Sketch:
  ```python
  def _match_elements(self, elements, suffix_min, elem_idx, word, pos, scratch):
      ...
      if elem.name in scratch:
          # already-bound consistency check ...
      else:
          for length in range(min_len, max_len + 1):
              value = word[pos : pos + length]
              scratch[elem.name] = value
              yield from self._match_elements(elements, suffix_min, next_idx, word, pos + length, scratch)
              del scratch[elem.name]
  ```
  At the top-level `match()` entry, freeze `scratch` into a `Binding` only when `elem_idx >= len(elements)`.
- **Effort:** M

#### [P1-2] String slicing in the matcher's tightest loop
- **File:** `src/post_canonical/matching/matcher.py:129, 136, 146`
- **Category:** Performance
- **Problem:** Constant matches do `word[pos:end_pos] == elem`, bound-variable consistency checks do `word[pos:end_pos] == bound_value`, and unbound variables slice once per attempted length. Each slice allocates a new string. `word.startswith(elem, pos)` performs the same comparison without allocating. The variable-length slice is needed (the value is yielded), but the equality slices are pure overhead.
- **Recommendation:**
  ```python
  # Constant arm
  if word.startswith(elem, pos):
      yield from self._match_elements(elements, suffix_min, next_idx, word, pos + len(elem), binding)

  # Bound-variable arm
  if word.startswith(bound_value, pos):
      yield from self._match_elements(elements, suffix_min, next_idx, word, pos + len(bound_value), binding)
  ```
  Leave line 146 alone (the value is genuinely needed).
- **Effort:** S

#### [P1-3] `SystemBuilder` and `to_ascii_tree` are not in the public API
- **File:** `src/post_canonical/__init__.py:73-105`
- **Category:** API
- **Problem:** `SystemBuilder` is the primary construction path shown in `README.md:39-51`, and `to_ascii_tree` is shown in `README.md:117`. Neither is imported in `__init__.py` or listed in `__all__`. `from post_canonical import SystemBuilder` raises `ImportError`. Users have to discover the underscore-free internal module path.
- **Recommendation:** Add to `__init__.py`:
  ```python
  from .builder import SystemBuilder
  from .visualization import to_ascii_tree, to_dot, to_latex, to_mermaid
  ```
  and extend `__all__` accordingly. While there, decide on visibility for `RuleExecutor`: it is in `system/__init__.py`'s `__all__` but not the package-level one. Either expose it intentionally or drop it from the sub-package list.
- **Effort:** S

#### [P1-4] `PostCanonicalSystem` is frozen but missing `slots=True`
- **File:** `src/post_canonical/system/pcs.py:13`
- **Category:** Anti-pattern
- **Problem:** Every other core frozen dataclass uses `@dataclass(frozen=True, slots=True)`. The library-level invariant (per `CLAUDE.md`) is that all core types do. `PostCanonicalSystem` only has `frozen=True`, so it carries a `__dict__` and trips the consistency promise. No functional bug, but it is the largest and most allocated value type in the library.
- **Recommendation:** `@dataclass(frozen=True, slots=True)`. Verify mypy and tests still pass (slots interacts with subclassing, but this class is not subclassed).
- **Effort:** S

#### [P1-5] `ExecutionConfig` is mutable and unhashable by default
- **File:** `src/post_canonical/system/executor.py:22-27`
- **Category:** Anti-pattern
- **Problem:** `ExecutionConfig` is a plain `@dataclass`, so callers can mutate `config.max_results` mid-execution and the executor will behave inconsistently. It is also passed through public APIs as if it were a value object.
- **Recommendation:** `@dataclass(frozen=True, slots=True)`. No call sites mutate it currently, so this is mechanical.
- **Effort:** S

#### [P1-6] `Enum` members use `auto()` where string values would aid debugging and serialization
- **File:** `src/post_canonical/system/executor.py:15-19`, `src/post_canonical/query/reachability.py` (`QueryResult`), `src/post_canonical/core/variable.py` (`VariableKind`)
- **Category:** Anti-pattern
- **Problem:** `auto()` produces opaque integer values. `QueryResult.NOT_FOUND.value` is `2`, not `"not_found"`. JSON serialization downstream has to special-case the enum. Repr in error messages and the REPL is uglier than it needs to be.
- **Recommendation:** Use string-valued enums uniformly:
  ```python
  class ExecutionMode(StrEnum):
      DETERMINISTIC = "deterministic"
      NON_DETERMINISTIC = "non_deterministic"
  ```
  `StrEnum` (3.11+) makes them naturally JSON-friendly. Audit `.name` vs `.value` call sites; most code uses `.name` which still works.
- **Effort:** M

#### [P1-7] `CLAUDE.md` propagates the same "BFS/DFS" myth as P0-1
- **File:** `CLAUDE.md:21` (the one in this repo, just authored)
- **Category:** Docs
- **Problem:** The freshly written `CLAUDE.md` describes `system/` as `executor (BFS/DFS, det/non-det)`. There is no DFS path; the second axis is the only execution-mode axis.
- **Recommendation:** Replace with `executor (BFS, deterministic/non-deterministic)`. Same edit conceptually as P0-1 but in a separate file.
- **Effort:** S

#### [P1-8] README REPL transcript shows the wrong version string
- **File:** `README.md:82`
- **Category:** Docs
- **Problem:** The transcript says `Post Canonical Systems REPL v2.0.0`. Current package version is 2.2.0. If the REPL prints the version dynamically (it should), the transcript will diverge again on every release.
- **Recommendation:** Either (a) drop the version line from the rendered example, or (b) hardcode the placeholder `vX.Y.Z` and add a doc-test that the actual REPL output uses `__version__`. Cheapest fix is (a).
- **Effort:** S

#### [P1-9] CHANGELOG has no entries for v2.1 or v2.2
- **File:** `CHANGELOG.md`
- **Category:** Docs
- **Problem:** Two minor releases since v2.0 are undocumented; current shipping version is 2.2.0. Recent commits (`b94066f Bump version to 2.2.0`, `3598776 Fix bugs, optimize hot paths, reduce duplication`) suggest at least bugfix and perf entries belong here.
- **Recommendation:** Reconstruct from `git log` between the v2.0 and v2.2 tag points and add `## [2.2.0]` and `## [2.1.0]` sections. Going forward, hook a release-prep step that fails CI if the top-of-changelog version does not match `__version__`.
- **Effort:** M

#### [P1-10] No tests exist for `visualization.py`, `cli.py`, or `builder.py`
- **File:** missing - `tests/test_visualization.py`, `tests/test_cli.py`, `tests/test_builder.py` do not exist
- **Category:** Tests
- **Problem:** `visualization.py` (~219 LOC), `cli.py` (~556 LOC), and `builder.py` together account for roughly half the user-facing surface and have zero direct test coverage. Visualization escaping logic for LaTeX / Mermaid is exactly the kind of code that breaks silently on a corner-case symbol. The REPL parses a small command grammar with no parser tests. The builder normalizes `$x` vs `${x}` syntax with no syntax-edge tests.
- **Recommendation:** Three new files:
  - `tests/test_visualization.py`: smoke + escape tests for each format. For each: empty derivation, single-step, multi-step with shared inputs (proof DAG case), Unicode word, alphabet symbols requiring LaTeX escaping (`_`, `\`, `$`, `{`).
  - `tests/test_builder.py`: `.rule()` before `.var()`, mixed `$x` / `${x}` in one pattern, longest-prefix-match between two declared vars `$x` and `$xy`, missing `.alphabet()`, multiple axioms with the same word.
  - `tests/test_cli.py`: drive the REPL via a string-buffer transcript runner. Cover: `alphabet`, `var`, `axiom`, `rule "..."`, `generate N`, `query "..."`, malformed inputs, EOF on stdin, KeyboardInterrupt.
- **Effort:** L

---

### P2 - Quality improvements worth doing

#### [P2-1] `apply_rules_all` rebuilds a `frozenset` per BFS level
- **File:** `src/post_canonical/system/pcs.py:104, 150`
- **Category:** Performance
- **Problem:** Both `generate` and `iterate` call `executor.apply_rules_all(frozenset(...))`. The executor only iterates the collection (`for derived_word in words` in `_apply_single_antecedent`); freezing it is a no-op for correctness and an O(M) allocation per level. With 100 BFS rounds and a 50-word frontier, that is 5000 wasted frozenset constructions.
- **Recommendation:** Change `RuleExecutor.apply_rules_all` and `apply_rules` to accept `Iterable[DerivedWord]` (or `Collection[DerivedWord]` if multi-pass is needed inside). The multi-antecedent path materializes via `list(word_map.keys())` already.
- **Effort:** S

#### [P2-2] Missing early-exit prune before the unbound-variable loop
- **File:** `src/post_canonical/matching/matcher.py:138-145`
- **Category:** Performance
- **Problem:** `max_len = max(min_len, len(word) - pos - suffix_min[next_idx])` already encodes the length-feasibility constraint, but the entire variable branch is entered even when the remaining word cannot accommodate the remaining pattern. Adding a single check pre-loop short-circuits whole subtrees:
  ```python
  remaining = len(word) - pos
  if remaining < suffix_min[elem_idx]:
      return
  ```
- **Recommendation:** Insert that guard immediately after `if elem_idx >= len(elements)` and remove the redundant `max(min_len, ...)` ceiling once you have it.
- **Effort:** S

#### [P2-3] Multi-antecedent unifier exhaustively iterates `permutations`
- **File:** `src/post_canonical/matching/unifier.py:93` (per the perf agent; needs investigation)
- **Category:** Performance
- **Problem:** Reportedly uses `itertools.permutations(available_words, n)` to try word combinations against `n` antecedent patterns. For M = 20 frontier words and n = 3, that is 6840 attempts with no early-exit on partial unification failure.
- **Recommendation:** Needs investigation. Two cheap wins to consider: (a) order antecedents by descending constraint (fewest variables first) so failing patterns prune the tree earlier; (b) build a per-pattern candidate list by filtering words whose length is compatible with `min_match_length`, then take the cartesian product over those. Save the deeper restructuring for after profiling.
- **Effort:** L

#### [P2-4] `Pattern.parse` raises bare `ValueError` without listing declared variables
- **File:** `src/post_canonical/core/pattern.py:147`
- **Category:** API
- **Problem:** `raise ValueError(f"Unknown variable: ${{{var_name}}}")`. The builder layer catches similar mistakes with a richer `BuilderError` (`builder.py:246`) that lists declared vars and offers a hint. The core parser, called both from the builder and directly, is far less helpful.
- **Recommendation:** Add a `PatternError(ValueError)` to `core/errors.py`. Pass the declared-variable set through `Pattern.parse` so the message reads:
  ```
  PatternError: Unknown variable '${z}' at position 4
    Declared: {x, y}
    Hint: Add 'z' as a variable, or check the spelling.
  ```
- **Effort:** M

#### [P2-5] `pcs.generate` and `generate_words` return `frozenset`
- **File:** `src/post_canonical/system/pcs.py:73, 117`
- **Category:** API
- **Problem:** `frozenset` is unordered and unindexable. The README's first example sorts the result (`sorted(words, ...)`) precisely because the frozenset arrives in arbitrary order. For an API whose users typically want to print, slice, or compare results, `tuple` (or `list`) is friendlier and still immutable enough.
- **Recommendation:** Return `tuple[DerivedWord, ...]` (and `tuple[str, ...]`) ordered by derivation depth, then word length, then lexicographic. Users who want set semantics can `set(...)` the tuple. Adjust tests; this is a breaking API change so wait until v3.0 or shadow with a new method (`generate_ordered`) and deprecate.
- **Effort:** M

#### [P2-6] `__post_init__` validation in `PostCanonicalSystem` runs eagerly even when constructed by trusted code
- **File:** `src/post_canonical/system/pcs.py:35-65`
- **Category:** API
- **Problem:** Validation is done in `__post_init__`, so `SystemBuilder.build()` re-runs validation that the builder already enforced. The error messages here are also weaker than the builder's: `f"Undeclared variable in rule: {var}"` does not name the rule. For systems with hundreds of rules this is annoying.
- **Recommendation:** Two options. (a) Add an `unsafe_construct` classmethod that skips validation, used by the builder. (b) Improve messages to include `rule.name` (already used at line 61). Pick (b) at minimum:
  ```python
  raise ValueError(
      f"Rule '{rule.name}' uses undeclared variable {var}. "
      f"Declared: {sorted(v.name for v in self.variables)}"
  )
  ```
- **Effort:** S

#### [P2-7] `object.__setattr__` hack appears in five frozen-dataclass `__init__`s
- **File:** `src/post_canonical/core/alphabet.py:19-30`, `src/post_canonical/core/pattern.py:53-55`, `src/post_canonical/core/rule.py:29-42`, `src/post_canonical/system/derivation.py:43-44`, `src/post_canonical/matching/binding.py:22-27`
- **Category:** Anti-pattern
- **Problem:** Each class overrides `__init__` to normalize inputs (sort, freeze, dedupe), then uses `object.__setattr__` to write through the frozen barrier. It works, but `__post_init__` plus `field(default_factory=...)` or a plain `from_*` classmethod factory accomplishes the same with idiomatic dataclass code.
- **Recommendation:** For each, prefer a classmethod factory pattern:
  ```python
  @dataclass(frozen=True, slots=True)
  class Alphabet:
      symbols: frozenset[str]
      _sorted: tuple[str, ...]

      @classmethod
      def from_symbols(cls, symbols: str | Iterable[str]) -> "Alphabet":
          symbol_set = frozenset(symbols)
          ...
          return cls(symbols=symbol_set, _sorted=tuple(sorted(symbol_set)))
  ```
  Keep `__init__` as the dataclass-default, gate normalization behind the factory. Done in one PR per class to keep diffs small.
- **Effort:** M

#### [P2-8] `Sequence` / `list` / `tuple` are used inconsistently in signatures
- **File:** `src/post_canonical/builder.py:70` (`list[ProductionRule]`), `src/post_canonical/matching/unifier.py:25` (`Sequence[Pattern]`), `src/post_canonical/matching/matcher.py:82` (`tuple[PatternElement, ...]`)
- **Category:** Types
- **Problem:** Public input parameters use a mix of `list`, `Sequence`, and `tuple`, with no consistent rule. Strict mypy users hit unnecessary friction at call sites.
- **Recommendation:** Adopt a one-line policy: public input parameters take `Sequence[T]` (or `Iterable[T]` when single-pass); internal storage is `tuple[T, ...]` for immutable, `list[T]` for mutable; return types are concrete (`tuple` or `list`, never `Sequence`). Document in `CLAUDE.md`.
- **Effort:** M

#### [P2-9] `cli.py:84` suppresses an avoidable type error with `# type: ignore[arg-type]`
- **File:** `src/post_canonical/cli.py:84`
- **Category:** Types
- **Problem:** `builder = SystemBuilder(self._alphabet)  # type: ignore[arg-type]` papers over `Alphabet | None` vs `str | Alphabet`. The surrounding code already validates non-None; mypy just cannot see it.
- **Recommendation:** Replace with an explicit `assert self._alphabet is not None, "alphabet must be set"` immediately above. mypy narrows; the comment goes away.
- **Effort:** S

#### [P2-10] `visualization.py` is a flat 219-LOC module bundling four independent exporters
- **File:** `src/post_canonical/visualization.py`
- **Category:** Structure
- **Problem:** Four exporter functions (`to_dot`, `to_latex`, `to_ascii_tree`, `to_mermaid`) plus their format-specific escape helpers all sit in one file. Any future exporter (HTML, SVG, JSON-LD) inflates the module further and forces shared imports across formats that share nothing.
- **Recommendation:** Convert to `visualization/` subpackage with one file per format. Re-export the four names from `visualization/__init__.py`. Pair this with [P1-10] when writing `tests/test_visualization.py` so the new tests can also be split per format.
- **Effort:** M

#### [P2-11] No property-based tests for the matcher's central invariant
- **File:** missing - `tests/test_properties.py`
- **Category:** Tests
- **Problem:** The matcher's contract is that any binding it yields, when substituted into the pattern, must equal the input word. There is no property test that exercises this; sample-driven tests cannot cover the variable-length search space.
- **Recommendation:** Add `hypothesis` as a dev dep (no runtime impact) and write three properties:
  1. **Matcher round-trip:** `for binding in match(p, w): assert p.substitute(binding) == w`.
  2. **JSON round-trip:** `decode(encode(s)) == s` for systems built by a Hypothesis strategy.
  3. **Pattern parse round-trip:** `Pattern.parse(str(p), vars) == p` for arbitrary patterns.
- **Effort:** M

#### [P2-12] Multi-antecedent rules: same-word-twice and overlapping bindings are not exercised
- **File:** `tests/test_executor.py`
- **Category:** Tests
- **Problem:** `permutations(available_words, n)` allows the same word to satisfy multiple antecedents in some configurations. There is no explicit test pinning that behavior, nor a test where the same variable appears in two antecedents (forcing cross-antecedent binding consistency).
- **Recommendation:** Add `test_multi_antecedent_same_word_satisfies_two_patterns` and `test_shared_var_across_antecedents_must_unify`. Pin the chosen semantics either way; today the behavior is implicit.
- **Effort:** S

#### [P2-13] `max_steps=10` default is undocumented and silent
- **File:** `src/post_canonical/system/pcs.py:71`, `README.md:54`
- **Category:** Docs / API
- **Problem:** `generate(max_steps=10)` is the default. Users running on infinite or rapidly-expanding systems get truncated output with no warning. The default does not appear in the README, and the docstring does not justify it.
- **Recommendation:** Document the default in the docstring with the rationale ("ten steps prevents accidental runaway") and have `generate` log or warn (via a flag, not always) when the result was reached because the step limit was hit, not because a fixed point was reached. Alternative: make `max_steps` keyword-only and require it explicitly.
- **Effort:** S

#### [P2-14] Pattern parse syntax is not documented as a formal grammar
- **File:** `README.md:66-73`, `docs/ARCHITECTURE.md`
- **Category:** Docs
- **Problem:** Examples show `$x` and `${x}` interchangeably, but the rules are not stated. `Pattern.parse` only accepts `${...}` (see `pattern.py:135-145`); the builder's `_normalize_pattern_string` accepts both. Users coming via the JSON codec will see `${...}`-only strings and wonder why.
- **Recommendation:** Add a "Pattern syntax" section to the README with a short BNF and a one-liner about which entry points accept `$x` shorthand vs require `${x}`:
  ```
  pattern    ::= element+
  element    ::= constant | variable
  constant   ::= [^$]+
  variable   ::= "${" name "}"            (canonical, used by Pattern.parse)
                | "$" name                (shorthand, accepted by SystemBuilder only)
  name       ::= [A-Za-z_][A-Za-z0-9_]*
  ```
- **Effort:** S

#### [P2-15] `presets/` split is over-engineered for the current contents
- **File:** `src/post_canonical/presets/alphabets.py`, `src/post_canonical/presets/examples.py`
- **Category:** Structure
- **Problem:** `alphabets.py` is 7 constants. `examples.py` is 3 builder functions. Combined they total under 60 LOC. The directory split adds an `__init__.py` and a re-export step for almost no payoff.
- **Recommendation:** Either flatten to a single `presets.py` (preferred), or keep the split and commit to growing it (load-from-file, user presets directory). Pick a direction.
- **Effort:** S

---

### P3 - Nice-to-have polish

#### [P3-1] Repeated `min_length()` calls per variable
- **File:** `src/post_canonical/matching/matcher.py:95, 139`
- **Category:** Performance
- **Problem:** `Variable.min_length()` runs once during suffix-min precomputation and again inside the matching loop for the same variable. Trivial cost, but wasted work for hot patterns.
- **Recommendation:** Cache `min_length` as a `cached_property` on `Variable`, or stash it on a parallel array alongside `suffix_min`.
- **Effort:** S

#### [P3-2] `ProductionRule.sort_key` is a property recomputed on every read
- **File:** `src/post_canonical/core/rule.py` (`sort_key`), `src/post_canonical/system/executor.py:49`, `src/post_canonical/system/pcs.py:181`
- **Category:** Performance
- **Problem:** Each access reconstructs `(-self.priority, self.name or "")`. The executor caches the sort once at init, but `pcs.describe()` re-sorts on every call.
- **Recommendation:** Convert `sort_key` to a regular field (computed in `__init__` / `__post_init__`) on the frozen rule. Or use `functools.cached_property` if you keep the property API.
- **Effort:** S

#### [P3-3] CLI line wrapping uses a manual chunk loop
- **File:** `src/post_canonical/cli.py:370-377`
- **Category:** Anti-pattern
- **Problem:** Manual accumulator pattern reimplements `itertools.batched`, available since 3.12 (which the project targets).
- **Recommendation:**
  ```python
  from itertools import batched
  for batch in batched(words, max_per_line):
      print(prefix + ", ".join(batch))
  ```
- **Effort:** S

#### [P3-4] `JSONCodec` raises a vague error on version mismatch
- **File:** `src/post_canonical/serialization/json_codec.py:118`
- **Category:** API
- **Problem:** `raise ValueError(f"Unsupported version: {version}")`. No mention of supported version, no upgrade path.
- **Recommendation:**
  ```python
  raise ValueError(
      f"Unsupported JSON schema version '{version}'. "
      f"This codec supports version '{self.VERSION}'. "
      f"To migrate, re-encode the system with the current codec."
  )
  ```
- **Effort:** S

#### [P3-5] `ProductionRule`, `DerivedWord`, `Variable` rely on default dataclass `__repr__`
- **File:** `src/post_canonical/core/rule.py`, `src/post_canonical/system/derivation.py`, `src/post_canonical/core/variable.py`
- **Category:** API
- **Problem:** REPL output for a derived word shows the full nested derivation tree as a default-formatted dataclass repr - dozens of lines for a 3-step derivation. Each class has a usable `__str__`, but Python's REPL calls `__repr__`.
- **Recommendation:** Add concise `__repr__`s that mirror `__str__` for these three. Keep the dataclass-style repr behind `__rich_repr__` if you ever add `rich` (the codebase has no runtime deps; do not add one).
- **Effort:** S

#### [P3-6] REPL "no axioms" error could include an example
- **File:** `src/post_canonical/cli.py` (around line 103)
- **Category:** API
- **Problem:** "No axioms defined. Use 'axiom <word>' first." User who just typed `generate` may not know what a valid `<word>` looks like.
- **Recommendation:** Append a concrete one: `"... Use 'axiom <word>' first (e.g., 'axiom MI')."`
- **Effort:** S

#### [P3-7] `SINGLE` and `NON_EMPTY` boundary cases not covered by tests
- **File:** `tests/test_matcher.py`, `tests/test_variable.py`
- **Category:** Tests
- **Problem:** No test asserts that a `SINGLE` variable refuses to match the empty word, and no test asserts a `NON_EMPTY` variable matches a one-character word at the end of input.
- **Recommendation:** Two parametrized cases. Should be 30 minutes of work and they harden a real user-facing contract.
- **Effort:** S

#### [P3-8] `iterate()` has no test that exercises bounded consumption
- **File:** `tests/test_pcs.py:223-239`
- **Category:** Tests
- **Problem:** Existing tests slice with explicit indexing. The lazy-generator contract is best validated with `itertools.islice(system.iterate(), n)` to confirm it does not over-produce. For palindrome / binary-doubler systems the test should run a thousand items and confirm it terminates only because we asked it to.
- **Recommendation:** Add `test_iterate_islice_bounded` and `test_iterate_yields_in_bfs_order`.
- **Effort:** S

#### [P3-9] CONTRIBUTING.md and release process are missing
- **File:** missing - `CONTRIBUTING.md`
- **Category:** Docs
- **Problem:** No documented release flow. The two-place version invariant (`pyproject.toml` and `__init__.py`) is real and easy to break. There is no checklist for changelog, tag, publish.
- **Recommendation:** Write a short `CONTRIBUTING.md` with: setup (uv sync), test (uv run pytest), lint (uv run ruff check), release checklist (bump both versions, add changelog entry, tag, build, push). Optionally add a CI guard that compares `pyproject.toml` and `__init__.py` versions.
- **Effort:** S

#### [P3-10] README example output for the MU puzzle is wrong
- **File:** `README.md:54-56`
- **Category:** Docs
- **Problem:** The expected output comment lists 8 words. Running the example with the four MU rules at `max_steps=3` produces a different set (the `III_to_U` and `delete_UU` rules can fire within three steps and add `MU`-adjacent words). _Needs investigation - I have not run the example end-to-end as part of this review, but at least one other reviewer reported a discrepancy._
- **Recommendation:** Run `python example.py` in the repo and pin the actual sorted output as the comment, or trim the example to `max_steps=2` where the answer is small enough to verify by hand.
- **Effort:** S

---

## Themes and patterns

- **Inconsistent fidelity to the "frozen + slots" invariant.** Five core types use `object.__setattr__` to normalize inputs through the frozen barrier ([P2-7]); two value types miss `slots` or `frozen` outright ([P1-4], [P1-5]). The repo has a strong stated invariant that the code mostly honors but never quite enforces. A short audit one-liner (`grep -L "slots=True" src/**/*.py | xargs grep -l "@dataclass(frozen=True)"`) would surface every miss.
- **The matcher is the right place to spend perf attention.** [P1-1], [P1-2], [P2-1], [P2-2], [P2-3], [P3-1], [P3-2] are all in or near the matcher / executor hot path. Together they likely halve the cost of a typical `generate()` call. The same is not true of any other module - perf engineering anywhere else is premature.
- **Documentation has drifted from code in concrete, checkable ways.** The DFS myth ([P0-1], [P1-7]), the v2.0.0 REPL banner ([P1-8]), the missing changelog entries ([P1-9]), the wrong README output ([P3-10]). All of these are caught by either a small CI doc-test or an `__version__` consistency check. The investment is one afternoon.
- **The public API surface is silently misleading.** [P1-3] hides documented entry points; [P2-5] returns frozensets where users want sequences; [P2-13] truncates results without saying so. None individually is severe, but collectively they make the library feel like an "internal tool that grew a README." Pinning `__all__` and tightening return contracts removes that smell.
- **Tests cover the engine but not the surface.** Matching, derivation, and pattern logic are well-tested. Visualization, REPL, and the builder DSL - the parts users actually touch - have zero tests. [P1-10] and [P2-11] are the highest-leverage test additions because they catch a class of bug invisible to the existing suite.

## Recommended next 5 actions

1. **Fix the DFS-claim trio in one tiny PR** (`CHANGELOG.md`, `CLAUDE.md`, optionally re-link the ARCHITECTURE.md sections). Resolves [P0-1] and [P1-7]. 15-minute job; clears the only correctness-of-claims defect.
2. **Add `SystemBuilder` and the four `to_*` exporters to `__init__.__all__`** ([P1-3]). One-line PR with the highest leverage on user experience: makes the README's quick-start actually work.
3. **Apply the four-line matcher perf patch:** `Binding.extend` save/restore ([P1-1]), `str.startswith` for the constant and bound-variable arms ([P1-2]), the pre-loop suffix-min guard ([P2-2]), and the BFS-level frozenset removal ([P2-1]). This is one cohesive PR and hits the biggest engineering win in the whole list.
4. **Lock down the dataclass invariants** ([P1-4], [P1-5]) and **flip `Enum`s to string values** ([P1-6]). Mechanical, contained to a few files, removes the largest "consistency drift" theme.
5. **Stand up the missing test triplet** ([P1-10]) and add property-based round-trip tests ([P2-11]). After this, the codebase has tests for everything users touch and a regression net under the matcher contract. Combined with action 3, perf optimizations are no longer scary.
