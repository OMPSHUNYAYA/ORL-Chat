# ORL-Chat v2.0.0 Architecture

## Purpose

ORL-Chat resolves bounded conversation state from declared typed evidence. It separates transport observations, conversational actions, relationship structure, participation evaluation, evidence-boundary evaluation, portable receipts, and execution authority.

The governing contract is:

`same admitted canonical conversation evidence + same bound conversation context + same ruleset + same text profile + same participation profile + same boundary declaration -> same bounded conversation-state bundle or deterministic refusal`

## Processing Structure

`raw JSON -> strict intake and exact-integer admission -> exact text-profile validation -> canonical context and observations -> observation identity -> action identity -> deduplication -> typed relationship graph -> active proposal frontier -> participation evaluation -> topic receipts -> boundary receipt -> public receipt + private bundle -> Conversation-State Capsule`

The processing path is structural rather than chronological. Arrival position and wall-clock timestamps do not determine the bounded result.

## Layer 1: Strict Intake

Strict intake occurs before conversation-state resolution.

Strict-JSON failures occur before a conversation document exists and are surfaced as parser refusals. Inputs that parse successfully but violate the supported structural contract produce canonical `REFUSED` bundles.

`strict-parser refusal != canonical REFUSED bundle`

The intake boundary checks:

- UTF-8 JSON structure.
- Duplicate object keys.
- Unsupported floating-point and non-finite numeric forms.
- Integer tokens outside `-9007199254740991` through `9007199254740991`.
- Exact supported field sets.
- Supported schema and profile identities.
- Exact Unicode scalar-sequence treatment under the declared text profile.
- Identifier and value limits.
- Participant, observation, target, graph-depth, and input-byte limits.
- Cross-conversation and cross-topic references.
- Self-targets and unsupported target kinds.
- Missing targets preserved as explicit missing dependencies.
- Conflicting reuse of observation and action references.

`invalid parsed structure -> REFUSED bundle`

A parser-refused input does not produce a conversation document. A structurally refused document does not enter topic resolution. A valid dependency cycle within the declared graph-depth bound is admitted for topic evaluation and produces `ABSTAIN / DEPENDENCY_CYCLE`.

## Exact Text Profile

The ruleset binds:

`ORL-CHAT-UNICODE-SCALAR-EXACT-2-D01`

Text is preserved as exact Unicode code-point sequences. Admission uses a frozen explicit control, format, and surrogate table rather than host-runtime normalization or category data.

`canonical equivalence != structural identity`

The Python producer, independent Python verifier, and JavaScript resolver implement the same code-point checks.

## Declared Resource Boundary

The graph contract includes:

`MAX_GRAPH_DEPTH = 256`

The value counts dependency edges followed from one action before a terminal action or repeated action is reached. A path requiring more than 256 such edges is refused with the same deterministic error in the Python producer, independent Python verifier, and JavaScript resolver.

`256 dependency edges / 257 actions -> admitted`

`257 dependency edges / 258 actions -> REFUSED`

The three implementations use iterative cycle discovery and iterative dependency-readiness evaluation. The shared bound also limits graph-walk work independently of runtime call-stack capacity.

`within bound + cycle -> ABSTAIN / DEPENDENCY_CYCLE`

`graph depth exceeded -> REFUSED`

## Layer 2: Bound Context

Every admitted action is bound to a declared context containing:

- Conversation identity.
- Purpose identity.
- Ruleset profile.
- Participation profile.
- Declared participant set where applicable.
- `execution_authority = NONE`.

Context binding prevents structurally valid evidence from one conversation or purpose from being silently reused in another.

## Layer 3: Observation and Action Identity

An observation records a source-side presentation of an action. An action is the canonical conversational operation that participates in resolution.

`observation multiplicity != action multiplicity`

Consequences:

- Exact repeated observations are absorbed.
- Different relay observations can refer to one canonical action.
- Observation identity remains distinct from action identity.
- Conflicting reuse of an observation reference is refused.
- Conflicting reuse of an action reference is refused.

Presentation text is retained in private reconstruction material but does not determine action identity.

## Layer 4: Typed Relationship Graph

Supported action kinds are:

- `PROPOSE`
- `AMEND`
- `WITHDRAW`
- `ENDORSE`
- `OBJECT`

`PROPOSE` creates a proposal-producing node.

`AMEND` creates a proposal-producing node and supersedes its supported target.

`WITHDRAW` removes its supported target from the active frontier.

`ENDORSE` and `OBJECT` contribute declared participation signals to a supported proposal-producing target.

The admitted action set is represented as a typed directed graph. The graph is validated before its frontier is evaluated.

## Layer 5: Active Proposal Frontier

The active frontier is derived from the complete admitted graph.

`active_frontier = admitted proposal-producing actions not superseded or withdrawn under the declared ruleset`

The resolver does not replay a chat sequence to discover the final proposal. It evaluates the canonical graph as a complete bounded structure.

## Layer 6: Participation Evaluation

Supported participation profiles are:

- `NO_ENDORSEMENT_REQUIRED`
- `SINGLE_DECLARED_ENDORSER`
- `ALL_DECLARED_PARTICIPANTS`
- `EXACT_DECLARED_PARTICIPANT_SET`
- `DECLARED_THRESHOLD`

Participation evaluation uses declared structural signals only. It does not authenticate actors or prove consent.

## Layer 7: Topic Resolution

For each admitted topic:

Validation refusal precedes topic resolution. For admitted topic evidence, the implemented reason-code precedence is:

`DEPENDENCY_CYCLE > PARTICIPANT_SIGNAL_CONFLICT > MULTIPLE_ACTIVE_PROPOSALS > MISSING_DEPENDENCY > NO_ACTIVE_PROPOSAL > ACTIVE_PROPOSAL_OBJECTED > participation evaluation`

The final participation evaluation produces `RESOLVED` when satisfied and `INCOMPLETE / PARTICIPATION_INCOMPLETE` otherwise.

A confirmed or endorsed proposal does not silently erase another active incompatible proposal. Competing active proposals remain visible as a bounded disagreement.

## Layer 8: Evidence Boundary

The evidence boundary is evaluated separately from topic resolution.

- `OPEN` means the evidence set is not declared complete.
- `SEALED` means the expected observation-reference set exactly matches the observed set.
- `INCOMPLETE` and `CONFLICT` can result when a requested sealed boundary does not match the observed set.

`SEALED` is not a universal completeness claim. It is a result within the declared boundary.

## Layer 9: Receipts and Bundle

The resolver produces:

- Topic receipts.
- A boundary receipt.
- A public receipt.
- A private reconstruction bundle.

The public receipt exposes bounded structural results without raw declared values or raw presentation text.

The private bundle retains canonical admitted evidence and reconstruction material.

Both declare:

`execution_authority = NONE`

## Layer 10: Conversation-State Capsule

A Conversation-State Capsule is derived from a verified private bundle.

`verified private bundle -> selected structural identities + committed resolved values + witnesses -> capsule`

The capsule supports portable verification and bounded comparison while omitting raw values, raw presentations, participant names, observation sources, and action references.

## Verification Structure

`Python producer -> separate Python verifier -> separate JavaScript resolver -> frozen parity vectors -> hostile and falsification assurance -> capsule parity and comparison`

The Python verifier does not import the producer kernel. The JavaScript resolver is separately implemented and reproduces the declared canonical bundle identities across the frozen parity corpus.

## Authority Separation

ORL-Chat separates:

- Evidence declaration.
- Proposal creation.
- Relationship declaration.
- Participation-profile evaluation.
- Resolution authority.
- Evidence-boundary declaration.
- Capsule verification.
- Action authorization.
- Execution.

ORL-Chat performs bounded resolution and artifact construction. It does not grant action authorization or execution authority.

## Core Invariants

Where implemented and tested:

- Same admitted canonical evidence and profiles reproduce the same bounded result.
- Observation order does not determine resolution.
- Supported node partitioning and canonical merge do not determine resolution.
- Exact duplicate observations do not multiply actions.
- Relay observations do not multiply canonical actions.
- Malformed, unsupported, or over-depth evidence is refused before resolution.
- Multiple incompatible active proposals do not produce a forced result.
- Public artifacts remain separated from private reconstruction content.
- Altered bundle or capsule identities fail verification.

## Architectural Boundary

ORL-Chat is not a natural-language parser, transport protocol, authentication system, signature system, consensus protocol, contract engine, authorization service, or execution engine.

An external parser may propose typed structure. That structure remains subject to strict intake and bounded resolution. An external authorization layer may act on a verified result only under its own policies, current-state checks, safety controls, and authority.
