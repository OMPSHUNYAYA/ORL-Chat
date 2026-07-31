#!/usr/bin/env python3

import argparse
import importlib.util
import sys
from pathlib import Path

PROFILE = "ORL-CHAT-CROSS-LANGUAGE-PARITY-2-D01"
VECTOR_PROFILE = "ORL-CHAT-CROSS-LANGUAGE-VECTOR-2-D01"


def load_kernel(root):
    path = root / "demo" / "ORL_Chat_Reference_Kernel_v2_0_0.py"
    spec = importlib.util.spec_from_file_location("orl_chat_reference_kernel", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected_record(kernel, bundle):
    core = kernel.bundle_without_self_verification(bundle)
    expected = {
        "result": bundle["result"],
        "canonical_bundle_sha256": kernel.sha256_text(kernel.canonical_json(core)),
    }
    if bundle["result"] == "REFUSED":
        expected["refusal_id"] = bundle["refusal_id"]
        expected["errors"] = list(bundle["errors"])
        return expected
    expected.update({
        "conversation_resolution_id": bundle["conversation_resolution_id"],
        "private_bundle_id": bundle["private_bundle_id"],
        "public_receipt_id": bundle["public_receipt"]["public_receipt_id"],
        "context_id": bundle["context"]["context_id"],
        "action_set_id": bundle["evidence"]["action_set_id"],
        "observation_set_id": bundle["evidence"]["observation_set_id"],
        "graph_root": bundle["graph"]["graph_root"],
        "topic_receipt_root": bundle["topics"]["topic_receipt_root"],
        "boundary_receipt_id": bundle["boundary"]["boundary_receipt_id"],
        "boundary_state": bundle["boundary"]["state"],
        "state_counts": bundle["topics"]["state_counts"],
        "topic_receipts": [
            {
                "topic_id": receipt["topic_id"],
                "state": receipt["state"],
                "reason_code": receipt["reason_code"],
                "topic_receipt_id": receipt["topic_receipt_id"],
                "resolved_action_id": receipt["resolved_action_id"],
                "resolved_declared_value": receipt["resolved_declared_value"],
            }
            for receipt in bundle["topics"]["receipts"]
        ],
    })
    return expected


def generate(root):
    kernel = load_kernel(root)
    vectors = []
    for path in sorted((root / "examples").glob("ORL_Chat_*_Input_v2_0_0.json")):
        name = path.name[len("ORL_Chat_"):-len("_Input_v2_0_0.json")]
        document = kernel.read_json_document(path, strict_canonical=True)
        bundle = kernel.resolve_conversation_bundle(
            document["context"],
            document["observations"],
            document["boundary"],
        )
        basis = {
            "profile": VECTOR_PROFILE,
            "name": name,
            "input": document,
            "expected": expected_record(kernel, bundle),
        }
        vector = dict(basis)
        vector["vector_id"] = kernel.identity("parity_vector", VECTOR_PROFILE, basis)
        vectors.append(vector)
    manifest_basis = {
        "profile": PROFILE,
        "version": kernel.VERSION,
        "architecture_profile": kernel.ARCHITECTURE_PROFILE,
        "ruleset_profile": kernel.RULESET_PROFILE,
        "text_profile": kernel.TEXT_PROFILE,
        "browser_resolver": "demo/ORL_Chat_Browser_Resolver_v2_0_0.js",
        "reference_kernel": "demo/ORL_Chat_Reference_Kernel_v2_0_0.py",
        "vector_ids": sorted(vector["vector_id"] for vector in vectors),
    }
    document = dict(manifest_basis)
    document["vectors"] = vectors
    document["parity_set_id"] = kernel.identity("parity_set", PROFILE, manifest_basis)
    return document, kernel


def main():
    parser = argparse.ArgumentParser(description="Generate ORL-Chat cross-language parity vectors.")
    parser.add_argument("--output", default="parity/ORL_Chat_Cross_Language_Parity_Vectors_v2_0_0.json")
    parser.add_argument("--verify-existing", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    document, kernel = generate(root)
    output = root / args.output
    expected_bytes = kernel.canonical_artifact_text(document).encode("utf-8")
    try:
        display_path = output.relative_to(root)
    except ValueError:
        display_path = output
    if args.verify_existing:
        valid = output.is_file() and output.read_bytes() == expected_bytes
        print("ORL-Chat cross-language vector reproducibility verification")
        print("result: " + ("PASS" if valid else "FAIL"))
        print("vectors: " + str(len(document["vectors"])))
        print("parity_set_id: " + document["parity_set_id"])
        print("file: " + str(display_path))
        return 0 if valid else 1
    kernel.write_json_document(output, document)
    print("ORL-Chat cross-language vector generation")
    print("result: PASS")
    print("vectors: " + str(len(document["vectors"])))
    print("parity_set_id: " + document["parity_set_id"])
    print("output: " + str(display_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
