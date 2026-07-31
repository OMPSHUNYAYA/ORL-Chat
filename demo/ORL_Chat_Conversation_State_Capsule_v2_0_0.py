#!/usr/bin/env python3

import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path

VERSION = "2.0.0"
CAPSULE_PROFILE = "ORL-CHAT-CONVERSATION-STATE-CAPSULE-2-C01"
COMPARISON_PROFILE = "ORL-CHAT-CAPSULE-COMPARISON-2-C01"
VALUE_COMMITMENT_PROFILE = "ORL-CHAT-CAPSULE-VALUE-COMMITMENT-2-C01"
EXECUTION_AUTHORITY = "NONE"
SUPPORTED_RELATIONS = (
    "IDENTICAL",
    "COMPATIBLE",
    "SUPERSEDES",
    "DIVERGES",
    "INCOMPARABLE",
    "UNSUPPORTED",
)
CAPSULE_FIELDS = {
    "profile",
    "version",
    "architecture_profile",
    "ruleset_profile",
    "context_id",
    "conversation_id",
    "purpose_id",
    "conversation_resolution_id",
    "source_public_receipt_id",
    "source_private_bundle_id",
    "boundary_state",
    "boundary_receipt_id",
    "action_set_id",
    "observation_set_id",
    "action_ids",
    "observation_ids",
    "graph_root",
    "relationship_edges",
    "topics",
    "state_counts",
    "execution_authority",
    "capsule_id",
}
TOPIC_FIELDS = {
    "topic_id",
    "state",
    "reason_code",
    "active_action_ids",
    "resolved_action_id",
    "resolved_value_commitment",
    "topic_receipt_id",
    "participation_satisfied",
    "active_endorser_count",
    "active_objector_count",
    "witness_codes",
}
HEX_ID_RE = re.compile(r"^[a-z_]+_[0-9a-f]{64}$")


class CapsuleError(ValueError):
    pass


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def canonical_artifact_text(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n"


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def identity(prefix, profile, value):
    return prefix + "_" + sha256_text(canonical_json({"profile": profile, "value": value}))


def strict_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CapsuleError("duplicate JSON object key: " + key)
        result[key] = value
    return result


def reject_float(value):
    raise CapsuleError("floating-point JSON numbers are not supported: " + value)


def reject_constant(value):
    raise CapsuleError("non-standard JSON numeric constant is not supported: " + value)


def parse_exact_integer(value):
    maximum = "9007199254740991"
    digits = value[1:] if value.startswith("-") else value
    magnitude = digits.lstrip("0") or "0"
    if len(magnitude) > len(maximum) or (len(magnitude) == len(maximum) and magnitude > maximum):
        raise CapsuleError("integer exceeds exact interoperable range: " + value)
    return int(value)


def read_json(path, strict_canonical=False):
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CapsuleError("JSON document must be strict UTF-8") from exc
    if text.startswith("\ufeff"):
        raise CapsuleError("UTF-8 BOM is not supported")
    try:
        value = json.loads(
            text,
            object_pairs_hook=strict_pairs,
            parse_int=parse_exact_integer,
            parse_float=reject_float,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise CapsuleError("invalid JSON: " + str(exc)) from exc
    if strict_canonical and text != canonical_artifact_text(value):
        raise CapsuleError("JSON document is not in canonical artifact form")
    return value


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_artifact_text(value))


def without_field(value, field):
    result = deepcopy(value)
    result.pop(field, None)
    return result


def is_identity(value, prefix=None):
    if not isinstance(value, str) or not HEX_ID_RE.fullmatch(value):
        return False
    return prefix is None or value.startswith(prefix + "_")


def value_commitment(value):
    return identity("declared_value", VALUE_COMMITMENT_PROFILE, value)


def witness_codes(receipt, boundary_state):
    codes = [
        "STATE_" + receipt["state"],
        "REASON_" + receipt["reason_code"],
        "BOUNDARY_" + boundary_state,
    ]
    if receipt.get("participation") is None:
        codes.append("PARTICIPATION_NOT_EVALUATED")
    elif receipt["participation"].get("satisfied"):
        codes.append("PARTICIPATION_SATISFIED")
    else:
        codes.append("PARTICIPATION_INCOMPLETE")
    if receipt.get("active_action_ids"):
        codes.append("ACTIVE_FRONTIER_PRESENT")
    else:
        codes.append("ACTIVE_FRONTIER_EMPTY")
    if receipt.get("missing_dependencies"):
        codes.append("MISSING_DEPENDENCY_PRESENT")
    if receipt.get("cycle_action_refs"):
        codes.append("DEPENDENCY_CYCLE_PRESENT")
    if receipt.get("active_signal_conflicts"):
        codes.append("ACTIVE_SIGNAL_CONFLICT_PRESENT")
    if receipt.get("active_objectors"):
        codes.append("ACTIVE_OBJECTION_PRESENT")
    return sorted(set(codes))


def create_capsule(bundle):
    errors = validate_source_bundle(bundle)
    if errors:
        raise CapsuleError("source bundle is not capsule-admissible: " + "; ".join(errors))

    public = bundle["public_receipt"]
    topics = []
    for receipt in sorted(bundle["topics"]["receipts"], key=lambda item: item["topic_id"]):
        resolved_commitment = None
        if receipt["state"] == "RESOLVED":
            resolved_commitment = value_commitment(receipt["resolved_declared_value"])
        topics.append({
            "topic_id": receipt["topic_id"],
            "state": receipt["state"],
            "reason_code": receipt["reason_code"],
            "active_action_ids": sorted(receipt["active_action_ids"]),
            "resolved_action_id": receipt["resolved_action_id"],
            "resolved_value_commitment": resolved_commitment,
            "topic_receipt_id": receipt["topic_receipt_id"],
            "participation_satisfied": None if receipt["participation"] is None else bool(receipt["participation"]["satisfied"]),
            "active_endorser_count": len(receipt["active_endorsers"]),
            "active_objector_count": len(receipt["active_objectors"]),
            "witness_codes": witness_codes(receipt, bundle["boundary"]["state"]),
        })

    edges = []
    for edge in bundle["graph"]["edges"]:
        edges.append({
            "source_action_id": edge["source_action_id"],
            "relation": edge["relation"],
            "target_action_id": edge["target_action_id"],
        })
    edges.sort(key=lambda item: (item["source_action_id"], item["relation"], item["target_action_id"]))

    basis = {
        "profile": CAPSULE_PROFILE,
        "version": VERSION,
        "architecture_profile": bundle["architecture_profile"],
        "ruleset_profile": bundle["ruleset_profile"],
        "context_id": bundle["context"]["context_id"],
        "conversation_id": public["conversation_id"],
        "purpose_id": public["purpose_id"],
        "conversation_resolution_id": bundle["conversation_resolution_id"],
        "source_public_receipt_id": public["public_receipt_id"],
        "source_private_bundle_id": bundle["private_bundle_id"],
        "boundary_state": bundle["boundary"]["state"],
        "boundary_receipt_id": bundle["boundary"]["boundary_receipt_id"],
        "action_set_id": bundle["evidence"]["action_set_id"],
        "observation_set_id": bundle["evidence"]["observation_set_id"],
        "action_ids": sorted(item["action_id"] for item in bundle["evidence"]["actions"]),
        "observation_ids": sorted(item["observation_id"] for item in bundle["evidence"]["observations"]),
        "graph_root": bundle["graph"]["graph_root"],
        "relationship_edges": edges,
        "topics": topics,
        "state_counts": deepcopy(bundle["topics"]["state_counts"]),
        "execution_authority": EXECUTION_AUTHORITY,
    }
    capsule = deepcopy(basis)
    capsule["capsule_id"] = identity("conversation_state_capsule", CAPSULE_PROFILE, basis)
    return capsule


def validate_source_bundle(bundle):
    errors = []
    if not isinstance(bundle, dict):
        return ["bundle must be an object"]
    if bundle.get("result") != "ACCEPTED":
        errors.append("bundle result must be ACCEPTED")
    if bundle.get("execution_authority") != EXECUTION_AUTHORITY:
        errors.append("bundle execution_authority must be NONE")
    required = ["architecture_profile", "ruleset_profile", "context", "evidence", "graph", "topics", "boundary", "public_receipt", "conversation_resolution_id", "private_bundle_id"]
    for field in required:
        if field not in bundle:
            errors.append("bundle missing field " + field)
    if errors:
        return errors
    if not is_identity(bundle["context"].get("context_id"), "context"):
        errors.append("invalid context_id")
    if not is_identity(bundle["evidence"].get("action_set_id"), "action_set"):
        errors.append("invalid action_set_id")
    if not is_identity(bundle["evidence"].get("observation_set_id"), "observation_set"):
        errors.append("invalid observation_set_id")
    if not is_identity(bundle["graph"].get("graph_root"), "graph"):
        errors.append("invalid graph_root")
    if not is_identity(bundle["conversation_resolution_id"], "conversation_resolution"):
        errors.append("invalid conversation_resolution_id")
    if not is_identity(bundle["private_bundle_id"], "private_bundle"):
        errors.append("invalid private_bundle_id")
    if not is_identity(bundle["public_receipt"].get("public_receipt_id"), "public_receipt"):
        errors.append("invalid public_receipt_id")
    if bundle["public_receipt"].get("conversation_resolution_id") != bundle.get("conversation_resolution_id"):
        errors.append("public receipt conversation_resolution_id mismatch")
    if bundle["public_receipt"].get("execution_authority") != EXECUTION_AUTHORITY:
        errors.append("public receipt execution_authority must be NONE")
    action_ids = [item.get("action_id") for item in bundle["evidence"].get("actions", [])]
    observation_ids = [item.get("observation_id") for item in bundle["evidence"].get("observations", [])]
    if len(action_ids) != len(set(action_ids)) or any(not is_identity(item, "action") for item in action_ids):
        errors.append("invalid or duplicate action identity")
    if len(observation_ids) != len(set(observation_ids)) or any(not is_identity(item, "observation") for item in observation_ids):
        errors.append("invalid or duplicate observation identity")
    for receipt in bundle["topics"].get("receipts", []):
        if receipt.get("state") not in ("RESOLVED", "INCOMPLETE", "ABSTAIN"):
            errors.append("unsupported topic state")
        if not is_identity(receipt.get("topic_receipt_id"), "topic_receipt"):
            errors.append("invalid topic_receipt_id")
        if receipt.get("execution_authority") != EXECUTION_AUTHORITY:
            errors.append("topic execution_authority must be NONE")
        if receipt.get("state") == "RESOLVED":
            if receipt.get("resolved_action_id") is None or receipt.get("resolved_declared_value") is None:
                errors.append("resolved topic lacks resolved action or value")
    return errors


def verify_capsule(capsule):
    errors = []
    if not isinstance(capsule, dict):
        return {"valid": False, "errors": ["capsule must be an object"], "profile": CAPSULE_PROFILE}
    actual_fields = set(capsule.keys())
    if actual_fields != CAPSULE_FIELDS:
        for field in sorted(CAPSULE_FIELDS - actual_fields):
            errors.append("missing field " + field)
        for field in sorted(actual_fields - CAPSULE_FIELDS):
            errors.append("unsupported field " + field)
    if errors:
        return {"valid": False, "errors": errors, "profile": CAPSULE_PROFILE}
    if capsule["profile"] != CAPSULE_PROFILE:
        errors.append("unsupported capsule profile")
    if capsule["version"] != VERSION:
        errors.append("unsupported capsule version")
    if capsule["execution_authority"] != EXECUTION_AUTHORITY:
        errors.append("execution_authority must be NONE")
    for field, prefix in (
        ("context_id", "context"),
        ("conversation_resolution_id", "conversation_resolution"),
        ("source_public_receipt_id", "public_receipt"),
        ("source_private_bundle_id", "private_bundle"),
        ("boundary_receipt_id", "boundary_receipt"),
        ("action_set_id", "action_set"),
        ("observation_set_id", "observation_set"),
        ("graph_root", "graph"),
        ("capsule_id", "conversation_state_capsule"),
    ):
        if not is_identity(capsule[field], prefix):
            errors.append("invalid " + field)
    if capsule["boundary_state"] not in ("OPEN", "SEALED", "INCOMPLETE", "CONFLICT"):
        errors.append("unsupported boundary_state")
    for field, prefix in (("action_ids", "action"), ("observation_ids", "observation")):
        values = capsule[field]
        if not isinstance(values, list) or values != sorted(set(values)) or any(not is_identity(item, prefix) for item in values):
            errors.append(field + " must be a sorted unique identity array")
    if not isinstance(capsule["relationship_edges"], list):
        errors.append("relationship_edges must be an array")
    else:
        expected_edges = sorted(capsule["relationship_edges"], key=lambda item: (item.get("source_action_id", ""), item.get("relation", ""), item.get("target_action_id", "")))
        if capsule["relationship_edges"] != expected_edges:
            errors.append("relationship_edges must be canonically sorted")
        for edge in capsule["relationship_edges"]:
            if set(edge.keys()) != {"source_action_id", "relation", "target_action_id"}:
                errors.append("relationship edge field set is invalid")
                continue
            if edge["relation"] not in ("AMEND", "WITHDRAW", "ENDORSE", "OBJECT"):
                errors.append("unsupported relationship edge")
            if edge["source_action_id"] not in capsule["action_ids"] or edge["target_action_id"] not in capsule["action_ids"]:
                errors.append("relationship edge references an absent action")
    if not isinstance(capsule["topics"], list):
        errors.append("topics must be an array")
    else:
        topic_ids = []
        for topic in capsule["topics"]:
            if not isinstance(topic, dict) or set(topic.keys()) != TOPIC_FIELDS:
                errors.append("topic field set is invalid")
                continue
            topic_ids.append(topic["topic_id"])
            if topic["state"] not in ("RESOLVED", "INCOMPLETE", "ABSTAIN"):
                errors.append("unsupported topic state")
            if topic["active_action_ids"] != sorted(set(topic["active_action_ids"])):
                errors.append("active_action_ids must be sorted and unique")
            if any(item not in capsule["action_ids"] for item in topic["active_action_ids"]):
                errors.append("active action is absent from capsule action set")
            if topic["state"] == "RESOLVED":
                if not is_identity(topic["resolved_action_id"], "action"):
                    errors.append("resolved topic has invalid resolved_action_id")
                if not is_identity(topic["resolved_value_commitment"], "declared_value"):
                    errors.append("resolved topic has invalid value commitment")
            else:
                if topic["resolved_action_id"] is not None or topic["resolved_value_commitment"] is not None:
                    errors.append("unresolved topic must not carry a resolved action or value commitment")
            if not is_identity(topic["topic_receipt_id"], "topic_receipt"):
                errors.append("invalid topic_receipt_id")
            if topic["participation_satisfied"] not in (True, False, None):
                errors.append("invalid participation_satisfied value")
            if not isinstance(topic["active_endorser_count"], int) or topic["active_endorser_count"] < 0:
                errors.append("invalid active_endorser_count")
            if not isinstance(topic["active_objector_count"], int) or topic["active_objector_count"] < 0:
                errors.append("invalid active_objector_count")
            if not isinstance(topic["witness_codes"], list) or topic["witness_codes"] != sorted(set(topic["witness_codes"])):
                errors.append("witness_codes must be sorted and unique")
        if topic_ids != sorted(set(topic_ids)):
            errors.append("topics must be sorted and unique by topic_id")
    counts = {"RESOLVED": 0, "INCOMPLETE": 0, "ABSTAIN": 0}
    for topic in capsule.get("topics", []):
        if isinstance(topic, dict) and topic.get("state") in counts:
            counts[topic["state"]] += 1
    if capsule["state_counts"] != counts:
        errors.append("state_counts mismatch")
    expected_id = identity("conversation_state_capsule", CAPSULE_PROFILE, without_field(capsule, "capsule_id"))
    if capsule["capsule_id"] != expected_id:
        errors.append("capsule_id mismatch")
    return {
        "profile": CAPSULE_PROFILE,
        "valid": not errors,
        "errors": errors,
        "expected_capsule_id": expected_id,
    }


def verify_capsule_against_bundle(capsule, bundle):
    verification = verify_capsule(capsule)
    if not verification["valid"]:
        return verification
    try:
        expected = create_capsule(bundle)
    except CapsuleError as exc:
        return {"profile": CAPSULE_PROFILE, "valid": False, "errors": [str(exc)]}
    if canonical_json(capsule) != canonical_json(expected):
        return {
            "profile": CAPSULE_PROFILE,
            "valid": False,
            "errors": ["capsule does not reconstruct from the supplied bundle"],
            "expected_capsule_id": expected["capsule_id"],
        }
    return {"profile": CAPSULE_PROFILE, "valid": True, "errors": [], "expected_capsule_id": expected["capsule_id"]}


def topic_map(capsule):
    return {item["topic_id"]: item for item in capsule["topics"]}


def resolved_commitments_compatible(left, right):
    left_topics = topic_map(left)
    right_topics = topic_map(right)
    for topic_id in sorted(set(left_topics) & set(right_topics)):
        a = left_topics[topic_id]
        b = right_topics[topic_id]
        if a["state"] == "RESOLVED" and b["state"] == "RESOLVED":
            if a["resolved_value_commitment"] != b["resolved_value_commitment"]:
                return False
    return True


def materially_changes_state(left, right):
    left_topics = topic_map(left)
    right_topics = topic_map(right)
    for topic_id in sorted(set(left_topics) | set(right_topics)):
        a = left_topics.get(topic_id)
        b = right_topics.get(topic_id)
        if a is None or b is None:
            return True
        signature_a = (a["state"], a["reason_code"], tuple(a["active_action_ids"]), a["resolved_value_commitment"])
        signature_b = (b["state"], b["reason_code"], tuple(b["active_action_ids"]), b["resolved_value_commitment"])
        if signature_a != signature_b:
            return True
    return False


def compare_capsules(left, right):
    left_verification = verify_capsule(left)
    right_verification = verify_capsule(right)
    if not left_verification["valid"] or not right_verification["valid"]:
        basis = {
            "profile": COMPARISON_PROFILE,
            "relation": "UNSUPPORTED",
            "left_capsule_id": left.get("capsule_id") if isinstance(left, dict) else None,
            "right_capsule_id": right.get("capsule_id") if isinstance(right, dict) else None,
            "left_valid": left_verification["valid"],
            "right_valid": right_verification["valid"],
            "reasons": sorted(set(left_verification["errors"] + right_verification["errors"])),
        }
        result = deepcopy(basis)
        result["comparison_id"] = identity("capsule_comparison", COMPARISON_PROFILE, basis)
        return result

    if left["capsule_id"] == right["capsule_id"]:
        relation = "IDENTICAL"
        reasons = ["CAPSULE_IDENTITIES_MATCH"]
    else:
        comparable_fields = ("architecture_profile", "ruleset_profile", "context_id", "conversation_id", "purpose_id")
        mismatches = [field for field in comparable_fields if left[field] != right[field]]
        if mismatches:
            relation = "INCOMPARABLE"
            reasons = ["COMPARISON_CONTEXT_DIFFERS:" + field for field in mismatches]
        elif not resolved_commitments_compatible(left, right):
            relation = "DIVERGES"
            reasons = ["RESOLVED_VALUE_COMMITMENT_DIVERGES"]
        else:
            left_actions = set(left["action_ids"])
            right_actions = set(right["action_ids"])
            left_observations = set(left["observation_ids"])
            right_observations = set(right["observation_ids"])
            action_superset = right_actions > left_actions
            observation_superset = right_observations > left_observations
            if action_superset and materially_changes_state(left, right):
                relation = "SUPERSEDES"
                reasons = ["RIGHT_ACTION_SET_STRICTLY_EXTENDS_LEFT", "STRUCTURAL_STATE_CHANGED_WITHOUT_RESOLVED_VALUE_DIVERGENCE"]
            elif right_actions == left_actions and (observation_superset or left_observations > right_observations):
                relation = "COMPATIBLE"
                reasons = ["SAME_ACTION_SET_WITH_DIFFERENT_OBSERVATION_COVERAGE"]
            elif right_actions.issuperset(left_actions) or left_actions.issuperset(right_actions):
                relation = "COMPATIBLE"
                reasons = ["NESTED_ACTION_EVIDENCE_WITHOUT_RESOLVED_VALUE_DIVERGENCE"]
            else:
                relation = "COMPATIBLE"
                reasons = ["SAME_CONTEXT_WITHOUT_RESOLVED_VALUE_DIVERGENCE"]

    basis = {
        "profile": COMPARISON_PROFILE,
        "relation": relation,
        "left_capsule_id": left["capsule_id"],
        "right_capsule_id": right["capsule_id"],
        "left_valid": True,
        "right_valid": True,
        "reasons": reasons,
    }
    result = deepcopy(basis)
    result["comparison_id"] = identity("capsule_comparison", COMPARISON_PROFILE, basis)
    return result


def explain_witness_code(code):
    fixed = {
        "BOUNDARY_OPEN": "The observed evidence set is declared open.",
        "BOUNDARY_SEALED": "The declared evidence boundary exactly matches the observed references.",
        "BOUNDARY_INCOMPLETE": "The requested sealed boundary is missing declared observations.",
        "BOUNDARY_CONFLICT": "The requested sealed boundary contains unexpected observations or mixed boundary differences.",
        "PARTICIPATION_SATISFIED": "The declared participation profile is satisfied for the active proposal.",
        "PARTICIPATION_INCOMPLETE": "The declared participation profile is not yet satisfied.",
        "PARTICIPATION_NOT_EVALUATED": "Participation is not evaluated because no single eligible active proposal reached that stage.",
        "ACTIVE_FRONTIER_PRESENT": "At least one active proposal remains on the structural frontier.",
        "ACTIVE_FRONTIER_EMPTY": "No active proposal remains on the structural frontier.",
        "MISSING_DEPENDENCY_PRESENT": "At least one relationship action refers to an unavailable declared dependency.",
        "DEPENDENCY_CYCLE_PRESENT": "The topic contains a declared relationship cycle.",
        "ACTIVE_SIGNAL_CONFLICT_PRESENT": "The same admitted actor both endorsed and objected to an active proposal.",
        "ACTIVE_OBJECTION_PRESENT": "At least one admitted objection targets the active proposal.",
    }
    if code in fixed:
        return fixed[code]
    if code.startswith("STATE_"):
        return "The bounded topic state is " + code[6:] + "."
    if code.startswith("REASON_"):
        return "The governing resolver reason is " + code[7:] + "."
    return "Unsupported witness code: " + code


def self_test():
    checks = []

    def check(group, name, condition):
        checks.append((group, name, bool(condition)))

    minimal = {
        "profile": CAPSULE_PROFILE,
        "version": VERSION,
        "architecture_profile": "ORL-CHAT-ARCH-2-D01",
        "ruleset_profile": "ORL-CHAT-RULES-2-D01",
        "context_id": "context_" + "0" * 64,
        "conversation_id": "c",
        "purpose_id": "p",
        "conversation_resolution_id": "conversation_resolution_" + "1" * 64,
        "source_public_receipt_id": "public_receipt_" + "2" * 64,
        "source_private_bundle_id": "private_bundle_" + "3" * 64,
        "boundary_state": "OPEN",
        "boundary_receipt_id": "boundary_receipt_" + "4" * 64,
        "action_set_id": "action_set_" + "5" * 64,
        "observation_set_id": "observation_set_" + "6" * 64,
        "action_ids": [],
        "observation_ids": [],
        "graph_root": "graph_" + "7" * 64,
        "relationship_edges": [],
        "topics": [],
        "state_counts": {"RESOLVED": 0, "INCOMPLETE": 0, "ABSTAIN": 0},
        "execution_authority": "NONE",
    }
    minimal["capsule_id"] = identity("conversation_state_capsule", CAPSULE_PROFILE, minimal)
    check("CAPSULE", "minimal-valid", verify_capsule(minimal)["valid"])
    check("PARSER", "maximum positive integer", parse_exact_integer("9007199254740991") == 9007199254740991)
    check("PARSER", "maximum negative integer", parse_exact_integer("-9007199254740991") == -9007199254740991)
    for label, token in (("integer above exact range", "9007199254740992"), ("integer below exact range", "-9007199254740992"), ("extreme integer token", "9" * 1024)):
        refused = False
        try:
            parse_exact_integer(token)
        except CapsuleError:
            refused = True
        check("PARSER", label, refused)
    tampered = deepcopy(minimal)
    tampered["boundary_state"] = "SEALED"
    check("CAPSULE", "tamper-detected", not verify_capsule(tampered)["valid"])
    check("COMPARISON", "identical", compare_capsules(minimal, deepcopy(minimal))["relation"] == "IDENTICAL")
    malformed = deepcopy(minimal)
    malformed["profile"] = "unsupported"
    check("COMPARISON", "unsupported", compare_capsules(minimal, malformed)["relation"] == "UNSUPPORTED")
    other = deepcopy(minimal)
    other["conversation_id"] = "other"
    other["capsule_id"] = identity("conversation_state_capsule", CAPSULE_PROFILE, without_field(other, "capsule_id"))
    check("COMPARISON", "incomparable", compare_capsules(minimal, other)["relation"] == "INCOMPARABLE")
    for code in (
        "BOUNDARY_OPEN",
        "PARTICIPATION_SATISFIED",
        "STATE_RESOLVED",
        "REASON_ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED",
    ):
        check("WITNESS", code, not explain_witness_code(code).startswith("Unsupported"))

    groups = {}
    for group, _, passed in checks:
        groups.setdefault(group, [0, 0])
        groups[group][1] += 1
        if passed:
            groups[group][0] += 1
    for group in sorted(groups):
        passed, total = groups[group]
        print(group + ": " + str(passed) + "/" + str(total) + " PASS" if passed == total else group + ": " + str(passed) + "/" + str(total) + " FAIL")
    passed = sum(1 for _, _, ok in checks if ok)
    print("TOTAL: " + str(passed) + "/" + str(len(checks)) + (" PASS" if passed == len(checks) else " FAIL"))
    return passed == len(checks)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ORL_Chat_Conversation_State_Capsule_v2_0_0.py")
    parser.add_argument("--create")
    parser.add_argument("--output")
    parser.add_argument("--verify")
    parser.add_argument("--bundle")
    parser.add_argument("--compare", nargs=2, metavar=("LEFT", "RIGHT"))
    parser.add_argument("--comparison-output")
    parser.add_argument("--strict-canonical", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.self_test:
            return 0 if self_test() else 1
        if args.create:
            bundle = read_json(args.create, strict_canonical=args.strict_canonical)
            capsule = create_capsule(bundle)
            if args.output:
                write_json(args.output, capsule)
            print("ORL-Chat conversation-state capsule")
            print("result: PASS")
            print("capsule_id: " + capsule["capsule_id"])
            print("topics: " + str(len(capsule["topics"])))
            print("execution_authority: " + capsule["execution_authority"])
            return 0
        if args.verify:
            capsule = read_json(args.verify, strict_canonical=args.strict_canonical)
            if args.bundle:
                bundle = read_json(args.bundle, strict_canonical=args.strict_canonical)
                result = verify_capsule_against_bundle(capsule, bundle)
            else:
                result = verify_capsule(capsule)
            print("ORL-Chat capsule verification")
            print("result: " + ("PASS" if result["valid"] else "FAIL"))
            for error in result.get("errors", []):
                print("error: " + error)
            return 0 if result["valid"] else 1
        if args.compare:
            left = read_json(args.compare[0], strict_canonical=args.strict_canonical)
            right = read_json(args.compare[1], strict_canonical=args.strict_canonical)
            result = compare_capsules(left, right)
            if args.comparison_output:
                write_json(args.comparison_output, result)
            print("ORL-Chat capsule comparison")
            print("relation: " + result["relation"])
            print("comparison_id: " + result["comparison_id"])
            for reason in result["reasons"]:
                print("reason: " + reason)
            return 0 if result["relation"] != "UNSUPPORTED" else 1
        parser.error("choose --create, --verify, --compare, or --self-test")
    except (CapsuleError, OSError, ValueError) as exc:
        print("ORL-Chat capsule operation")
        print("result: FAIL")
        print("error: " + str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
