#!/usr/bin/env python3

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL_PATH = ROOT / "demo" / "ORL_Chat_Reference_Kernel_v2_0_0.py"
RESOLVER_PATH = ROOT / "demo" / "ORL_Chat_Browser_Resolver_v2_0_0.js"
PROFILE = "ORL-CHAT-SEEDED-PROPERTY-VERIFICATION-2-D01"
PRNG_PROFILE = "ORL-CHAT-SPLITMIX64-2-D01"

NODE_DRIVER = r'''
const fs = require("fs");
const ORL = require(process.argv[2]);
const documents = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const records = documents.map(function (document) {
  const bundle = ORL.resolveDocument(document, true);
  return {
    canonical: ORL.canonicalArtifactText(ORL.bundleWithoutSelfVerification(bundle)),
    text_profile: ORL.PROFILES.text
  };
});
process.stdout.write(JSON.stringify(records));
'''




class SplitMix64:
    MASK = (1 << 64) - 1

    def __init__(self, seed):
        self.state = seed & self.MASK

    def next_u64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & self.MASK
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & self.MASK
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & self.MASK
        return (value ^ (value >> 31)) & self.MASK

    def randbelow(self, upper):
        if upper <= 0:
            raise ValueError("upper bound must be positive")
        limit = (1 << 64) - ((1 << 64) % upper)
        while True:
            value = self.next_u64()
            if value < limit:
                return value % upper

    def shuffle(self, values):
        for index in range(len(values) - 1, 0, -1):
            target = self.randbelow(index + 1)
            values[index], values[target] = values[target], values[index]


def load_kernel():
    spec = importlib.util.spec_from_file_location("orl_chat_property_kernel", KERNEL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def structural_identity(bundle):
    if bundle["result"] == "REFUSED":
        return {
            "result": bundle["result"],
            "refusal_id": bundle["refusal_id"],
        }
    return {
        "result": bundle["result"],
        "conversation_resolution_id": bundle["conversation_resolution_id"],
        "private_bundle_id": bundle["private_bundle_id"],
        "public_receipt_id": bundle["public_receipt"]["public_receipt_id"],
        "context_id": bundle["context"]["context_id"],
        "action_set_id": bundle["evidence"]["action_set_id"],
        "observation_set_id": bundle["evidence"]["observation_set_id"],
        "graph_root": bundle["graph"]["graph_root"],
        "topic_receipt_root": bundle["topics"]["topic_receipt_root"],
        "boundary_receipt_id": bundle["boundary"]["boundary_receipt_id"],
    }


def make_case(kernel, rng, index):
    case_type = index % 7
    conversation_id = "property-conversation-" + str(index)
    participation = kernel.make_participation(
        "SINGLE_DECLARED_ENDORSER",
        participants=["alice", "bob"],
        threshold=1,
    )
    context = kernel.make_context(conversation_id, "seeded-property", participation)
    topic = "topic-" + str(index % 3)
    values = ["café", "cafe\u0301", "தமிழ்", "𐀀", {"mode": "bounded", "value": index}]
    value = deepcopy(values[rng.randbelow(len(values))])
    actions = []

    if case_type == 0:
        actions.append(kernel.make_action("proposal", conversation_id, topic, "alice", "PROPOSE", value))
        chain_length = 1 + rng.randbelow(4)
        target = "proposal"
        for position in range(chain_length):
            ref = "amend-" + str(position)
            actions.append(kernel.make_action(ref, conversation_id, topic, "alice", "AMEND", {"step": position, "value": deepcopy(value)}, [target]))
            target = ref
        actions.append(kernel.make_action("endorse", conversation_id, topic, "bob", "ENDORSE", None, [target]))
        expected = ("RESOLVED", "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED")
    elif case_type == 1:
        actions.extend([
            kernel.make_action("proposal-a", conversation_id, topic, "alice", "PROPOSE", value),
            kernel.make_action("proposal-b", conversation_id, topic, "bob", "PROPOSE", "alternative-" + str(index)),
            kernel.make_action("endorse-a", conversation_id, topic, "alice", "ENDORSE", None, ["proposal-a"]),
        ])
        expected = ("ABSTAIN", "MULTIPLE_ACTIVE_PROPOSALS")
    elif case_type == 2:
        actions.extend([
            kernel.make_action("proposal-a", conversation_id, topic, "alice", "PROPOSE", value),
            kernel.make_action("proposal-b", conversation_id, topic, "bob", "PROPOSE", "alternative-" + str(index)),
            kernel.make_action("withdraw-b", conversation_id, topic, "bob", "WITHDRAW", None, ["proposal-b"]),
            kernel.make_action("endorse-a", conversation_id, topic, "alice", "ENDORSE", None, ["proposal-a"]),
        ])
        expected = ("RESOLVED", "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED")
    elif case_type == 3:
        actions.append(kernel.make_action("amend-missing", conversation_id, topic, "alice", "AMEND", value, ["missing-proposal"]))
        expected = ("INCOMPLETE", "MISSING_DEPENDENCY")
    elif case_type == 4:
        actions.extend([
            kernel.make_action("amend-a", conversation_id, topic, "alice", "AMEND", value, ["amend-b"]),
            kernel.make_action("amend-b", conversation_id, topic, "bob", "AMEND", "cycle-" + str(index), ["amend-a"]),
        ])
        expected = ("ABSTAIN", "DEPENDENCY_CYCLE")
    elif case_type == 5:
        actions.extend([
            kernel.make_action("proposal", conversation_id, topic, "alice", "PROPOSE", value),
            kernel.make_action("endorse", conversation_id, topic, "alice", "ENDORSE", None, ["proposal"]),
            kernel.make_action("object", conversation_id, topic, "alice", "OBJECT", None, ["proposal"]),
        ])
        expected = ("ABSTAIN", "PARTICIPANT_SIGNAL_CONFLICT")
    else:
        actions.extend([
            kernel.make_action("proposal", conversation_id, topic, "alice", "PROPOSE", value),
            kernel.make_action("object", conversation_id, topic, "bob", "OBJECT", None, ["proposal"]),
        ])
        expected = ("ABSTAIN", "ACTIVE_PROPOSAL_OBJECTED")

    observations = [
        kernel.make_observation("obs-" + str(position), "node-" + str(position % 3), action, "presentation-" + str(position))
        for position, action in enumerate(actions)
    ]
    rng.shuffle(observations)
    document = kernel.make_input(context, observations, kernel.make_boundary("OPEN"))
    return document, expected


def variants(kernel, document):
    baseline = deepcopy(document)
    reversed_document = deepcopy(document)
    reversed_document["observations"].reverse()
    parts = [[], [], []]
    for index, observation in enumerate(document["observations"]):
        parts[index % 3].append(deepcopy(observation))
    partitioned = deepcopy(document)
    partitioned["observations"] = kernel.merge_observation_sets(parts[2], parts[0], parts[1])
    duplicated = deepcopy(document)
    duplicated["observations"].append(deepcopy(duplicated["observations"][0]))
    return [baseline, reversed_document, partitioned, duplicated]


def node_resolve(node_bin, documents, timeout):
    with tempfile.TemporaryDirectory() as workdir:
        input_path = Path(workdir) / "property_inputs.json"
        driver_path = Path(workdir) / "property_driver.js"
        input_path.write_text(json.dumps(documents, ensure_ascii=False, allow_nan=False), encoding="utf-8", newline="\n")
        driver_path.write_text(NODE_DRIVER, encoding="utf-8", newline="\n")
        completed = subprocess.run(
            [node_bin, str(driver_path), str(RESOLVER_PATH), str(input_path)],
            capture_output=True,
            timeout=timeout,
        )
    try:
        stdout = completed.stdout.decode("utf-8")
        stderr = completed.stderr.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("Node resolver output is not valid UTF-8") from exc
    if completed.returncode != 0:
        raise RuntimeError(stderr.strip() or stdout.strip() or "Node resolver failed")
    return json.loads(stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="ORL_Chat_Seeded_Property_Verifier_v2_0_0.py",
        description="Run reproducible generated graph checks across Python and JavaScript.",
    )
    parser.add_argument("--seed", type=int, default=20260731)
    parser.add_argument("--cases", type=int, default=32)
    parser.add_argument("--node", default="node")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--receipt-output")
    args = parser.parse_args(argv or sys.argv[1:])
    if args.cases < 1 or args.cases > 1000:
        print("ERROR: --cases must be between 1 and 1000", file=sys.stderr)
        return 2

    kernel = load_kernel()
    rng = SplitMix64(args.seed)
    case_records = []
    all_documents = []
    case_variants = []
    for index in range(args.cases):
        document, expected = make_case(kernel, rng, index)
        generated = variants(kernel, document)
        start = len(all_documents)
        all_documents.extend(generated)
        case_variants.append((index, expected, generated, start))

    try:
        javascript_records = node_resolve(args.node, all_documents, args.timeout)
    except (OSError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2

    groups = defaultdict(lambda: [0, 0])

    def check(group, condition):
        groups[group][1] += 1
        if condition:
            groups[group][0] += 1
        return bool(condition)

    for index, expected, generated, start in case_variants:
        python_bundles = []
        parity = []
        for offset, document in enumerate(generated):
            bundle = kernel.resolve_conversation_bundle(document["context"], document["observations"], document["boundary"])
            python_bundles.append(bundle)
            python_text = kernel.canonical_artifact_text(kernel.bundle_without_self_verification(bundle))
            javascript = javascript_records[start + offset]
            parity.append(check("CROSS_LANGUAGE", javascript["text_profile"] == kernel.TEXT_PROFILE and javascript["canonical"] == python_text))

        baseline_identity = structural_identity(python_bundles[0])
        order_ok = check("ORDER", structural_identity(python_bundles[1]) == baseline_identity)
        partition_ok = check("PARTITION", structural_identity(python_bundles[2]) == baseline_identity)
        duplicate_ok = check("DUPLICATE", structural_identity(python_bundles[3]) == baseline_identity)
        receipt = python_bundles[0].get("topics", {}).get("receipts", [{}])[0]
        state_ok = check("STATE", receipt.get("state") == expected[0] and receipt.get("reason_code") == expected[1])
        case_records.append({
            "case": index,
            "expected_state": expected[0],
            "expected_reason": expected[1],
            "cross_language": all(parity),
            "order": order_ok,
            "partition": partition_ok,
            "duplicate": duplicate_ok,
            "state": state_ok,
        })

    passed = 0
    total = 0
    for group in sorted(groups):
        group_passed, group_total = groups[group]
        passed += group_passed
        total += group_total
        print(group + ": " + str(group_passed) + "/" + str(group_total) + (" PASS" if group_passed == group_total else " FAIL"))
    passed_cases = sum(1 for record in case_records if all((record["cross_language"], record["order"], record["partition"], record["duplicate"], record["state"])))
    print("PRNG_PROFILE: " + PRNG_PROFILE)
    print("CASES: " + str(passed_cases) + "/" + str(args.cases) + (" PASS" if passed_cases == args.cases else " FAIL"))
    print("ASSERTIONS: " + str(passed) + "/" + str(total) + (" PASS" if passed == total else " FAIL"))

    if args.receipt_output:
        basis = {
            "profile": PROFILE,
            "version": kernel.VERSION,
            "architecture_profile": kernel.ARCHITECTURE_PROFILE,
            "ruleset_profile": kernel.RULESET_PROFILE,
            "text_profile": kernel.TEXT_PROFILE,
            "prng_profile": PRNG_PROFILE,
            "seed": args.seed,
            "generated_cases": args.cases,
            "passed_cases": passed_cases,
            "assertions": total,
            "passed_assertions": passed,
            "records": case_records,
        }
        receipt = dict(basis)
        receipt["property_verification_id"] = kernel.identity("property_verification", PROFILE, basis)
        kernel.write_json_document(args.receipt_output, receipt)

    return 0 if passed == total and passed_cases == args.cases else 1


if __name__ == "__main__":
    raise SystemExit(main())
