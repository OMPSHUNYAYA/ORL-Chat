# ORL-Chat v2.0.0 Claim and Threat Boundary

## Supported Claim

Within the declared schemas, profiles, limits, text profile, and evidence boundary:

`same admitted canonical evidence + same context + same ruleset + same text profile + same participation profile + same boundary declaration -> same bounded conversation-state bundle and capsule, or the same deterministic refusal`

The package tests this relation through Python production, separate Python reconstruction, separate JavaScript reconstruction, frozen vectors, live cross-implementation comparison, generated bounded properties, order and partition variants, hostile inputs, falsification, mutation detection, resource bounds, graph-depth and cycle tests, privacy checks, and capsule parity.

## Meaning of the Supported Claim

The supported claim concerns deterministic resolution of declared typed conversation evidence.

Message arrival position and wall-clock time do not select the bounded result. Operational systems can still be required for observation, delivery, provenance, security, and real-world action.

`operational mechanism != sole bounded resolution authority`

## Not Claimed

ORL-Chat does not establish:

- Unrestricted natural-language understanding.
- Correct extraction of typed structure from prose.
- Factual truth.
- Source authenticity.
- Participant identity.
- Authenticated consent.
- Message delivery, receipt, reading, or comprehension.
- Legal agreement or enforceability.
- Social, organizational, or distributed consensus.
- Authorization or execution authority.
- Safety, legality, suitability, or wisdom of an instruction.
- Completeness beyond the declared evidence boundary.
- Immutability or finality outside the declared artifact.
- Semantic equivalence between different Unicode scalar sequences.
- Protection against compromised hosts or malicious code replacement.
- Production suitability without independent domain validation and surrounding controls.
- Independent third-party certification.

## State Boundaries

`REFUSED` means the submitted structure did not satisfy the supported intake contract.

`INCOMPLETE` means valid admitted evidence was insufficient for a bounded result.

`ABSTAIN` means valid admitted evidence contained a bounded disagreement or conflict that prevented a single result.

`RESOLVED` means the declared rules produced one bounded state from the admitted evidence.

None of these states proves factual truth, consent, authority, or real-world occurrence.

## Evidence-Boundary Boundary

`SEALED` means the declared expected observation-reference set exactly matches the observed reference set.

It does not prove:

- That every real-world message was disclosed.
- That no external evidence exists.
- That every source is authentic.
- That the declared boundary was chosen correctly.
- That the result remains current after new evidence appears.

## Strict-Intake and Structured-Refusal Boundary

Strict-JSON failures occur before a conversation document exists. They are surfaced as parser refusals and do not carry `conversation_resolution_id`, `private_bundle_id`, `public_receipt_id`, or `refusal_id` values.

Inputs that pass strict-JSON intake but violate the declared structural contract produce canonical `REFUSED` bundles with deterministic `refusal_id` values.

`strict-parser refusal != canonical REFUSED bundle`

The exact interoperable integer range is:

`-9007199254740991 <= integer <= 9007199254740991`

Both Python paths and the JavaScript resolver reject an out-of-range integer token during strict-JSON parsing, before semantic validation or runtime-specific number construction.

## Text-Profile Boundary

ORL-Chat v2.0.0 uses:

`ORL-CHAT-UNICODE-SCALAR-EXACT-2-D01`

The producer, independent verifier, and JavaScript resolver preserve strings as exact code-point sequences. They do not use runtime NFC normalization, runtime Unicode General_Category data, or runtime `strip()` or `trim()` tables for admission.

A frozen explicit table refuses supported control, format, and surrogate code points. LF and TAB remain permitted in presentation text and declared-value strings. CR is refused.

`"café" != "cafe\u0301"`

The distinction is intentional. ORL-Chat does not infer that canonically equivalent or visually similar strings have the same meaning or identity.

Changing the frozen code-point table or text treatment defines a new text profile and requires regenerated vectors and verification artifacts.

## Graph-Depth Boundary

ORL-Chat follows at most 256 dependency edges from any action before a terminal action or repeated action must be reached. Inputs exceeding that bound are refused deterministically before runtime-specific stack behavior can affect the result.

`256 dependency edges / 257 actions -> admitted`

`257 dependency edges / 258 actions -> REFUSED`

A cycle within the bound remains a valid bounded disagreement and resolves to `ABSTAIN / DEPENDENCY_CYCLE`.

## Threats Addressed Within the Model

- Arrival-order dependence.
- Supported node-partition dependence.
- Exact duplicate observations.
- Relay observation multiplicity.
- Conflicting observation and action identifiers.
- Missing dependencies and invalid relation targets.
- Cross-topic and cross-conversation targets.
- Relationship cycles within the declared graph-depth bound.
- Dependency paths exceeding `MAX_GRAPH_DEPTH = 256`.
- Multiple incompatible active proposals.
- Non-participant signals and signal conflicts.
- Malformed JSON and duplicate JSON keys.
- Unsupported numeric forms and integers outside the exact interoperable range.
- Noncanonical artifacts where strict canonical verification is requested.
- Frozen text-profile violations.
- Resource-bound violations.
- Bundle and capsule identity tampering.
- Public-artifact leakage of tested private fields.

## Threats Outside the Model

- Forged source identities.
- Stolen credentials or signing keys.
- Compromised applications, browsers, operating systems, or runtimes.
- Malicious but schema-valid false declarations.
- Side-channel leakage and traffic analysis.
- Guessing attacks against low-entropy value commitments.
- Network transport security.
- Cryptographic signing and key management.
- Replay protection outside the declared context.
- Legal enforceability and human misunderstanding.
- Unsafe or unlawful real-world action.
- Incorrect domain policy.
- Availability outside the declared resource checks.

## Value-Commitment Boundary

A capsule stores a deterministic commitment to a resolved declared value rather than the raw value.

The commitment supports equality comparison within the declared profile. It is not encryption, zero-knowledge proof, or secrecy assurance. Low-entropy values may be recoverable by enumeration.

## Independent Verification Boundary

The independent Python verifier is separately implemented from the producer kernel, and the JavaScript resolver is separately implemented from both Python paths.

The live cross-check resolves the same fresh input in Python and JavaScript, removes only each producer's implementation-specific `self_verification` stamp, and compares the remaining canonical bundle bytes.

This supports cross-implementation reconstruction. It does not establish independent third-party review, certification, formal verification, or production qualification.

## Modification Boundary

Changing implementation files, schemas, rulesets, limits, profiles, corpora, vectors, manifests, canonicalization rules, or the text profile creates a new verification boundary.

Modified materials require their own verification and must not be presented as reproducing the original v2.0.0 evidence unless the declared checks pass for the modified package.
