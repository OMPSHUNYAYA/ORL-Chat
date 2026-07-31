# ORL-Chat v2.0.0 Quickstart

## Requirements

- Python 3.9 or later.
- Node.js 18 or later.
- A modern browser for the laboratories.

## Complete Verification

From `Public_Release`, use one command appropriate to the environment:

```text
python -B VERIFY_ALL.py
VERIFY_ALL.bat
./verify_all.sh
```

Expected final line:

```text
ORL-Chat v2.0.0 complete verification: PASS
```

## Resolve the Representative Scenario

```text
python -B demo/ORL_Chat_Reference_Kernel_v2_0_0.py --scenario corrected-instruction
```

## Canonicalize Ordinary Strict JSON

```text
python -B demo/ORL_Chat_Reference_Kernel_v2_0_0.py --canonicalize input.json --output canonical_input.json
```

Canonicalization writes sorted, two-space, LF-terminated JSON. It does not by itself establish semantic admission.

## Independently Verify a Frozen Bundle

```text
python -B verifier/ORL_Chat_Independent_Verifier_v2_0_0.py --verify examples/ORL_Chat_corrected_instruction_Bundle_v2_0_0.json --strict-canonical
```

## Cross-Check Both Live Implementations

```text
python -B verifier/ORL_Chat_Cross_Language_Cross_Check_v2_0_0.py --all-examples
```

Expected result:

```text
TOTAL: 17/17 PARITY
```

## Cross-Check Strict-Parser Outcomes

```text
python -B verifier/ORL_Chat_Cross_Language_Cross_Check_v2_0_0.py --all-parser-cases
```

Expected result:

```text
TOTAL: 8/8 PARSER PARITY
```

## Run Generated Properties

```text
python -B verifier/ORL_Chat_Seeded_Property_Verifier_v2_0_0.py --seed 20260731 --cases 32
```

Expected result:

```text
CASES: 32/32 PASS
ASSERTIONS: 256/256 PASS
```

## Open the Browser Laboratories

```text
python -m http.server 8000
```

Open:

```text
http://localhost:8000/demo/ORL_Chat_Structural_Lab_v2_0_0.html
http://localhost:8000/demo/ORL_Chat_Capsule_Lab_v2_0_0.html
```

Stop the server with `Ctrl+C`.

## Create and Verify a Capsule

```text
python -B demo/ORL_Chat_Conversation_State_Capsule_v2_0_0.py --create capsules/source_bundles/corrected-resolved_Bundle_v2_0_0.json --strict-canonical --output ORL_Chat_Capsule.json
python -B demo/ORL_Chat_Conversation_State_Capsule_v2_0_0.py --verify ORL_Chat_Capsule.json --strict-canonical
```

## Compare Capsules

```text
python -B demo/ORL_Chat_Conversation_State_Capsule_v2_0_0.py --compare capsulesrtifactsase-incomplete_Capsule_v2_0_0.json capsulesrtifacts\corrected-resolved_Capsule_v2_0_0.json --strict-canonical
```

Expected relation:

```text
SUPERSEDES
```

## Verify the Graph-Depth Refusal Vector

```text
python -B demo/ORL_Chat_Reference_Kernel_v2_0_0.py --input examples/ORL_Chat_deep_chain_Input_v2_0_0.json --strict-canonical-input
```

Expected result:

```text
REFUSED
```

`MAX_GRAPH_DEPTH = 256` counts dependency edges: 256 edges connecting 257 actions are admitted; 257 edges connecting 258 actions are refused.

## Boundary

All artifacts declare `execution_authority = NONE`. Verification does not establish factual truth, authenticated consent, legal agreement, authorization, or production suitability.
