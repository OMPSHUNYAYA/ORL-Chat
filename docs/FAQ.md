# ORL-Chat v2.0.0

## Frequently Asked Questions

ORL-Chat is a bounded reference implementation for deterministic conversation-evidence reconciliation. It resolves declared typed actions and relationships under a versioned structural contract while keeping language interpretation, identity, consent, delivery, truth, authorization, and execution outside its authority boundary.

## Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Declared Evidence and Supported Actions](#2-declared-evidence-and-supported-actions)
3. [Resolution Outcomes and Evidence Boundaries](#3-resolution-outcomes-and-evidence-boundaries)
4. [Receipts, Bundles, and Conversation-State Capsules](#4-receipts-bundles-and-conversation-state-capsules)
5. [Capsule Comparison Relations](#5-capsule-comparison-relations)
6. [Verification, Browser Use, and Canonical Data](#6-verification-browser-use-and-canonical-data)
7. [Modification, Integration, and Deployment](#7-modification-integration-and-deployment)

---

## 1. Purpose and Scope

### 1.1 What problem does ORL-Chat address?

ORL-Chat resolves the current bounded state of declared proposals, amendments, withdrawals, endorsements, and objections without allowing message arrival position or wall-clock time to become the resolution authority.

Its governing contract is:

`same admitted canonical evidence + same bound context + same rules, text profile, and participation profile + same boundary -> same bounded conversation-state bundle or deterministic refusal`

### 1.2 Does ORL-Chat understand unrestricted conversation language?

No. ORL-Chat resolves declared typed actions and relationships under a bounded ruleset.

A human, parser, or AI system may propose typed structure, but the proposed structure remains subject to strict intake, canonicalization, validation, and deterministic resolution.

### 1.3 Does ORL-Chat decide what a sentence means?

No. Presentation text may be retained in the private reconstruction material, but it does not determine canonical action identity or the bounded resolution result.

ORL-Chat resolves declared structure, not unrestricted semantics.

### 1.4 Does a `RESOLVED` topic prove that the declared value is factually true?

No. `RESOLVED` establishes the bounded state of admitted declared evidence under the selected rules and participation profile. It does not establish factual truth.

### 1.5 Does an endorsement prove authenticated consent?

No. An endorsement is a declared structural signal. Authentication, identity proofing, consent verification, and legal validity remain outside ORL-Chat.

### 1.6 Does ORL-Chat prove that a message was delivered, read, or understood?

No. Delivery, receipt, reading, comprehension, and source authenticity require separate evidence and systems.

### 1.7 Does ORL-Chat replace a chat platform or messaging protocol?

No. Transport, storage, delivery, encryption, availability, user interfaces, and messaging protocols remain separate responsibilities.

### 1.8 Does ORL-Chat replace a consensus system?

No. ORL-Chat resolves declared typed evidence under a bounded ruleset. It does not establish distributed, social, legal, political, or organizational consensus.

---

## 2. Declared Evidence and Supported Actions

### 2.1 Which actions are supported?

The ORL-Chat v2.0.0 grammar supports:

- `PROPOSE`
- `AMEND`
- `WITHDRAW`
- `ENDORSE`
- `OBJECT`

Unsupported action types are not silently interpreted.

### 2.2 What is the difference between an observation and an action?

An observation records a source-side presentation of an action. Multiple observations may refer to one canonical action.

`observation multiplicity != action multiplicity`

This separation allows relay or source multiplicity to remain visible without multiplying the underlying conversational action.

### 2.3 What happens to exact duplicate observations?

Exact duplicates are absorbed. They do not create additional canonical actions or alter the bounded result.

### 2.4 What is a relay observation?

A relay observation is a distinct observation path carrying the same canonical action. It can preserve evidence that an action appeared through multiple observation paths without creating a second action.

### 2.5 What happens when an identifier is reused with different content?

Conflicting reuse of an observation reference or action reference is refused before topic resolution.

`same identifier + different canonical content -> REFUSED`

### 2.6 Which participation profiles are supported?

ORL-Chat v2.0.0 supports:

- `NO_ENDORSEMENT_REQUIRED`
- `SINGLE_DECLARED_ENDORSER`
- `ALL_DECLARED_PARTICIPANTS`
- `EXACT_DECLARED_PARTICIPANT_SET`
- `DECLARED_THRESHOLD`

These profiles evaluate declared evidence. They do not authenticate participants or prove consent.

---

## 3. Resolution Outcomes and Evidence Boundaries

### 3.1 Which resolution outcomes are available?

- `RESOLVED`: one active proposal remains and the selected participation profile is satisfied.
- `INCOMPLETE`: the admitted evidence is valid but insufficient for resolution.
- `ABSTAIN`: the admitted evidence contains a bounded unresolved disagreement or conflict.
- `REFUSED`: the submitted structure fails strict intake or validation.

### 3.2 Why is `REFUSED` separate from `INCOMPLETE`?

`REFUSED` concerns invalid, conflicting, malformed, or unsupported input that is not admitted into topic resolution.

`INCOMPLETE` concerns valid admitted input that lacks sufficient evidence for a bounded result.

### 3.3 What happens when two incompatible proposals remain active?

ORL-Chat does not force a winner. The topic resolves to `ABSTAIN` under the supported rules.

### 3.4 Can a withdrawal repair an earlier disagreement?

Yes. A supported withdrawal can remove one proposal from the active frontier. If one compatible proposal remains and the participation profile is satisfied, the topic can resolve.

This is a structural relationship within the admitted evidence graph. It is not a claim that wall-clock sequence determines the result.

### 3.5 What does `OPEN` mean?

`OPEN` means the observed evidence set is not declared complete under the selected evidence-boundary contract.

### 3.6 What does `SEALED` mean?

`SEALED` means the declared expected observation-reference set exactly matches the observed reference set.

It does not prove that no undisclosed message or evidence exists elsewhere.

### 3.7 What precedence applies when several topic conditions coexist?

After strict validation, ORL-Chat applies this reason-code precedence:

`DEPENDENCY_CYCLE > PARTICIPANT_SIGNAL_CONFLICT > MULTIPLE_ACTIVE_PROPOSALS > MISSING_DEPENDENCY > NO_ACTIVE_PROPOSAL > ACTIVE_PROPOSAL_OBJECTED > participation evaluation`

The final participation evaluation produces `RESOLVED` when satisfied and `INCOMPLETE / PARTICIPATION_INCOMPLETE` otherwise.

### 3.8 How are dependency cycles handled?

A structurally valid cycle within the declared graph-depth bound is admitted and produces `ABSTAIN / DEPENDENCY_CYCLE`. It is not treated as an intake refusal.

### 3.9 What is the maximum supported graph depth?

ORL-Chat declares `MAX_GRAPH_DEPTH = 256`. From any action, at most 256 dependency edges may be followed before reaching a terminal action or a repeated action. A chain containing 257 actions connected by 256 edges is admitted. A chain requiring 257 edges is refused with a deterministic error shared by the Python and JavaScript implementations.

---

## 4. Receipts, Bundles, and Conversation-State Capsules

### 4.1 What is the public receipt?

The public receipt is a portable structural summary containing identities, topic states, reason codes, participation summaries, and boundary status without exposing raw presentation text or raw declared values.

### 4.2 What is the private reconstruction bundle?

The private reconstruction bundle contains the admitted observations, presentations, declared values, relationship graph, witnesses, and reconstruction material required for complete verification.

### 4.3 What is a Conversation-State Capsule?

A Conversation-State Capsule is a portable, privacy-separated state derived from a verified private bundle.

It carries structural identities, topic states, value commitments, witness codes, and evidence coverage without carrying raw presentations, raw declared values, participant names, observation sources, or action references.

### 4.4 Is a value commitment encryption?

No. A value commitment is a deterministic identity commitment. It is not encryption and does not provide confidentiality by itself.

Low-entropy values may be guessable through enumeration.

### 4.5 Can a Conversation-State Capsule authorize execution?

No. Every capsule declares:

`execution_authority = NONE`

A downstream system must perform its own identity, authorization, policy, safety, legality, and current-state checks.

---

## 5. Capsule Comparison Relations

### 5.1 What does `IDENTICAL` mean?

`IDENTICAL` means the canonical capsule identities match.

### 5.2 What does `COMPATIBLE` mean?

`COMPATIBLE` means the declared comparison context matches and the common topics do not contain divergent resolved-value commitments.

### 5.3 What does `SUPERSEDES` mean?

`SUPERSEDES` means the right capsule contains a strict action-set extension that changes the bounded structural state without producing resolved-value divergence.

### 5.4 Does `SUPERSEDES` mean later in time?

No. `SUPERSEDES` is a structural relation. It is not derived from timestamps or wall-clock chronology.

### 5.5 Does `SUPERSEDES` establish legal priority or authority?

No. It does not establish legal priority, consent, organizational authority, execution permission, or enforceability.

### 5.6 What does `DIVERGES` mean?

`DIVERGES` means a common topic resolves to a different declared-value commitment.

### 5.7 What does `INCOMPARABLE` mean?

`INCOMPARABLE` means the declared comparison context differs, so the bounded comparison profile does not authorize a substantive relation.

### 5.8 What does `UNSUPPORTED` mean?

`UNSUPPORTED` means that at least one capsule fails structural verification or cannot be evaluated under the supported comparison contract.

---

## 6. Verification, Browser Use, and Canonical Data

### 6.1 Why can the browser show a `file:` origin warning?

Browsers treat local `file:` URLs as restricted or unique security origins. This may limit script, file, frame, or resource behavior even when the laboratory itself opens.

From the `Public_Release` directory, start a local server:

```text
python -m http.server 8000
```

Then open either laboratory through the local server:

```text
http://localhost:8000/demo/ORL_Chat_Structural_Lab_v2_0_0.html
http://localhost:8000/demo/ORL_Chat_Capsule_Lab_v2_0_0.html
```

Stop the server with `Ctrl+C`.

### 6.2 Is the browser only displaying frozen results?

No. The supplied JavaScript implementation computes supported results, reconstructs bundles, creates and verifies capsules, compares capsules, and performs tamper, order, partition, privacy, and parity checks.

Sixteen frozen vectors provide expected identities for bounded conformance verification, including an over-depth graph refusal case.

### 6.3 Is the Python verifier independent of the producer kernel?

The Python verifier is separately implemented and does not import the producer kernel. The JavaScript resolver is also separately implemented.

This demonstrates separate implementation reconstruction and cross-language parity. It does not constitute independent third-party certification.

### 6.4 Why are floating-point JSON numbers refused?

The canonical contract avoids cross-runtime ambiguity by accepting exact interoperable integers and refusing unsupported floating-point forms.

### 6.5 Are duplicate JSON keys allowed?

No. Duplicate keys are refused because ordinary parsers may silently retain different values and thereby create ambiguous evidence.

### 6.6 How does ORL-Chat handle Unicode normalization?

ORL-Chat does not normalize admitted strings. It preserves exact Unicode code-point sequences under `ORL-CHAT-UNICODE-SCALAR-EXACT-2-D01`.

`"café" != "cafe\u0301"`

Both sequences may be admitted, but they remain structurally distinct.

### 6.7 Does text validation depend on the runtime Unicode database?

No. The producer, independent verifier, and JavaScript resolver use the same frozen explicit boundary-whitespace, control, format, and surrogate code-point tables. They do not use runtime NFC normalization, runtime Unicode category data, or runtime `strip()` or `trim()` tables for admission.

### 6.8 Is `--strict-canonical` required for ordinary integration input?

No. It is a verification mode for files that must already use canonical artifact bytes. Ordinary strict JSON can be canonicalized with the reference kernel before publication or hashing.

### 6.9 What is the difference between a parser refusal and a `REFUSED` bundle?

A parser refusal occurs before a conversation document exists. It reports a strict-JSON intake error and has no bundle or `refusal_id`.

A `REFUSED` bundle is produced after successful JSON parsing when the submitted structure violates the supported semantic, identity, relationship, or resource contract.

`strict-parser refusal != canonical REFUSED bundle`

### 6.10 Which integers are accepted?

Strict JSON accepts integers in this inclusive range:

`-9007199254740991 <= integer <= 9007199254740991`

Python and JavaScript compare the decimal token against this boundary before constructing runtime numbers. Tokens outside the range are parser refusals.

### 6.11 What is the live cross-implementation checker?

It resolves the same fresh input through Python and JavaScript, removes only each implementation's `self_verification` stamp, and compares the remaining canonical bundle bytes. It also supports raw strict-parser outcome parity through `--all-parser-cases`.

### 6.12 What is the seeded property verifier?

It uses a fixed seed to generate bounded valid graphs and checks cross-language parity, order invariance, partition invariance, duplicate absorption, and expected state precedence. It reports generated cases separately from the assertion total.

### 6.13 Does the package include a SHA-256 manifest?

Yes. The minimal manifest is:

`hashes/SHA256SUMS.txt`

It covers 14 verification-critical files:

- Four core implementation files.
- Six principal verifier files.
- The shared cross-platform verification runner.
- Three corpus or vector-root files.

Root files, documentation, browser HTML presentation files, examples, reports, hostile fixtures, falsification fixtures, generators, and generated capsule sub-artifacts are intentionally outside the minimal hash scope.

### 6.14 What does the SHA-256 manifest establish?

The manifest supports byte-level integrity checking for the selected files. It does not establish semantic correctness, source authenticity, legal approval, or production suitability.

The selected files must still be evaluated through the supplied verification paths.

---

## 7. Modification, Integration, and Deployment

### 7.1 Can the implementation be modified?

Yes, subject to the terms in `LICENSE`.

Modified files should be clearly identified as modified and verified under their own identities. Modifications must not imply that they were verified, approved, or endorsed by the original project maintainers.

### 7.2 Is ORL-Chat production certified?

No. ORL-Chat v2.0.0 is a bounded public reference implementation.

Production use requires independent domain validation and appropriate source authentication, authorization, security, privacy, safety, legal, operational, monitoring, recovery, and deployment controls.

### 7.3 Can an AI or parser supply ORL-Chat input?

Yes. A human, parser, or AI system may propose typed actions and relationships.

The proposal remains subject to the same strict intake, validation, canonicalization, context binding, and deterministic resolution as any other submitted structure.

### 7.4 What should a downstream system verify before executing an action?

A downstream system should independently verify:

- Identity and source authenticity.
- Authorization and current authority.
- Current state and dependency validity.
- Safety and domain constraints.
- Legal and organizational requirements.
- Policy and compliance conditions.
- Replay and duplication protections.
- Execution limits and recovery controls.

ORL-Chat does not grant execution authority.

### 7.5 What is the recommended integration boundary?

A bounded integration can follow this pattern:

`human or AI proposal -> declared typed structure -> ORL-Chat resolution -> independent action admission -> execute or refuse -> verification receipt`

ORL-Chat resolves the declared conversation state. A separate admission or execution system must determine whether any real-world action is authorized and safe.
