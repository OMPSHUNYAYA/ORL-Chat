# ORL-Chat v2.0.0 Verification Guide

## Complete Verification

From `Public_Release`, use any one of these commands:

```text
python -B VERIFY_ALL.py
VERIFY_ALL.bat
./verify_all.sh
```

`VERIFY_ALL.py` owns the ordered verification gate. The platform wrappers invoke that same runner. Every path stops at the first failure. The final success line is:

```text
ORL-Chat v2.0.0 complete verification: PASS
```

## Verification Stages

### 1. Python reference-kernel audit

```text
python -B demo/ORL_Chat_Reference_Kernel_v2_0_0.py --self-test
```

Expected: `2955/2955 PASS`.

### 2. Separate Python verifier audit

```text
python -B verifier/ORL_Chat_Independent_Verifier_v2_0_0.py --self-test
```

Expected: `173/173 PASS`.

### 3. Frozen corpus verification

```text
python -B verifier/ORL_Chat_Independent_Verifier_v2_0_0.py --verify-corpus corpus/ORL_Chat_Frozen_Corpus_Manifest_v2_0_0.json --strict-canonical
```

Expected: `13/13 PASS`.

### 4. Cross-language vector reproducibility

```text
python -B verifier/ORL_Chat_Cross_Language_Vector_Generator_v2_0_0.py --verify-existing
```

Expected: 17 vectors and a byte-identical parity document.

### 5. JavaScript resolver and vector parity

```text
node verifier/ORL_Chat_Browser_Parity_Verifier_v2_0_0.js --self-test
```

Expected: `442/442 PASS`.

### 6. Live Python-JavaScript bundle cross-check

```text
python -B verifier/ORL_Chat_Cross_Language_Cross_Check_v2_0_0.py --all-examples
```

Expected: `17/17 PARITY`.

This stage resolves each shipped input through both live implementations, removes only the implementation-specific `self_verification` field, and compares the remaining canonical bundle bytes. Node subprocess output is decoded explicitly as strict UTF-8, independent of the host operating-system code page.

### 7. Strict-parser outcome parity

```text
python -B verifier/ORL_Chat_Cross_Language_Cross_Check_v2_0_0.py --all-parser-cases
```

Expected: `8/8 PARSER PARITY`.

The parser corpus covers duplicate keys, floating-point numbers, exact-integer overflow in both directions, an extreme integer token, UTF-8 BOM refusal, noncanonical artifact refusal, and trailing-content refusal.

A strict-parser refusal occurs before a conversation document exists. A semantic or structural refusal occurs after parsing and produces a canonical `REFUSED` bundle.

`strict-parser refusal != canonical REFUSED bundle`

### 8. Seeded generated-property verification

```text
python -B verifier/ORL_Chat_Seeded_Property_Verifier_v2_0_0.py --seed 20260731 --cases 32
```

Expected:

```text
CASES: 32/32 PASS
ASSERTIONS: 256/256 PASS
```

The fixed seed and `ORL-CHAT-SPLITMIX64-2-D01` generator produce bounded graphs and check Python-JavaScript identity, order invariance, partition invariance, duplicate absorption, and expected state precedence.

### 9. Conversation-State Capsule audit

```text
python -B demo/ORL_Chat_Conversation_State_Capsule_v2_0_0.py --self-test
```

Expected: `14/14 PASS`.

### 10. Capsule vector regeneration

```text
python -B verifier/ORL_Chat_Capsule_Vector_Generator_v2_0_0.py
```

Expected: 8 capsules, 7 comparisons, and a stable vector-set identity.

### 11. Adversarial assurance

```text
python -B verifier/ORL_Chat_C3_Assurance_Verifier_v2_0_0.py --self-test --write-report
```

Expected: `154/154 PASS`.

### 12. Capsule JavaScript parity

```text
node verifier/ORL_Chat_Capsule_Parity_Verifier_v2_0_0.js --self-test
```

Expected: `310/310 PASS`.

### 13. Selected-file SHA-256 verification

The shared runner checks `hashes/SHA256SUMS.txt` against the selected 14-file surface.

## Exact-Integer Verification

Strict JSON accepts only:

`-9007199254740991 <= integer <= 9007199254740991`

The Python producer, independent Python verifier, capsule reader, and JavaScript resolver compare integer tokens against the same decimal boundary before constructing runtime numbers. This avoids Python arbitrary-precision behavior and JavaScript rounding differences.

The parser tests include:

- Maximum positive and negative accepted integers.
- Positive and negative one-step overflow.
- An extreme-length integer token.
- Live Python-JavaScript parser-outcome parity.

## Text-Profile Verification

The producer and independent verifier include direct tests for:

- The declared text-profile identity.
- Acceptance of composed and decomposed exact sequences.
- Distinct identity for different code-point sequences.
- Refusal of a frozen format character.
- Refusal of surrogate code points.
- Refusal of the frozen leading/trailing whitespace table.
- Permitted LF and TAB behavior.

The parity set adds Unicode-sensitive accepted and refused vectors. The live cross-check includes both vectors.

## Strict Canonical Verification

Ordinary ingestion does not require sorted keys, two-space indentation, or one LF terminator.

`--strict-canonical-input` and `--strict-canonical` require byte-canonical artifact form. Use them for published artifacts, frozen corpora, and reproducibility checks.

Canonicalize ordinary strict JSON with:

```text
python -B demo/ORL_Chat_Reference_Kernel_v2_0_0.py --canonicalize input.json --output canonical_input.json
```

## Graph-Depth Verification

`MAX_GRAPH_DEPTH = 256` counts dependency edges, not actions.

`256 dependency edges / 257 actions -> admitted`

`257 dependency edges / 258 actions -> REFUSED`

## Browser Laboratories

The Structural Laboratory runs the embedded 17-vector parity set. The Capsule Laboratory creates, verifies, and compares privacy-separated capsule states.

## Verification Reports

Public reports and deterministic receipts are under `VERIFY/`.

## Hash Policy

The selected manifest covers 14 files: four core implementations, six principal verifiers, the shared verification runner, and three corpus or vector roots. It is a byte-integrity surface, not a semantic correctness or certification claim.

## Verification Boundary

Passing checks establish conformance only within the declared schemas, rules, text profile, limits, evidence boundary, and supplied implementations. They do not establish source authenticity, authorization, legal validity, safety, or production qualification.
