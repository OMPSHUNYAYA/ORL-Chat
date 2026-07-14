# 🧩 ORL-Chat Model and Invariant Sketch

**Deterministic Bounded Conversation-State Resolution**

This document describes the current ORL-Chat resolver model and states the invariants demonstrated by the committed reference scenario.

It is a model and invariant sketch, not a universal proof of conversational meaning, distributed convergence, security, or production correctness.

The governing relation is:

`same deduplicated supported message fragments + same resolver rules -> same bounded conversation-state result`

ORL-Chat is developed within the Shunyaya Framework.

---

# 1. Scope

ORL-Chat resolves a bounded conversation state from:

- supported message fragments
- declared message kinds
- explicit target relationships
- deterministic resolver rules

The current model does not perform unrestricted natural-language understanding.

In this document, “meaning” refers only to the declared value selected by the supported relationship graph and resolver rules.

For the committed scenario:

`resolved declared value = Meeting at 5 PM`

This does not establish:

- factual truth
- hidden intent
- speaker identity
- legal agreement
- social meaning
- authorization
- real-world acceptance

The more precise technical term is:

`bounded resolved conversation state`

---

# 2. Basic Objects

Let:

- `M` be a finite collection of supported message fragments
- `D(M)` be exact-duplicate absorption
- `T` be a topic identifier
- `R_v` be the deterministic resolver under ruleset version `v`
- `R_v(M,T)` be the bounded resolver result for topic `T`
- `P(M)` be a permutation of the same fragment collection
- `U(A,B)` be the current bounded sharing operation between fragment collections `A` and `B`

A supported fragment contains fields such as:

```text
id
topic
kind
text
value
targets
```

The current implementation supports four declared kinds:

```text
OPEN
REPLACE
RETRACT
CONFIRM
```

A formal versioned schema is not yet part of the implementation.

---

# 3. Exact-Duplicate Absorption

The current duplicate key is:

`(id, topic, kind, text, value, targets)`

The implementation retains one copy of each exact key.

Therefore, exact-duplicate absorption is idempotent:

`D(D(M)) = D(M)`

For the current resolver:

`R_v(M,T) = R_v(D(M),T)`

when the only difference is repetition of exactly identical supported fragments.

This establishes exact-duplicate absorption within the current model.

It does not establish:

- general replay protection
- transport-level idempotency
- sender authentication
- nonce validation
- message authenticity
- safe handling of conflicting reuse of the same identifier

The current implementation does not reject every case in which one message identifier is reused with different content.

---

# 4. Bounded Sharing Operation

The current sharing operation is implemented conceptually as:

`U(A,B) = D(A + B)`

where `+` denotes collection concatenation before exact-duplicate absorption.

For exact supported fragments:

`D(A + B) = D(B + A)`

Therefore, at the level of exact deduplicated fragment content:

`U(A,B) = U(B,A)`

The operation is also idempotent:

`U(A,A) = D(A)`

and, for already deduplicated collections:

`U(A,A) = A`

These properties concern fragment-set construction only.

They do not prove:

- network delivery
- eventual delivery
- reliable broadcast
- consensus
- synchronization
- fault tolerance
- distributed finality

The committed demonstration uses a scripted sharing step.

---

# 5. Supported Relationship Rules

## 5.1 OPEN

An `OPEN` fragment introduces a proposal.

The current resolver treats it as valid when:

- it has no targets
- it contains a non-null value

Conceptually:

`valid_OPEN(m) iff targets(m) = empty AND value(m) != null`

---

## 5.2 REPLACE

A `REPLACE` fragment supersedes its valid targets and introduces a replacement proposal.

The current resolver requires:

- at least one target
- every target to be present in the same topic
- every target to be structurally valid
- a non-null replacement value

Conceptually:

`valid_REPLACE(m) iff targets_present AND targets_valid AND value(m) != null`

---

## 5.3 RETRACT

A `RETRACT` fragment removes its valid targeted proposal from the active set.

The current resolver requires:

- at least one target
- every target to be present
- every target to be structurally valid

Conceptually:

`valid_RETRACT(m) iff targets_present AND targets_valid`

---

## 5.4 CONFIRM

A `CONFIRM` fragment confirms a valid targeted proposal when that proposal remains active.

The current resolver requires:

- at least one target
- every target to be present
- every target to be structurally valid

Conceptually:

`valid_CONFIRM(m) iff targets_present AND targets_valid`

A structurally valid confirmation does not prove identity, authority, agreement, or truth outside the model.

---

# 6. Dependency Validity

The resolver recursively evaluates dependencies.

A supported fragment may be marked invalid for reasons including:

```text
cyclic_dependency
invalid_open
missing_targets
missing_dependency
dependency_not_satisfied
missing_value
unknown_kind
```

A dependency cycle is rejected within the evaluated path.

Conceptually:

`dependency_cycle -> invalid fragment`

A missing target produces an invalid dependent fragment:

`missing target -> missing_dependency`

This is bounded dependency validation.

It is not a complete hostile-input validation system.

Malformed required fields may still cause execution errors.

---

# 7. Deterministic Processing Order

The resolver computes a dependency depth for each message identifier and processes identifiers using:

`(dependency_depth, message_id)`

as the deterministic ordering key.

This means the resolver does not preserve input arrival position as processing authority.

For valid supported inputs, equal deduplicated fragment content produces equal:

- dependency relationships
- depth values
- identifier ordering
- active-proposal transitions
- topic-state output

Therefore:

`D(M_i) = D(M_j) -> R_v(M_i,T) = R_v(M_j,T)`

provided both executions use the same implementation and resolver rules.

---

# 8. Active-Proposal Model

For each topic, the resolver maintains an active proposal collection.

The current transitions are:

```text
OPEN    -> add proposal
REPLACE -> remove targets, add replacement
RETRACT -> remove targets
CONFIRM -> mark an active target as confirmed
```

After valid replacements and retractions are processed, superseded proposals are removed from the active set.

The final classification depends on:

- active proposal identifiers
- confirmed active proposal identifiers
- invalid fragment identifiers

---

# 9. Resolution States

## 9.1 RESOLVED

The current resolver returns `RESOLVED` when exactly one confirmed proposal remains active.

`count(confirmed_active_proposals) = 1 -> RESOLVED`

Under the current branch order, this condition takes precedence even if additional unconfirmed active proposals remain.

The result includes:

- final message identifier
- final text
- final declared value
- active identifiers
- confirmed identifiers
- invalid identifiers

`RESOLVED` means the current resolver conditions were satisfied.

It does not mean that the declared value is factually true or externally authorized.

---

## 9.2 ABSTAIN

The current resolver returns `ABSTAIN` when multiple confirmed active proposals remain:

`count(confirmed_active_proposals) > 1 -> ABSTAIN`

It also returns `ABSTAIN` when no active proposal is confirmed and multiple active proposals remain:

`count(confirmed_active_proposals) = 0 AND count(active_proposals) > 1 -> ABSTAIN`

Under the current branch order, multiple active proposals do not produce `ABSTAIN` when exactly one of them is confirmed. That case is classified as `RESOLVED`.

These conditions preserve the conflicts recognized by the current resolver rather than silently selecting one branch.

They do not repair, negotiate, or adjudicate the conflict.

---

## 9.3 INCOMPLETE

The current resolver returns `INCOMPLETE` when, for example:

```text
one active proposal lacks confirmation
required dependencies are missing
no proposal can be resolved
```

Conceptually:

`missing required relationship -> INCOMPLETE`

The resolver does not invent missing fragments or missing relationships.

---

# 10. Same-Evidence Node Equality

Let two nodes hold fragment collections `M_A` and `M_B`.

If:

`D(M_A) = D(M_B)`

and both apply the same resolver ruleset `v`, then:

`R_v(M_A,T) = R_v(M_B,T)`

This is the central current-model equality condition.

It can also be written as:

`same deduplicated supported evidence + same rules -> same bounded result`

This is deterministic same-evidence equality.

It is not:

- consensus
- quorum agreement
- voting
- reliable broadcast
- Byzantine agreement
- immutable finality

ORL-Chat does not claim equality while nodes permanently hold materially different evidence.

---

# 11. Committed Two-Node Scenario

The supplied scenario contains five structurally related messages:

```text
M1 = opening proposal
M2 = replacement proposal
M3 = retraction
M4 = final replacement
M5 = confirmation
```

Initial node views:

```text
Node-A = M1, M2
Node-B = M3, M4, M5
```

Expected local states before sharing:

```text
R_v(Node-A) = INCOMPLETE
R_v(Node-B) = INCOMPLETE
```

After the scripted bounded sharing step:

```text
Node-A' = U(Node-A, Node-B)
Node-B' = U(Node-B, Node-A)
```

Because:

`D(Node-A') = D(Node-B')`

the deterministic resolver is expected to produce:

`R_v(Node-A') = R_v(Node-B')`

For the committed scenario:

```text
State       = RESOLVED
Final Value = Meeting at 5 PM
```

Expected equality result:

```text
converged_after_merge = True
```

The word “converged” here means equal resolver output after equal evidence is installed.

It does not prove an autonomous distributed convergence protocol.

---

# 12. Arrival-Permutation Invariant

Let `P(M)` be any permutation of the same five unique committed fragments.

The intended current-model invariant is:

`R_v(P(M),T) = R_v(M,T)`

The Python reference implementation exhaustively checks:

`5! = 120`

permutations.

Expected result:

```text
checked_permutations     = 120
permutation_independence = True
```

Therefore, for the supplied five-message scenario under the current Python implementation:

`for every tested P(M): R_v(P(M),T) = R_v(M,T)`

This is an exhaustive scenario result.

It is not a universal proof for:

- arbitrary numbers of messages
- arbitrary message schemas
- arbitrary relationship graphs
- malformed inputs
- hostile inputs
- different resolver implementations

Exhaustive permutation testing grows factorially and does not scale by itself.

---

# 13. Time-Authority Boundary

The committed resolver does not inspect timestamps or wall-clock values when classifying the supplied scenario.

Therefore, for the current implementation:

`timestamp data is not part of the classification function`

More precisely:

`R_v(M,T)` is computed from supported fragment content and declared relationships, not from a temporal ordering field.

This supports the bounded claim:

> Timestamps are not resolution authority in the supplied model.

It does not prove that time is unnecessary for all communication systems.

Time may remain important for:

- deadlines
- expiration
- legal records
- causality policies
- monitoring
- operations
- display

---

# 14. Synchronization Boundary

The supplied scenario does not require synchronized clocks or simultaneous delivery.

However, both nodes produce equal outputs only after they receive equal deduplicated supported evidence.

Therefore, the precise condition is:

`equal installed evidence + equal rules -> equal bounded result`

The model does not supply or prove:

- clock synchronization
- transport synchronization
- message delivery
- eventual delivery
- network convergence
- consensus

The phrase “no synchronization required” must be interpreted narrowly as:

> The resolver calculation does not require synchronized clocks once the same supported evidence is available.

---

# 15. Repeatability

For unchanged supported inputs and unchanged resolver implementation:

`R_v(M,T)` is deterministic.

Therefore:

`R_v(M,T) on run 1 = R_v(M,T) on run 2`

The Python implementation contains no probabilistic choice in the resolver path.

This supports repeatability of:

- topic states
- active identifiers
- confirmed identifiers
- final declared value
- bounded result signatures

This is implementation repeatability.

It is not universal cross-platform or cross-language conformance.

---

# 16. Canonical Result Serialization and Hashing

The Python implementation serializes result objects using JSON with:

```text
sort_keys = True
separators = (",", ":")
UTF-8 encoding
```

Conceptually:

`canonical_result_bytes = UTF8(canonical_json(result))`

The SHA-256 relation is:

`result_hash = SHA256(canonical_result_bytes)`

Therefore:

`same canonical result bytes -> same SHA-256 hash`

The implementation also supports optional sorted, human-readable JSON output.

The generated hash provides deterministic identity for the current result object.

It does not independently prove:

- behavioral correctness
- semantic truth
- message authenticity
- schema conformance
- independent reconstruction
- security
- production safety

The current “certificate” is not yet a formal schema-bound, ruleset-bound, independently reconstructed certificate.

---

# 17. Incomplete and Conflict Preservation

The current model avoids forced resolution in two declared conditions.

## Incomplete preservation

`INCOMPLETE -> no final declared value is forced by the resolver`

## Conflict preservation

`ABSTAIN -> no single conflicting active proposal is silently selected`

These properties reduce forced selection within the bounded model.

They do not establish universal semantic or conversational safety.

---

# 18. Evidence Growth Is Not Monotonic Resolution

The current resolver output is not guaranteed to move only toward `RESOLVED`.

New evidence can change the active relationship graph.

Possible transitions include:

```text
INCOMPLETE -> RESOLVED
INCOMPLETE -> ABSTAIN
RESOLVED   -> ABSTAIN
RESOLVED   -> another bounded state
```

Therefore, the following universal claim is not valid:

`more evidence -> permanently preserved resolution`

The current model does not define immutable finality or structural closure.

A future closure layer would need separate rules for when a result can no longer be changed by admissible evidence.

---

# 19. No Universal Conservative-Extension Claim

The current implementation does not prove:

`human interpretation = ORL-Chat result`

for every valid conversation.

It shows only that the supplied declared correction chain produces a bounded result under the current explicit rules.

The resolver result may be consistent with an ordinary reading of the scenario, but this is not a formal equivalence theorem for natural language.

---

# 20. Browser Demonstration Boundary

The browser demonstration visually presents:

- scrambled arrival views
- two incomplete local fragment collections
- scripted sharing
- the correction and confirmation chain
- the expected final result

The browser currently does not independently:

- execute the full Python resolver
- enumerate all `120` permutations
- reconstruct the Python result hash
- establish Python-browser conformance

Therefore, browser labels such as:

```text
Permutation tested: 120
Proof verified: TRUE
```

must be interpreted as a visual replay of the Python reference result.

They are not independently computed browser proofs.

---

# 21. What the Implementation Contains and the Scenario Establishes

## Implemented resolver capabilities

The current Python reference implementation contains:

- exact-duplicate absorption
- explicit dependency validation
- cycle detection
- deterministic relationship processing
- `RESOLVED`, `INCOMPLETE`, and `ABSTAIN` classification paths
- canonical result serialization
- deterministic SHA-256 result hashing

The presence of these code paths does not mean that every capability is exercised by the committed five-message scenario.

## Results established by the committed scenario

For the committed supported five-message scenario, execution demonstrates:

- different initial node views
- `INCOMPLETE` at both nodes before sharing
- equal deduplicated evidence after scripted sharing
- same-evidence node equality after sharing
- a final `RESOLVED` state
- the final declared value `Meeting at 5 PM`
- exhaustive invariance across all `120` fragment permutations
- repeatable canonical result hashing
- local execution without timestamp or wall-clock classification authority

These are bounded scenario and implementation results.

---

# 22. What This Sketch Does Not Prove

This document does not prove:

- unrestricted natural-language understanding
- universal meaning resolution
- factual truth
- speaker identity
- message authenticity
- authorization
- encryption
- access control
- delivery guarantees
- consensus
- Byzantine fault tolerance
- reliable broadcast
- immutable finality
- conflict repair
- complete replay prevention
- complete malformed-input refusal
- universal order independence
- universal time independence
- Python-browser conformance
- production readiness
- safe behavior on arbitrary or hostile inputs

---

# 23. Current Technical Gaps

Important current gaps include:

- no formal versioned input schema
- incomplete explicit invalid-input refusal
- malformed required fields may cause exceptions
- conflicting reuse of a message identifier is not safely rejected in every case
- some status flags are declared rather than independently reconstructed
- exhaustive permutation checking scales factorially
- no canonical byte-level message serialization specification
- no independent receipt reconstruction
- no shared Python-browser conformance suite
- no structural-closure or immutable-finality layer

---

# 24. Future Proof Obligations

A stronger release should define and test:

## 24.1 Schema validity

`valid_schema(message) = True OR explicit_refusal`

## 24.2 Identifier consistency

`same message id + different canonical content -> explicit conflict refusal`

## 24.3 Canonical serialization

`same validated message object -> same canonical bytes`

## 24.4 Ruleset binding

`resolver result` and any receipt should bind:

```text
schema_version
ruleset_version
canonical fragment root
topic
resolution state
final declared value
```

## 24.5 Cross-language conformance

`Python result = browser result`

for a shared committed vector corpus.

## 24.6 Metamorphic invariants

Examples:

```text
exact duplicate insertion does not change result
supported permutation does not change result
invalid dependency produces explicit refusal or documented state
identifier conflict is never silently overwritten
```

## 24.7 Independent reconstruction

A verifier should be able to reconstruct the result and receipt without trusting the producer’s claimed output.

## 24.8 Structural closure

A future closure model should distinguish:

```text
resolution_state = RESOLVED | INCOMPLETE | ABSTAIN
closure_state    = OPEN | SEALED
```

and define when admissible later evidence may or may not alter a resolved state.

This closure model is not part of the current implementation.

---

# 25. Future Target Relation

The stronger future target is:

`same validated canonical message fragments + same ruleset version -> same independently verified bounded conversation-state result`

This requires:

- formal schemas
- explicit refusal
- canonical bytes
- ruleset versioning
- shared conformance vectors
- independent reconstruction
- receipt verification

The current release does not yet satisfy this stronger target.

---

# 26. Summary of Current Invariants

Within the current model and Python implementation, with the node-equality and permutation results specifically confirmed by the committed scenario:

## Exact duplicate absorption

`D(D(M)) = D(M)`

## Same-evidence equality

`D(M_A) = D(M_B) -> R_v(M_A,T) = R_v(M_B,T)`

## Supplied-scenario permutation invariance

`for all 120 tested P(M): R_v(P(M),T) = R_v(M,T)`

## Repeatability

`same supported input + same implementation -> same bounded result`

## Result-hash identity

`same canonical result bytes -> same SHA-256 hash`

## Incomplete preservation

`INCOMPLETE -> no final declared value forced`

## Conflict preservation

`ABSTAIN -> no conflicting active proposal silently selected`

Each statement is bounded by the current supported schema assumptions, implementation behavior, and committed scenario.

---

# ⭐ Final Statement

ORL-Chat is a deterministic bounded conversation-state resolver over explicit message relationships.

For the committed scenario:

`same deduplicated supported message fragments + same resolver rules -> same bounded conversation-state result`

The Python implementation exhaustively confirms that result across all `120` permutations of the supplied five-message fragment collection.

This establishes a bounded structure-governed resolution result.

It does not establish universal conversational meaning, truth, consensus, delivery, security, finality, or production correctness.
