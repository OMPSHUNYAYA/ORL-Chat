#!/usr/bin/env python3

import argparse
import hashlib
import itertools
import json
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

VERSION = "2.0.0"
ARCHITECTURE_PROFILE = "ORL-CHAT-ARCH-2-D01"
RULESET_PROFILE = "ORL-CHAT-RULES-2-D01"
TEXT_PROFILE = "ORL-CHAT-UNICODE-SCALAR-EXACT-2-D01"
CONTEXT_SCHEMA = "ORL-CHAT-CONTEXT-2-D01"
PARTICIPATION_SCHEMA = "ORL-CHAT-PARTICIPATION-2-D01"
ACTION_SCHEMA = "ORL-CHAT-ACTION-2-D01"
OBSERVATION_SCHEMA = "ORL-CHAT-OBSERVATION-2-D01"
BOUNDARY_SCHEMA = "ORL-CHAT-BOUNDARY-2-D01"
GRAPH_PROFILE = "ORL-CHAT-GRAPH-2-D01"
TOPIC_RECEIPT_PROFILE = "ORL-CHAT-TOPIC-RECEIPT-2-D01"
BOUNDARY_RECEIPT_PROFILE = "ORL-CHAT-BOUNDARY-RECEIPT-2-D01"
PUBLIC_RECEIPT_PROFILE = "ORL-CHAT-PUBLIC-RECEIPT-2-D01"
PRIVATE_BUNDLE_PROFILE = "ORL-CHAT-PRIVATE-BUNDLE-2-D01"
PRODUCER_VERIFICATION_PROFILE = "ORL-CHAT-PRODUCER-VERIFICATION-2-D01"
INDEPENDENT_VERIFICATION_PROFILE = "ORL-CHAT-INDEPENDENT-VERIFICATION-2-D01"
SELF_TEST_PROFILE = "ORL-CHAT-INDEPENDENT-VERIFIER-SELF-TEST-2-D01"
CORPUS_PROFILE = "ORL-CHAT-CORPUS-2-D01"
CORPUS_MANIFEST_PROFILE = "ORL-CHAT-CORPUS-MANIFEST-2-D01"
CORPUS_VERIFICATION_PROFILE = "ORL-CHAT-CORPUS-VERIFICATION-2-D01"
EXECUTION_AUTHORITY = "NONE"
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_IDENTIFIER_LENGTH = 128
MAX_PRESENTATION_LENGTH = 8192
MAX_VALUE_STRING_LENGTH = 8192
MAX_VALUE_DEPTH = 16
MAX_VALUE_NODES = 4096
MAX_ARRAY_LENGTH = 256
MAX_OBJECT_FIELDS = 256
MAX_OBSERVATIONS = 4096
MAX_PARTICIPANTS = 256
MAX_GRAPH_DEPTH = 256
MAX_SAFE_INTEGER = 9007199254740991
FROZEN_BOUNDARY_WHITESPACE_RANGES = (
    (0x0009, 0x000D),
    (0x0020, 0x0020),
    (0x0085, 0x0085),
    (0x00A0, 0x00A0),
    (0x1680, 0x1680),
    (0x2000, 0x200A),
    (0x2028, 0x2029),
    (0x202F, 0x202F),
    (0x205F, 0x205F),
    (0x3000, 0x3000),
)
FROZEN_FORMAT_RANGES = (
    (0x00AD, 0x00AD),
    (0x0600, 0x0605),
    (0x061C, 0x061C),
    (0x06DD, 0x06DD),
    (0x070F, 0x070F),
    (0x0890, 0x0891),
    (0x08E2, 0x08E2),
    (0x180E, 0x180E),
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x2064),
    (0x2066, 0x206F),
    (0xFEFF, 0xFEFF),
    (0xFFF9, 0xFFFB),
    (0x110BD, 0x110BD),
    (0x110CD, 0x110CD),
    (0x13430, 0x1343F),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0001, 0xE0001),
    (0xE0020, 0xE007F),
)
ACTION_KINDS = ("PROPOSE", "AMEND", "WITHDRAW", "ENDORSE", "OBJECT")
PROPOSAL_KINDS = ("PROPOSE", "AMEND")
RELATION_KINDS = ("AMEND", "WITHDRAW", "ENDORSE", "OBJECT")
PARTICIPATION_PROFILES = (
    "NO_ENDORSEMENT_REQUIRED",
    "SINGLE_DECLARED_ENDORSER",
    "ALL_DECLARED_PARTICIPANTS",
    "EXACT_DECLARED_PARTICIPANT_SET",
    "DECLARED_THRESHOLD",
)


class VerificationInputError(ValueError):
    pass


class DuplicateKeyError(VerificationInputError):
    pass


def stable_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def canonical_artifact_text(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    ) + "\n"


def digest_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derive_id(prefix, profile, value):
    return prefix + "_" + digest_text(stable_json({"profile": profile, "value": value}))


def duplicate_safe_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError("duplicate JSON object key: " + key)
        result[key] = value
    return result


def deny_float(value):
    raise VerificationInputError("floating-point JSON numbers are not supported: " + value)


def deny_constant(value):
    raise VerificationInputError("non-standard JSON numeric constant is not supported: " + value)


def parse_exact_integer(value):
    digits = value[1:] if value.startswith("-") else value
    magnitude = digits.lstrip("0") or "0"
    maximum = str(MAX_SAFE_INTEGER)
    if len(magnitude) > len(maximum) or (len(magnitude) == len(maximum) and magnitude > maximum):
        raise VerificationInputError("integer exceeds exact interoperable range: " + value)
    return int(value)


def parse_json_text(text):
    try:
        return json.loads(
            text,
            object_pairs_hook=duplicate_safe_pairs,
            parse_int=parse_exact_integer,
            parse_float=deny_float,
            parse_constant=deny_constant,
        )
    except VerificationInputError:
        raise
    except json.JSONDecodeError as exc:
        raise VerificationInputError("invalid JSON: " + str(exc)) from exc


def load_json_file(path, strict_canonical=False):
    path = Path(path)
    raw = path.read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise VerificationInputError("JSON document exceeds maximum byte length")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationInputError("JSON document must be strict UTF-8") from exc
    if text.startswith("\ufeff"):
        raise VerificationInputError("UTF-8 BOM is not supported")
    value = parse_json_text(text)
    if strict_canonical and text != canonical_artifact_text(value):
        raise VerificationInputError("JSON document is not in canonical artifact form with sorted keys, two-space indentation, and one LF terminator")
    return value


def save_json_file(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = canonical_artifact_text(value)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def exact_field_errors(record, fields, label):
    if not isinstance(record, dict):
        return [label + ": must be an object"]
    actual = set(record.keys())
    expected = set(fields)
    errors = []
    for field in sorted(expected - actual):
        errors.append(label + ": missing field " + field)
    for field in sorted(actual - expected):
        errors.append(label + ": unsupported field " + field)
    return errors


def is_frozen_boundary_whitespace(code_point):
    return any(start <= code_point <= end for start, end in FROZEN_BOUNDARY_WHITESPACE_RANGES)


def has_frozen_boundary_whitespace(value):
    if value == "":
        return False
    return is_frozen_boundary_whitespace(ord(value[0])) or is_frozen_boundary_whitespace(ord(value[-1]))


def is_frozen_format_code_point(code_point):
    return any(start <= code_point <= end for start, end in FROZEN_FORMAT_RANGES)


def is_frozen_control_code_point(code_point):
    return 0x0000 <= code_point <= 0x001F or 0x007F <= code_point <= 0x009F


def is_surrogate_code_point(code_point):
    return 0xD800 <= code_point <= 0xDFFF


def bad_identifier_character(value):
    for char in value:
        code_point = ord(char)
        if is_frozen_control_code_point(code_point) or is_frozen_format_code_point(code_point) or is_surrogate_code_point(code_point):
            return True
    return False


def bad_text_character(value):
    for char in value:
        code_point = ord(char)
        if code_point in (0x0009, 0x000A):
            continue
        if is_frozen_control_code_point(code_point) or is_frozen_format_code_point(code_point) or is_surrogate_code_point(code_point):
            return True
    return False


def identifier_errors(value, label):
    if not isinstance(value, str):
        return [label + ": must be a string"]
    errors = []
    if value == "":
        errors.append(label + ": must not be empty")
    if len(value) > MAX_IDENTIFIER_LENGTH:
        errors.append(label + ": exceeds maximum length")
    if has_frozen_boundary_whitespace(value):
        errors.append(label + ": leading or trailing whitespace is not allowed")
    if bad_identifier_character(value):
        errors.append(label + ": control, format, and surrogate characters are not allowed")
    return errors


def text_errors(value, label):
    if not isinstance(value, str):
        return [label + ": must be a string"]
    errors = []
    if len(value) > MAX_PRESENTATION_LENGTH:
        errors.append(label + ": exceeds maximum length")
    if bad_text_character(value):
        errors.append(label + ": unsupported control, format, carriage-return, or surrogate character")
    return errors


def value_errors(value, label="declared_value"):
    errors = []
    nodes = [0]

    def inspect(item, path, depth):
        nodes[0] += 1
        if nodes[0] > MAX_VALUE_NODES:
            errors.append(label + ": exceeds maximum node count")
            return
        if depth > MAX_VALUE_DEPTH:
            errors.append(path + ": exceeds maximum nesting depth")
            return
        if item is None or isinstance(item, bool):
            return
        if isinstance(item, int) and not isinstance(item, bool):
            if abs(item) > MAX_SAFE_INTEGER:
                errors.append(path + ": integer exceeds exact interoperable range")
            return
        if isinstance(item, float):
            errors.append(path + ": floating-point values are not supported")
            return
        if isinstance(item, str):
            if len(item) > MAX_VALUE_STRING_LENGTH:
                errors.append(path + ": string exceeds maximum length")
            if bad_text_character(item):
                errors.append(path + ": unsupported control, format, carriage-return, or surrogate character")
            return
        if isinstance(item, list):
            if len(item) > MAX_ARRAY_LENGTH:
                errors.append(path + ": array exceeds maximum length")
                return
            for index, child in enumerate(item):
                inspect(child, path + "[" + str(index) + "]", depth + 1)
            return
        if isinstance(item, dict):
            if len(item) > MAX_OBJECT_FIELDS:
                errors.append(path + ": object exceeds maximum field count")
                return
            for key in sorted(item.keys()):
                errors.extend(identifier_errors(key, path + ".<key>"))
                inspect(item[key], path + "." + key, depth + 1)
            return
        errors.append(path + ": unsupported value type")

    inspect(value, label, 0)
    return errors


def identifier_array_errors(value, label, maximum):
    if not isinstance(value, list):
        return [label + ": must be an array"]
    errors = []
    if len(value) > maximum:
        errors.append(label + ": exceeds maximum length")
    for index, item in enumerate(value):
        errors.extend(identifier_errors(item, label + "[" + str(index) + "]"))
    if len(value) != len(set(value)):
        errors.append(label + ": duplicate values are not allowed")
    return errors


def participation_errors(record):
    fields = ["schema", "profile", "participants", "required_endorsers", "threshold"]
    errors = exact_field_errors(record, fields, "participation")
    if errors:
        return errors
    if record["schema"] != PARTICIPATION_SCHEMA:
        errors.append("participation.schema: unsupported schema")
    if record["profile"] not in PARTICIPATION_PROFILES:
        errors.append("participation.profile: unsupported profile")
    errors.extend(identifier_array_errors(record["participants"], "participation.participants", MAX_PARTICIPANTS))
    errors.extend(identifier_array_errors(record["required_endorsers"], "participation.required_endorsers", MAX_PARTICIPANTS))
    threshold = record["threshold"]
    if not isinstance(threshold, int) or isinstance(threshold, bool):
        errors.append("participation.threshold: must be an integer")
    elif threshold < 0 or threshold > MAX_PARTICIPANTS:
        errors.append("participation.threshold: out of supported range")
    if errors:
        return errors

    participants = set(record["participants"])
    required = set(record["required_endorsers"])
    profile = record["profile"]
    threshold = record["threshold"]

    if not required.issubset(participants):
        errors.append("participation.required_endorsers: must be a subset of participants")
    if profile == "NO_ENDORSEMENT_REQUIRED":
        if participants or required or threshold != 0:
            errors.append("participation: NO_ENDORSEMENT_REQUIRED requires empty participant fields and threshold 0")
    elif profile == "SINGLE_DECLARED_ENDORSER":
        if not participants:
            errors.append("participation: SINGLE_DECLARED_ENDORSER requires participants")
        if required or threshold != 1:
            errors.append("participation: SINGLE_DECLARED_ENDORSER requires empty required_endorsers and threshold 1")
    elif profile == "ALL_DECLARED_PARTICIPANTS":
        if not participants:
            errors.append("participation: ALL_DECLARED_PARTICIPANTS requires participants")
        if required or threshold != len(participants):
            errors.append("participation: ALL_DECLARED_PARTICIPANTS requires empty required_endorsers and threshold equal to participant count")
    elif profile == "EXACT_DECLARED_PARTICIPANT_SET":
        if not participants or not required:
            errors.append("participation: EXACT_DECLARED_PARTICIPANT_SET requires participants and required_endorsers")
        if threshold != len(required):
            errors.append("participation: EXACT_DECLARED_PARTICIPANT_SET requires threshold equal to required_endorsers count")
    elif profile == "DECLARED_THRESHOLD":
        if not participants:
            errors.append("participation: DECLARED_THRESHOLD requires participants")
        if required:
            errors.append("participation: DECLARED_THRESHOLD requires empty required_endorsers")
        if threshold < 1 or threshold > len(participants):
            errors.append("participation: DECLARED_THRESHOLD threshold must be within participant count")
    return errors


def context_errors(record):
    fields = ["schema", "conversation_id", "purpose_id", "ruleset_profile", "participation", "execution_authority"]
    errors = exact_field_errors(record, fields, "context")
    if errors:
        return errors
    if record["schema"] != CONTEXT_SCHEMA:
        errors.append("context.schema: unsupported schema")
    errors.extend(identifier_errors(record["conversation_id"], "context.conversation_id"))
    errors.extend(identifier_errors(record["purpose_id"], "context.purpose_id"))
    if record["ruleset_profile"] != RULESET_PROFILE:
        errors.append("context.ruleset_profile: unsupported ruleset profile")
    errors.extend(participation_errors(record["participation"]))
    if record["execution_authority"] != EXECUTION_AUTHORITY:
        errors.append("context.execution_authority: must be NONE")
    return errors


def action_errors(record):
    fields = ["schema", "action_ref", "conversation_id", "topic_id", "actor", "kind", "declared_value", "targets"]
    errors = exact_field_errors(record, fields, "action")
    if errors:
        return errors
    if record["schema"] != ACTION_SCHEMA:
        errors.append("action.schema: unsupported schema")
    errors.extend(identifier_errors(record["action_ref"], "action.action_ref"))
    errors.extend(identifier_errors(record["conversation_id"], "action.conversation_id"))
    errors.extend(identifier_errors(record["topic_id"], "action.topic_id"))
    errors.extend(identifier_errors(record["actor"], "action.actor"))
    kind = record["kind"]
    if kind not in ACTION_KINDS:
        errors.append("action.kind: unsupported kind")
    errors.extend(identifier_array_errors(record["targets"], "action.targets", 1))
    if kind in PROPOSAL_KINDS:
        if record["declared_value"] is None:
            errors.append("action.declared_value: proposal-producing actions require a non-null value")
        else:
            errors.extend(value_errors(record["declared_value"], "action.declared_value"))
    elif kind in ("WITHDRAW", "ENDORSE", "OBJECT") and record["declared_value"] is not None:
        errors.append("action.declared_value: relation-only actions require null")
    if kind == "PROPOSE" and record["targets"] != []:
        errors.append("action.targets: PROPOSE requires no targets")
    if kind in RELATION_KINDS and len(record["targets"]) != 1:
        errors.append("action.targets: relation action requires exactly one target")
    return errors


def observation_errors(record):
    fields = ["schema", "observation_ref", "source", "presentation", "action"]
    errors = exact_field_errors(record, fields, "observation")
    if errors:
        return errors
    if record["schema"] != OBSERVATION_SCHEMA:
        errors.append("observation.schema: unsupported schema")
    errors.extend(identifier_errors(record["observation_ref"], "observation.observation_ref"))
    errors.extend(identifier_errors(record["source"], "observation.source"))
    errors.extend(text_errors(record["presentation"], "observation.presentation"))
    errors.extend(action_errors(record["action"]))
    return errors


def boundary_errors(record):
    fields = ["schema", "state", "expected_observation_refs"]
    errors = exact_field_errors(record, fields, "boundary")
    if errors:
        return errors
    if record["schema"] != BOUNDARY_SCHEMA:
        errors.append("boundary.schema: unsupported schema")
    if record["state"] not in ("OPEN", "SEALED"):
        errors.append("boundary.state: must be OPEN or SEALED")
    errors.extend(identifier_array_errors(record["expected_observation_refs"], "boundary.expected_observation_refs", MAX_OBSERVATIONS))
    if record["state"] == "OPEN" and record["expected_observation_refs"]:
        errors.append("boundary.expected_observation_refs: OPEN boundary requires an empty list")
    return errors


def normalize_participation(record):
    return {
        "schema": PARTICIPATION_SCHEMA,
        "profile": record["profile"],
        "participants": sorted(record["participants"]),
        "required_endorsers": sorted(record["required_endorsers"]),
        "threshold": record["threshold"],
    }


def normalize_context(record):
    return {
        "schema": CONTEXT_SCHEMA,
        "conversation_id": record["conversation_id"],
        "purpose_id": record["purpose_id"],
        "ruleset_profile": RULESET_PROFILE,
        "participation": normalize_participation(record["participation"]),
        "execution_authority": EXECUTION_AUTHORITY,
    }


def normalize_action(record):
    return {
        "schema": ACTION_SCHEMA,
        "action_ref": record["action_ref"],
        "conversation_id": record["conversation_id"],
        "topic_id": record["topic_id"],
        "actor": record["actor"],
        "kind": record["kind"],
        "declared_value": deepcopy(record["declared_value"]),
        "targets": sorted(record["targets"]),
    }


def normalize_observation(record):
    return {
        "schema": OBSERVATION_SCHEMA,
        "observation_ref": record["observation_ref"],
        "source": record["source"],
        "presentation": record["presentation"],
        "action": normalize_action(record["action"]),
    }


def normalize_boundary(record):
    return {
        "schema": BOUNDARY_SCHEMA,
        "state": record["state"],
        "expected_observation_refs": sorted(record["expected_observation_refs"]),
    }


def compute_context_id(record):
    return derive_id("context", CONTEXT_SCHEMA, normalize_context(record))


def compute_action_id(record):
    return derive_id("action", ACTION_SCHEMA, normalize_action(record))


def compute_observation_id(record):
    basis = {
        "schema": OBSERVATION_SCHEMA,
        "observation_ref": record["observation_ref"],
        "source": record["source"],
        "presentation": record["presentation"],
        "action_id": compute_action_id(record["action"]),
    }
    return derive_id("observation", OBSERVATION_SCHEMA, basis)


def reconstruct_context(record):
    errors = context_errors(record)
    if errors:
        return {"validation_state": "REFUSED", "errors": errors}
    normalized = normalize_context(record)
    return {
        "validation_state": "ACCEPTED",
        "context": normalized,
        "context_id": compute_context_id(normalized),
    }


def reconstruct_evidence(records, context):
    if not isinstance(records, list):
        return {"validation_state": "REFUSED", "errors": ["observations: must be an array"]}
    if len(records) > MAX_OBSERVATIONS:
        return {"validation_state": "REFUSED", "errors": ["observations: exceeds maximum length"]}

    errors = []
    normalized_records = []
    for index, record in enumerate(records):
        found = observation_errors(record)
        if found:
            errors.extend("observations[" + str(index) + "]: " + item for item in found)
        else:
            normalized = normalize_observation(record)
            if normalized["action"]["conversation_id"] != context["conversation_id"]:
                errors.append("observations[" + str(index) + "]: action.conversation_id does not match context")
            else:
                normalized_records.append(normalized)
    if errors:
        return {"validation_state": "REFUSED", "errors": errors}

    unique_observations = {}
    observation_ref_index = defaultdict(dict)
    for record in normalized_records:
        oid = compute_observation_id(record)
        unique_observations[oid] = record
        observation_ref_index[record["observation_ref"]][oid] = record

    observation_ref_conflicts = []
    for ref in sorted(observation_ref_index.keys()):
        ids = sorted(observation_ref_index[ref].keys())
        if len(ids) > 1:
            observation_ref_conflicts.append({"observation_ref": ref, "observation_ids": ids})
    if observation_ref_conflicts:
        return {
            "validation_state": "REFUSED",
            "errors": ["observation_ref content conflict: " + item["observation_ref"] for item in observation_ref_conflicts],
        }

    action_ref_index = defaultdict(dict)
    actions = {}
    action_observation_ids = defaultdict(list)
    action_sources = defaultdict(set)
    action_presentations = defaultdict(list)

    for oid in sorted(unique_observations.keys()):
        observation = unique_observations[oid]
        action = observation["action"]
        aid = compute_action_id(action)
        actions[aid] = action
        action_ref_index[action["action_ref"]][aid] = action
        action_observation_ids[aid].append(oid)
        action_sources[aid].add(observation["source"])
        action_presentations[aid].append({"observation_id": oid, "presentation": observation["presentation"]})

    action_ref_conflicts = []
    for ref in sorted(action_ref_index.keys()):
        ids = sorted(action_ref_index[ref].keys())
        if len(ids) > 1:
            action_ref_conflicts.append({"action_ref": ref, "action_ids": ids})
    if action_ref_conflicts:
        return {
            "validation_state": "REFUSED",
            "errors": ["action_ref content conflict: " + item["action_ref"] for item in action_ref_conflicts],
        }

    action_entries = []
    action_ref_to_id = {}
    for aid in sorted(actions.keys()):
        action = actions[aid]
        action_ref_to_id[action["action_ref"]] = aid
        action_entries.append({
            "action_id": aid,
            "action": deepcopy(action),
            "observation_ids": sorted(action_observation_ids[aid]),
            "sources": sorted(action_sources[aid]),
            "observation_count": len(action_observation_ids[aid]),
            "presentations": sorted(action_presentations[aid], key=lambda item: item["observation_id"]),
        })

    observation_entries = []
    for oid in sorted(unique_observations.keys()):
        observation = unique_observations[oid]
        observation_entries.append({
            "observation_id": oid,
            "observation_ref": observation["observation_ref"],
            "source": observation["source"],
            "presentation": observation["presentation"],
            "action_id": compute_action_id(observation["action"]),
        })

    action_set_basis = {"profile": ACTION_SCHEMA, "action_ids": sorted(actions.keys())}
    observation_set_basis = {"profile": OBSERVATION_SCHEMA, "observation_ids": sorted(unique_observations.keys())}
    return {
        "validation_state": "ACCEPTED",
        "raw_observation_count": len(records),
        "unique_observation_count": len(unique_observations),
        "exact_observation_duplicate_count": len(records) - len(unique_observations),
        "unique_action_count": len(actions),
        "observation_multiplicity_count": len(unique_observations) - len(actions),
        "actions": action_entries,
        "observations": observation_entries,
        "action_ref_to_id": action_ref_to_id,
        "action_set_id": derive_id("action_set", ACTION_SCHEMA, action_set_basis),
        "observation_set_id": derive_id("observation_set", OBSERVATION_SCHEMA, observation_set_basis),
    }


def reconstruct_graph(evidence, context):
    action_by_ref = {}
    action_id_by_ref = {}
    for entry in evidence["actions"]:
        action = entry["action"]
        action_by_ref[action["action_ref"]] = action
        action_id_by_ref[action["action_ref"]] = entry["action_id"]

    errors = []
    missing = []
    edges = []
    participants = set(context["participation"]["participants"])

    for ref in sorted(action_by_ref.keys()):
        action = action_by_ref[ref]
        if action["kind"] in ("ENDORSE", "OBJECT") and action["actor"] not in participants:
            errors.append("action " + ref + ": actor is not admitted by the participation profile")
        if action["kind"] in RELATION_KINDS:
            target_ref = action["targets"][0]
            if target_ref == ref:
                errors.append("action " + ref + ": self-target is not supported")
                continue
            if target_ref not in action_by_ref:
                missing.append({
                    "action_ref": ref,
                    "action_id": action_id_by_ref[ref],
                    "missing_target_ref": target_ref,
                })
                continue
            target = action_by_ref[target_ref]
            if target["conversation_id"] != action["conversation_id"]:
                errors.append("action " + ref + ": cross-conversation target is not supported")
                continue
            if target["topic_id"] != action["topic_id"]:
                errors.append("action " + ref + ": cross-topic target is not supported")
                continue
            if target["kind"] not in PROPOSAL_KINDS:
                errors.append("action " + ref + ": target must be PROPOSE or AMEND")
                continue
            edges.append({
                "source_action_ref": ref,
                "source_action_id": action_id_by_ref[ref],
                "relation": action["kind"],
                "target_action_ref": target_ref,
                "target_action_id": action_id_by_ref[target_ref],
            })

    if errors:
        return {"validation_state": "REFUSED", "errors": errors}

    adjacency = defaultdict(list)
    for edge in edges:
        adjacency[edge["source_action_ref"]].append(edge["target_action_ref"])

    for start_ref in sorted(action_by_ref.keys()):
        seen = {start_ref}
        current = start_ref
        depth = 0
        while adjacency.get(current):
            current = adjacency[current][0]
            if current in seen:
                break
            seen.add(current)
            depth += 1
            if depth > MAX_GRAPH_DEPTH:
                errors.append("action " + start_ref + ": dependency chain exceeds maximum depth")
                break
        if errors:
            break

    if errors:
        return {"validation_state": "REFUSED", "errors": errors}

    cycles = set()
    completed = set()
    for start_ref in sorted(action_by_ref.keys()):
        if start_ref in completed:
            continue
        path = []
        path_index = {}
        current = start_ref
        while current not in completed and current not in path_index:
            path_index[current] = len(path)
            path.append(current)
            targets = adjacency.get(current, [])
            if not targets:
                current = None
                break
            current = targets[0]
        if current is not None and current in path_index:
            cycles.update(path[path_index[current]:])
        completed.update(path)

    nodes = []
    for ref in sorted(action_by_ref.keys()):
        action = action_by_ref[ref]
        nodes.append({
            "action_ref": ref,
            "action_id": action_id_by_ref[ref],
            "topic_id": action["topic_id"],
            "actor": action["actor"],
            "kind": action["kind"],
        })

    sorted_edges = sorted(edges, key=lambda item: (item["source_action_id"], item["relation"], item["target_action_id"]))
    sorted_missing = sorted(missing, key=lambda item: (item["action_ref"], item["missing_target_ref"]))
    basis = {
        "profile": GRAPH_PROFILE,
        "nodes": nodes,
        "edges": sorted_edges,
        "missing_dependencies": sorted_missing,
        "cycle_action_refs": sorted(cycles),
    }
    return {
        "validation_state": "ACCEPTED",
        "profile": GRAPH_PROFILE,
        "nodes": nodes,
        "edges": sorted_edges,
        "missing_dependencies": sorted_missing,
        "cycle_action_refs": sorted(cycles),
        "graph_root": derive_id("graph", GRAPH_PROFILE, basis),
        "action_by_ref": action_by_ref,
        "action_id_by_ref": action_id_by_ref,
    }


def readiness(action_by_ref, cycles):
    memo = {}
    for start_ref in sorted(action_by_ref.keys()):
        if start_ref in memo:
            continue
        path = []
        path_refs = set()
        current = start_ref
        while True:
            if current in memo:
                result = memo[current]
                break
            if current in cycles or current in path_refs:
                result = False
                break
            action = action_by_ref[current]
            if action["kind"] == "PROPOSE":
                memo[current] = True
                result = True
                break
            target_ref = action["targets"][0]
            if target_ref not in action_by_ref:
                memo[current] = False
                result = False
                break
            path.append(current)
            path_refs.add(current)
            current = target_ref
        for ref in reversed(path):
            memo[ref] = result
    return memo


def participation_result(participation, endorsers):
    profile = participation["profile"]
    participants = set(participation["participants"])
    required = set(participation["required_endorsers"])
    actual = set(endorsers)
    threshold = participation["threshold"]

    if profile == "NO_ENDORSEMENT_REQUIRED":
        satisfied = True
        missing = []
        surplus = sorted(actual)
    elif profile == "SINGLE_DECLARED_ENDORSER":
        satisfied = len(actual) >= 1
        missing = [] if satisfied else ["ONE_DECLARED_ENDORSER"]
        surplus = []
    elif profile == "ALL_DECLARED_PARTICIPANTS":
        missing = sorted(participants - actual)
        surplus = sorted(actual - participants)
        satisfied = not missing and not surplus
    elif profile == "EXACT_DECLARED_PARTICIPANT_SET":
        missing = sorted(required - actual)
        surplus = sorted(actual - required)
        satisfied = not missing and not surplus
    else:
        shortage = max(0, threshold - len(actual))
        missing = [] if shortage == 0 else ["ADDITIONAL_ENDORSERS_REQUIRED:" + str(shortage)]
        surplus = sorted(actual - participants)
        satisfied = len(actual) >= threshold and not surplus

    return {
        "profile": profile,
        "participants": sorted(participants),
        "required_endorsers": sorted(required),
        "threshold": threshold,
        "endorsers": sorted(actual),
        "endorsement_count": len(actual),
        "missing": missing,
        "surplus": surplus,
        "satisfied": satisfied,
    }


def reconstruct_topic_receipt(topic_id, actions, action_id_by_ref, graph, context):
    action_by_ref = {action["action_ref"]: action for action in actions}
    cycles = set(graph["cycle_action_refs"]) & set(action_by_ref.keys())
    missing = [item for item in graph["missing_dependencies"] if item["action_ref"] in action_by_ref]
    ready = readiness(action_by_ref, cycles)

    proposals = sorted(ref for ref, action in action_by_ref.items() if action["kind"] in PROPOSAL_KINDS and ready.get(ref, False))
    superseded = set()
    withdrawn = set()
    for ref in sorted(action_by_ref.keys()):
        action = action_by_ref[ref]
        if not ready.get(ref, False):
            continue
        if action["kind"] == "AMEND":
            superseded.add(action["targets"][0])
        elif action["kind"] == "WITHDRAW":
            withdrawn.add(action["targets"][0])
    active = sorted(ref for ref in proposals if ref not in superseded | withdrawn)

    endorsements = defaultdict(set)
    objections = defaultdict(set)
    signals = defaultdict(list)
    for ref in sorted(action_by_ref.keys()):
        action = action_by_ref[ref]
        if not ready.get(ref, False):
            continue
        if action["kind"] == "ENDORSE":
            target = action["targets"][0]
            endorsements[target].add(action["actor"])
            signals[(target, action["actor"])].append(("ENDORSE", ref))
        elif action["kind"] == "OBJECT":
            target = action["targets"][0]
            objections[target].add(action["actor"])
            signals[(target, action["actor"])].append(("OBJECT", ref))

    conflicts = []
    for key in sorted(signals.keys()):
        kinds = {item[0] for item in signals[key]}
        if kinds == {"ENDORSE", "OBJECT"}:
            conflicts.append({
                "target_action_ref": key[0],
                "actor": key[1],
                "signal_action_refs": sorted(item[1] for item in signals[key]),
            })
    active_conflicts = [
        item for item in conflicts
        if item["target_action_ref"] in active
    ]

    state = None
    reason = None
    resolved_ref = None
    resolved_id = None
    resolved_value = None
    participation = None
    active_endorsers = []
    active_objectors = []

    if cycles:
        state = "ABSTAIN"
        reason = "DEPENDENCY_CYCLE"
    elif active_conflicts:
        state = "ABSTAIN"
        reason = "PARTICIPANT_SIGNAL_CONFLICT"
    elif len(active) > 1:
        state = "ABSTAIN"
        reason = "MULTIPLE_ACTIVE_PROPOSALS"
    elif missing:
        state = "INCOMPLETE"
        reason = "MISSING_DEPENDENCY"
    elif not active:
        state = "INCOMPLETE"
        reason = "NO_ACTIVE_PROPOSAL"
    else:
        current = active[0]
        active_endorsers = sorted(endorsements.get(current, set()))
        active_objectors = sorted(objections.get(current, set()))
        participation = participation_result(context["participation"], active_endorsers)
        if active_objectors:
            state = "ABSTAIN"
            reason = "ACTIVE_PROPOSAL_OBJECTED"
        elif participation["satisfied"]:
            state = "RESOLVED"
            reason = "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED"
            resolved_ref = current
            resolved_id = action_id_by_ref[current]
            resolved_value = deepcopy(action_by_ref[current]["declared_value"])
        else:
            state = "INCOMPLETE"
            reason = "PARTICIPATION_INCOMPLETE"

    summaries = []
    for ref in sorted(action_by_ref.keys()):
        action = action_by_ref[ref]
        summaries.append({
            "action_ref": ref,
            "action_id": action_id_by_ref[ref],
            "actor": action["actor"],
            "kind": action["kind"],
            "targets": list(action["targets"]),
            "dependency_ready": bool(ready.get(ref, False)),
            "active_proposal": ref in active,
            "superseded": ref in superseded,
            "withdrawn": ref in withdrawn,
            "declared_value": deepcopy(action["declared_value"]),
        })

    without_id = {
        "profile": TOPIC_RECEIPT_PROFILE,
        "ruleset_profile": RULESET_PROFILE,
        "topic_id": topic_id,
        "state": state,
        "reason_code": reason,
        "action_ids": sorted(action_id_by_ref[ref] for ref in action_by_ref.keys()),
        "active_action_refs": active,
        "active_action_ids": sorted(action_id_by_ref[ref] for ref in active),
        "superseded_action_refs": sorted(superseded),
        "withdrawn_action_refs": sorted(withdrawn),
        "missing_dependencies": sorted(missing, key=lambda item: (item["action_ref"], item["missing_target_ref"])),
        "cycle_action_refs": sorted(cycles),
        "signal_conflicts": conflicts,
        "active_signal_conflicts": active_conflicts,
        "active_endorsers": active_endorsers,
        "active_objectors": active_objectors,
        "participation": participation,
        "resolved_action_ref": resolved_ref,
        "resolved_action_id": resolved_id,
        "resolved_declared_value": resolved_value,
        "actions": summaries,
        "execution_authority": EXECUTION_AUTHORITY,
    }
    receipt = deepcopy(without_id)
    receipt["topic_receipt_id"] = derive_id("topic_receipt", TOPIC_RECEIPT_PROFILE, without_id)
    return receipt


def reconstruct_topics(evidence, graph, context):
    grouped = defaultdict(list)
    for entry in evidence["actions"]:
        grouped[entry["action"]["topic_id"]].append(entry["action"])
    receipts = []
    for topic_id in sorted(grouped.keys()):
        receipts.append(reconstruct_topic_receipt(topic_id, grouped[topic_id], graph["action_id_by_ref"], graph, context))
    counts = Counter(item["state"] for item in receipts)
    root_basis = {"profile": TOPIC_RECEIPT_PROFILE, "topic_receipt_ids": sorted(item["topic_receipt_id"] for item in receipts)}
    return {
        "receipts": receipts,
        "state_counts": {
            "RESOLVED": counts.get("RESOLVED", 0),
            "INCOMPLETE": counts.get("INCOMPLETE", 0),
            "ABSTAIN": counts.get("ABSTAIN", 0),
        },
        "topic_receipt_root": derive_id("topic_receipt_root", TOPIC_RECEIPT_PROFILE, root_basis),
    }


def reconstruct_boundary(boundary, evidence):
    observed = sorted(item["observation_ref"] for item in evidence["observations"])
    expected = sorted(boundary["expected_observation_refs"])
    if boundary["state"] == "OPEN":
        state = "OPEN"
        missing = []
        unexpected = []
    else:
        missing = sorted(set(expected) - set(observed))
        unexpected = sorted(set(observed) - set(expected))
        if not missing and not unexpected:
            state = "SEALED"
        elif missing and not unexpected:
            state = "INCOMPLETE"
        else:
            state = "CONFLICT"
    without_id = {
        "profile": BOUNDARY_RECEIPT_PROFILE,
        "declared_state": boundary["state"],
        "state": state,
        "observed_observation_refs": observed,
        "expected_observation_refs": expected,
        "missing_observation_refs": missing,
        "unexpected_observation_refs": unexpected,
        "observed_observation_set_id": evidence["observation_set_id"],
    }
    receipt = deepcopy(without_id)
    receipt["boundary_receipt_id"] = derive_id("boundary_receipt", BOUNDARY_RECEIPT_PROFILE, without_id)
    return receipt


def public_summary(topic):
    return {
        "topic_id": topic["topic_id"],
        "state": topic["state"],
        "reason_code": topic["reason_code"],
        "active_action_ids": list(topic["active_action_ids"]),
        "resolved_action_id": topic["resolved_action_id"],
        "active_endorser_count": len(topic["active_endorsers"]),
        "active_objector_count": len(topic["active_objectors"]),
        "participation_satisfied": None if topic["participation"] is None else topic["participation"]["satisfied"],
        "topic_receipt_id": topic["topic_receipt_id"],
        "execution_authority": EXECUTION_AUTHORITY,
    }


def make_refusal(errors):
    refusal = {
        "profile": PRIVATE_BUNDLE_PROFILE,
        "version": VERSION,
        "result": "REFUSED",
        "architecture_profile": ARCHITECTURE_PROFILE,
        "ruleset_profile": RULESET_PROFILE,
        "execution_authority": EXECUTION_AUTHORITY,
        "errors": list(errors),
    }
    refusal["refusal_id"] = derive_id("refusal", PRIVATE_BUNDLE_PROFILE, refusal)
    return refusal


def reconstruct_bundle(context, observations, boundary):
    intake = []
    if not isinstance(context, dict):
        intake.append("context: must be an object")
    if not isinstance(observations, list):
        intake.append("observations: must be an array")
    if not isinstance(boundary, dict):
        intake.append("boundary: must be an object")
    if intake:
        return make_refusal(intake)

    context_result = reconstruct_context(context)
    found_boundary_errors = boundary_errors(boundary)
    if context_result["validation_state"] == "REFUSED" or found_boundary_errors:
        errors = []
        if context_result["validation_state"] == "REFUSED":
            errors.extend(context_result["errors"])
        errors.extend(found_boundary_errors)
        return make_refusal(errors)

    normalized_boundary = normalize_boundary(boundary)
    evidence = reconstruct_evidence(observations, context_result["context"])
    if evidence["validation_state"] == "REFUSED":
        return make_refusal(evidence["errors"])
    graph = reconstruct_graph(evidence, context_result["context"])
    if graph["validation_state"] == "REFUSED":
        return make_refusal(graph["errors"])

    topics = reconstruct_topics(evidence, graph, context_result["context"])
    boundary_receipt = reconstruct_boundary(normalized_boundary, evidence)
    resolution_basis = {
        "profile": PRIVATE_BUNDLE_PROFILE,
        "version": VERSION,
        "architecture_profile": ARCHITECTURE_PROFILE,
        "ruleset_profile": RULESET_PROFILE,
        "context_id": context_result["context_id"],
        "action_set_id": evidence["action_set_id"],
        "graph_root": graph["graph_root"],
        "topic_receipt_root": topics["topic_receipt_root"],
        "boundary_receipt_id": boundary_receipt["boundary_receipt_id"],
    }
    conversation_resolution_id = derive_id("conversation_resolution", PRIVATE_BUNDLE_PROFILE, resolution_basis)
    summaries = [public_summary(receipt) for receipt in topics["receipts"]]
    public_without_id = {
        "profile": PUBLIC_RECEIPT_PROFILE,
        "version": VERSION,
        "architecture_profile": ARCHITECTURE_PROFILE,
        "ruleset_profile": RULESET_PROFILE,
        "context_id": context_result["context_id"],
        "conversation_id": context_result["context"]["conversation_id"],
        "purpose_id": context_result["context"]["purpose_id"],
        "action_set_id": evidence["action_set_id"],
        "graph_root": graph["graph_root"],
        "topic_receipt_root": topics["topic_receipt_root"],
        "boundary_receipt_id": boundary_receipt["boundary_receipt_id"],
        "boundary_state": boundary_receipt["state"],
        "state_counts": deepcopy(topics["state_counts"]),
        "topic_summaries": summaries,
        "conversation_resolution_id": conversation_resolution_id,
        "execution_authority": EXECUTION_AUTHORITY,
    }
    public_receipt = deepcopy(public_without_id)
    public_receipt["public_receipt_id"] = derive_id("public_receipt", PUBLIC_RECEIPT_PROFILE, public_without_id)
    bundle_basis = {
        "profile": PRIVATE_BUNDLE_PROFILE,
        "conversation_resolution_id": conversation_resolution_id,
        "observation_set_id": evidence["observation_set_id"],
        "public_receipt_id": public_receipt["public_receipt_id"],
    }
    private_bundle_id = derive_id("private_bundle", PRIVATE_BUNDLE_PROFILE, bundle_basis)
    public_graph = {
        "profile": graph["profile"],
        "nodes": deepcopy(graph["nodes"]),
        "edges": deepcopy(graph["edges"]),
        "missing_dependencies": deepcopy(graph["missing_dependencies"]),
        "cycle_action_refs": deepcopy(graph["cycle_action_refs"]),
        "graph_root": graph["graph_root"],
    }
    return {
        "profile": PRIVATE_BUNDLE_PROFILE,
        "version": VERSION,
        "result": "ACCEPTED",
        "architecture_profile": ARCHITECTURE_PROFILE,
        "ruleset_profile": RULESET_PROFILE,
        "execution_authority": EXECUTION_AUTHORITY,
        "inputs": {
            "context": deepcopy(context),
            "observations": deepcopy(observations),
            "boundary": deepcopy(boundary),
        },
        "context": context_result,
        "evidence": evidence,
        "graph": public_graph,
        "topics": topics,
        "boundary": boundary_receipt,
        "public_receipt": public_receipt,
        "conversation_resolution_id": conversation_resolution_id,
        "private_bundle_id": private_bundle_id,
    }


def strip_producer_verification(bundle):
    result = deepcopy(bundle)
    result.pop("self_verification", None)
    return result


def verify_refusal(bundle):
    fields = [
        "profile",
        "version",
        "result",
        "architecture_profile",
        "ruleset_profile",
        "execution_authority",
        "errors",
        "refusal_id",
    ]
    errors = exact_field_errors(bundle, fields, "refusal")
    if errors:
        return errors
    if bundle["profile"] != PRIVATE_BUNDLE_PROFILE:
        errors.append("refusal.profile mismatch")
    if bundle["version"] != VERSION:
        errors.append("refusal.version mismatch")
    if bundle["result"] != "REFUSED":
        errors.append("refusal.result mismatch")
    if bundle["architecture_profile"] != ARCHITECTURE_PROFILE:
        errors.append("refusal.architecture_profile mismatch")
    if bundle["ruleset_profile"] != RULESET_PROFILE:
        errors.append("refusal.ruleset_profile mismatch")
    if bundle["execution_authority"] != EXECUTION_AUTHORITY:
        errors.append("refusal.execution_authority mismatch")
    if not isinstance(bundle["errors"], list) or not all(isinstance(item, str) for item in bundle["errors"]):
        errors.append("refusal.errors must be an array of strings")
    basis = deepcopy(bundle)
    supplied = basis.pop("refusal_id", None)
    expected = derive_id("refusal", PRIVATE_BUNDLE_PROFILE, basis)
    if supplied != expected:
        errors.append("refusal_id mismatch")
    return errors


def compare_bundle(bundle):
    if not isinstance(bundle, dict):
        return {
            "profile": INDEPENDENT_VERIFICATION_PROFILE,
            "valid": False,
            "errors": ["bundle must be an object"],
        }
    if bundle.get("result") == "REFUSED":
        errors = verify_refusal(bundle)
        return {
            "profile": INDEPENDENT_VERIFICATION_PROFILE,
            "valid": not errors,
            "errors": errors,
            "bundle_result": "REFUSED",
            "expected_conversation_resolution_id": None,
            "expected_private_bundle_id": None,
            "expected_public_receipt_id": None,
        }
    if bundle.get("result") != "ACCEPTED":
        return {
            "profile": INDEPENDENT_VERIFICATION_PROFILE,
            "valid": False,
            "errors": ["bundle.result must be ACCEPTED or REFUSED"],
        }
    inputs = bundle.get("inputs")
    if not isinstance(inputs, dict):
        return {
            "profile": INDEPENDENT_VERIFICATION_PROFILE,
            "valid": False,
            "errors": ["accepted bundle is missing inputs"],
        }
    input_field_errors = exact_field_errors(inputs, ["context", "observations", "boundary"], "inputs")
    if input_field_errors:
        return {
            "profile": INDEPENDENT_VERIFICATION_PROFILE,
            "valid": False,
            "errors": input_field_errors,
        }

    expected = reconstruct_bundle(inputs["context"], inputs["observations"], inputs["boundary"])
    errors = []
    if expected.get("result") != "ACCEPTED":
        errors.append("embedded inputs do not reconstruct an accepted bundle")
    else:
        supplied_core = strip_producer_verification(bundle)
        if stable_json(supplied_core) != stable_json(expected):
            scalar_checks = ["conversation_resolution_id", "private_bundle_id"]
            for field in scalar_checks:
                if bundle.get(field) != expected.get(field):
                    errors.append(field + " mismatch")
            nested_checks = [
                ("context", "context_id"),
                ("evidence", "action_set_id"),
                ("evidence", "observation_set_id"),
                ("graph", "graph_root"),
                ("topics", "topic_receipt_root"),
                ("boundary", "boundary_receipt_id"),
                ("public_receipt", "public_receipt_id"),
            ]
            for section, field in nested_checks:
                if bundle.get(section, {}).get(field) != expected.get(section, {}).get(field):
                    errors.append(section + "." + field + " mismatch")
            if bundle.get("topics", {}).get("receipts") != expected.get("topics", {}).get("receipts"):
                errors.append("topic receipts mismatch")
            if bundle.get("public_receipt") != expected.get("public_receipt"):
                errors.append("public receipt content mismatch")
            if not errors:
                errors.append("bundle content mismatch")

    producer_self = bundle.get("self_verification")
    if producer_self is not None:
        if not isinstance(producer_self, dict):
            errors.append("producer self_verification must be an object")
        elif producer_self.get("profile") != PRODUCER_VERIFICATION_PROFILE:
            errors.append("producer self_verification profile mismatch")
        elif producer_self.get("valid") is not True:
            errors.append("producer self_verification does not report valid")

    return {
        "profile": INDEPENDENT_VERIFICATION_PROFILE,
        "valid": not errors,
        "errors": errors,
        "bundle_result": bundle.get("result"),
        "expected_conversation_resolution_id": expected.get("conversation_resolution_id"),
        "expected_private_bundle_id": expected.get("private_bundle_id"),
        "expected_public_receipt_id": expected.get("public_receipt", {}).get("public_receipt_id"),
    }


def make_participation(profile, participants=None, required=None, threshold=0):
    return {
        "schema": PARTICIPATION_SCHEMA,
        "profile": profile,
        "participants": list(participants or []),
        "required_endorsers": list(required or []),
        "threshold": threshold,
    }


def make_context(conversation_id, participation):
    return {
        "schema": CONTEXT_SCHEMA,
        "conversation_id": conversation_id,
        "purpose_id": "self-test",
        "ruleset_profile": RULESET_PROFILE,
        "participation": participation,
        "execution_authority": EXECUTION_AUTHORITY,
    }


def make_action(ref, conversation_id, topic, actor, kind, value=None, targets=None):
    return {
        "schema": ACTION_SCHEMA,
        "action_ref": ref,
        "conversation_id": conversation_id,
        "topic_id": topic,
        "actor": actor,
        "kind": kind,
        "declared_value": deepcopy(value),
        "targets": list(targets or []),
    }


def make_observation(ref, source, action, presentation=""):
    return {
        "schema": OBSERVATION_SCHEMA,
        "observation_ref": ref,
        "source": source,
        "presentation": presentation,
        "action": deepcopy(action),
    }


def make_boundary(state="OPEN", refs=None):
    return {
        "schema": BOUNDARY_SCHEMA,
        "state": state,
        "expected_observation_refs": list(refs or []),
    }


def self_test_input():
    participation = make_participation("ALL_DECLARED_PARTICIPANTS", ["alice", "bob"], threshold=2)
    context = make_context("independent-verifier-self-test", participation)
    actions = [
        make_action("proposal", context["conversation_id"], "instruction", "alice", "PROPOSE", "A"),
        make_action("amend", context["conversation_id"], "instruction", "alice", "AMEND", "B", ["proposal"]),
        make_action("endorse-a", context["conversation_id"], "instruction", "alice", "ENDORSE", None, ["amend"]),
        make_action("endorse-b", context["conversation_id"], "instruction", "bob", "ENDORSE", None, ["amend"]),
    ]
    observations = [
        make_observation("obs-proposal", "a", actions[0], "A"),
        make_observation("obs-amend", "b", actions[1], "B"),
        make_observation("obs-endorse-a", "a", actions[2], "PRIVATE_PRESENTATION_MARKER_ALPHA"),
        make_observation("obs-endorse-b", "b", actions[3], "PRIVATE_PRESENTATION_MARKER_BETA"),
    ]
    boundary = make_boundary("SEALED", [item["observation_ref"] for item in observations])
    return context, observations, boundary


class SelfTest:
    def __init__(self):
        self.groups = defaultdict(lambda: {"pass": 0, "fail": 0, "failures": []})

    def check(self, group, label, condition):
        if condition:
            self.groups[group]["pass"] += 1
        else:
            self.groups[group]["fail"] += 1
            self.groups[group]["failures"].append(label)

    def equal(self, group, label, left, right):
        self.check(group, label, left == right)

    def raises(self, group, label, function, exception=Exception):
        try:
            function()
        except exception:
            self.check(group, label, True)
        except Exception:
            self.check(group, label, False)
        else:
            self.check(group, label, False)

    def result(self):
        groups = {}
        for name in sorted(self.groups.keys()):
            item = self.groups[name]
            groups[name] = {
                "pass": item["pass"],
                "fail": item["fail"],
                "total": item["pass"] + item["fail"],
                "failures": list(item["failures"]),
            }
        passed = sum(item["pass"] for item in groups.values())
        failed = sum(item["fail"] for item in groups.values())
        return {
            "profile": SELF_TEST_PROFILE,
            "version": VERSION,
            "pass": passed,
            "fail": failed,
            "total": passed + failed,
            "groups": groups,
        }


def run_self_test():
    test = SelfTest()
    context, observations, boundary = self_test_input()
    bundle = reconstruct_bundle(context, observations, boundary)
    test.equal("RECONSTRUCTION", "accepted", bundle["result"], "ACCEPTED")
    test.equal("RECONSTRUCTION", "resolved", bundle["topics"]["receipts"][0]["state"], "RESOLVED")
    test.equal("RECONSTRUCTION", "resolved value", bundle["topics"]["receipts"][0]["resolved_declared_value"], "B")
    test.equal("RECONSTRUCTION", "sealed", bundle["boundary"]["state"], "SEALED")
    test.equal("RECONSTRUCTION", "authority", bundle["execution_authority"], "NONE")
    test.equal("TEXT_PROFILE", "declared profile", TEXT_PROFILE, "ORL-CHAT-UNICODE-SCALAR-EXACT-2-D01")
    test.equal("TEXT_PROFILE", "decomposed identifier accepted", identifier_errors("cafe\u0301", "identifier"), [])
    test.check("TEXT_PROFILE", "canonical equivalents remain distinct", stable_json("cafe\u0301") != stable_json("café"))
    test.check("TEXT_PROFILE", "frozen format refused", bool(identifier_errors("a\u200bb", "identifier")))
    test.check("TEXT_PROFILE", "surrogate refused", bool(identifier_errors("a\ud800b", "identifier")))
    test.check("TEXT_PROFILE", "frozen boundary whitespace refused", bool(identifier_errors("\u3000identifier", "identifier")))

    producer_like = deepcopy(bundle)
    producer_like["self_verification"] = {
        "profile": PRODUCER_VERIFICATION_PROFILE,
        "valid": True,
        "errors": [],
        "expected_conversation_resolution_id": bundle["conversation_resolution_id"],
        "expected_private_bundle_id": bundle["private_bundle_id"],
        "expected_public_receipt_id": bundle["public_receipt"]["public_receipt_id"],
    }
    test.check("VERIFICATION", "valid bundle", compare_bundle(producer_like)["valid"])

    for index, permutation in enumerate(itertools.permutations(observations)):
        candidate = reconstruct_bundle(context, list(permutation), boundary)
        test.equal("ORDER", "permutation resolution " + str(index), candidate["conversation_resolution_id"], bundle["conversation_resolution_id"])
        test.equal("ORDER", "permutation public " + str(index), candidate["public_receipt"]["public_receipt_id"], bundle["public_receipt"]["public_receipt_id"])
        test.equal("ORDER", "permutation state " + str(index), candidate["topics"]["receipts"][0]["state"], "RESOLVED")

    for mask in range(1 << len(observations)):
        selected = [observations[index] for index in range(len(observations)) if mask & (1 << index)]
        ordered = selected + [observations[index] for index in range(len(observations)) if not mask & (1 << index)]
        candidate = reconstruct_bundle(context, ordered, boundary)
        test.equal("PARTITION", "partition " + str(mask), candidate["conversation_resolution_id"], bundle["conversation_resolution_id"])

    mutations = []
    tampered = deepcopy(producer_like)
    tampered["topics"]["receipts"][0]["state"] = "ABSTAIN"
    mutations.append(("topic state", tampered))
    tampered = deepcopy(producer_like)
    tampered["topics"]["receipts"][0]["resolved_declared_value"] = "C"
    mutations.append(("resolved value", tampered))
    tampered = deepcopy(producer_like)
    tampered["graph"]["graph_root"] = "graph_forged"
    mutations.append(("graph root", tampered))
    tampered = deepcopy(producer_like)
    tampered["boundary"]["state"] = "OPEN"
    mutations.append(("boundary state", tampered))
    tampered = deepcopy(producer_like)
    tampered["public_receipt"]["public_receipt_id"] = "public_receipt_forged"
    mutations.append(("public receipt", tampered))
    tampered = deepcopy(producer_like)
    tampered["conversation_resolution_id"] = "conversation_resolution_forged"
    mutations.append(("resolution id", tampered))
    tampered = deepcopy(producer_like)
    tampered["private_bundle_id"] = "private_bundle_forged"
    mutations.append(("bundle id", tampered))
    tampered = deepcopy(producer_like)
    tampered["inputs"]["observations"][1]["action"]["declared_value"] = "C"
    mutations.append(("input", tampered))
    tampered = deepcopy(producer_like)
    tampered["self_verification"]["valid"] = False
    mutations.append(("producer verification", tampered))
    for label, candidate in mutations:
        test.check("TAMPER", label, not compare_bundle(candidate)["valid"])

    conflict_observations = deepcopy(observations)
    conflict = deepcopy(observations[0])
    conflict["observation_ref"] = "obs-conflict"
    conflict["action"]["declared_value"] = "C"
    conflict_observations.append(conflict)
    refused = reconstruct_bundle(context, conflict_observations, make_boundary("OPEN"))
    test.equal("REFUSAL", "action ref conflict", refused["result"], "REFUSED")
    test.check("REFUSAL", "valid refusal", compare_bundle(refused)["valid"])
    forged_refusal = deepcopy(refused)
    forged_refusal["errors"].append("forged")
    test.check("REFUSAL", "forged refusal", not compare_bundle(forged_refusal)["valid"])

    missing_observations = [deepcopy(observations[1])]
    missing_bundle = reconstruct_bundle(context, missing_observations, make_boundary("OPEN"))
    test.equal("STATES", "missing dependency", missing_bundle["topics"]["receipts"][0]["state"], "INCOMPLETE")
    test.equal("STATES", "missing reason", missing_bundle["topics"]["receipts"][0]["reason_code"], "MISSING_DEPENDENCY")

    competing_context = make_context("competing", make_participation("SINGLE_DECLARED_ENDORSER", ["alice", "bob"], threshold=1))
    competing_actions = [
        make_action("p1", "competing", "topic", "alice", "PROPOSE", "A"),
        make_action("p2", "competing", "topic", "bob", "PROPOSE", "B"),
        make_action("e1", "competing", "topic", "alice", "ENDORSE", None, ["p1"]),
    ]
    competing_observations = [make_observation("o" + str(index), "n", action, str(index)) for index, action in enumerate(competing_actions)]
    competing = reconstruct_bundle(competing_context, competing_observations, make_boundary("OPEN"))
    test.equal("STATES", "competing abstain", competing["topics"]["receipts"][0]["state"], "ABSTAIN")
    test.equal("STATES", "competing reason", competing["topics"]["receipts"][0]["reason_code"], "MULTIPLE_ACTIVE_PROPOSALS")

    withdrawal_actions = competing_actions + [
        make_action("withdraw-p2", "competing", "topic", "bob", "WITHDRAW", None, ["p2"]),
        make_action("e2", "competing", "topic", "bob", "ENDORSE", None, ["p1"]),
    ]
    withdrawal_observations = [make_observation("w" + str(index), "n", action, "w" + str(index)) for index, action in enumerate(withdrawal_actions)]
    withdrawal = reconstruct_bundle(competing_context, withdrawal_observations, make_boundary("OPEN"))
    test.equal("STATES", "withdrawal repair resolved", withdrawal["topics"]["receipts"][0]["state"], "RESOLVED")
    test.equal("STATES", "withdrawal repair value", withdrawal["topics"]["receipts"][0]["resolved_declared_value"], "A")

    object_actions = [
        make_action("object-proposal", "competing", "object-topic", "alice", "PROPOSE", "A"),
        make_action("object-endorse", "competing", "object-topic", "alice", "ENDORSE", None, ["object-proposal"]),
        make_action("object-object", "competing", "object-topic", "bob", "OBJECT", None, ["object-proposal"]),
    ]
    object_observations = [make_observation("j" + str(index), "n", action, "j" + str(index)) for index, action in enumerate(object_actions)]
    object_bundle = reconstruct_bundle(competing_context, object_observations, make_boundary("OPEN"))
    test.equal("STATES", "objected abstain", object_bundle["topics"]["receipts"][0]["state"], "ABSTAIN")
    test.equal("STATES", "objected reason", object_bundle["topics"]["receipts"][0]["reason_code"], "ACTIVE_PROPOSAL_OBJECTED")

    inactive_context = make_context("inactive-conflict", make_participation("ALL_DECLARED_PARTICIPANTS", ["alice", "bob"], threshold=2))
    inactive_actions = [
        make_action("active", "inactive-conflict", "topic", "alice", "PROPOSE", "A"),
        make_action("inactive", "inactive-conflict", "topic", "bob", "PROPOSE", "B"),
        make_action("withdraw-inactive", "inactive-conflict", "topic", "bob", "WITHDRAW", None, ["inactive"]),
        make_action("endorse-active-a", "inactive-conflict", "topic", "alice", "ENDORSE", None, ["active"]),
        make_action("endorse-active-b", "inactive-conflict", "topic", "bob", "ENDORSE", None, ["active"]),
        make_action("endorse-inactive", "inactive-conflict", "topic", "bob", "ENDORSE", None, ["inactive"]),
        make_action("object-inactive", "inactive-conflict", "topic", "bob", "OBJECT", None, ["inactive"]),
    ]
    inactive_observations = [make_observation("inactive-" + str(index), "n", action, "") for index, action in enumerate(inactive_actions)]
    inactive_bundle = reconstruct_bundle(inactive_context, inactive_observations, make_boundary("OPEN"))
    test.equal("STATES", "inactive signal conflict ignored for state", inactive_bundle["topics"]["receipts"][0]["state"], "RESOLVED")
    test.equal("STATES", "inactive signal conflict preserved", len(inactive_bundle["topics"]["receipts"][0]["signal_conflicts"]), 1)
    test.equal("STATES", "no active signal conflict", len(inactive_bundle["topics"]["receipts"][0]["active_signal_conflicts"]), 0)

    cycle_context = make_context("cycle", make_participation("NO_ENDORSEMENT_REQUIRED", threshold=0))
    cycle_actions = [
        make_action("cycle-a", "cycle", "topic", "alice", "AMEND", "A", ["cycle-b"]),
        make_action("cycle-b", "cycle", "topic", "bob", "AMEND", "B", ["cycle-a"]),
    ]
    cycle_observations = [make_observation("c" + str(index), "n", action, "c" + str(index)) for index, action in enumerate(cycle_actions)]
    cycle_bundle = reconstruct_bundle(cycle_context, cycle_observations, make_boundary("OPEN"))
    test.equal("STATES", "cycle abstain", cycle_bundle["topics"]["receipts"][0]["state"], "ABSTAIN")
    test.equal("STATES", "cycle reason", cycle_bundle["topics"]["receipts"][0]["reason_code"], "DEPENDENCY_CYCLE")

    open_bundle = reconstruct_bundle(context, observations, make_boundary("OPEN"))
    test.equal("BOUNDARY", "open", open_bundle["boundary"]["state"], "OPEN")
    test.equal("BOUNDARY", "sealed", bundle["boundary"]["state"], "SEALED")
    expected_refs = [item["observation_ref"] for item in observations]
    incomplete_boundary = reconstruct_bundle(context, observations[:-1], make_boundary("SEALED", expected_refs))
    test.equal("BOUNDARY", "incomplete", incomplete_boundary["boundary"]["state"], "INCOMPLETE")
    conflict_boundary = reconstruct_bundle(context, observations, make_boundary("SEALED", expected_refs[:-1]))
    test.equal("BOUNDARY", "conflict", conflict_boundary["boundary"]["state"], "CONFLICT")
    mixed_boundary = reconstruct_bundle(context, observations, make_boundary("SEALED", expected_refs[:-1] + ["unknown-observation"]))
    test.equal("BOUNDARY", "mixed conflict", mixed_boundary["boundary"]["state"], "CONFLICT")

    profile_records = [
        make_participation("NO_ENDORSEMENT_REQUIRED", threshold=0),
        make_participation("SINGLE_DECLARED_ENDORSER", ["a", "b"], threshold=1),
        make_participation("ALL_DECLARED_PARTICIPANTS", ["a", "b"], threshold=2),
        make_participation("EXACT_DECLARED_PARTICIPANT_SET", ["a", "b", "c"], ["a", "c"], 2),
        make_participation("DECLARED_THRESHOLD", ["a", "b", "c"], threshold=2),
    ]
    for record in profile_records:
        test.equal("PARTICIPATION", record["profile"] + " valid", participation_errors(record), [])
    test.check("PARTICIPATION", "none satisfied", participation_result(profile_records[0], [])["satisfied"])
    test.check("PARTICIPATION", "single incomplete", not participation_result(profile_records[1], [])["satisfied"])
    test.check("PARTICIPATION", "single satisfied", participation_result(profile_records[1], ["a"])["satisfied"])
    test.check("PARTICIPATION", "all incomplete", not participation_result(profile_records[2], ["a"])["satisfied"])
    test.check("PARTICIPATION", "all satisfied", participation_result(profile_records[2], ["a", "b"])["satisfied"])
    test.check("PARTICIPATION", "exact satisfied", participation_result(profile_records[3], ["a", "c"])["satisfied"])
    test.check("PARTICIPATION", "exact surplus", not participation_result(profile_records[3], ["a", "b", "c"])["satisfied"])
    test.check("PARTICIPATION", "threshold incomplete", not participation_result(profile_records[4], ["a"])["satisfied"])
    test.check("PARTICIPATION", "threshold satisfied", participation_result(profile_records[4], ["a", "c"])["satisfied"])

    test.equal("IDENTITY", "stable object order", stable_json({"b": 2, "a": 1}), stable_json({"a": 1, "b": 2}))
    test.equal("IDENTITY", "same action", compute_action_id(observations[0]["action"]), compute_action_id(deepcopy(observations[0]["action"])))
    changed_action = deepcopy(observations[0]["action"])
    changed_action["declared_value"] = "changed"
    test.check("IDENTITY", "changed action", compute_action_id(observations[0]["action"]) != compute_action_id(changed_action))
    changed_presentation = deepcopy(observations[0])
    changed_presentation["presentation"] = "changed presentation"
    test.equal("IDENTITY", "presentation independent action", compute_action_id(observations[0]["action"]), compute_action_id(changed_presentation["action"]))
    test.check("IDENTITY", "presentation changes observation", compute_observation_id(observations[0]) != compute_observation_id(changed_presentation))

    invalid_context = deepcopy(context)
    invalid_context["unsupported"] = True
    test.check("VALIDATION", "context field", bool(context_errors(invalid_context)))
    invalid_context = deepcopy(context)
    invalid_context["execution_authority"] = "EXECUTE"
    test.check("VALIDATION", "authority", bool(context_errors(invalid_context)))
    invalid_context = deepcopy(context)
    invalid_context["conversation_id"] = " bad"
    test.check("VALIDATION", "identifier whitespace", bool(context_errors(invalid_context)))
    invalid_action = deepcopy(observations[0]["action"])
    invalid_action["declared_value"] = None
    test.check("VALIDATION", "proposal null", bool(action_errors(invalid_action)))
    invalid_action = deepcopy(observations[0]["action"])
    invalid_action["targets"] = ["unexpected"]
    test.check("VALIDATION", "proposal target", bool(action_errors(invalid_action)))
    invalid_action = deepcopy(observations[0]["action"])
    invalid_action["declared_value"] = 1.5
    test.check("VALIDATION", "float", bool(action_errors(invalid_action)))
    invalid_observation = deepcopy(observations[0])
    invalid_observation["presentation"] = "a\rb"
    test.check("VALIDATION", "carriage return", bool(observation_errors(invalid_observation)))
    invalid_boundary = make_boundary("OPEN", ["unexpected"])
    test.check("VALIDATION", "open boundary refs", bool(boundary_errors(invalid_boundary)))

    test.equal("PARSER", "basic", parse_json_text('{"a":1}'), {"a": 1})
    test.equal("PARSER", "maximum positive integer", parse_json_text('{"a":9007199254740991}'), {"a": 9007199254740991})
    test.equal("PARSER", "maximum negative integer", parse_json_text('{"a":-9007199254740991}'), {"a": -9007199254740991})
    test.raises("PARSER", "integer above exact range", lambda: parse_json_text('{"a":9007199254740992}'), VerificationInputError)
    test.raises("PARSER", "integer below exact range", lambda: parse_json_text('{"a":-9007199254740992}'), VerificationInputError)
    test.raises("PARSER", "extreme integer token", lambda: parse_json_text('{"a":' + '9' * 1024 + '}'), VerificationInputError)
    test.raises("PARSER", "duplicate", lambda: parse_json_text('{"a":1,"a":2}'), DuplicateKeyError)
    test.raises("PARSER", "float", lambda: parse_json_text('{"a":1.5}'), VerificationInputError)
    test.raises("PARSER", "NaN", lambda: parse_json_text('{"a":NaN}'), VerificationInputError)
    test.raises("PARSER", "trailing comma", lambda: parse_json_text('{"a":1,}'), VerificationInputError)

    public_text = stable_json(bundle["public_receipt"])
    test.check("PRIVACY", "no presentation", "PRIVATE_PRESENTATION_MARKER_ALPHA" not in public_text and "PRIVATE_PRESENTATION_MARKER_BETA" not in public_text)
    test.check("PRIVACY", "no value", '"B"' not in public_text)
    test.check("PRIVACY", "private retains", '"B"' in stable_json(bundle))

    with TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "bundle.json"
        save_json_file(path, producer_like)
        loaded = load_json_file(path)
        test.check("FILE", "round trip", compare_bundle(loaded)["valid"])
        strict_loaded = load_json_file(path, strict_canonical=True)
        test.check("FILE", "strict artifact", compare_bundle(strict_loaded)["valid"])
        compact_path = Path(temp_dir) / "compact.json"
        with compact_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(stable_json(producer_like) + "\n")
        test.raises("FILE", "compact not artifact canonical", lambda: load_json_file(compact_path, strict_canonical=True), VerificationInputError)

    return test.result()


def verify_corpus_manifest(path, strict_canonical=False):
    path = Path(path)
    try:
        manifest = load_json_file(path, strict_canonical=strict_canonical)
    except (OSError, VerificationInputError) as exc:
        return {
            "profile": CORPUS_VERIFICATION_PROFILE,
            "valid": False,
            "errors": [str(exc)],
            "entries": [],
        }

    errors = []
    fields = ["profile", "version", "corpus_profile", "entries", "manifest_id"]
    errors.extend(exact_field_errors(manifest, fields, "manifest"))
    if errors:
        return {
            "profile": CORPUS_VERIFICATION_PROFILE,
            "valid": False,
            "errors": errors,
            "entries": [],
        }
    if manifest["profile"] != CORPUS_MANIFEST_PROFILE:
        errors.append("manifest.profile mismatch")
    if manifest["version"] != VERSION:
        errors.append("manifest.version mismatch")
    if manifest["corpus_profile"] != CORPUS_PROFILE:
        errors.append("manifest.corpus_profile mismatch")
    if not isinstance(manifest["entries"], list):
        errors.append("manifest.entries must be an array")
    without_id = deepcopy(manifest)
    supplied_manifest_id = without_id.pop("manifest_id")
    expected_manifest_id = derive_id("corpus_manifest", CORPUS_MANIFEST_PROFILE, without_id)
    if supplied_manifest_id != expected_manifest_id:
        errors.append("manifest_id mismatch")
    if errors:
        return {
            "profile": CORPUS_VERIFICATION_PROFILE,
            "valid": False,
            "errors": errors,
            "entries": [],
        }

    entry_results = []
    base = path.parent
    for index, entry in enumerate(manifest["entries"]):
        entry_errors = exact_field_errors(
            entry,
            ["scenario", "file", "sha256", "result", "conversation_resolution_id", "private_bundle_id", "public_receipt_id"],
            "entry",
        )
        if entry_errors:
            entry_results.append({"index": index, "valid": False, "errors": entry_errors})
            continue
        bundle_path = base / entry["file"]
        try:
            raw = bundle_path.read_bytes()
            actual_sha = hashlib.sha256(raw).hexdigest()
            bundle = load_json_file(bundle_path, strict_canonical=False)
        except (OSError, VerificationInputError) as exc:
            entry_results.append({
                "scenario": entry["scenario"],
                "file": entry["file"],
                "valid": False,
                "errors": [str(exc)],
            })
            continue
        verification = compare_bundle(bundle)
        found = []
        if actual_sha != entry["sha256"]:
            found.append("sha256 mismatch")
        if bundle.get("result") != entry["result"]:
            found.append("result mismatch")
        if bundle.get("conversation_resolution_id") != entry["conversation_resolution_id"]:
            found.append("conversation_resolution_id mismatch")
        if bundle.get("private_bundle_id") != entry["private_bundle_id"]:
            found.append("private_bundle_id mismatch")
        if bundle.get("public_receipt", {}).get("public_receipt_id") != entry["public_receipt_id"]:
            found.append("public_receipt_id mismatch")
        found.extend(verification["errors"])
        entry_results.append({
            "scenario": entry["scenario"],
            "file": entry["file"],
            "valid": not found,
            "errors": found,
            "sha256": actual_sha,
        })

    all_errors = list(errors)
    for item in entry_results:
        if not item["valid"]:
            all_errors.append("entry failed: " + str(item.get("scenario", item.get("index"))))
    return {
        "profile": CORPUS_VERIFICATION_PROFILE,
        "valid": not all_errors,
        "errors": all_errors,
        "manifest_id": supplied_manifest_id,
        "entries": entry_results,
        "passed_entries": sum(1 for item in entry_results if item["valid"]),
        "total_entries": len(entry_results),
    }


def print_self_test(result):
    for group in sorted(result["groups"].keys()):
        item = result["groups"][group]
        print(group + ": " + str(item["pass"]) + "/" + str(item["total"]) + " PASS")
        for failure in item["failures"]:
            print("  FAIL: " + failure)
    print("TOTAL: " + str(result["pass"]) + "/" + str(result["total"]) + " PASS")


def print_verification(result, path):
    print("ORL-Chat independent verification")
    print("file: " + str(path))
    print("result: " + ("PASS" if result["valid"] else "FAIL"))
    for error in result["errors"]:
        print("error: " + error)
    if result.get("expected_conversation_resolution_id"):
        print("expected_conversation_resolution_id: " + result["expected_conversation_resolution_id"])
    if result.get("expected_private_bundle_id"):
        print("expected_private_bundle_id: " + result["expected_private_bundle_id"])
    if result.get("expected_public_receipt_id"):
        print("expected_public_receipt_id: " + result["expected_public_receipt_id"])


def print_corpus(result):
    print("ORL-Chat corpus verification")
    print("result: " + ("PASS" if result["valid"] else "FAIL"))
    print("entries: " + str(result.get("passed_entries", 0)) + "/" + str(result.get("total_entries", 0)) + " PASS")
    for entry in result.get("entries", []):
        print(str(entry.get("scenario", entry.get("index"))) + ": " + ("PASS" if entry["valid"] else "FAIL"))
        for error in entry.get("errors", []):
            print("  error: " + error)
    for error in result.get("errors", []):
        print("error: " + error)


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="ORL_Chat_Independent_Verifier_v2_0_0.py")
    parser.add_argument("--verify")
    parser.add_argument("--verify-corpus")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--strict-canonical", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    selected = sum(bool(item) for item in (args.verify, args.verify_corpus, args.self_test))
    if selected != 1:
        print("ERROR: choose exactly one of --verify, --verify-corpus, or --self-test", file=sys.stderr)
        return 2

    if args.self_test:
        result = run_self_test()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        else:
            print_self_test(result)
        return 0 if result["fail"] == 0 else 1

    if args.verify_corpus:
        result = verify_corpus_manifest(args.verify_corpus, strict_canonical=args.strict_canonical)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        else:
            print_corpus(result)
        return 0 if result["valid"] else 1

    try:
        bundle = load_json_file(args.verify, strict_canonical=args.strict_canonical)
    except (OSError, VerificationInputError) as exc:
        result = {
            "profile": INDEPENDENT_VERIFICATION_PROFILE,
            "valid": False,
            "errors": [str(exc)],
        }
    else:
        result = compare_bundle(bundle)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print_verification(result, args.verify)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
