#!/usr/bin/env python3

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL_PATH = ROOT / "demo" / "ORL_Chat_Reference_Kernel_v2_0_0.py"
CAPSULE_PATH = ROOT / "demo" / "ORL_Chat_Conversation_State_Capsule_v2_0_0.py"
OUTPUT_ROOT = ROOT / "capsules"
VECTOR_PATH = OUTPUT_ROOT / "ORL_Chat_Conversation_State_Capsule_Vectors_v2_0_0.json"
VECTOR_PROFILE = "ORL-CHAT-CAPSULE-VECTOR-SET-2-C01"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


kernel = load_module("orl_chat_kernel", KERNEL_PATH)
capsule_lib = load_module("orl_chat_capsule", CAPSULE_PATH)


def fixed_context(conversation_id="conversation-capsule-lineage"):
    return kernel.make_context(
        conversation_id,
        "active-instruction",
        kernel.make_participation(
            "ALL_DECLARED_PARTICIPANTS",
            participants=["alice", "bob"],
            threshold=2,
        ),
    )


def observe(ref, source, action, presentation):
    return kernel.make_observation(ref, source, action, presentation)


def scenario_documents():
    conversation_id = "conversation-capsule-lineage"
    context = fixed_context(conversation_id)
    propose = kernel.make_action("proposal-3pm", conversation_id, "meeting-time", "alice", "PROPOSE", "3 PM")
    amend5 = kernel.make_action("amend-5pm", conversation_id, "meeting-time", "alice", "AMEND", "5 PM", ["proposal-3pm"])
    amend6 = kernel.make_action("amend-6pm", conversation_id, "meeting-time", "alice", "AMEND", "6 PM", ["proposal-3pm"])
    endorse5a = kernel.make_action("endorse-5pm-alice", conversation_id, "meeting-time", "alice", "ENDORSE", None, ["amend-5pm"])
    endorse5b = kernel.make_action("endorse-5pm-bob", conversation_id, "meeting-time", "bob", "ENDORSE", None, ["amend-5pm"])
    endorse6a = kernel.make_action("endorse-6pm-alice", conversation_id, "meeting-time", "alice", "ENDORSE", None, ["amend-6pm"])
    endorse6b = kernel.make_action("endorse-6pm-bob", conversation_id, "meeting-time", "bob", "ENDORSE", None, ["amend-6pm"])
    withdraw6 = kernel.make_action("withdraw-6pm", conversation_id, "meeting-time", "bob", "WITHDRAW", None, ["amend-6pm"])

    o_propose = observe("obs-proposal", "node-a", propose, "Meet at 3 PM")
    o_amend5 = observe("obs-amend-5", "node-a", amend5, "Correction: meet at 5 PM")
    o_endorse5a = observe("obs-endorse-5-a", "node-a", endorse5a, "Alice confirms 5 PM")
    o_endorse5b = observe("obs-endorse-5-b", "node-b", endorse5b, "Bob confirms 5 PM")
    o_amend6 = observe("obs-amend-6", "node-b", amend6, "Alternative correction: meet at 6 PM")
    o_endorse6a = observe("obs-endorse-6-a", "node-a", endorse6a, "Alice confirms 6 PM")
    o_endorse6b = observe("obs-endorse-6-b", "node-b", endorse6b, "Bob confirms 6 PM")
    o_withdraw6 = observe("obs-withdraw-6", "node-b", withdraw6, "Withdraw the 6 PM alternative")
    relay5 = observe("obs-amend-5-relay", "node-c", amend5, "Relayed correction: meet at 5 PM")

    def sealed(observations):
        return kernel.make_boundary("SEALED", [item["observation_ref"] for item in observations])

    base = [o_propose]
    corrected = [o_propose, o_amend5, o_endorse5a, o_endorse5b]
    alternative = [o_propose, o_amend6, o_endorse6a, o_endorse6b]
    competing = [o_propose, o_amend5, o_amend6, o_endorse5a, o_endorse5b]
    repaired = competing + [o_withdraw6]
    relay = corrected + [relay5]
    exact_duplicate = corrected + [deepcopy(o_amend5)]

    unrelated_context = fixed_context("conversation-capsule-unrelated")
    unrelated_propose = kernel.make_action("proposal-3pm", "conversation-capsule-unrelated", "meeting-time", "alice", "PROPOSE", "3 PM")
    unrelated_obs = [observe("obs-proposal", "node-a", unrelated_propose, "Meet at 3 PM")]

    return {
        "base-incomplete": kernel.make_input(context, base, sealed(base)),
        "corrected-resolved": kernel.make_input(context, corrected, sealed(corrected)),
        "corrected-exact-duplicate": kernel.make_input(context, exact_duplicate, sealed(corrected)),
        "corrected-relay": kernel.make_input(context, relay, sealed(relay)),
        "alternative-resolved": kernel.make_input(context, alternative, sealed(alternative)),
        "competing-amendments": kernel.make_input(context, competing, sealed(competing)),
        "withdrawal-repair": kernel.make_input(context, repaired, sealed(repaired)),
        "unrelated-context": kernel.make_input(unrelated_context, unrelated_obs, sealed(unrelated_obs)),
    }


def main():
    input_dir = OUTPUT_ROOT / "source_inputs"
    bundle_dir = OUTPUT_ROOT / "source_bundles"
    capsule_dir = OUTPUT_ROOT / "artifacts"
    comparison_dir = OUTPUT_ROOT / "comparisons"
    for directory in (input_dir, bundle_dir, capsule_dir, comparison_dir):
        directory.mkdir(parents=True, exist_ok=True)

    capsules = {}
    capsule_entries = []
    for name, document in scenario_documents().items():
        bundle = kernel.resolve_conversation_bundle(document["context"], document["observations"], document["boundary"], run_self_verify=True)
        if bundle.get("result") != "ACCEPTED" or not bundle.get("self_verification", {}).get("valid"):
            raise RuntimeError("scenario did not produce a verified bundle: " + name)
        capsule = capsule_lib.create_capsule(bundle)
        verification = capsule_lib.verify_capsule_against_bundle(capsule, bundle)
        if not verification["valid"]:
            raise RuntimeError("capsule did not verify: " + name)
        input_path = input_dir / (name + "_Input_v2_0_0.json")
        bundle_path = bundle_dir / (name + "_Bundle_v2_0_0.json")
        capsule_path = capsule_dir / (name + "_Capsule_v2_0_0.json")
        kernel.write_json_document(input_path, document)
        kernel.write_json_document(bundle_path, bundle)
        capsule_lib.write_json(capsule_path, capsule)
        capsules[name] = capsule
        capsule_entries.append({
            "name": name,
            "input_file": str(input_path.relative_to(ROOT)).replace("\\", "/"),
            "bundle_file": str(bundle_path.relative_to(ROOT)).replace("\\", "/"),
            "capsule_file": str(capsule_path.relative_to(ROOT)).replace("\\", "/"),
            "capsule_id": capsule["capsule_id"],
            "topic_states": {item["topic_id"]: item["state"] for item in capsule["topics"]},
        })

    tampered = deepcopy(capsules["corrected-resolved"])
    tampered["boundary_state"] = "OPEN"
    capsule_lib.write_json(capsule_dir / "tampered-capsule_v2_0_0.json", tampered)

    pairs = [
        ("identical-exact-duplicate", "corrected-resolved", "corrected-exact-duplicate", "IDENTICAL"),
        ("compatible-relay", "corrected-resolved", "corrected-relay", "COMPATIBLE"),
        ("supersedes-incomplete", "base-incomplete", "corrected-resolved", "SUPERSEDES"),
        ("supersedes-disagreement", "competing-amendments", "withdrawal-repair", "SUPERSEDES"),
        ("diverges-value", "corrected-resolved", "alternative-resolved", "DIVERGES"),
        ("incomparable-context", "corrected-resolved", "unrelated-context", "INCOMPARABLE"),
    ]
    comparisons = []
    for name, left_name, right_name, expected in pairs:
        result = capsule_lib.compare_capsules(capsules[left_name], capsules[right_name])
        if result["relation"] != expected:
            raise RuntimeError(name + " expected " + expected + " but received " + result["relation"])
        path = comparison_dir / (name + "_Comparison_v2_0_0.json")
        capsule_lib.write_json(path, result)
        comparisons.append({
            "name": name,
            "left": left_name,
            "right": right_name,
            "expected_relation": expected,
            "comparison_file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "comparison_id": result["comparison_id"],
        })

    unsupported = capsule_lib.compare_capsules(capsules["corrected-resolved"], tampered)
    if unsupported["relation"] != "UNSUPPORTED":
        raise RuntimeError("tampered capsule comparison must be UNSUPPORTED")
    unsupported_path = comparison_dir / "unsupported-tamper_Comparison_v2_0_0.json"
    capsule_lib.write_json(unsupported_path, unsupported)
    comparisons.append({
        "name": "unsupported-tamper",
        "left": "corrected-resolved",
        "right": "tampered-capsule",
        "expected_relation": "UNSUPPORTED",
        "comparison_file": str(unsupported_path.relative_to(ROOT)).replace("\\", "/"),
        "comparison_id": unsupported["comparison_id"],
    })

    basis = {
        "profile": VECTOR_PROFILE,
        "version": "2.0.0",
        "capsules": capsule_entries,
        "comparisons": comparisons,
        "execution_authority": "NONE",
    }
    vector_set = deepcopy(basis)
    vector_set["vector_set_id"] = capsule_lib.identity("capsule_vector_set", VECTOR_PROFILE, basis)
    capsule_lib.write_json(VECTOR_PATH, vector_set)
    print("ORL-Chat conversation-state capsule vector generation")
    print("result: PASS")
    print("capsules: " + str(len(capsule_entries)))
    print("comparisons: " + str(len(comparisons)))
    print("vector_set_id: " + vector_set["vector_set_id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
