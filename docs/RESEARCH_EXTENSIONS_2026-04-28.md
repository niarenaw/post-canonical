# Research: Shippable Extensions to post-canonical

_Date: 2026-04-28_

## Executive Summary

- **Bidirectional BFS reachability** is the single biggest practical win - it preserves shortest-proof guarantees while typically cutting node expansions by orders of magnitude on word problems, and slots cleanly behind the existing `ReachabilityQuery` interface.
- **Tag-system and cyclic-tag-system front-ends** unlock famous universal models (Cocke-Minsky, Wolfram Rule 110 simulator) on top of the executor without touching the matching engine, and connect the library directly to the small-universal-Turing-machine literature.
- **Static analysis: invariants, termination, confluence** turns post-canonical into a teaching tool that not only runs systems but reasons about them, including a Knuth-Bendix-style critical-pair finder over Post-style productions.
- **Visualization: Petri-net and proof-DAG views** generalize the existing single-derivation exporters to render shared inputs, multi-antecedent concurrency, and full reachability frontiers.
- **Preset-pack: FRACTRAN, SK combinators, primality, Collatz** turns the presets module into a "computability zoo" that demonstrates Turing completeness in concrete, runnable form.

## What already exists (so we don't propose duplicates)

Grounded in `src/post_canonical/__init__.py`, `docs/ARCHITECTURE.md`, and the source modules:

- Core types: `Alphabet`, `Variable` (ANY / NON_EMPTY / SINGLE), `Pattern`, `ProductionRule` with multi-antecedent support.
- Backtracking pattern matcher (`matching/matcher.py`) and multi-pattern unifier (`matching/unifier.py`) for multi-antecedent rules.
- BFS execution (`system/executor.py`) with DETERMINISTIC and NON_DETERMINISTIC modes; lazy generator-based `iterate()`.
- Forward-only reachability query (`query/reachability.py`) with derivation extraction.
- Derivation tracking: `Derivation`, `DerivationStep`, `DerivedWord` (immutable, full proof trace).
- Visualization exporters (`visualization.py`): DOT, LaTeX, ASCII tree, Mermaid - currently single-derivation only.
- JSON serialization round-trip (`serialization/json_codec.py`).
- `pcs` REPL (`cli.py`) and fluent `SystemBuilder` DSL (`builder.py`).
- Preset alphabets and example systems: MU puzzle, binary doubler, palindrome generator.

So the proposals below avoid: forward BFS reachability, basic derivation export, axiom/rule containers, MU puzzle, basic palindromes / doubler, JSON I/O, and the REPL skeleton.

---

## Candidate Extensions

### 1. Bidirectional BFS reachability

- **What it is:** Run BFS forward from axioms and BFS backward from the target, expanding the smaller frontier each round and stopping when frontiers meet. For a target `t`, the backward step inverts each rule: given a consequent template `C` matching some superstring of `t`, antecedent instances are reconstructed via the same unifier. Math: for an unweighted derivation graph with branching factor `b` and solution depth `d`, unidirectional BFS expands `O(b^d)`; bidirectional BFS expands `O(2 b^(d/2))`. The MM algorithm of Holte et al. (2016) generalizes this with admissible heuristics and guarantees the meeting node lies at depth `d/2`, never beyond the midpoint.
- **Why it's worth shipping:** The MU puzzle, palindrome systems, and any monotone (length-non-decreasing) system have huge forward frontiers but tractable backward expansions. The backward pass also gives a free "is the target on the right alphabet / is its structure even consistent with rule outputs" sanity check before launching forward search.
- **Sketched API:**

```python
# query/bidirectional.py
from collections.abc import Iterator
from dataclasses import dataclass

from ..core.rule import ProductionRule
from ..system.derivation import Derivation
from ..system.pcs import PostCanonicalSystem
from .reachability import ReachabilityResult


@dataclass(frozen=True, slots=True)
class BidirectionalConfig:
    max_words: int = 10_000
    expand_smaller_frontier: bool = True
    invertible_only: bool = False  # If True, fail fast on rules with no clean inverse.


class BidirectionalReachabilityQuery:
    """Meet-in-the-middle reachability for length-bounded systems."""

    def __init__(self, system: PostCanonicalSystem) -> None:
        self.system = system
        self._inverse_rules = _compute_inverse_rules(system.rules)

    def is_derivable(
        self,
        target: str,
        config: BidirectionalConfig | None = None,
    ) -> ReachabilityResult: ...

    def _expand_backward(
        self, frontier: frozenset[str]
    ) -> Iterator[tuple[str, ProductionRule]]: ...
```

- **Implementation notes:** New module `query/bidirectional.py` next to existing `reachability.py`; reuse `MultiPatternUnifier` for the backward step (rule inversion = consequent-as-pattern matching). Combining both halves of a derivation yields a full `Derivation` by concatenating the forward chain with the reversed backward chain.
- **Risk / scope creep:** Inverting non-injective rules (e.g. MU's `xUUy -> xy` deletion) creates infinite backward branching. Mitigation: require the user to mark rules as length-non-decreasing, or introduce a `max_pre_image_length` knob on the backward expansion.
- **Effort:** M (a week).
- **Citations:**
  - Holte, Felner, Sharon, Sturtevant. "Bidirectional Search That Is Guaranteed to Meet in the Middle." AAAI 2016. https://ai.dmi.unibas.ch/research/reading_group/holte-et-al-aaai2016.pdf - introduces MM, the first BiHS guaranteed to meet at the midpoint.
  - Wang, Weiss, Mu, Salzman. "Bidirectional Search while Ensuring Meet-In-The-Middle." IJCAI 2025. https://www.ijcai.org/proceedings/2025/999 - tighter termination conditions, two orders of magnitude over MM.
  - "Bidirectional Search in Practice." https://thelinuxcode.com/bidirectional-search-in-practice-faster-shortest-paths-by-meeting-in-the-middle/ - practical guidance: alternate expansions, expand smaller frontier first.

---

### 2. A* / IDA* with admissible heuristics on words

- **What it is:** Heuristic-guided search using `f(n) = g(n) + h(n)` where `g` is the depth from axioms and `h` is a lower bound on remaining steps. Admissible candidate heuristics for string rewriting: (a) `|len(target) - len(current)| / max_length_change_per_rule`, (b) Hamming-style mismatch on a fixed-length suffix once length matches, (c) symbol-multiset distance: for each symbol `s`, compute the difference in count between current word and target, divided by the max change in `s` any rule can produce. Korf's IDA* uses repeated depth-first iterations with an `f`-cutoff to keep memory linear in depth.
- **Why it's worth shipping:** The reachability frontier on systems like SK reduction or arithmetic encodings explodes; a length-driven heuristic prunes most branches. IDA* in particular complements the existing BFS with linear-memory search for deep proofs.
- **Sketched API:**

```python
# query/heuristic.py
from collections.abc import Callable
from dataclasses import dataclass

type Heuristic = Callable[[str, str], int]  # (current, target) -> lower bound


@dataclass(frozen=True, slots=True)
class HeuristicSearchConfig:
    heuristic: Heuristic
    max_expansions: int = 100_000
    epsilon: float = 1.0  # Weight on h(n); 1.0 = admissible A*.


def length_difference_heuristic(rules: frozenset[ProductionRule]) -> Heuristic: ...
def symbol_count_heuristic(rules: frozenset[ProductionRule]) -> Heuristic: ...


class AStarQuery:
    def __init__(self, system: PostCanonicalSystem, config: HeuristicSearchConfig) -> None: ...
    def is_derivable(self, target: str) -> ReachabilityResult: ...


class IDAStarQuery:
    """Linear-memory variant via iteratively-deepening f-cost cutoff."""
    ...
```

- **Implementation notes:** Heuristic factories live in `query/heuristics.py`; both factories statically analyze rules to compute per-symbol max delta. The priority queue is `heapq` from stdlib.
- **Risk / scope creep:** Picking a heuristic that is actually admissible (never overestimates) is subtle - rules with variable-width substitutions (e.g. `Mx -> Mxx`) make the per-step word-length change unbounded. Document that admissibility holds only when each rule's length change is bounded a priori, otherwise fall back to weighted (epsilon-admissible) A*.
- **Effort:** M (a week).
- **Citations:**
  - Korf. "Recent Progress in the Design and Analysis of Admissible Heuristic Functions." AAAI 2000. https://cdn.aaai.org/AAAI/2000/AAAI00-212.pdf - canonical treatment of admissibility, IDA*, pattern databases.
  - Edelkamp et al. "Cost-Algebraic Heuristic Search." AAAI 2005. https://cdn.aaai.org/AAAI/2005/AAAI05-216.pdf - generalization of A* admissibility used to justify symbol-count style heuristics.
  - "Possible Heuristic Function for Word Ladder." https://stackoverflow.com/questions/35284428/possible-heuristic-function-for-word-ladder - concrete discussion of word-distance heuristics.

---

### 3. Tag system and cyclic-tag-system front-ends

- **What it is:** Tag system: alphabet `{a_1, ..., a_k}`, deletion number `m`, and for each symbol a production word; at each step the leftmost symbol is examined, the first `m` symbols are deleted, and the production for that examined symbol is appended at the right. Cyclic tag systems (CTS) reduce this further to a fixed cyclic list of "production words"; at each step the leftmost bit is consumed, and if it was 1 the next production in the cycle is appended. Cocke and Minsky (1964) proved 2-tag systems universal; Cook proved CTS universal as part of the Rule 110 universality result.
- **Why it's worth shipping:** Both formalisms are special cases of Post canonical systems, so they ride on the existing executor for free. Adds a famously universal model (smallest known universal Turing machine encodings go through tag systems) and extends the `presets` module from "puzzles" to "models of computation."
- **Sketched API:**

```python
# presets/tag_systems.py
from collections.abc import Sequence
from dataclasses import dataclass

from ..system.pcs import PostCanonicalSystem


@dataclass(frozen=True, slots=True)
class TagSystem:
    alphabet: tuple[str, ...]
    deletion_number: int  # m >= 2 required for universality
    productions: dict[str, str]  # symbol -> word appended
    axiom: str

    def to_pcs(self) -> PostCanonicalSystem:
        """Compile to an equivalent multi-rule Post canonical system."""
        ...


@dataclass(frozen=True, slots=True)
class CyclicTagSystem:
    productions: tuple[str, ...]  # Cycled in order each step
    axiom: str

    def to_pcs(self) -> PostCanonicalSystem: ...


def cocke_minsky_universal_2tag() -> TagSystem: ...
def cook_rule110_via_cts(rule110_input: str) -> CyclicTagSystem: ...
```

- **Implementation notes:** The compilation `to_pcs()` introduces auxiliary state symbols (one per cycle position for CTS) and emits one Post production per (state, scanned-symbol) pair. Tag systems use a single ANY variable to capture the "rest of tape" tail.
- **Risk / scope creep:** Faithfully reproducing the Cocke-Minsky encoding is non-trivial - the encoding from Turing machine to 2-tag is exponential in tape size. Ship the compiler plus a small worked example (e.g. a 3-state TM); leave the full Rule 110 simulator to a separate notebook example.
- **Effort:** M (a week).
- **Citations:**
  - Cocke, Minsky. "Universality of Tag Systems with P = 2." JACM 1964. https://dl.acm.org/doi/10.1145/321203.321206 - the canonical universality proof for 2-tag systems via Post canonical systems.
  - Cook (in Wolfram Science). "Universality in Elementary Cellular Automata." https://content.wolfram.com/sites/13/2018/02/15-1-1.pdf - cyclic tag systems simulating 2-tag systems and Rule 110.
  - Wolfram. "Cyclic Tag Systems." NKS p. 95. http://www.wolframscience.com/nks/p95--cyclic-tag-systems - introduction and rule format.
  - Neary. "Small Universal Turing Machines." 2008. https://gwern.net/doc/cs/computable/2008-neary.pdf - improves cyclic tag system simulation overhead from exponential to polynomial.

---

### 4. Markov normal-algorithm front-end

- **What it is:** Markov algorithms are ordered string-rewriting systems: at each step the first applicable rule (in the user-supplied order) fires on the leftmost match, with optional "termination" rules that halt the run. They are equivalent to Turing machines (the Church-Turing principle of normalization) and translate cleanly to Post normal-form productions of shape `gP -> Pg'`.
- **Why it's worth shipping:** Markov algorithms are the deterministic counterpart to non-deterministic Post canonical systems; exposing them gives users a familiar "step-by-step procedure" entry point. This is also how Hofstadter-style typographic systems are typically taught.
- **Sketched API:**

```python
# presets/markov.py
from collections.abc import Sequence
from dataclasses import dataclass

from ..core.alphabet import Alphabet
from ..system.pcs import PostCanonicalSystem


@dataclass(frozen=True, slots=True)
class MarkovRule:
    lhs: str
    rhs: str
    terminating: bool = False


@dataclass(frozen=True, slots=True)
class MarkovAlgorithm:
    alphabet: Alphabet
    rules: tuple[MarkovRule, ...]  # Order is significant.
    axiom: str

    def to_pcs(self) -> PostCanonicalSystem:
        """Compile via Post normal-form theorem with priority encoding."""
        ...

    def step(self, word: str) -> tuple[str, bool]:
        """One Markov step; second element is True if terminating rule fired."""
        ...
```

- **Implementation notes:** Each Markov rule becomes a Post production with antecedent `${prefix} lhs ${suffix}` and consequent `${prefix} rhs ${suffix}`, with rule ordering encoded via `ProductionRule.priority`. Terminating rules add a guard symbol that no other rule matches. Live in `presets/markov.py` to avoid inflating `core/`.
- **Risk / scope creep:** Pure Markov semantics (leftmost match, ordered rules) requires DETERMINISTIC mode and a tiebreaker beyond priority (leftmost match position). Surface this as an `ExecutionMode.LEFTMOST_DETERMINISTIC` option rather than overloading existing modes.
- **Effort:** S (1-2 days).
- **Citations:**
  - "Markov algorithm." Wikipedia. https://en.wikipedia.org/wiki/Markov_algorithm - definition, ordered application, equivalence to Turing machines.
  - "Post canonical system." Wikipedia. https://en.wikipedia.org/wiki/Post_canonical_system - the normal-form theorem reducing any Post system (and by reduction any Markov algorithm) to productions of form `gP -> Pg'`.
  - "Normalisation using Markov algorithms." Edinburgh DCS notes. https://www.dcs.ed.ac.uk/home/tl/prop/node9.html - worked normalization example.

---

### 5. Knuth-Bendix-style critical-pair analyzer

- **What it is:** Given two rules `l1 -> r1` and `l2 -> r2`, a **critical pair** arises wherever a suffix of `l1` overlaps a prefix of `l2` (or vice versa). The two ways of rewriting the overlap produce a pair `(t1, t2)`; if `t1` and `t2` reduce to the same normal form the pair is "joinable." The Knuth-Bendix completion procedure iteratively orients non-joinable pairs as new rules until the system is confluent (or diverges). Even partial completion is informative: a list of critical pairs gives concrete rule interactions to inspect.
- **Why it's worth shipping:** Today users have to eyeball whether their rules are confluent. A critical-pair report turns that into a mechanical check: "rules `add_U` and `III_to_U` overlap at `MIIIIIII`; here are the two reducts." Even without orienting, this lets users see which rules conflict.
- **Sketched API:**

```python
# query/critical_pairs.py
from collections.abc import Iterator
from dataclasses import dataclass

from ..core.rule import ProductionRule
from ..system.pcs import PostCanonicalSystem


@dataclass(frozen=True, slots=True)
class CriticalPair:
    overlap_word: str
    rule_a: ProductionRule
    rule_b: ProductionRule
    reduct_a: str
    reduct_b: str
    joinable: bool  # True if both reduce to a common normal form within budget.


class CriticalPairAnalyzer:
    def __init__(self, system: PostCanonicalSystem) -> None: ...

    def critical_pairs(self) -> Iterator[CriticalPair]: ...

    def confluence_report(self, max_overlap_length: int = 20) -> ConfluenceReport: ...
```

- **Implementation notes:** Live in `query/critical_pairs.py`. Overlap detection only needs the constant skeleton of antecedent patterns; variable parts are rebound. For now, treat each antecedent as a regex-like pattern and find string overlaps directly. Joinability uses a length-bounded BFS reusing the existing executor.
- **Risk / scope creep:** Full Knuth-Bendix completion needs a reduction ordering (LPO/RPO), which is itself a research artifact; SAT-based encodings exist but are heavyweight. Ship critical-pair detection plus a manual `orient(pair, direction)` API; full automated completion is a follow-up.
- **Effort:** L (multi-week, full); M for analysis-only.
- **Citations:**
  - "Knuth-Bendix completion algorithm." Wikipedia. https://en.wikipedia.org/wiki/Knuth-Bendix_completion_algorithm - canonical description with deduce/orient/simplify rules.
  - Zucker. "String Knuth Bendix." 2024. https://www.philipzucker.com/string_knuth/ - clean Python implementation of string KB; useful reference for overlap finding.
  - Wehrman, Stump. "Knuth-Bendix Completion with a Termination Checker." https://wehrman.org/pub/jar-slothrop.pdf - completion that delegates to an external termination oracle, sidestepping the user-supplied ordering.
  - Codish, Schneider-Kamp, Lagoon, Thiemann, Giesl. "SAT Solving for Termination Proofs with Recursive Path Orders and Dependency Pairs." https://arxiv.org/pdf/cs/0605074 - LPO/RPO termination via SAT, relevant if completion is later automated.

---

### 6. Termination heuristics and length-monotonicity check

- **What it is:** Even without full Knuth-Bendix, several quick termination heuristics work on string rewriting: (a) **strict length reduction** - every rule satisfies `|consequent| < |antecedent|` for all bindings (decidable since variable kinds bound length effects); (b) **weight functions** - assign each symbol a positive integer weight and check that every rule strictly decreases total weight; (c) **lexicographic path order (LPO)** on the symbol alphabet, decidable in PSPACE per Codish et al.
- **Why it's worth shipping:** A termination certificate is a major UX win: users learn whether their system halts on every input, or only sometimes, or maybe never. Even a quick "this system is length-non-increasing therefore terminates" message is hugely informative.
- **Sketched API:**

```python
# query/termination.py
from dataclasses import dataclass
from enum import Enum, auto

from ..system.pcs import PostCanonicalSystem


class TerminationStatus(Enum):
    TERMINATING = auto()      # Proven via some certificate.
    NON_TERMINATING = auto()  # Found a self-cycle.
    UNKNOWN = auto()


@dataclass(frozen=True, slots=True)
class TerminationCertificate:
    status: TerminationStatus
    method: str  # "length_reducing", "weight_function", "lpo", "loop_detected"
    witness: dict[str, int] | str | None  # Weights, or a looping word


class TerminationChecker:
    def __init__(self, system: PostCanonicalSystem) -> None: ...

    def check_length_reducing(self) -> TerminationCertificate: ...
    def check_weight_function(self) -> TerminationCertificate: ...
    def check_loop(self, max_iterations: int = 100) -> TerminationCertificate: ...
    def check_all(self) -> TerminationCertificate: ...
```

- **Implementation notes:** New module `query/termination.py`. Length-reducing check is direct over `ProductionRule.consequent` and antecedents. Weight-function search is a small ILP solvable by Z3-free brute search over weight vectors in `[1, k]^|alphabet|` for small `k`, or a hand-rolled simplex pass. Loop detection runs DETERMINISTIC mode and looks for a repeated word.
- **Risk / scope creep:** True LPO is non-trivial to implement well; defer to a follow-up if needed. Stay zero-runtime-deps.
- **Effort:** M (a week).
- **Citations:**
  - Codish et al. "SAT Solving for Termination Proofs with Recursive Path Orders." https://arxiv.org/pdf/cs/0605074 - propositional encoding of LPO/RPO; even without SAT, the inference rules are usable for a small-alphabet brute search.
  - Zantema. "TORPA: Termination of Rewriting Proved Automatically." https://www.sciweavers.org/publications/torpa-termination-rewriting-proved-automatically - combination of polynomial interpretations, RPO, dependency pairs for SRSs.
  - Stack Exchange (TLW). "Efficient algorithm for iterated find/replace." https://cs.stackexchange.com/questions/28307/efficient-algorithm-for-iterated-find-replace - description of monotone (length-reducing) systems and the noetherian property.

---

### 7. Automatic invariant discovery (Parikh / mod-k counts)

- **What it is:** For each rule `l -> r`, compute the **delta vector** `Delta(rule)` over the alphabet: `count_s(r) - count_s(l)` for each symbol `s`. The set of reachable Parikh vectors lies inside the affine lattice `Parikh(axiom) + Z>=0 * {Delta(rule_i)}`. Linear invariants - functions `f(word) = sum c_s * count_s(word)` that are preserved or constant-mod-k - solve `c . Delta(rule) = 0 (mod k)` for every rule. The MU puzzle's "I-count mod 3" invariant falls out of this in two lines of linear algebra.
- **Why it's worth shipping:** Discovering MU's invariant by hand is a famous "aha" moment; doing it automatically lets the library report "your system has these conservation laws" before any search. Connects directly to Parikh's Theorem and Presburger arithmetic.
- **Sketched API:**

```python
# query/invariants.py
from dataclasses import dataclass

from ..system.pcs import PostCanonicalSystem


@dataclass(frozen=True, slots=True)
class LinearInvariant:
    coefficients: dict[str, int]  # Symbol -> coefficient
    modulus: int | None  # None = exact, int = invariant mod k

    def evaluate(self, word: str) -> int: ...


@dataclass(frozen=True, slots=True)
class InvariantReport:
    exact: tuple[LinearInvariant, ...]    # f(w) constant for all reachable w
    mod_k: tuple[LinearInvariant, ...]    # f(w) mod k constant
    can_prove_unreachable: tuple[str, ...]  # Targets ruled out by invariants


class InvariantAnalyzer:
    def __init__(self, system: PostCanonicalSystem) -> None: ...
    def discover(self, max_modulus: int = 12) -> InvariantReport: ...
    def prove_unreachable(self, target: str) -> LinearInvariant | None: ...
```

- **Implementation notes:** Live in `query/invariants.py`. Build the rule delta matrix `D` over `Z^|alphabet|`, then compute the integer null space (pure-Python integer Gaussian elimination - Hermite normal form is overkill for typical small systems). For mod-`k` invariants, repeat over `Z/kZ` for small `k`. Hooking into reachability lets `is_derivable` short-circuit when the target violates a known invariant.
- **Risk / scope creep:** Variable-width substitutions (e.g. `Mx -> Mxx`) make `Delta` a function of the binding rather than a fixed vector; restrict to "closed" rules where antecedent and consequent have the same multiset of variable occurrences, plus pure constants. This still covers MU and most teaching examples.
- **Effort:** M (a week).
- **Citations:**
  - "MU puzzle." Wikipedia. https://en.wikipedia.org/wiki/MU_puzzle - the canonical I-count-mod-3 invariant derivation.
  - Verma, Seidl, Schwentick. "On the Complexity of Equational Horn Clauses." (Parikh's Theorem in Presburger form.) Discussed in https://arxiv.org/pdf/2210.02925 - context-free Parikh images are semilinear and Presburger-definable.
  - Lin. "Some Applications of Parikh's Theorem to Verification." https://anthonywlin.github.io/papers/lics10a.pdf - normal-form theorems and polynomial-time algorithms for Parikh images.
  - "What are some puzzles that are solved by using invariants?" Math Stack Exchange. https://math.stackexchange.com/questions/3744038/what-are-some-puzzles-that-are-solved-by-using-invariants - MU and related invariant puzzles.

---

### 8. FRACTRAN, SK, and primality preset pack

- **What it is:** A coordinated set of presets that demonstrate Turing completeness in concrete form:
  - **FRACTRAN encoding:** Conway's PRIMEGAME `(17/91, 78/85, ..., 55/1)` encoded as a Post system over the alphabet `{p_1, p_2, ...}` (one symbol per prime), with one rule per fraction `n/d`: "if the multiset contains `d`'s prime factorization, replace with `n`'s factorization."
  - **SK combinator reducer:** alphabet `{S, K, (, )}`, rules implementing `Sxyz -> xz(yz)` and `Kxy -> x` via multi-antecedent productions plus parser auxiliaries.
  - **Collatz:** a Post system over a unary alphabet that halves on even and applies `3n+1` on odd, demonstrating undecidable-conjecture-territory dynamics.
  - **Fibonacci / unary primality:** classic examples used in the cyclic tag system literature.
- **Why it's worth shipping:** Right now `presets/examples.py` ships three pedagogical systems (MU puzzle, doubler, palindromes). Adding FRACTRAN and SK turns the presets into a "computability museum" that connects post-canonical to Conway, Curry, and Schönfinkel without leaving the library.
- **Sketched API:**

```python
# presets/computability.py
from ..system.pcs import PostCanonicalSystem


def create_fractran_primegame() -> PostCanonicalSystem:
    """Conway's PRIMEGAME, encoded as a Post system over prime-power symbols."""
    ...


def create_sk_reducer() -> PostCanonicalSystem:
    """SKI combinator beta-reduction as a Post canonical system."""
    ...


def create_collatz_machine() -> PostCanonicalSystem:
    """Collatz iteration over unary representation of n."""
    ...


def create_fibonacci_generator() -> PostCanonicalSystem: ...
def create_unary_primality_test() -> PostCanonicalSystem: ...
```

- **Implementation notes:** Each lives in `presets/computability.py`. SK requires careful bracket handling; using SINGLE-kind variables for atoms and ANY for the rest of the expression handles most cases, with auxiliary marker symbols for parsing.
- **Risk / scope creep:** SK is the trickiest - parenthesis matching in pure string rewriting is verbose. Ship a minimal SK that handles applicative redexes only; full lambda-calculus encoding is out of scope.
- **Effort:** M (a week) for all five.
- **Citations:**
  - "FRACTRAN." Esolang. http://www.esolangs.org/wiki/Fractran - Conway's definition and PRIMEGAME.
  - Lomont. "A Universal FRACTRAN Interpreter in FRACTRAN." 2017. https://lomont.org/posts/2017/fractran/ - encoding tricks and prime-flow-control patterns.
  - Raganwald. "Remembering John Conway's FRACTRAN." https://raganwald.com/2020/05/03/fractran.html - prime-factorization state encoding and Collatz connection.
  - Manning, Donaldson. "A Turing Machine For SKI Combinators." JFP 2016. https://www.macs.hw.ac.uk/~greg/temp/TM+SKI/MD-JFP-2016.pdf - direct combinator reduction as linear symbol-string rewriting; a near-perfect blueprint for an SK Post system.

---

### 9. Post Correspondence Problem (PCP) module

- **What it is:** A PCP instance is a finite list of pairs `(u_i, v_i)` over an alphabet; a solution is an index sequence `i_1 ... i_n` with `u_{i_1} ... u_{i_n} = v_{i_1} ... v_{i_n}`. Famous undecidable problem (Post 1946); decidable for size 2, undecidable for size >= 7. Trivially recast in this library: state = (top, bottom) pair; one rule per `(u_i, v_i)` that appends both halves; goal predicate is `top == bottom`.
- **Why it's worth shipping:** PCP is iconic in undecidability proofs and very visual (block-stacking metaphor). It is a non-trivially distinct application of the existing executor: states are pairs of strings, not single words. Adding it shows that the executor can model two-tape rewriting, not just single-tape, by encoding pairs as `top$bottom` with `$` as separator.
- **Sketched API:**

```python
# presets/pcp.py
from collections.abc import Iterator
from dataclasses import dataclass

from ..system.pcs import PostCanonicalSystem


@dataclass(frozen=True, slots=True)
class PCPInstance:
    pairs: tuple[tuple[str, str], ...]  # (top_i, bottom_i)
    alphabet_symbols: tuple[str, ...]

    def to_pcs(self) -> PostCanonicalSystem:
        """Encode as Post canonical system over alphabet plus separator '#'."""
        ...

    def search(self, max_length: int = 20) -> Iterator[tuple[int, ...]]:
        """Yield index sequences whose top and bottom strings match."""
        ...


def hard_pcp_size_3() -> PCPInstance: ...   # Known to require length-66 solution
def matiyasevich_undecidable_size_7() -> PCPInstance: ...
```

- **Implementation notes:** Encoding: state `top#bottom`, axiom `#`, one rule per pair appending `u_i` left of `#` and `v_i` right. Goal: any state of form `w#w`. The reachability check from extension #2 plus goal predicate hooks make this almost free.
- **Risk / scope creep:** "Goal predicate" as `lambda w: top_of(w) == bottom_of(w)` is not currently first-class in `ReachabilityQuery`, which only matches exact target strings. Adding a `predicate: Callable[[str], bool]` parameter to reachability is a small but real API change - call it out as part of this work.
- **Effort:** S (1-2 days).
- **Citations:**
  - "Post correspondence problem." Wikipedia. https://en.wikipedia.org/wiki/Post_correspondence_problem - definition, undecidability, block visualization.
  - Zhao, Hayes, Holte. "Welcome to the Post's Correspondence Problem!" UAlberta. http://webdocs.cs.ualberta.ca/~games/PCP/ - online PCP solver and instance database.
  - "PCP." Goodrich UCI lecture notes. https://ics.uci.edu/~goodrich/teach/cs162/notes/pcp.pdf - reduction proofs; useful for verifying our encoding.
  - "PCP Hard Instances." https://webdocs.cs.ualberta.ca/~games/PCP/paper/CG2002.pdf - 199 hard instances with optimal solutions of length >= 100, used as a benchmark suite.

---

### 10. Reachability-frontier and proof-DAG visualization

- **What it is:** Three new exporters: (a) **reachability frontier graph** - render the BFS exploration tree from axioms with depth and branching factor; (b) **proof DAG** - for derivations that share intermediate words across multi-antecedent rules, the existing tree-based DOT/Mermaid output duplicates nodes; render as a true DAG instead; (c) **Petri-net view** - one place per word in the reachable set, one transition per rule, edges representing antecedent-consumption / consequent-production. Petri nets are the canonical concurrency model for multi-input rewriting.
- **Why it's worth shipping:** Today `to_dot/to_mermaid` accept a single `Derivation`. There's no exporter for the full reachability set, and multi-antecedent derivations show as trees instead of DAGs. Petri-net export enables structural analysis (P-invariants, T-invariants) via off-the-shelf Petri tooling.
- **Sketched API:**

```python
# visualization.py (extend existing module)

def to_reachability_graph(
    system: PostCanonicalSystem, max_depth: int = 5, format: str = "dot"
) -> str: ...


def to_proof_dag(
    derived: DerivedWord, format: str = "mermaid"
) -> str:
    """Render derivation as a DAG, deduplicating shared subderivations."""
    ...


def to_petri_net(
    system: PostCanonicalSystem, words: frozenset[str], format: str = "pnml"
) -> str:
    """Render words as places, rules as transitions, in PNML for Snoopy/CPN Tools."""
    ...
```

- **Implementation notes:** Proof-DAG dedup: walk the derivation tree, hash-cons identical subderivations, emit each unique `(word, derivation)` pair once. Petri-net export targets PNML (Petri Net Markup Language), which Snoopy, GreatSPN, and CPN Tools all consume.
- **Risk / scope creep:** Full reachability graphs blow up fast; gate this exporter on a hard `max_words` like the existing `ReachabilityQuery`. PNML schema is verbose - link out to the spec, generate the minimal P/T-net flavor.
- **Effort:** M (a week).
- **Citations:**
  - Stehr, Meseguer, Olveczky. "Representation and Execution of Petri Nets Using Rewriting Logic as a Unifying Framework." 2001. https://www.sciencedirect.com/science/article/pii/S1571066104809496 - formal correspondence between Petri nets and rewriting systems; justifies the encoding.
  - Rawson, Rawson. "nt-petri-net." https://github.com/MarshallRawson/nt-petri-net - colored, non-deterministic Petri net implementation; pattern for a Python port.
  - "Qualitative Analysis of Signaling Networks Using Petri Nets and Invariant Computation." https://www.mdpi.com/2673-4117/7/5/202 - shows how P-invariants and T-invariants of Petri nets reveal conservation laws (parallels extension #7).

---

### 11. L-system / parallel-rewriting execution mode

- **What it is:** L-systems (Lindenmayer 1968) differ from Chomsky-style grammars by applying productions **in parallel** at every step: every symbol is rewritten simultaneously. D0L systems are deterministic context-free L-systems; stochastic and context-sensitive variants extend the framework. Parallel application is a different fixed-point semantics on top of the same `ProductionRule` structure already in this library.
- **Why it's worth shipping:** It's a one-flag generalization of the executor that opens up plant-modeling, fractal generation, and the "algorithmic beauty of plants" examples without touching the matching engine. Demonstrates that the library's data model is broader than its current execution semantics.
- **Sketched API:**

```python
# system/executor.py - extend existing enum
class ExecutionMode(Enum):
    DETERMINISTIC = auto()
    NON_DETERMINISTIC = auto()
    PARALLEL = auto()  # L-system style: rewrite every match simultaneously each step.


# presets/lsystems.py
def create_algae_lsystem() -> PostCanonicalSystem:
    """A -> AB, B -> A. Generates the Fibonacci word lengths."""
    ...


def create_koch_curve_lsystem() -> PostCanonicalSystem: ...
def create_dragon_curve_lsystem() -> PostCanonicalSystem: ...
```

- **Implementation notes:** PARALLEL mode partitions the input word into non-overlapping rule matches (use first-match-wins for determinism) and rewrites all in one step. Scope: only context-free L-systems (single-symbol antecedents); context-sensitive needs a different match algorithm.
- **Risk / scope creep:** "Non-overlapping" is ambiguous when rules overlap; pick leftmost-disjoint as the documented convention. Stochastic L-systems require a probability per rule, which the current `ProductionRule` doesn't have - leave stochastic variants to a separate, optional extension.
- **Effort:** S (1-2 days) for D0L; M for full bracketed turtle-graphics integration.
- **Citations:**
  - "L-system." Wikipedia. https://en.wikipedia.org/wiki/L-system - definition, deterministic vs. stochastic, context-free vs. context-sensitive.
  - "L-Systems." LPy documentation. https://lpy.readthedocs.io/en/latest/user/lsystems.html - formal Python implementation reference; useful for API conventions.
  - Reimer. "Generating a Garden with Python." https://mundyreimer.github.io/blog/lindenmayer-grammars-1 - bracketed L-systems and turtle interpretation in Python.

---

### 12. Equivalence-class pruning via canonicalization

- **What it is:** Many systems have symmetries that produce vast numbers of redundant words. Two examples: (a) **palindrome generator** treats `01` and `10` as different states even though both extend to size-2 palindromes via mirror-image rule applications; (b) **commutative subsystems** where multiple rules produce permutations of the same multiset. Canonicalization computes a canonical representative per equivalence class (e.g. lexicographic minimum under symbol permutation, or sorted-multiset form for commutative blocks) and prunes the BFS to one representative per class. Hashed equivalence-class membership can be checked in `O(|word|)` per state.
- **Why it's worth shipping:** Large speedups on symmetric systems with no math sleight of hand. Standard pruning technique in pattern-database AI search; relatively rare to see applied to Post systems specifically.
- **Sketched API:**

```python
# query/canonicalization.py
from collections.abc import Callable
from dataclasses import dataclass

type Canonicalizer = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class CanonicalReachabilityConfig:
    canonicalize: Canonicalizer
    max_words: int = 10_000


def lex_min_under_alphabet_permutation(symbols: tuple[str, ...]) -> Canonicalizer: ...
def sorted_subword_canonical(separator: str) -> Canonicalizer: ...


class CanonicalReachabilityQuery:
    def __init__(
        self,
        system: PostCanonicalSystem,
        canonicalizer: Canonicalizer,
    ) -> None: ...

    def is_derivable(self, target: str) -> ReachabilityResult: ...
```

- **Implementation notes:** This is a thin wrapper around `ReachabilityQuery.is_derivable` that hashes `canonicalize(word)` instead of `word` in the visited set. Document the soundness condition: the canonicalizer must commute with rule application (i.e. if `w -> w'` then `c(w) -> c(w')` modulo class), or be applied only at the visited-set level (safe but doesn't reduce branching).
- **Risk / scope creep:** Soundness is the trap. Naive canonicalization can lose reachable targets. The library's contribution should be (1) a few correct canonicalizers for the obvious cases, (2) clear docs on when it's safe to plug your own.
- **Effort:** S (1-2 days) for the framework; correctness proofs for individual canonicalizers are case-by-case.
- **Citations:**
  - Korf. "Recent Progress in the Design and Analysis of Admissible Heuristic Functions." https://cdn.aaai.org/AAAI/2000/AAAI00-212.pdf - pattern databases as a form of equivalence-class abstraction.
  - Chen, Tian. "Learning to Perform Local Rewriting for Combinatorial Optimization." https://arxiv.org/pdf/1810.00337 - region-picking and rule-picking under rewriting; canonicalization-style reasoning is implicit.
  - Beam Search overview. Wikipedia. https://en.wikipedia.org/wiki/Beam_search - related pruning strategies and complete-search variants like BULB.

---

## Theoretical backdrop (under 500 words)

Three results anchor everything above.

**Post's Normal-Form Theorem (Post 1943).** Every Post canonical system is reducible to a normal-form system with one axiom and productions of shape `gP -> Pg'`. This is the central reason the executor's data model is enough to host tag systems, Markov algorithms, and string rewriting systems as front-ends - they are all special cases. The proof proceeds in four reductions: collapse multiple axioms, reduce multi-premise to single-premise, reduce multi-variable to single-variable, and rotate the variable to the right of the antecedent (sources: https://en.wikipedia.org/wiki/Post_canonical_system, https://encyclopediaofmath.org/wiki/Post_canonical_system, https://www.ivanociardelli.altervista.org/wp-content/uploads/2018/04/Minsky-Ch-13.pdf).

**Universality of 2-Tag Systems (Cocke and Minsky 1964).** Any Turing machine can be simulated by a 2-tag system with deletion number `m = 2` (https://dl.acm.org/doi/10.1145/321203.321206). Tag systems are themselves a restricted form of Post canonical system. This grounds Extension #3 (tag system front-end) in textbook computability theory and gives a direct route from arbitrary Turing computation to runs of this library. Cook's later proof of universality of cyclic tag systems (https://content.wolfram.com/sites/13/2018/02/15-1-1.pdf) - which underlies the universality of Rule 110 - extends this further, with simulation overhead improved to polynomial by Neary and Woods (https://gwern.net/doc/cs/computable/2008-neary.pdf).

**Undecidability of the Word Problem (Novikov 1955, Boone 1958) and PCP (Post 1946).** Reachability in general Post canonical systems is undecidable; even the Post correspondence problem (a degenerate two-tape variant) is undecidable for instance size >= 7 (https://en.wikipedia.org/wiki/Post_correspondence_problem). This sets the boundary for everything in cluster B and C: the library can never give a complete decision procedure for arbitrary systems, only sound semi-decision procedures that succeed on classes characterized by termination certificates, invariants, or bounded search.

The interplay matters: Knuth-Bendix completion (https://en.wikipedia.org/wiki/Knuth-Bendix_completion_algorithm) is also a semi-decision procedure - it terminates with a confluent system when the input has one, runs forever otherwise. This is why Extension #5 ships critical-pair detection without insisting on full completion: partial information is decidable and useful, even when the full procedure cannot be guaranteed to halt.

Parikh's Theorem (https://arxiv.org/pdf/2210.02925) provides a smaller, decidable wedge: the Parikh image of any context-free language is semilinear, hence Presburger-definable. For Post systems whose rules have constant Parikh delta vectors, linear invariants are computable from a small Hermite-normal-form calculation - the basis for Extension #7 - and prove unreachability for any target violating the discovered conservation laws (the MU puzzle's I-count-mod-3 invariant being the canonical example).

Together these results explain both what is possible and why it has to be incomplete: every analysis tool in cluster B/C is a sound-but-incomplete refinement bumping against undecidability.

## Recommended phasing

**Phase 1 (highest value-to-effort).**

1. **Bidirectional BFS reachability** (Extension #1) - immediate wins on existing examples; small, well-scoped.
2. **Termination heuristics** (Extension #6) - unlocks "this system halts" certificates; a few hours of work for the length-reducing case.
3. **L-system / parallel mode** (Extension #11) - a one-flag generalization that opens up an entire class of users.

**Phase 2 (formal-methods angle).**

4. **Automatic invariant discovery** (Extension #7) - the MU-puzzle "aha" moment, automated. High pedagogical value.
5. **Critical-pair analyzer** (Extension #5, analysis-only flavor) - mechanical confluence inspection; defer full Knuth-Bendix.
6. **Reachability/proof-DAG/Petri visualizers** (Extension #10) - extends the existing exporters; small surface-area changes.

**Phase 3 (computability museum).**

7. **Tag and cyclic tag systems** (Extension #3) - bridges to small-universal-Turing-machine literature.
8. **Markov algorithm front-end** (Extension #4) - deterministic counterpart; pairs naturally with #3.
9. **FRACTRAN/SK/Collatz preset pack** (Extension #8) - concrete demos of universality.

**Phase 4 (advanced search and curiosities).**

10. **A* / IDA* heuristic search** (Extension #2) - benefit appears mostly on deep proofs and FRACTRAN-style systems from #8, so sequence after them.
11. **PCP module** (Extension #9) - small but requires goal-predicate API; do once #1 has motivated that change.
12. **Equivalence-class pruning** (Extension #12) - powerful but needs case-by-case soundness proofs; ship last with conservative defaults.
