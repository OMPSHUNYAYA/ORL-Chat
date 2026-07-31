# ORL-Chat v2.0.0 Integration Guide

## Integration Purpose

ORL-Chat can be placed between a source of declared conversation evidence and a downstream system that needs a bounded, reproducible conversation state.

`human or AI language -> optional typed-structure proposal -> strict intake -> bounded resolution -> verified receipt or capsule -> independent authorization and revalidation -> execute or refuse`

A parser or AI may propose typed structure. It must not bypass strict intake or become the sole authority that admits the bounded result.

## Required Integration Separation

Keep language interpretation, source authentication, evidence transport, structural resolution, artifact verification, authorization, current-state revalidation, safety evaluation, and execution as separate responsibilities.

ORL-Chat covers structural resolution and artifact construction only.

## Input Contract

An integrating producer supplies one bound context, one participation profile, one evidence boundary, and a list of supported observations containing typed actions.

Supported actions are `PROPOSE`, `AMEND`, `WITHDRAW`, `ENDORSE`, and `OBJECT`.

Do not depend on object-key order, observation-array order, timestamp order, or network arrival order to define the result.

## Resource Envelope

Integrations must preserve the declared limits, including:

`MAX_GRAPH_DEPTH = 256`

An additional dependency edge is `REFUSED` with the same deterministic error in the Python producer, independent Python verifier, and JavaScript resolver.

`256 dependency edges / 257 actions -> admitted`

`257 dependency edges / 258 actions -> REFUSED`

Do not pre-truncate, silently split, or reinterpret an over-depth graph. A larger envelope requires a new profile and regenerated verification artifacts.

A dependency cycle within the bound is admitted and resolves to `ABSTAIN / DEPENDENCY_CYCLE`.

## Canonicalization

Ordinary ingestion accepts strict JSON that satisfies the supported data and semantic rules. Object-key order, indentation, and final-newline style do not need to be canonical at ingestion.

Canonical artifact form uses:

- UTF-8 without a BOM.
- Sorted object keys.
- Two-space indentation.
- One LF terminator.
- Exact interoperable integers.
- No duplicate object keys.

`--strict-canonical-input` and `--strict-canonical` are verification modes. They require the supplied bytes to already match canonical artifact form. Use them for frozen corpora, published artifacts, hash-governed files, and byte-reproducibility checks.

To canonicalize ordinary strict JSON:

```text
python -B demo/ORL_Chat_Reference_Kernel_v2_0_0.py --canonicalize input.json --output canonical_input.json
```

Canonicalization does not by itself establish semantic admission.

## Strict-JSON Refusal Channel

Strict-JSON intake failures occur before a conversation document exists and are surfaced as parser refusals. Inputs that parse successfully but violate the supported structure produce canonical `REFUSED` bundles.

`strict-parser refusal != canonical REFUSED bundle`

The exact interoperable integer range is:

`-9007199254740991 <= integer <= 9007199254740991`

Out-of-range integer tokens are rejected during parsing in Python and JavaScript. Integrations must not pre-parse such values through a runtime that rounds, truncates, or silently converts them before ORL-Chat receives the original JSON bytes.

To cross-check all shipped parser cases:

```text
python -B verifier/ORL_Chat_Cross_Language_Cross_Check_v2_0_0.py --all-parser-cases
```

## Text Profile

ORL-Chat v2.0.0 declares:

`ORL-CHAT-UNICODE-SCALAR-EXACT-2-D01`

Strings are preserved as exact code-point sequences. Runtime NFC normalization, Unicode category databases, and runtime `strip()` or `trim()` tables are not used for admission.

- Canonically equivalent sequences remain distinct.
- Identifiers refuse the frozen control, format, and surrogate table.
- Presentation and declared-value strings permit LF and TAB, refuse CR, and refuse the remaining frozen table.
- A producer must not normalize, fold, transliterate, or visually equate strings before ORL-Chat unless that transformation is a separately declared upstream operation.

Changing the text profile requires regenerated vectors and cross-language verification.

## Producer Integration

Representative resolution command:

```text
python -B demo/ORL_Chat_Reference_Kernel_v2_0_0.py --input examples/ORL_Chat_corrected_instruction_Input_v2_0_0.json --strict-canonical-input --output ORL_Chat_Bundle.json --public-receipt-output ORL_Chat_Public_Receipt.json
```

Treat `REFUSED` as an intake failure. Do not reinterpret it as `INCOMPLETE` or force a topic result.

For admitted evidence, preserve:

`DEPENDENCY_CYCLE > PARTICIPANT_SIGNAL_CONFLICT > MULTIPLE_ACTIVE_PROPOSALS > MISSING_DEPENDENCY > NO_ACTIVE_PROPOSAL > ACTIVE_PROPOSAL_OBJECTED > participation evaluation`

## Verification Integration

Verify a private bundle before relying on its structural state:

```text
python -B verifier/ORL_Chat_Independent_Verifier_v2_0_0.py --verify ORL_Chat_Bundle.json --strict-canonical
```

Cross-check the same input through both live implementations:

```text
python -B verifier/ORL_Chat_Cross_Language_Cross_Check_v2_0_0.py --input input.json
```

Cross-check every shipped input:

```text
python -B verifier/ORL_Chat_Cross_Language_Cross_Check_v2_0_0.py --all-examples
```

A mismatch returns a nonzero status and prints a bounded unified diff.

Run reproducible generated properties:

```text
python -B verifier/ORL_Chat_Seeded_Property_Verifier_v2_0_0.py --seed 20260731 --cases 32
```

Verification establishes consistency with the declared contract. It does not establish source authenticity or authorization.

## Public Receipt and Capsule Integration

Use the public receipt for portable identities, states, reason codes, participation counts, boundary state, and evidence roots without raw presentations or declared values.

Use a Conversation-State Capsule for portable state, committed values, witnesses, evidence coverage, and comparison without the full private bundle.

Create a capsule only from a verified private bundle:

```text
python -B demo/ORL_Chat_Conversation_State_Capsule_v2_0_0.py --create ORL_Chat_Bundle.json --strict-canonical --output ORL_Chat_Capsule.json
```

## Comparison Integration

`compare(left, right) -> relation of right to left`

Do not interpret `SUPERSEDES` as a timestamp, legal priority, or authorization decision. Each downstream application defines its own policy for `IDENTICAL`, `COMPATIBLE`, `SUPERSEDES`, `DIVERGES`, `INCOMPARABLE`, and `UNSUPPORTED`.

## Execution Boundary

Every public receipt, private bundle, and capsule declares:

`execution_authority = NONE`

A downstream executor independently establishes identity, authorization, current state, safety, legal and organizational policy, domain validity, replay controls, audit, and rollback behavior.

## Change and Validity

When new admitted evidence appears, resolve a new bundle and capsule. Do not mutate a verified artifact in place.

Changing code, rules, profiles, limits, text treatment, or canonicalization requires a new verification boundary and a complete re-run.
