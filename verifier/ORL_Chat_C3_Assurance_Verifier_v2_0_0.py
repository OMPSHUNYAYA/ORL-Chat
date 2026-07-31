#!/usr/bin/env python3

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL_PATH = ROOT / "demo" / "ORL_Chat_Reference_Kernel_v2_0_0.py"
INDEPENDENT_PATH = ROOT / "verifier" / "ORL_Chat_Independent_Verifier_v2_0_0.py"
CAPSULE_PATH = ROOT / "demo" / "ORL_Chat_Conversation_State_Capsule_v2_0_0.py"
GENERATOR_PATH = ROOT / "verifier" / "ORL_Chat_Capsule_Vector_Generator_v2_0_0.py"
HOSTILE_ROOT = ROOT / "hostile"
FALSIFICATION_ROOT = ROOT / "falsification"
ASSURANCE_PROFILE = "ORL-CHAT-C3-ASSURANCE-2-C01"
HOSTILE_MANIFEST_PROFILE = "ORL-CHAT-HOSTILE-CORPUS-2-C01"
FALSIFICATION_MANIFEST_PROFILE = "ORL-CHAT-FALSIFICATION-CORPUS-2-C01"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


kernel = load_module("orl_chat_kernel_c3", KERNEL_PATH)
independent = load_module("orl_chat_independent_c3", INDEPENDENT_PATH)
capsule_lib = load_module("orl_chat_capsule_c3", CAPSULE_PATH)
generator = load_module("orl_chat_capsule_generator_c3", GENERATOR_PATH)


def set_path(value, path, replacement):
    result = deepcopy(value)
    cursor = result
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = replacement
    return result


def base_document():
    return deepcopy(generator.scenario_documents()["corrected-resolved"])


def expected_refused(document, substring=None):
    top_errors = kernel.exact_fields(document, ["context", "observations", "boundary"], "input") if isinstance(document, dict) else ["input: must be an object"]
    if top_errors:
        result = kernel.make_refusal(top_errors)
    else:
        result = kernel.resolve_conversation_bundle(document.get("context"), document.get("observations"), document.get("boundary"), run_self_verify=True)
    if result.get("result") != "REFUSED":
        return False
    if substring is None:
        return True
    return any(substring in item for item in result.get("errors", []))


def object_hostile_cases():
    base = base_document()
    cases = []

    def add(name, document, reason):
        cases.append((name, document, reason))

    doc = deepcopy(base); doc["extra"] = True; add("top-level-extra-field", doc, None)
    doc = deepcopy(base); doc["context"]["schema"] = "unsupported"; add("context-schema", doc, "context.schema")
    doc = deepcopy(base); doc["context"]["ruleset_profile"] = "unsupported"; add("context-ruleset", doc, "ruleset_profile")
    doc = deepcopy(base); doc["context"]["execution_authority"] = "EXECUTE"; add("context-authority", doc, "execution_authority")
    doc = deepcopy(base); doc["context"]["participation"]["profile"] = "MAJORITY"; add("participation-profile", doc, "participation.profile")
    doc = deepcopy(base); doc["context"]["participation"]["participants"] = ["alice", "alice"]; add("participant-duplicate", doc, "participants")
    doc = deepcopy(base); doc["context"]["participation"]["threshold"] = -1; add("negative-threshold", doc, "threshold")
    doc = deepcopy(base); doc["observations"] = "not-an-array"; add("observations-not-array", doc, "observations")
    doc = deepcopy(base); doc["observations"][0]["extra"] = True; add("observation-extra-field", doc, "unsupported field extra")
    doc = deepcopy(base); doc["observations"][0]["source"] = ""; add("observation-empty-source", doc, "source")
    doc = deepcopy(base); doc["observations"][0]["action"]["kind"] = "ACCEPT"; add("unsupported-action-kind", doc, "kind")
    doc = deepcopy(base); doc["observations"][1]["action"]["targets"] = []; add("missing-relation-target", doc, "targets")
    doc = deepcopy(base); doc["observations"][1]["action"]["targets"] = ["amend-5pm"]; add("self-target", doc, "self-target")
    doc = deepcopy(base); doc["observations"][1]["action"]["topic_id"] = "other-topic"; add("cross-topic-target", doc, "cross-topic")
    doc = deepcopy(base); doc["observations"][1]["action"]["conversation_id"] = "other-conversation"; add("cross-conversation-target", doc, "conversation_id")
    doc = deepcopy(base); doc["observations"][2]["action"]["actor"] = "mallory"; add("nonparticipant-signal", doc, "actor is not admitted")
    doc = deepcopy(base); conflict = deepcopy(doc["observations"][0]); conflict["source"] = "other-node"; doc["observations"].append(conflict); doc["boundary"] = kernel.make_boundary("OPEN", []); add("observation-ref-conflict", doc, "observation_ref content conflict")
    doc = deepcopy(base); conflict = deepcopy(doc["observations"][1]); conflict["action"]["declared_value"] = "7 PM"; conflict["observation_ref"] = "obs-conflicting-action"; doc["observations"].append(conflict); doc["boundary"] = kernel.make_boundary("OPEN", []); add("action-ref-conflict", doc, "action_ref content conflict")
    doc = deepcopy(base); doc["boundary"]["schema"] = "unsupported"; add("boundary-schema", doc, "boundary.schema")
    doc = deepcopy(base); doc["boundary"]["state"] = "FINAL"; add("boundary-state", doc, "boundary.state")
    doc = deepcopy(base); doc["boundary"]["expected_observation_refs"].append(doc["boundary"]["expected_observation_refs"][0]); add("boundary-duplicate-ref", doc, "expected_observation_refs")
    doc = deepcopy(base); doc["observations"][0]["action"]["declared_value"] = 1.5; add("floating-declared-value", doc, "floating-point")
    doc = deepcopy(base); value = "leaf"; [None for _ in range(18)];
    for _ in range(18): value = [value]
    doc["observations"][0]["action"]["declared_value"] = value; add("declared-value-depth", doc, "maximum nesting depth")
    doc = deepcopy(base); doc["observations"][0]["presentation"] = "bad\rtext"; add("presentation-carriage-return", doc, "presentation")
    doc = deepcopy(base); doc["observations"][0]["action"]["topic_id"] = "bad\u200btopic"; add("identifier-frozen-format", doc, "format")
    doc = deepcopy(base); doc["context"] = []; add("context-not-object", doc, "context")
    return cases


def raw_hostile_cases():
    base = base_document()
    canonical = kernel.canonical_artifact_text(base)
    duplicate_key = canonical.replace('  "boundary": {', '  "boundary": null,\n  "boundary": {', 1)
    float_number = canonical.replace('"threshold": 2', '"threshold": 2.5', 1)
    noncanonical = json.dumps(base, ensure_ascii=False, sort_keys=False, separators=(",", ":"))
    bom = "\ufeff" + canonical
    trailing = canonical + " \n"
    integer_above = b'{"value":9007199254740992}\n'
    integer_below = b'{"value":-9007199254740992}\n'
    integer_extreme = ('{"value":' + '9' * 1024 + '}\n').encode("ascii")
    return [
        ("duplicate-json-key", duplicate_key.encode("utf-8"), False),
        ("floating-json-number", float_number.encode("utf-8"), False),
        ("integer-above-exact-range", integer_above, False),
        ("integer-below-exact-range", integer_below, False),
        ("integer-extreme-length", integer_extreme, False),
        ("utf8-bom", bom.encode("utf-8"), False),
        ("noncanonical-json", noncanonical.encode("utf-8"), True),
        ("trailing-content", trailing.encode("utf-8"), True),
    ]


def generate_fixtures():
    object_dir = HOSTILE_ROOT / "inputs"
    raw_dir = HOSTILE_ROOT / "raw"
    object_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, document, reason in object_hostile_cases():
        path = object_dir / (name + ".json")
        kernel.write_json_document(path, document)
        entries.append({
            "name": name,
            "kind": "resolver-input",
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "expected_result": "REFUSED",
            "expected_reason_substring": reason,
        })
    for name, raw, strict_only in raw_hostile_cases():
        path = raw_dir / (name + ".json")
        path.write_bytes(raw)
        entries.append({
            "name": name,
            "kind": "strict-parser",
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "expected_result": "REFUSED",
            "strict_canonical_only": strict_only,
        })
    basis = {
        "profile": HOSTILE_MANIFEST_PROFILE,
        "version": "2.0.0",
        "entries": entries,
        "execution_authority": "NONE",
    }
    manifest = deepcopy(basis)
    manifest["manifest_id"] = capsule_lib.identity("hostile_manifest", HOSTILE_MANIFEST_PROFILE, basis)
    capsule_lib.write_json(HOSTILE_ROOT / "ORL_Chat_Hostile_Corpus_Manifest_v2_0_0.json", manifest)

    corrected_bundle = kernel.resolve_conversation_bundle(**{
        "context": base_document()["context"],
        "observations": base_document()["observations"],
        "boundary": base_document()["boundary"],
        "run_self_verify": True,
    })
    corrected_capsule = capsule_lib.create_capsule(corrected_bundle)
    FALSIFICATION_ROOT.mkdir(parents=True, exist_ok=True)
    mutations = [
        ("bundle-conversation-id", "bundle", set_path(corrected_bundle, ["public_receipt", "conversation_id"], "tampered")),
        ("bundle-graph-root", "bundle", set_path(corrected_bundle, ["graph", "graph_root"], "graph_" + "0" * 64)),
        ("bundle-topic-value", "bundle", set_path(corrected_bundle, ["topics", "receipts", 0, "resolved_declared_value"], "9 PM")),
        ("bundle-boundary-state", "bundle", set_path(corrected_bundle, ["boundary", "state"], "OPEN")),
        ("bundle-public-receipt-id", "bundle", set_path(corrected_bundle, ["public_receipt", "public_receipt_id"], "public_receipt_" + "0" * 64)),
        ("bundle-private-bundle-id", "bundle", set_path(corrected_bundle, ["private_bundle_id"], "private_bundle_" + "0" * 64)),
        ("bundle-action-content", "bundle", set_path(corrected_bundle, ["inputs", "observations", 1, "action", "declared_value"], "8 PM")),
        ("bundle-observation-source", "bundle", set_path(corrected_bundle, ["inputs", "observations", 0, "source"], "tampered-node")),
        ("capsule-boundary-state", "capsule", set_path(corrected_capsule, ["boundary_state"], "OPEN")),
        ("capsule-topic-state", "capsule", set_path(corrected_capsule, ["topics", 0, "state"], "ABSTAIN")),
        ("capsule-action-id", "capsule", set_path(corrected_capsule, ["action_ids", 0], "action_" + "0" * 64)),
        ("capsule-witness", "capsule", set_path(corrected_capsule, ["topics", 0, "witness_codes"], ["STATE_RESOLVED"])),
    ]
    falsification_entries = []
    for name, kind, artifact in mutations:
        path = FALSIFICATION_ROOT / (name + ".json")
        capsule_lib.write_json(path, artifact)
        falsification_entries.append({
            "name": name,
            "kind": kind,
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "expected_result": "FAIL",
        })
    basis = {
        "profile": FALSIFICATION_MANIFEST_PROFILE,
        "version": "2.0.0",
        "entries": falsification_entries,
        "execution_authority": "NONE",
    }
    manifest = deepcopy(basis)
    manifest["manifest_id"] = capsule_lib.identity("falsification_manifest", FALSIFICATION_MANIFEST_PROFILE, basis)
    capsule_lib.write_json(FALSIFICATION_ROOT / "ORL_Chat_Falsification_Corpus_Manifest_v2_0_0.json", manifest)
    print("ORL-Chat C3 fixture generation")
    print("hostile: " + str(len(entries)))
    print("falsification: " + str(len(falsification_entries)))
    print("result: PASS")


def long_chain_document(length, cycle=False):
    conversation_id = "conversation-depth-" + str(length) + ("-cycle" if cycle else "")
    context = kernel.make_context(
        conversation_id,
        "depth-assurance",
        kernel.make_participation("NO_ENDORSEMENT_REQUIRED", participants=[]),
    )
    actions = []
    if cycle:
        for index in range(length):
            ref = "amend-" + str(index)
            target = "amend-" + str((index + 1) % length)
            actions.append(kernel.make_action(ref, conversation_id, "depth", "actor", "AMEND", index, [target]))
    else:
        actions.append(kernel.make_action("proposal-0", conversation_id, "depth", "actor", "PROPOSE", 0))
        for index in range(1, length):
            actions.append(kernel.make_action("amend-" + str(index), conversation_id, "depth", "actor", "AMEND", index, ["proposal-0" if index == 1 else "amend-" + str(index - 1)]))
    observations = [kernel.make_observation("obs-" + str(index), "node-" + str(index % 3), action, "") for index, action in enumerate(actions)]
    boundary = kernel.make_boundary("SEALED", [item["observation_ref"] for item in observations])
    return kernel.make_input(context, observations, boundary)


def run_assurance():
    checks = []

    def check(group, name, condition):
        checks.append((group, name, bool(condition)))

    generate_fixtures()

    for name, document, reason in object_hostile_cases():
        check("HOSTILE", name, expected_refused(document, reason))

    for name, raw, strict_only in raw_hostile_cases():
        path = HOSTILE_ROOT / "raw" / (name + ".json")
        refused = False
        try:
            if strict_only:
                kernel.read_json_document(path, strict_canonical=True)
            else:
                kernel.read_json_document(path, strict_canonical=False)
        except Exception:
            refused = True
        check("PARSER", name, refused)

    for length in (1, 2, 4, 8, 16, 32, 64, 128, 256, 257):
        document = long_chain_document(length, cycle=False)
        bundle = kernel.resolve_conversation_bundle(document["context"], document["observations"], document["boundary"], run_self_verify=True)
        state = bundle.get("topics", {}).get("receipts", [{}])[0].get("state")
        check("GRAPH_DEPTH", "chain-" + str(length), bundle.get("result") == "ACCEPTED" and state == "RESOLVED" and independent.compare_bundle(bundle)["valid"])

    document = long_chain_document(258, cycle=False)
    bundle = kernel.resolve_conversation_bundle(document["context"], document["observations"], document["boundary"], run_self_verify=True)
    check("GRAPH_DEPTH", "chain-258-refused", bundle.get("result") == "REFUSED" and bundle.get("errors") == ["action amend-257: dependency chain exceeds maximum depth"] and independent.compare_bundle(bundle)["valid"])

    deep_example = kernel.read_json_document(ROOT / "examples" / "ORL_Chat_deep_chain_Input_v2_0_0.json", strict_canonical=True)
    deep_bundle = kernel.resolve_conversation_bundle(deep_example["context"], deep_example["observations"], deep_example["boundary"], run_self_verify=True)
    check("GRAPH_DEPTH", "canonical-deep-chain", deep_bundle.get("result") == "REFUSED" and deep_bundle.get("errors") == ["action amend-0001: dependency chain exceeds maximum depth"] and independent.compare_bundle(deep_bundle)["valid"])

    maximum_document = long_chain_document(4096, cycle=False)
    maximum_bundle = kernel.resolve_conversation_bundle(maximum_document["context"], maximum_document["observations"], maximum_document["boundary"], run_self_verify=True)
    check("GRAPH_DEPTH", "chain-4096-refused", maximum_bundle.get("result") == "REFUSED" and independent.compare_bundle(maximum_bundle)["valid"])

    for length in (2, 4, 8, 16, 32, 64, 128, 257):
        document = long_chain_document(length, cycle=True)
        bundle = kernel.resolve_conversation_bundle(document["context"], document["observations"], document["boundary"], run_self_verify=True)
        state = bundle.get("topics", {}).get("receipts", [{}])[0].get("state")
        reason = bundle.get("topics", {}).get("receipts", [{}])[0].get("reason_code")
        check("GRAPH_CYCLE", "cycle-" + str(length), bundle.get("result") == "ACCEPTED" and state == "ABSTAIN" and reason == "DEPENDENCY_CYCLE" and independent.compare_bundle(bundle)["valid"])

    document = long_chain_document(258, cycle=True)
    bundle = kernel.resolve_conversation_bundle(document["context"], document["observations"], document["boundary"], run_self_verify=True)
    check("GRAPH_CYCLE", "cycle-258-refused", bundle.get("result") == "REFUSED" and independent.compare_bundle(bundle)["valid"])

    base = base_document()
    under_participants = deepcopy(base)
    under_participants["context"] = kernel.make_context("c-participants", "resource", kernel.make_participation("DECLARED_THRESHOLD", participants=["p" + str(i) for i in range(256)], threshold=1))
    under_participants["observations"] = []
    under_participants["boundary"] = kernel.make_boundary("OPEN", [])
    check("RESOURCE", "participants-256", kernel.resolve_conversation_bundle(under_participants["context"], [], under_participants["boundary"])["result"] == "ACCEPTED")
    over_participants = deepcopy(under_participants)
    over_participants["context"]["participation"]["participants"].append("p256")
    check("RESOURCE", "participants-257", kernel.resolve_conversation_bundle(over_participants["context"], [], over_participants["boundary"])["result"] == "REFUSED")

    one = deepcopy(base["observations"][0])
    observations_4096 = [deepcopy(one) for _ in range(4096)]
    check("RESOURCE", "observations-4096", kernel.resolve_conversation_bundle(base["context"], observations_4096, kernel.make_boundary("OPEN", []))["result"] == "ACCEPTED")
    observations_4097 = observations_4096 + [deepcopy(one)]
    check("RESOURCE", "observations-4097", kernel.resolve_conversation_bundle(base["context"], observations_4097, kernel.make_boundary("OPEN", []))["result"] == "REFUSED")

    for field, accepted_length, refused_length in (
        ("identifier", 128, 129),
        ("presentation", 8192, 8193),
        ("value", 8192, 8193),
    ):
        accepted = deepcopy(base)
        refused = deepcopy(base)
        if field == "identifier":
            for observation in accepted["observations"]:
                observation["action"]["topic_id"] = "x" * accepted_length
            for observation in refused["observations"]:
                observation["action"]["topic_id"] = "x" * refused_length
        elif field == "presentation":
            accepted["observations"][0]["presentation"] = "x" * accepted_length
            refused["observations"][0]["presentation"] = "x" * refused_length
        else:
            accepted["observations"][0]["action"]["declared_value"] = "x" * accepted_length
            refused["observations"][0]["action"]["declared_value"] = "x" * refused_length
        accepted["boundary"] = kernel.make_boundary("OPEN", [])
        refused["boundary"] = kernel.make_boundary("OPEN", [])
        check("RESOURCE", field + "-accepted", kernel.resolve_conversation_bundle(accepted["context"], accepted["observations"], accepted["boundary"])["result"] == "ACCEPTED")
        check("RESOURCE", field + "-refused", kernel.resolve_conversation_bundle(refused["context"], refused["observations"], refused["boundary"])["result"] == "REFUSED")

    corrected = kernel.resolve_conversation_bundle(base["context"], base["observations"], base["boundary"], run_self_verify=True)
    corrected_capsule = capsule_lib.create_capsule(corrected)
    check("CAPSULE", "create-verify", capsule_lib.verify_capsule_against_bundle(corrected_capsule, corrected)["valid"])
    check("CAPSULE", "privacy-value", "5 PM" not in capsule_lib.canonical_json(corrected_capsule))
    check("CAPSULE", "privacy-presentation", "Correction: meet at 5 PM" not in capsule_lib.canonical_json(corrected_capsule))
    check("CAPSULE", "authority-none", corrected_capsule["execution_authority"] == "NONE")

    vector_set = capsule_lib.read_json(ROOT / "capsules" / "ORL_Chat_Conversation_State_Capsule_Vectors_v2_0_0.json", strict_canonical=True)
    capsule_by_name = {}
    for entry in vector_set["capsules"]:
        capsule = capsule_lib.read_json(ROOT / entry["capsule_file"], strict_canonical=True)
        capsule_by_name[entry["name"]] = capsule
        check("CAPSULE", "vector-" + entry["name"], capsule_lib.verify_capsule(capsule)["valid"] and capsule["capsule_id"] == entry["capsule_id"])
        for topic in capsule["topics"]:
            for code in topic["witness_codes"]:
                check("WITNESS", entry["name"] + "-" + code, not capsule_lib.explain_witness_code(code).startswith("Unsupported"))

    for entry in vector_set["comparisons"]:
        left = capsule_by_name[entry["left"]]
        if entry["right"] == "tampered-capsule":
            right = capsule_lib.read_json(ROOT / "capsules" / "artifacts" / "tampered-capsule_v2_0_0.json", strict_canonical=True)
        else:
            right = capsule_by_name[entry["right"]]
        result = capsule_lib.compare_capsules(left, right)
        check("COMPARISON", entry["name"], result["relation"] == entry["expected_relation"] and result["comparison_id"] == entry["comparison_id"])

    falsification_manifest = capsule_lib.read_json(FALSIFICATION_ROOT / "ORL_Chat_Falsification_Corpus_Manifest_v2_0_0.json", strict_canonical=True)
    for entry in falsification_manifest["entries"]:
        artifact = capsule_lib.read_json(ROOT / entry["file"], strict_canonical=True)
        if entry["kind"] == "bundle":
            detected = not independent.compare_bundle(artifact)["valid"]
        else:
            detected = not capsule_lib.verify_capsule(artifact)["valid"]
        check("FALSIFICATION", entry["name"], detected)

    for index, path in enumerate([
        ["conversation_resolution_id"],
        ["private_bundle_id"],
        ["public_receipt", "public_receipt_id"],
        ["graph", "graph_root"],
        ["evidence", "action_set_id"],
        ["evidence", "observation_set_id"],
        ["boundary", "boundary_receipt_id"],
        ["topics", "topic_receipt_root"],
    ]):
        prefix = path[-1].replace("_id", "")
        mutated = set_path(corrected, path, prefix + "_" + str(index) * 64)
        check("MUTATION", "bundle-id-" + str(index), not independent.compare_bundle(mutated)["valid"])

    capsule_paths = [
        ["capsule_id"], ["context_id"], ["conversation_resolution_id"], ["source_public_receipt_id"],
        ["source_private_bundle_id"], ["boundary_receipt_id"], ["action_set_id"], ["observation_set_id"], ["graph_root"],
    ]
    for index, path in enumerate(capsule_paths):
        mutated = set_path(corrected_capsule, path, path[-1].replace("_id", "") + "_" + str(index) * 64)
        check("MUTATION", "capsule-id-" + str(index), not capsule_lib.verify_capsule(mutated)["valid"])

    groups = defaultdict(lambda: [0, 0])
    for group, _, passed in checks:
        groups[group][1] += 1
        if passed:
            groups[group][0] += 1
    all_pass = True
    for group in sorted(groups):
        passed, total = groups[group]
        all_pass = all_pass and passed == total
        print(group + ": " + str(passed) + "/" + str(total) + (" PASS" if passed == total else " FAIL"))
    passed = sum(1 for _, _, ok in checks if ok)
    print("TOTAL: " + str(passed) + "/" + str(len(checks)) + (" PASS" if all_pass else " FAIL"))
    return all_pass, groups, len(checks), passed


def write_report(groups, total, passed):
    lines = [
        "ORL-Chat v2.0.0 C3 Adversarial Assurance and Conversation-State Capsule",
        "",
    ]
    for group in sorted(groups):
        gp, gt = groups[group]
        lines.append(group + ": " + str(gp) + "/" + str(gt) + (" PASS" if gp == gt else " FAIL"))
    lines.extend([
        "TOTAL: " + str(passed) + "/" + str(total) + (" PASS" if passed == total else " FAIL"),
        "",
        "Scope:",
        "- Strict hostile-input refusal.",
        "- Graph-depth and dependency-cycle assurance within declared resource bounds.",
        "- Boundary resource checks.",
        "- Conversation-state capsule creation, privacy separation, verification, and comparison.",
        "- Falsification and deterministic mutation detection.",
        "- No execution authority is granted.",
        "",
    ])
    path = ROOT / "VERIFY" / "ORL_Chat_C3_Assurance_Verification_Report_v2_0_0.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ORL_Chat_C3_Assurance_Verifier_v2_0_0.py")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--generate-fixtures", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)
    if args.generate_fixtures and not args.self_test:
        generate_fixtures()
        return 0
    if args.self_test:
        passed, groups, total, count = run_assurance()
        if args.write_report:
            write_report(groups, total, count)
        return 0 if passed else 1
    parser.error("choose --self-test or --generate-fixtures")


if __name__ == "__main__":
    sys.exit(main())
