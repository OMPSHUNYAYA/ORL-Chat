# ⭐ ORL-Chat — Quickstart

**Deterministic Bounded Conversation-State Resolution**

ORL-Chat is a public deterministic reference model for resolving a bounded conversation state from supported message fragments and explicit relationships.

The governing relation is:

`same deduplicated supported message fragments + same resolver rules -> same bounded conversation-state result`

ORL-Chat is developed within the Shunyaya Framework.

---

# 1. Fastest Visual Walkthrough

Open:

`demo/orl_chat_interactive_demo.html`

Use:

- **Scramble Arrival**
- **Resolve Structure**
- **Replay Proof**

The browser presents the committed scenario visually.

Expected displayed result:

```text
State       = RESOLVED
Final Value = Meeting at 5 PM
```

The **Replay Proof** button is a scripted visual replay of the Python reference result.

The browser does not independently execute the full Python resolver or enumerate all `120` permutations.

---

# 2. Run the Python Reference Implementation

From the repository root, run:

```text
python demo/orl_chat_demo.py
```

On Windows, this may also be:

```text
py demo/orl_chat_demo.py
```

To write the result JSON:

```text
python demo/orl_chat_demo.py --write-output
```

Expected output file:

`outputs/orl_chat_result_general_chat_correction.json`

---

# 3. Expected Primary Result

Expected scenario:

```text
general_chat_correction
```

Expected message count:

```text
5
```

Expected node count:

```text
2
```

Expected final state:

```text
RESOLVED
```

Expected final message identifier:

```text
M4
```

Expected final declared value:

```text
Meeting at 5 PM
```

Expected node equality after sharing:

```text
converged_after_merge = True
```

---

# 4. Expected Pre-Merge State

The committed scenario begins with different local fragment collections:

```text
Node-A = M1, M2
Node-B = M3, M4, M5
```

Expected local states:

```text
Node-A = INCOMPLETE
Node-B = INCOMPLETE
```

Expected equality before sharing:

```text
converged_before_merge = False
```

The nodes do not initially hold the same evidence.

---

# 5. Expected Post-Merge State

The demonstration applies a scripted bounded sharing step:

`U(A,B) = D(A + B)`

where:

- `A` is Node-A's fragment collection
- `B` is Node-B's fragment collection
- `D` performs exact-duplicate absorption

After sharing, both nodes hold the same deduplicated supported fragment set.

Expected result:

```text
State       = RESOLVED
Final Value = Meeting at 5 PM
```

Expected equality:

```text
converged_after_merge = True
```

This is same-evidence node equality.

It is not consensus, reliable broadcast, delivery assurance, or distributed finality.

---

# 6. Expected Permutation Result

The Python implementation checks all permutations of the five unique committed fragments.

`5! = 120`

Expected result:

```text
checked_permutations     = 120
permutation_independence = True
```

This is an exhaustive result for the committed five-message scenario under the current Python implementation.

It is not a universal proof for arbitrary conversations, schemas, graphs, or implementations.

---

# 7. Current Message Model

The committed scenario uses message records with fields such as:

```text
id
topic
kind
text
value
targets
```

The current resolver supports:

```text
OPEN
REPLACE
RETRACT
CONFIRM
```

A formal versioned input schema is a future technical target.

---

# 8. Message Roles in the Committed Scenario

The committed five-message chain is:

```text
M1 = OPEN
M2 = REPLACE
M3 = RETRACT
M4 = REPLACE
M5 = CONFIRM
```

The declared conversation values progress through:

```text
M1 -> Meeting at 3 PM
M2 -> Meeting at 4 PM
M3 -> retracts an earlier proposal
M4 -> Meeting at 5 PM
M5 -> confirms M4
```

Under the current rules, `M4` remains the final confirmed active proposal.

Expected bounded result:

```text
one confirmed active proposal -> RESOLVED
```

---

# 9. Resolution States

## RESOLVED

The current resolver returns `RESOLVED` when exactly one confirmed proposal remains active.

`count(confirmed_active_proposals) = 1 -> RESOLVED`

Under the current branch order, this takes precedence even if additional unconfirmed active proposals remain.

---

## ABSTAIN

The current resolver returns `ABSTAIN` when:

`count(confirmed_active_proposals) > 1`

or when:

`count(confirmed_active_proposals) = 0 AND count(active_proposals) > 1`

---

## INCOMPLETE

The current resolver returns `INCOMPLETE` when, for example:

- one active proposal lacks confirmation
- required dependencies are missing
- no proposal can be resolved

These are resolver classifications within the bounded model.

They are not judgments about factual truth, human intent, legal agreement, or conversational safety in general.

---

# 10. What “Meaning” Means Here

In ORL-Chat, “meaning” refers narrowly to the declared value selected by the explicit relationship graph and resolver rules.

For the supplied scenario:

`resolved declared value = Meeting at 5 PM`

ORL-Chat does not infer unrestricted natural-language meaning.

It does not determine:

- sarcasm
- hidden intent
- emotional meaning
- factual truth
- social context
- speaker identity
- legal agreement
- real-world acceptance

The more precise technical term is:

`bounded resolved conversation state`

---

# 11. Exact-Duplicate Absorption

The current duplicate key includes:

```text
id
topic
kind
text
value
targets
```

The current-model relation is:

`D(D(M)) = D(M)`

An exactly repeated supported fragment is evaluated once.

This does not establish:

- general replay prevention
- sender authentication
- transport idempotency
- safe conflicting identifier reuse
- message authenticity

The committed five-message scenario is not a complete duplicate-safety test.

---

# 12. Deterministic Processing

The resolver computes a dependency depth for each message identifier and processes messages by:

`(dependency_depth, message_id)`

The resolver therefore does not preserve fragment arrival position as classification authority.

For equal deduplicated supported evidence and equal rules:

`D(M_A) = D(M_B) -> R_v(M_A,T) = R_v(M_B,T)`

This is the current same-evidence equality condition.

---

# 13. Time and Synchronization Boundary

The committed resolver does not inspect timestamps or wall-clock values when classifying the supplied scenario.

The bounded claim is:

> Timestamps are not resolution authority in the supplied model.

The resolver calculation also does not require synchronized clocks once the same supported evidence is installed.

This does not mean that time or synchronization is unnecessary for every communication system.

Time may still matter for:

- deadlines
- expiration
- legal records
- monitoring
- display
- operations

The current model does not provide:

- message delivery
- eventual delivery
- reliable broadcast
- clock synchronization
- transport synchronization
- consensus

---

# 14. Browser Demonstration Scope

The browser demonstration provides a visual walkthrough.

It shows:

- changing arrival presentation
- different initial node views
- a scripted sharing step
- the correction chain
- the expected final result

It does not independently:

- execute the Python resolver
- enumerate all `120` permutations
- reconstruct the Python hashes
- establish Python-browser conformance

Browser labels such as:

```text
Permutation tested: 120
Proof verified: TRUE
```

should be interpreted as a visual replay of the Python reference result.

---

# 15. Python Demonstration Scope

The Python implementation performs:

- scenario loading
- exact-duplicate absorption
- bounded fragment union
- dependency validation
- cycle detection
- deterministic relationship processing
- topic-state resolution
- pre-merge and post-merge node comparison
- exhaustive permutation checking for the supplied scenario
- canonical JSON serialization for signatures and hashing
- optional sorted, human-readable JSON output

The main committed scenario directly confirms:

- two different initial node views
- `INCOMPLETE` at both nodes before sharing
- equality after equal evidence is installed
- final `RESOLVED` state
- final declared value `Meeting at 5 PM`
- invariance across all `120` committed-fragment permutations

It does not directly exercise every cycle, duplicate, malformed-input, or `ABSTAIN` path.

---

# 16. Result Hashes

The Python implementation uses compact canonical JSON with:

```text
sort_keys = True
separators = (",", ":")
UTF-8 encoding
```

The relation is:

`result_hash = SHA256(canonical_result_bytes)`

Therefore:

`same canonical result bytes -> same SHA-256 hash`

The console displays:

- a state-signature hash
- a replay certificate hash

These hashes provide deterministic identity for the current serialized result object.

They do not independently prove:

- semantic truth
- behavioral correctness
- message authenticity
- independent reconstruction
- security
- production safety

---

# 17. Frozen Artifact Hashes

See:

`VERIFY/VERIFY.txt`

and:

`VERIFY/FREEZE_DEMO_SHA256.txt`

The artifact relation is:

`same file bytes -> same SHA-256 hash`

A successful frozen-hash comparison proves file identity only.

It does not prove program correctness.

Regenerate hashes only after intentional file changes and after completing behavioral checks.

---

# 18. Minimum Requirements

The current Python demonstration requires:

- Python 3.9 or later
- Python standard library
- the committed repository files

The browser presentation requires:

- a modern web browser

After the repository is available locally, the current demonstrations do not require:

- GPS
- NTP
- a live server
- a database
- internet access

---

# 19. Repository Structure

```text
ORL-Chat/
├── README.md
├── LICENSE
├── demo/
│   ├── orl_chat_demo.py
│   └── orl_chat_interactive_demo.html
├── docs/
│   ├── FAQ.md
│   ├── Quickstart.md
│   ├── Test-Guide.md
│   ├── Proof-Sketch.md
│   └── ORL-Chat-Structural-Meaning-Overview.png
├── inputs/
│   └── chat_fragments.json
├── outputs/
│   └── orl_chat_result_general_chat_correction.json
└── VERIFY/
    ├── FREEZE_DEMO_SHA256.txt
    └── VERIFY.txt
```

The generated output file may not exist until the Python script is run with `--write-output`.

---

# 20. Quick Repeatability Check

Run:

```text
python demo/orl_chat_demo.py
```

Run the same command again without changing files.

Expected stable values include:

- scenario name
- message count
- node count
- primary topic
- pre-merge states
- post-merge state
- final message identifier
- final declared value
- checked permutation count
- permutation result
- state-signature hash
- replay certificate hash

This is implementation repeatability.

It is not a universal cross-platform or cross-language conformance guarantee.

---

# 21. Quick Pass Checklist

The committed scenario passes when:

- the Python script runs without an unexpected exception
- Node-A is `INCOMPLETE` before sharing
- Node-B is `INCOMPLETE` before sharing
- the nodes differ before sharing
- both nodes hold equal deduplicated supported evidence after sharing
- both nodes produce equal post-sharing resolver states
- the final state is `RESOLVED`
- the final message identifier is `M4`
- the final declared value is `Meeting at 5 PM`
- `checked_permutations = 120`
- `permutation_independence = True`
- result hashes are produced
- repeated unchanged runs reproduce the same bounded result

For complete review criteria, see:

`docs/Test-Guide.md`

---

# 22. What the Current Demonstration Establishes

For the committed supported scenario, the Python implementation demonstrates:

- different initial node views
- same-evidence node equality after scripted sharing
- a deterministic bounded `RESOLVED` result
- the declared final value `Meeting at 5 PM`
- exhaustive invariance across all `120` fragment permutations
- deterministic canonical result hashing
- local execution without timestamp or wall-clock classification authority

These are bounded scenario and implementation results.

---

# 23. What the Current Demonstration Does Not Establish

The current demonstrations do not establish:

- unrestricted natural-language understanding
- universal meaning resolution
- factual truth
- speaker identity
- message authenticity
- authorization
- encryption
- access control
- delivery guarantees
- network convergence
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
- safe operation on arbitrary or hostile input

---

# 24. Possible Research Uses

ORL-Chat may inform future work in:

- structured amendment chains
- correction and retraction tracking
- offline instruction reconciliation
- multi-agent proposal tracking
- deterministic conversation auditing
- bounded conversational state machines
- independently verifiable resolver receipts

Real deployment would require additional:

- formal schemas
- identity
- authentication
- authorization
- secure transport
- delivery semantics
- operational policy
- adversarial testing
- human review paths

---

# 25. Future Technical Direction

A stronger revision should add:

- formal versioned message schemas
- explicit invalid-input refusal
- conflict-safe identifier handling
- canonical byte serialization
- deterministic byte-wise ordering
- shared Python-browser resolver logic
- assertion-based expected outputs
- duplicate-insertion vectors
- identifier-conflict vectors
- missing-dependency vectors
- dependency-cycle vectors
- dedicated `ABSTAIN` vectors
- multi-topic vectors
- scalable metamorphic testing
- independent reconstruction
- versioned resolver receipts
- structural-closure rules

Future target relation:

`same validated canonical message fragments + same ruleset version -> same independently verified bounded conversation-state result`

This stronger target is not part of the current demonstration.

---

# ⭐ One-Line Summary

ORL-Chat is a deterministic bounded conversation-state reference model in which nodes holding the same deduplicated supported message fragments and applying the same resolver rules produce the same declared result.

For the committed five-message scenario, the Python implementation produces:

`RESOLVED -> Meeting at 5 PM`

and confirms the same bounded state across all `120` fragment permutations.

The browser provides a scripted visual replay of that result.
