# ⭐ ORL-Chat — Test Guide

**Deterministic Bounded Conversation-State Resolution**

This guide explains how to run and evaluate the current ORL-Chat demonstrations.

The governing relation is:

`same deduplicated supported message fragments + same resolver rules -> same bounded conversation-state result`

ORL-Chat is developed within the Shunyaya Framework.

---

# 1. Test Scope

The current repository contains two different demonstration types:

- a Python reference implementation
- a scripted browser presentation

The Python implementation performs the actual bounded resolver calculation and checks all `5! = 120` permutations of the committed five-message scenario.

The browser demonstration visually presents the same scenario but does not independently execute the full Python resolver or enumerate the `120` permutations.

Therefore:

- use the browser for visual understanding
- use the Python implementation for behavioral checking
- use the frozen SHA-256 file for artifact-identity checking

These are separate verification activities.

---

# 2. Repository Files Used

## Python reference implementation

`demo/orl_chat_demo.py`

## Browser demonstration

`demo/orl_chat_interactive_demo.html`

## Committed scenario input

`inputs/chat_fragments.json`

## Optional generated output

`outputs/orl_chat_result_general_chat_correction.json`

## Verification instructions

`VERIFY/VERIFY.txt`

## Frozen demo hashes

`VERIFY/FREEZE_DEMO_SHA256.txt`

---

# 3. Quick Visual Demonstration

Open:

`demo/orl_chat_interactive_demo.html`

No web server is required for the current browser presentation.

Use the controls:

- **Scramble Arrival**
- **Resolve Structure**
- **Replay Proof**
- **Reset**

The **Replay Proof** button should be interpreted as a scripted visual replay of the Python reference result.

It is not an independently reconstructed browser proof.

---

# 4. What the Browser Demonstration Shows

The browser presents:

- one traditional arrival-order view
- two initial partial node views
- a scripted fragment-sharing step
- explicit correction and confirmation relationships
- the expected final bounded result

The displayed final result is:

```text
State       = RESOLVED
Final Value = Meeting at 5 PM
```

The browser also displays labels such as:

```text
Permutation tested: 120
Proof verified: TRUE
```

These labels visually reproduce the expected Python result.

The browser itself does not currently:

- execute the full Python resolver
- enumerate all `120` permutations
- reconstruct the Python result hash
- establish Python-browser conformance

---

# 5. Browser Control Guide

## 5.1 Scramble Arrival

This control randomizes the displayed order in the traditional-chat panel.

It demonstrates that the visible presentation order can change.

It does not alter the committed Python input file or run the structural resolver.

Expected observation:

```text
Order Changed, Meaning Unclear
```

The randomization affects only the visual traditional-chat list.

---

## 5.2 Resolve Structure

This control plays the scripted ORL-Chat resolution sequence.

Expected visual stages include:

- Node-A begins incomplete
- Node-B begins incomplete
- fragments are shared
- explicit relationships are evaluated
- earlier proposals are removed
- the surviving proposal is confirmed
- the displayed state becomes `RESOLVED`

Expected final displayed value:

```text
Meeting at 5 PM
```

---

## 5.3 Replay Proof

This control:

- resets the visual presentation
- scrambles the traditional arrival view
- runs the scripted resolution sequence

It is useful for:

- first-time viewing
- presentations
- visual walkthroughs

It does not independently verify the Python implementation.

---

## 5.4 Reset Controls

The left reset restores the traditional-chat panel.

The right reset restores the ORL-Chat panel to its initial visual state.

Neither reset changes repository files.

---

# 6. Run the Python Reference Implementation

From the repository root, run:

```text
python demo/orl_chat_demo.py
```

On Windows, this may also be:

```text
py demo/orl_chat_demo.py
```

The script should load:

`inputs/chat_fragments.json`

and print the bounded scenario result.

---

# 7. Write the JSON Result

Run:

```text
python demo/orl_chat_demo.py --write-output
```

Expected output file:

`outputs/orl_chat_result_general_chat_correction.json`

The written file is sorted and formatted for human readability.

Compact canonical JSON serialization is used internally for signatures and SHA-256 hashing.

---

# 8. Expected Scenario Identity

Expected scenario name:

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

Expected primary topic:

```text
meeting_time
```

The exact primary topic should match the committed input file.

---

# 9. Expected Pre-Merge Results

The committed initial views are:

```text
Node-A = M1, M2
Node-B = M3, M4, M5
```

Expected local states before sharing:

```text
Node-A = INCOMPLETE
Node-B = INCOMPLETE
```

Expected certificate checks:

```text
node_a_incomplete_before = True
node_b_incomplete_before = True
both_incomplete_before   = True
```

Expected equality before sharing:

```text
converged_before_merge = False
```

The two nodes begin with materially different fragment collections.

---

# 10. Expected Post-Merge Results

After the scripted bounded sharing operation, both nodes receive the same deduplicated supported fragments.

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

Expected final text should correspond to the committed `M4` fragment.

Expected equality result:

```text
converged_after_merge = True
```

This means both nodes produce the same bounded resolver state after equal evidence is installed.

It does not establish an autonomous networking or consensus protocol.

---

# 11. Expected Permutation Check

The Python implementation deduplicates the committed fragments and evaluates every permutation.

For five unique fragments:

`5! = 120`

Expected result:

```text
checked_permutations     = 120
permutation_independence = True
```

The baseline state-signature hash should be present.

This is an exhaustive result for the committed five-message scenario under the current Python implementation.

It is not a universal order-independence proof for arbitrary conversations or implementations.

---

# 12. Expected Structural Check Summary

The current console output should report values equivalent to:

```text
Node-A incomplete first  : True
Node-B incomplete first  : True
Both incomplete first    : True
Resolved after merge     : True
Final value present      : True
Permutation independence : True
Permutations checked     : 120
```

Expected overall bounded invariant result:

```text
structural_invariant_passed = True
```

Some no-time, no-order, and no-sync fields in the current result object are declared as `True` rather than independently reconstructed.

They should therefore be interpreted only within the documented current-model boundary.

---

# 13. Message Relationship Check

The committed scenario should contain a relationship chain equivalent to:

```text
M1 = OPEN
M2 = REPLACE
M3 = RETRACT
M4 = REPLACE
M5 = CONFIRM
```

Expected structural effect:

```text
M1 and M2 do not remain the final active proposal
M3 participates in the declared correction chain
M4 remains the final active proposal
M5 confirms M4
```

Expected bounded result:

```text
one confirmed active proposal -> RESOLVED
```

The test does not establish unrestricted natural-language understanding.

---

# 14. Resolution-State Behavior

The implementation contains classification paths for:

- `RESOLVED`
- `INCOMPLETE`
- `ABSTAIN`

## RESOLVED

The current resolver returns `RESOLVED` when exactly one confirmed proposal remains active.

`count(confirmed_active_proposals) = 1 -> RESOLVED`

Under the current branch order, this takes precedence even if additional unconfirmed active proposals remain.

## ABSTAIN

The current resolver returns `ABSTAIN` when:

`count(confirmed_active_proposals) > 1`

or when:

`count(confirmed_active_proposals) = 0 AND count(active_proposals) > 1`

## INCOMPLETE

The current resolver returns `INCOMPLETE` when, for example:

- one active proposal lacks confirmation
- dependencies are missing
- no proposal can be resolved

The committed five-message scenario directly exercises `INCOMPLETE` and `RESOLVED`.

It does not directly exercise every `ABSTAIN`, cycle, malformed-input, or duplicate-insertion path.

---

# 15. Exact-Duplicate Behavior

The current duplicate key includes:

```text
id
topic
kind
text
value
targets
```

The intended current-model relation is:

`D(D(M)) = D(M)`

The committed implementation contains exact-duplicate absorption.

However, the main five-message scenario should not be treated as a complete duplicate-safety test unless duplicate vectors are separately included and asserted.

Exact-duplicate absorption does not prove:

- general replay prevention
- sender authentication
- safe identifier reuse
- transport idempotency
- message authenticity

---

# 16. Dependency and Cycle Behavior

The implementation contains paths for reasons including:

```text
cyclic_dependency
invalid_open
missing_targets
missing_dependency
dependency_not_satisfied
missing_value
unknown_kind
```

The main committed scenario does not exercise every path.

A later conformance suite should include dedicated vectors for:

- missing target
- cyclic dependency
- unknown kind
- missing value
- conflicting identifier reuse
- malformed required fields

---

# 17. Deterministic Repeatability Check

Run the unchanged Python command multiple times:

```text
python demo/orl_chat_demo.py
```

Expected stable fields include:

- scenario name
- message count
- node count
- primary topic
- pre-merge states
- post-merge state
- final declared value
- permutation count
- permutation result
- baseline state-signature hash
- replay certificate

For unchanged files, inputs, Python behavior, and resolver rules, these values should remain the same.

This is implementation repeatability.

It is not a universal cross-platform or cross-language conformance guarantee.

---

# 18. Result Hash Check

The implementation computes hashes from compact canonical JSON using:

```text
sort_keys = True
separators = (",", ":")
UTF-8 encoding
SHA-256
```

Expected relation:

`same canonical result bytes -> same SHA-256 hash`

The console should display:

- a state-signature hash
- a replay certificate hash

A stable hash shows deterministic identity for the current serialized result object.

It does not prove:

- semantic truth
- behavioral correctness
- message authenticity
- independent reconstruction
- security
- production safety

---

# 19. Frozen Artifact Hash Check

Follow:

`VERIFY/VERIFY.txt`

and compare the committed demo files against:

`VERIFY/FREEZE_DEMO_SHA256.txt`

Expected relation:

`same file bytes -> same SHA-256 hash`

A successful comparison establishes artifact identity only.

It does not establish that the program behaves correctly.

Regenerate frozen hashes only after intentional file changes and after completing the relevant behavioral checks.

---

# 20. Pass Criteria

The current committed reference scenario passes when all of the following are observed:

- the Python script executes without an unexpected exception
- the committed input file is loaded
- Node-A is `INCOMPLETE` before sharing
- Node-B is `INCOMPLETE` before sharing
- the nodes are unequal before sharing
- both nodes receive the same deduplicated supported evidence after sharing
- both nodes produce equal post-sharing resolver states
- the final state is `RESOLVED`
- the final message identifier is `M4`
- the final declared value is `Meeting at 5 PM`
- all `120` supplied-scenario permutations match the baseline resolver state
- the result hashes are produced
- repeated unchanged runs reproduce the same bounded results

---

# 21. Fail Criteria

The current scenario fails review if any of the following occurs:

- the script cannot load the committed input
- an unexpected exception occurs on the committed input
- either node is not `INCOMPLETE` before sharing
- the nodes incorrectly match before sharing
- the post-sharing node states differ
- the final state is not `RESOLVED`
- the final message identifier is not `M4`
- the final declared value is not `Meeting at 5 PM`
- fewer or more than `120` unique-fragment permutations are checked
- any tested permutation produces a different bounded state signature
- repeated unchanged runs produce materially different bounded results
- a frozen artifact hash fails without an intentional file change

---

# 22. What a Passing Result Establishes

A passing committed scenario establishes that the current Python implementation:

- loaded the committed supported fragments
- produced the documented pre-merge and post-merge states
- produced same-evidence node equality after scripted sharing
- selected the declared value `Meeting at 5 PM`
- reproduced the same bounded state across all `120` committed-fragment permutations
- generated deterministic hashes for the current serialized result

These are bounded implementation and scenario results.

---

# 23. What a Passing Result Does Not Establish

A passing result does not prove:

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
- immutable finality
- conflict repair
- complete replay prevention
- complete malformed-input safety
- universal order independence
- universal time independence
- Python-browser conformance
- production readiness
- safe operation on arbitrary or hostile input

---

# 24. Browser and Python Comparison

The browser and Python demonstrations currently have different roles.

## Python

The Python implementation:

- loads the committed JSON input
- executes the resolver
- compares node states
- evaluates all `120` permutations
- computes deterministic hashes
- optionally writes a result file

## Browser

The browser demonstration:

- visually scrambles a traditional arrival list
- visually presents partial node views
- plays a scripted structural-resolution sequence
- displays the expected Python result

The browser does not independently establish equality with the Python implementation.

A future revision should add a shared conformance corpus and execute the same resolver rules in both environments.

---

# 25. Suggested One-Minute Review Flow

1. Open `demo/orl_chat_interactive_demo.html`.
2. Click **Scramble Arrival**.
3. Click **Resolve Structure**.
4. Confirm that the displayed final value is `Meeting at 5 PM`.
5. Run `python demo/orl_chat_demo.py`.
6. Confirm both pre-merge states are `INCOMPLETE`.
7. Confirm the post-merge state is `RESOLVED`.
8. Confirm `converged_after_merge = True`.
9. Confirm `checked_permutations = 120`.
10. Confirm `permutation_independence = True`.
11. Run again and compare the stable result fields.
12. Check frozen file hashes separately.

---

# 26. Future Test Expansion

A stronger test suite should add:

- formal schema-validity vectors
- explicit invalid-input refusal vectors
- duplicate-insertion vectors
- conflicting identifier-reuse vectors
- missing-target vectors
- dependency-cycle vectors
- multiple-confirmed-proposal vectors
- multiple-unconfirmed-active-proposal vectors
- one-confirmed-plus-one-unconfirmed-active vectors
- multi-topic vectors
- large-graph vectors
- selected permutation corpora
- metamorphic property tests
- canonical byte-serialization vectors
- Python-browser conformance vectors
- independent receipt reconstruction
- ruleset-version binding
- structural-closure tests

Future target relation:

`same validated canonical message fragments + same ruleset version -> same independently verified bounded conversation-state result`

This stronger target is not part of the current demonstration.

---

# ⭐ Final Test Statement

The current ORL-Chat Python reference implementation passes its committed scenario when two initially incomplete nodes receive the same deduplicated supported five-message fragment set, produce the same `RESOLVED` bounded conversation state, select the declared value `Meeting at 5 PM`, and reproduce that state across all `120` permutations of the committed fragments.

The browser provides a visual replay of that result.

Neither demonstration establishes unrestricted language understanding, truth, delivery, consensus, security, finality, or production correctness.
