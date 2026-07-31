# ORL-Chat v2.0.0 Conversation-State Capsule

## Purpose

A Conversation-State Capsule is a portable structural summary derived from a verified ORL-Chat private reconstruction bundle.

Its purpose is to carry the current bounded declared state without exposing the raw message presentations, raw proposal values, participant names, observation sources, or action references contained in the private reconstruction material.

## Construction

`verified private bundle -> selected structural identities + committed values + witnesses -> capsule`

The capsule contains:

- Architecture and ruleset profiles.
- Context, conversation, and purpose identities.
- Source public-receipt and private-bundle identities.
- Boundary state and boundary-receipt identity.
- Action-set and observation-set identities.
- Canonical action and observation identity arrays.
- Relationship edges expressed through action identities.
- Topic states and reason codes.
- Active action identities.
- Resolved action identity where available.
- A commitment to the resolved declared value rather than the raw value.
- Participation outcome counts.
- Witness codes.
- State counts.
- Capsule identity.
- `execution_authority = NONE`.

## Value Commitment

For a resolved declared value `v`:

`resolved_value_commitment = identity("declared_value", value_commitment_profile, v)`

The commitment provides deterministic equality comparison for the declared value within the profile.

It is not encryption, a digital signature, a zero-knowledge proof, or a secrecy guarantee. Low-entropy values may be guessable by enumeration.

## Privacy Boundary

The capsule omits:

- Raw presentation text.
- Raw declared values.
- Participant names.
- Observation sources.
- Action references.

It retains hashed structural identities, state, reason, witnesses, and counts needed for bounded verification and comparison.

Privacy separation reduces routine disclosure but does not establish anonymity, unlinkability, resistance to traffic analysis, or protection against value guessing.

## Verification

Capsule verification checks:

- Exact field sets.
- Supported profile and version.
- Identity formats.
- Sorted unique identity arrays.
- Relationship-edge integrity.
- Topic-state consistency.
- Resolved-value commitment presence only for resolved topics.
- State-count consistency.
- Source identity formats.
- `execution_authority = NONE`.
- Full capsule-identity reconstruction.

A capsule may also be verified against its source private bundle. Source binding checks that the portable state was constructed from the declared bundle rather than merely being self-consistent.

## Witnesses

Witness codes provide bounded machine-readable reasons for the topic state. The browser laboratory also maps supported codes to public-facing explanations.

Examples include:

- `ACTIVE_FRONTIER_PRESENT`
- `BOUNDARY_SEALED`
- `PARTICIPATION_SATISFIED`
- `STATE_RESOLVED`

Witnesses explain the declared resolver result. They do not prove truth, authenticity, consent, legality, or safety.

## Comparison Direction

Comparison is directional:

`compare(left, right) -> relation of right to left`

The supported relations are:

- `IDENTICAL`
- `COMPATIBLE`
- `SUPERSEDES`
- `DIVERGES`
- `INCOMPARABLE`
- `UNSUPPORTED`

## Relation Meanings

### IDENTICAL

The canonical capsule identities match.

### COMPATIBLE

The declared comparison context matches and common topics do not contain divergent resolved-value commitments.

### SUPERSEDES

The right action set strictly extends the left and changes the bounded state without resolved-value divergence.

`SUPERSEDES` is structural. It does not mean later in wall-clock time, legally controlling, or operationally authorized.

### DIVERGES

A common topic resolves to a different declared-value commitment.

### INCOMPARABLE

The declared comparison context differs, so the comparison profile does not authorize a substantive relation.

### UNSUPPORTED

At least one capsule fails structural verification.

## Source and Execution Boundaries

A capsule is not:

- A transcript.
- A digital signature.
- An authentication record.
- A proof of source authenticity.
- A legal agreement.
- A proof of delivery or reading.
- An authorization token.
- An executable instruction.

Every capsule declares:

`execution_authority = NONE`

A downstream system must perform its own authorization, current-state revalidation, safety checks, policy checks, and execution controls.
