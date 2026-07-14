# ⭐ ORL-Chat

**Deterministic Bounded Conversation-State Resolution**

![ORL-Chat](https://img.shields.io/badge/ORL--Chat-Bounded%20Conversation%20Resolution-black)
![Deterministic](https://img.shields.io/badge/Deterministic-Same--Evidence%20Resolution-green)
![Structure-Based](https://img.shields.io/badge/Resolution-Explicit%20Relationships-purple)
![No-Time-Authority](https://img.shields.io/badge/Timestamps-Not%20Resolution%20Authority-lightgrey)
![Order-Independent](https://img.shields.io/badge/Arrival%20Order-Not%20Resolution%20Authority-lightgrey)
![Permutation-Tested](https://img.shields.io/badge/Supplied%20Scenario-120%20Permutations-orange)
![Open-Use](https://img.shields.io/badge/Reference%20Implementation-Open%20Use-blue)

![ORL-Chat Verify](https://github.com/OMPSHUNYAYA/ORL-Chat/actions/workflows/orl-chat-verify.yml/badge.svg)

**A public deterministic reference model for resolving a bounded conversation state from supported message fragments and explicit relationships.**

ORL-Chat extends ORL into a conversational example domain.

For the supplied scenario, two nodes begin with different message fragments. After both receive the same deduplicated supported fragment set and apply the same resolver rules, they produce the same bounded conversation-state result.

The governing relation is:

`same deduplicated supported message fragments + same resolver rules -> same bounded conversation-state result`

ORL-Chat is developed within the Shunyaya Framework.

---

## ⚡ Try It in 30 Seconds

Open the browser demonstration:

`demo/orl_chat_interactive_demo.html`

Use:

- **Scramble Arrival**
- **Resolve Structure**
- **Replay Proof** — a scripted visual replay of the Python reference result

The browser presents the supplied scenario visually.

Then run the Python reference implementation:

```text
python demo/orl_chat_demo.py
```

To write the result JSON:

```text
python demo/orl_chat_demo.py --write-output
```

Expected primary result:

```text
State       = RESOLVED
Final Value = Meeting at 5 PM
```

The Python implementation also checks all `5! = 120` permutations of the supplied five-message scenario.

---

## 🧭 Visual Overview

![ORL-Chat Structural Overview](docs/ORL-Chat-Structural-Meaning-Overview.png)

---

## 🔗 Quick Links

### 📘 Documentation

- [Quickstart](docs/Quickstart.md)
- [FAQ](docs/FAQ.md)
- [Test Guide](docs/Test-Guide.md)
- [Model and Invariant Sketch](docs/Proof-Sketch.md)
- [Structural Overview](docs/ORL-Chat-Structural-Meaning-Overview.png)

### ⚡ Demonstrations

- [Python Reference Demo](demo/orl_chat_demo.py)
- [Browser Demonstration](demo/orl_chat_interactive_demo.html)

### 🔍 Verification

- [Verification Instructions](VERIFY/VERIFY.txt)
- [Frozen Demo Hashes](VERIFY/FREEZE_DEMO_SHA256.txt)

### 📂 Repository Layout

- [demo/](demo/) — Python reference implementation and browser presentation
- [docs/](docs/) — model, usage, testing, and visual documentation
- [inputs/](inputs/) — committed supported message-fragment scenarios
- [outputs/](outputs/) — generated deterministic result files
- [VERIFY/](VERIFY/) — execution and artifact-identity guidance

---

## 💡 Core Model

ORL-Chat does not perform unrestricted language understanding.

It resolves a bounded conversation state from:

- supported message fragments
- explicit message kinds
- explicit target relationships
- deterministic resolver rules

Conceptually:

`bounded_conversation_state = resolve(supported_message_fragments, resolver_rules)`

For the current model, messages use one of four kinds:

- `OPEN`
- `REPLACE`
- `RETRACT`
- `CONFIRM`

Relationships are expressed through explicit target message identifiers.

---

## 🧩 Current Supported Message Shape

The committed scenario uses message records containing fields such as:

```text
id
topic
kind
text
value
targets
```

Example shape:

```text
{
  "id": "M2",
  "topic": "meeting_time",
  "kind": "REPLACE",
  "text": "Correction: 4 PM",
  "value": "Meeting at 4 PM",
  "targets": ["M1"]
}
```

The current demonstrations expect values shaped like the committed scenario.

A formal versioned schema and complete invalid-input refusal profile are future hardening targets.

---

## 🔥 Current Resolution Rules

### OPEN

An `OPEN` message introduces a proposal.

For the current resolver, it must:

- have no targets
- contain a value

### REPLACE

A `REPLACE` message supersedes its valid targets and introduces a new value.

It must:

- identify at least one target
- reference targets present in the evaluated topic
- depend on structurally valid targets
- contain a replacement value

### RETRACT

A `RETRACT` message removes its valid targeted proposal from the active set.

It must:

- identify at least one target
- reference targets present in the evaluated topic
- depend on structurally valid targets

### CONFIRM

A `CONFIRM` message confirms its valid targeted proposal when that proposal remains active.

It must:

- identify at least one target
- reference targets present in the evaluated topic
- depend on structurally valid targets

---

## ⚖️ Resolution States

### RESOLVED

The current resolver produces `RESOLVED` when exactly one active proposal is also confirmed.

Conceptually:

`one confirmed active proposal -> RESOLVED`

The output includes the surviving proposal identifier, text, and declared value.

### INCOMPLETE

The current resolver produces `INCOMPLETE` when, for example:

- one active proposal lacks confirmation
- required dependencies are missing
- no proposal can yet be resolved

Conceptually:

`missing required relationship -> INCOMPLETE`

### ABSTAIN

The current resolver produces `ABSTAIN` when, for example:

- multiple confirmed active proposals remain
- multiple conflicting active proposals remain

Conceptually:

`conflicting active structure -> ABSTAIN`

These are resolver classifications within the declared model.

They are not judgments about human intent, legal agreement, truth, or conversational safety in general.

---

## 🔁 Same-Evidence Node Equality

Let:

- `E` be a supported message-fragment collection
- `D(E)` be exact-duplicate absorption
- `R_v(E)` be the resolver output under ruleset version `v`

For two nodes:

`D(E_i) = D(E_j) -> R_v(E_i) = R_v(E_j)`

This means that nodes holding the same deduplicated supported fragments and using the same resolver rules produce the same bounded conversation-state result.

ORL-Chat does not claim equality when nodes permanently hold materially different evidence.

---

## 🔀 Arrival-Order Independence

For a supported permutation `P(E)` containing the same message fragments, the intended current-model invariant is:

`R_v(P(E)) = R_v(E)`

The Python reference implementation checks this across all `120` permutations of the supplied five-message scenario.

This is an exhaustive result for that committed scenario.

It is not a universal proof for:

- arbitrary conversation size
- arbitrary message schemas
- arbitrary relationship graphs
- arbitrary implementations

Permutation testing grows factorially and is practical only for small scenarios without additional test strategies.

---

## ♻️ Exact Duplicate Absorption

The current duplicate key includes:

```text
id
topic
kind
text
value
targets
```

Applying exact-duplicate absorption twice has the same result as applying it once:

`D(D(E)) = D(E)`

An identical repeated message fragment is therefore evaluated once in the current model.

This does not establish:

- general message replay prevention
- transport-level idempotency
- sender authentication
- message authenticity
- protection against conflicting reuse of the same identifier

---

## 🧭 Supplied Scenario

The committed scenario contains five structurally related messages:

```text
M1 = opening proposal
M2 = replacement proposal
M3 = retraction
M4 = final replacement
M5 = confirmation
```

The two nodes begin with different fragments:

```text
Node-A = M1, M2
Node-B = M3, M4, M5
```

Before sharing, both local views are expected to be incomplete.

After both nodes receive the same supported fragments, the current resolver follows the declared relationships and produces:

```text
State       = RESOLVED
Final Value = Meeting at 5 PM
```

Expected node result:

```text
converged_after_merge = True
```

Expected permutation result:

```text
checked_permutations    = 120
permutation_independence = True
```

---

## 🧠 What “Meaning” Means Here

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
- legal agreement
- speaker identity
- whether the proposal should be accepted in the real world

The more precise technical term is:

`bounded resolved conversation state`

---

## ✅ What the Current Python Demonstration Establishes

For the supplied scenario, the Python implementation demonstrates:

- different initial node views
- exact duplicate absorption
- explicit dependency validation
- cycle detection
- deterministic relationship processing
- `RESOLVED`, `INCOMPLETE`, and `ABSTAIN` model states
- same-evidence node equality after merge
- exhaustive evaluation of all `120` arrival permutations
- canonical JSON serialization for the generated result object
- SHA-256 hashing of the bounded result object
- local execution without timestamps, GPS, NTP, database access, or a live server after download

These are bounded scenario and implementation claims.

---

## 🖥 Browser Demonstration Scope

The browser demo is a visual presentation of the supplied scenario.

It shows:

- different displayed arrival orders
- the two partial node views
- a scripted structural merge
- the correction and confirmation chain
- the expected final result

The current browser demo does not independently execute the full Python resolver or enumerate all `120` permutations.

Therefore, browser labels such as “permutation tested” or “proof verified” should be interpreted as a visual replay of the Python reference result, not an independently reconstructed browser proof.

A later technical revision should either:

- execute the resolver and conformance checks directly in the browser; or
- label the browser explicitly as a visual reference-result presentation.

---

## 🔐 Result Hash and Artifact Identity

The Python demo computes SHA-256 hashes over canonical JSON representations of the bounded result data.

This provides deterministic identity for the generated result object under the current implementation.

The repository also contains frozen demo-file hashes.

Two distinct relations apply:

`same canonical result bytes -> same result hash`

`same file bytes -> same frozen artifact hash`

Neither relation alone proves:

- semantic truth
- correct human interpretation
- complete conformance
- independent reconstruction
- message authenticity
- security
- production readiness

---

## 🛡 Current Boundary

ORL-Chat does not implement or prove:

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
- reliable broadcast
- Byzantine fault tolerance
- immutable finality
- conflict repair
- complete malformed-input validation
- universal cross-language conformance
- production readiness
- safe operation on arbitrary or hostile input

ORL-Chat is not:

- a chat application replacement
- a messaging transport
- a consensus protocol
- an AI language model
- a moderation system
- a legal agreement engine

---

## ⚠️ Current Technical Limitations

The current implementation should be interpreted only against the committed supported scenarios.

Important limitations include:

- no formal versioned input schema
- incomplete explicit refusal behavior
- malformed required fields may raise errors
- conflicting reuse of a message identifier is not safely rejected
- some no-time, no-order, and no-sync labels are declared rather than independently derived
- the result hash is not an independently reconstructed certificate
- exhaustive permutation testing scales factorially
- the browser demo is scripted rather than a full independent resolver
- cross-language conformance is not established

---

## 🔬 Research and Integration Direction

ORL-Chat may inform future work in:

- structured correction chains
- offline instruction reconciliation
- multi-agent proposal tracking
- deterministic conversation auditing
- explicit amendment and retraction models
- bounded conversational state machines
- independently verifiable resolver receipts

Any real deployment would require additional:

- formal schemas
- identity and authentication
- transport security
- authorization
- delivery semantics
- policy definition
- conflict repair
- operational controls
- adversarial testing

---

## 🧭 Future Technical Direction

A stronger revision should add:

- a formal versioned message schema
- explicit invalid-input refusal
- conflict-safe message identifier handling
- canonical byte serialization
- deterministic byte-wise ordering
- shared Python-browser resolver logic
- assertion-based expected outputs
- malformed-input vectors
- dependency-cycle vectors
- duplicate and identifier-conflict vectors
- adversarial relationship graphs
- scalable permutation and metamorphic testing
- independent reconstruction
- versioned resolver receipts
- a separately defined structural-closure layer

Future target relation:

`same validated canonical message fragments + same ruleset version -> same independently verified bounded conversation-state result`

This stronger target is not part of the current demonstrations.

---

## 📜 License

See [LICENSE](LICENSE).

Reference implementation: **ORL-Chat Open Use License v1.0**

Unless otherwise stated, architecture descriptions, diagrams, and documentation: **CC BY-NC 4.0**

---

## 🔗 Related Projects

- [ORL](https://github.com/OMPSHUNYAYA/Orderless-Ledger)
- [STOCRS](https://github.com/OMPSHUNYAYA/STOCRS)
- [SSUM-Time](https://github.com/OMPSHUNYAYA/SSUM-Time)

---

## ⭐ Final Statement

ORL-Chat demonstrates a bounded structural alternative to using timestamps or message arrival order as conversation-state resolution authority.

For the supplied scenario:

`same deduplicated supported message fragments + same resolver rules -> same bounded resolved conversation state`

The final declared value is:

`Meeting at 5 PM`

This result is produced by explicit message relationships and deterministic resolver rules, not unrestricted natural-language interpretation.
