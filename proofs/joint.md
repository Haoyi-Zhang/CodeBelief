# Joint code-and-change contradiction certificates: complete arguments

## 1. Model

Let `O` be a finite set of selectable **origins**.  An origin is a code span, an
explicit change record, or an explicit bridge assumption; every origin `o` has
a non-negative integer cost `w(o)`.  A base fact is a pair `(l,A)` consisting of
a ground literal `l` and a finite support `A subseteq O`.  A finite positive
Horn rule has the form

```
l_1 and ... and l_k -> h.
```

Strong negation is syntactic: `not:p` is a ground literal distinct from `p`.
There is no negation-as-failure.  Rules are fixed analyzer semantics and do not
become selectable evidence.  For a selection `S subseteq O`, exactly those base
facts whose support is contained in `S` are enabled.  Forward closure then
applies the fixed rules.  A selection is a contradiction certificate for target
`p` when its closure contains both `p` and `not:p`.  Its cost is
`sum_{o in S} w(o)`.

A proof support for a literal is the union of the supports of the base facts at
its leaves.  A support is inclusion-minimal when no strict subset is also a
support for the same literal.  The optimization objective is the cost of the
**union** of one proof support for `p` and one for `not:p`.  Shared code and
history evidence is therefore paid for once.

## 2. Antichain propagation

For each literal `l`, maintain an antichain `F(l)` of supports.  Initially,
insert every base support for `l`, discarding a support if an existing support
is its subset and deleting existing strict supersets when a smaller support is
inserted.  For each Horn rule, take every Cartesian product of one current
support per body literal, union the selected supports, and insert the union into
the head frontier using the same subset pruning.  Repeat to a fixed point.
Backpointers record the fact or rule and the premise proofs that produced every
retained support.

### Theorem 1 (termination)

Antichain propagation terminates on every finite input.

**Proof.**  Every retained object is a subset of the finite origin set `O`.
For each literal there are at most `2^|O|` distinct supports.  An insertion
adds a previously absent support and may remove supersets; it never creates a
new origin or a support outside the finite powerset.  There are finitely many
literals appearing in facts or rules.  Consequently only finitely many
successful insertions can occur, after which a complete pass changes no
frontier and the algorithm stops.  The implementation additionally has a
frontier cap that converts an unexpectedly large finite instance into an
explicit resource error; the cap is not used in this mathematical argument.

### Theorem 2 (soundness)

Every support retained in `F(l)` enables a Horn derivation of `l`.

**Proof.**  Induct on the backpointer tree.  A leaf support is attached to a
base fact `(l,A)`, so selecting `A` enables `l` by definition.  For an internal
node produced by `l_1 and ... and l_k -> h`, the induction hypothesis says each
premise support enables its premise.  Selecting their union enables every
premise simultaneously, so the Horn rule derives `h`.  Subset pruning only
removes supports; it never changes the proof attached to a retained support.

### Theorem 3 (completeness for inclusion-minimal supports)

At the fixed point, `F(l)` contains every inclusion-minimal proof support for
every derivable literal `l`.

**Proof.**  Let `A` be an inclusion-minimal support of a proof of `l`, and
induct on the height of a minimum-height proof with support `A`.  If the proof
is a base fact, its support is inserted initially.  It cannot be discarded by
a strict subset support without contradicting the minimality of `A`; an equal
support leaves an equivalent retained proof.

Otherwise the final inference is a rule with premise proofs having supports
`A_1,...,A_k` and union `A`.  Replace each premise proof, if necessary, by an
inclusion-minimal premise support `B_i subseteq A_i`.  By induction, each
`B_i` appears in its premise frontier.  A propagation pass therefore considers
`B = union_i B_i` for the rule head.  We have `B subseteq A`.  If `B` were a
strict subset, it would derive `l`, contradicting the inclusion-minimality of
`A`; hence `B=A`.  The insertion either retains `A` or finds an existing subset
support.  The latter must again equal `A`.  Thus `A` is present at the fixed
point.

### Corollary 4 (exact joint optimum)

Enumerating every pair in `F(p) x F(not:p)` and choosing a minimum-cost union
returns a globally minimum contradiction certificate.

**Proof.**  By Theorem 2 every enumerated pair is feasible.  Consider an
optimal certificate and choose one proof of each target under it.  Each proof
contains an inclusion-minimal sub-support for its target.  By Theorem 3 both
sub-supports occur in the corresponding frontiers, and their union is a subset
of the optimal certificate.  Non-negative costs imply that this enumerated
union costs no more than the optimum; feasibility implies it cannot cost less
than the optimum.  Hence the selected pair is optimal.

## 3. Computational boundary

### Theorem 5 (NP-completeness)

The decision problem “does a joint contradiction certificate of cost at most
`B` exist?” is NP-complete, even with unit origin costs, an acyclic positive
Horn program, and one side of the contradiction supplied by a single base
fact.  The result continues to hold when rule bodies are restricted to at most
two literals.

**Proof.**  Membership in NP follows because a selected origin set and two Horn
derivations can be checked in polynomial time; equivalently, forward closure
is polynomial in the finite program size.

For hardness, reduce SET COVER.  Given universe `E={e_1,...,e_m}`, sets
`S_1,...,S_n`, and bound `k`, create one unit-cost origin `x_j` and base fact
`chosen_j` supported by `{x_j}` for every set.  For every membership
`e_i in S_j`, add `chosen_j -> covered_i`.  Add a rule
`covered_1 and ... and covered_m -> p`.  Finally create one unit-cost origin
`z` and base fact `not:p` supported by `{z}`.  A contradiction certificate of
cost at most `k+1` must contain `z`; its remaining origins derive `p` exactly
when the corresponding sets cover every element.  Thus such a certificate
exists iff the SET COVER instance has a cover of size at most `k`.

The long conjunction can be replaced by an acyclic binary conjunction tree.
For example, rules combine `covered_1` and `covered_2` into an auxiliary fact,
then combine auxiliaries until deriving `p`.  These rules introduce no origins
and preserve the selected-set correspondence, while every body has size at
most two.  The construction is polynomial.

This theorem concerns the general finite provenance language.  It does not
make the earlier two-support threshold fragment hard; that fragment has the
singleton/pair closed form proved in `selection.md`.

## 4. Baselines and tight guarantees

### Theorem 6 (independent-side two-approximation)

Let `A` be a minimum-cost support for `p` and `B` a minimum-cost support for
`not:p`, chosen independently.  Then `w(A union B) <= 2 OPT`, where `OPT` is
the minimum joint-union cost.

**Proof.**  Let `A*` and `B*` be the two proof supports used by an optimal joint
certificate `U*=A* union B*`.  Individual optimality gives
`w(A)<=w(A*)<=w(U*)` and `w(B)<=w(B*)<=w(U*)`, because costs are non-negative.
Therefore

```
w(A union B) <= w(A)+w(B) <= 2 w(U*) = 2 OPT.
```

### Theorem 7 (the factor two is tight)

For every `k>=2`, there is a unit-cost instance on which independent-side
selection costs `2k`, while the joint optimum costs `k+1`.

**Proof.**  Give `p` a private support `A` of size `k` and a shared support `S`
of size `k+1`.  Give `not:p` a disjoint private support `B` of size `k` and the
same shared support `S`.  The independent minimum for each side is its private
support, so the union is `A union B` of size `2k`.  Joint selection uses `S`
for both sides and costs `k+1`.  No smaller support exists by construction.
The ratio `2k/(k+1)` tends to two.  `make_tight_two_approx` constructs exactly
this family, and the retained finite checks cover `k` through 128.

### Theorem 8 (deletion is inclusion-minimal but can be arbitrarily bad)

For the fixed Horn selection predicate, repeated successful single-origin
deletion returns an inclusion-minimal certificate.  Nevertheless, its cost
ratio to a minimum certificate is unbounded, even with unit costs.

**Proof.**  The predicate is upward closed: adding origins can only enable more
base facts and positive-Horn consequences.  Suppose the deletion procedure
stops at `S` but a proper subset `T subset S` is contradictory.  Choose
`x in S\T`.  Because `T subseteq S\{x}` and the predicate is upward closed,
`S\{x}` is contradictory, contradicting termination.  Hence the output is
inclusion-minimal.

For the gap, use origins `y,x_1,...,x_n`.  Both `p` and `not:p` have a proof
supported by `{y}` and another proof supported by `{x_1,...,x_n}`.  Start from
all origins and test `y` first.  It can be deleted because the long proof
remains.  No `x_i` can then be deleted, so the result has cost `n`, is
inclusion-minimal, and the optimum `{y}` costs one.  The ratio is `n`.
`make_deletion_gap` checks this family through `n=128`.

## 5. Version identity and source anchors

A source anchor is replayable only when its retained text occurs exactly once
in the declared snapshot excerpt.  A change origin names two tagged snapshots
and two distinct anchors; the independent replay checks both.  A bridge origin
is not inferred from equal spelling.  It records an explicit assumption that
two snapshot-local entities denote one evolving entity.  Removing that bridge
leaves version-indexed facts and is a negative control, not a failed detector.

The public-host configurations are seeded logic graphs around exact tagged
source excerpts.  The cJSON excerpt adds a `valuestring == NULL` guard, the
inih excerpt adds explicit consumption of an overlong input line, and the
mjson excerpt changes an integer-digit loop guard from the remaining value to
the place multiplier.  These syntactic changes are real retained inputs.  The
opposing policy literals and alternative proof structures are controlled
seeds.  Therefore the experiment validates extraction, provenance sharing,
optimization, and replay; it does not estimate real defect prevalence or
claim that every source change is a bug.

## 6. Relationship to the re-mined threshold counterexample

The fixed Horn predicate in this file is monotone in selected origins.  The
older re-mined threshold predicate in `selection.md` is different because
removing observations changes the denominator and therefore changes the
inference rule itself.  In that model a set can be 1-minimal yet contain a
valid non-immediate subset, and the local/global ratio is unbounded.  The same
model also collapses globally to a shared singleton, an opposite pair at
threshold at most one half, or no witness.  The completed project retains that
negative result as a warning against minimizing a moving predicate; it is not
used as evidence for the NP-hardness result above.
