#!/usr/bin/env python3

import argparse
import difflib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
KERNEL_PATH = ROOT / "demo" / "ORL_Chat_Reference_Kernel_v2_0_0.py"
RESOLVER_PATH = ROOT / "demo" / "ORL_Chat_Browser_Resolver_v2_0_0.js"
HOSTILE_MANIFEST_PATH = ROOT / "hostile" / "ORL_Chat_Hostile_Corpus_Manifest_v2_0_0.json"
PROFILE = "ORL-CHAT-CROSS-IMPLEMENTATION-CHECK-2-D01"

NODE_DRIVER = r'''
const fs = require("fs");
const ORL = require(process.argv[2]);
const inputPath = process.argv[3];
const strict = process.argv[4] === "strict";

function errorCode(message) {
  if (message.startsWith("duplicate JSON object key:")) return "DUPLICATE_KEY";
  if (message.startsWith("floating-point JSON numbers are not supported:")) return "FLOATING_POINT_NUMBER";
  if (message.startsWith("non-standard JSON numeric constant is not supported:")) return "NON_STANDARD_NUMBER";
  if (message.startsWith("integer exceeds exact interoperable range:")) return "INTEGER_OUT_OF_EXACT_RANGE";
  if (message === "UTF-8 BOM is not supported") return "UTF8_BOM";
  if (message === "JSON document exceeds maximum byte length") return "INPUT_TOO_LARGE";
  if (message.startsWith("JSON document is not in canonical artifact form")) return "NONCANONICAL_ARTIFACT";
  if (message === "JSON document must be strict UTF-8") return "INVALID_UTF8";
  if (message.startsWith("invalid JSON:") || message.includes(" at position ")) return "INVALID_JSON";
  return "STRICT_JSON_ERROR";
}

let text;
try {
  const bytes = fs.readFileSync(inputPath);
  if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
    process.stdout.write(JSON.stringify({
      stage: "STRICT_JSON",
      error_code: "UTF8_BOM",
      message: "UTF-8 BOM is not supported",
      text_profile: ORL.PROFILES.text
    }));
    process.exit(0);
  }
  text = new TextDecoder("utf-8", {fatal: true, ignoreBOM: true}).decode(bytes);
} catch (error) {
  process.stdout.write(JSON.stringify({
    stage: "STRICT_JSON",
    error_code: "INVALID_UTF8",
    message: "JSON document must be strict UTF-8",
    text_profile: ORL.PROFILES.text
  }));
  process.exit(0);
}

let document;
try {
  document = ORL.strictJsonLoads(text, strict);
} catch (error) {
  const message = String(error && error.message ? error.message : error);
  process.stdout.write(JSON.stringify({
    stage: "STRICT_JSON",
    error_code: errorCode(message),
    message,
    text_profile: ORL.PROFILES.text
  }));
  process.exit(0);
}

const bundle = ORL.resolveDocument(document, true);
const reduced = ORL.bundleWithoutSelfVerification(bundle);
const valid = bundle.self_verification ? bundle.self_verification.valid : null;
process.stdout.write(JSON.stringify({
  stage: "RESOLUTION",
  result: bundle.result,
  valid,
  text_profile: ORL.PROFILES.text,
  canonical: ORL.canonicalArtifactText(reduced)
}));
'''


def load_kernel():
    spec = importlib.util.spec_from_file_location("orl_chat_cross_check_kernel", KERNEL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parser_error_code(message):
    if message.startswith("duplicate JSON object key:"):
        return "DUPLICATE_KEY"
    if message.startswith("floating-point JSON numbers are not supported:"):
        return "FLOATING_POINT_NUMBER"
    if message.startswith("non-standard JSON numeric constant is not supported:"):
        return "NON_STANDARD_NUMBER"
    if message.startswith("integer exceeds exact interoperable range:"):
        return "INTEGER_OUT_OF_EXACT_RANGE"
    if message == "UTF-8 BOM is not supported":
        return "UTF8_BOM"
    if message == "JSON document exceeds maximum byte length":
        return "INPUT_TOO_LARGE"
    if message.startswith("JSON document is not in canonical artifact form"):
        return "NONCANONICAL_ARTIFACT"
    if message == "JSON document must be strict UTF-8":
        return "INVALID_UTF8"
    if message.startswith("invalid JSON:"):
        return "INVALID_JSON"
    return "STRICT_JSON_ERROR"


def python_side(kernel, input_path, strict_canonical):
    try:
        document = kernel.read_json_document(input_path, strict_canonical=strict_canonical)
    except kernel.StrictJSONError as exc:
        message = str(exc)
        return {
            "stage": "STRICT_JSON",
            "error_code": parser_error_code(message),
            "message": message,
            "text_profile": kernel.TEXT_PROFILE,
        }
    fields = kernel.exact_fields(document, ["context", "observations", "boundary"], "input")
    bundle = kernel.make_refusal(fields) if fields else kernel.resolve_conversation_bundle(
        document["context"], document["observations"], document["boundary"]
    )
    reduced = kernel.bundle_without_self_verification(bundle)
    return {
        "stage": "RESOLUTION",
        "result": bundle.get("result"),
        "valid": bundle.get("self_verification", {}).get("valid"),
        "text_profile": kernel.TEXT_PROFILE,
        "canonical": kernel.canonical_artifact_text(reduced),
        "bundle": bundle,
    }


def node_side(node_bin, input_path, strict_canonical, timeout):
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", newline="\n", delete=False) as handle:
        handle.write(NODE_DRIVER)
        driver_path = Path(handle.name)
    try:
        completed = subprocess.run(
            [
                node_bin,
                str(driver_path),
                str(RESOLVER_PATH),
                str(input_path),
                "strict" if strict_canonical else "open",
            ],
            capture_output=True,
            timeout=timeout,
        )
    finally:
        driver_path.unlink(missing_ok=True)
    try:
        stdout = completed.stdout.decode("utf-8")
        stderr = completed.stderr.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("Node resolver output is not valid UTF-8") from exc
    if completed.returncode != 0:
        raise RuntimeError(stderr.strip() or stdout.strip() or "Node resolver failed")
    return json.loads(stdout)


def compare_one(kernel, node_bin, label, input_path, strict_canonical, timeout, show_diff):
    python = python_side(kernel, input_path, strict_canonical)
    javascript = node_side(node_bin, input_path, strict_canonical, timeout)
    stage_match = python["stage"] == javascript.get("stage")
    text_profile_match = javascript.get("text_profile") == kernel.TEXT_PROFILE
    canonical_match = None
    self_verification_match = None
    error_code_match = None
    error_message_match = None

    if stage_match and python["stage"] == "STRICT_JSON":
        error_code_match = python["error_code"] == javascript.get("error_code")
        error_message_match = (
            python["message"] == javascript.get("message")
            if python["error_code"] == "INTEGER_OUT_OF_EXACT_RANGE"
            else True
        )
        passed = text_profile_match and error_code_match and error_message_match
    elif stage_match and python["stage"] == "RESOLUTION":
        canonical_match = python["canonical"] == javascript.get("canonical")
        self_verification_match = python["valid"] == javascript.get("valid") and python["valid"] in (True, None)
        passed = text_profile_match and canonical_match and self_verification_match
    else:
        passed = False

    if not passed and show_diff:
        if not stage_match:
            print("  stage: python=" + python["stage"] + " javascript=" + str(javascript.get("stage")))
        if not text_profile_match:
            print("  text_profile: python=" + kernel.TEXT_PROFILE + " javascript=" + str(javascript.get("text_profile")))
        if python["stage"] == "STRICT_JSON" and javascript.get("stage") == "STRICT_JSON":
            if not error_code_match:
                print("  error_code: python=" + python["error_code"] + " javascript=" + str(javascript.get("error_code")))
            if not error_message_match:
                print("  message: python=" + python["message"])
                print("  message: javascript=" + str(javascript.get("message")))
        if python["stage"] == "RESOLUTION" and javascript.get("stage") == "RESOLUTION":
            if not self_verification_match:
                print("  self_verification: python=" + str(python["valid"]) + " javascript=" + str(javascript.get("valid")))
            if not canonical_match:
                diff = difflib.unified_diff(
                    python["canonical"].splitlines(),
                    str(javascript.get("canonical", "")).splitlines(),
                    fromfile="python",
                    tofile="javascript",
                    lineterm="",
                )
                for line in list(diff)[:80]:
                    print("  " + line)

    try:
        display_path = str(Path(input_path).resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        display_path = str(input_path)

    record = {
        "label": label,
        "file": display_path,
        "stage": python["stage"],
        "text_profile": kernel.TEXT_PROFILE,
        "stage_match": stage_match,
        "text_profile_match": text_profile_match,
        "passed": passed,
    }
    if python["stage"] == "STRICT_JSON":
        record.update({
            "python_error_code": python["error_code"],
            "javascript_error_code": javascript.get("error_code"),
            "error_code_match": error_code_match,
            "error_message_match": error_message_match,
        })
    else:
        record.update({
            "result": python["result"],
            "python_self_verification": python["valid"],
            "javascript_self_verification": javascript.get("valid"),
            "canonical_sha256": kernel.sha256_text(python["canonical"]),
            "canonical_match": canonical_match,
            "self_verification_match": self_verification_match,
        })
    return record


def scenario_input(kernel, name, directory):
    path = Path(directory) / ("cross_check_" + name.replace("-", "_") + "_input.json")
    kernel.write_json_document(path, kernel.get_scenario(name))
    return path


def targets_from_args(kernel, args, directory):
    if args.all_scenarios:
        return [(name, scenario_input(kernel, name, directory), True) for name in kernel.scenario_names()]
    if args.all_examples:
        paths = sorted((ROOT / "examples").glob("ORL_Chat_*_Input_v2_0_0.json"))
        return [(path.stem, path, True) for path in paths]
    if args.all_parser_cases:
        manifest = kernel.read_json_document(HOSTILE_MANIFEST_PATH, strict_canonical=True)
        return [
            (
                entry["name"],
                ROOT / entry["file"],
                bool(entry.get("strict_canonical_only", False)),
            )
            for entry in manifest["entries"]
            if entry["kind"] == "strict-parser"
        ]
    if args.scenario is not None:
        if args.scenario not in set(kernel.scenario_names()):
            raise ValueError("unknown scenario: " + args.scenario)
        return [(args.scenario, scenario_input(kernel, args.scenario, directory), True)]
    return [(Path(args.input).name, Path(args.input), args.strict_canonical)]


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="ORL_Chat_Cross_Language_Cross_Check_v2_0_0.py",
        description="Compare Python and JavaScript outcomes for identical input bytes.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input")
    source.add_argument("--scenario")
    source.add_argument("--all-scenarios", action="store_true")
    source.add_argument("--all-examples", action="store_true")
    source.add_argument("--all-parser-cases", action="store_true")
    parser.add_argument("--strict-canonical", action="store_true")
    parser.add_argument("--node", default="node")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--no-diff", action="store_true")
    parser.add_argument("--receipt-output")
    args = parser.parse_args(argv or sys.argv[1:])

    kernel = load_kernel()
    records = []
    try:
        with tempfile.TemporaryDirectory() as workdir:
            for label, path, strict in targets_from_args(kernel, args, workdir):
                record = compare_one(
                    kernel,
                    args.node,
                    label,
                    path,
                    strict,
                    args.timeout,
                    not args.no_diff,
                )
                records.append(record)
                if record["passed"] and record["stage"] == "STRICT_JSON":
                    status = "PARSER PARITY"
                else:
                    status = "PARITY" if record["passed"] else "DIVERGENCE"
                print(label + ": " + status)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2

    passed = sum(1 for record in records if record["passed"])
    receipt_basis = {
        "profile": PROFILE,
        "version": kernel.VERSION,
        "architecture_profile": kernel.ARCHITECTURE_PROFILE,
        "ruleset_profile": kernel.RULESET_PROFILE,
        "text_profile": kernel.TEXT_PROFILE,
        "records": records,
        "passed": passed,
        "total": len(records),
    }
    receipt = dict(receipt_basis)
    receipt["cross_check_id"] = kernel.identity("cross_check", PROFILE, receipt_basis)
    if args.receipt_output:
        kernel.write_json_document(args.receipt_output, receipt)

    print("text_profile: " + kernel.TEXT_PROFILE)
    label = "PARSER PARITY" if records and all(record["stage"] == "STRICT_JSON" for record in records) else "PARITY"
    print("TOTAL: " + str(passed) + "/" + str(len(records)) + " " + label)
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
