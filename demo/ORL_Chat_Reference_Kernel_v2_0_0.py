#!/usr/bin/env python3

import argparse
import hashlib
import itertools
import json
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

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
VERIFICATION_PROFILE = "ORL-CHAT-PRODUCER-VERIFICATION-2-D01"
AUDIT_PROFILE = "ORL-CHAT-PRODUCER-AUDIT-2-D01"
CORPUS_PROFILE = "ORL-CHAT-CORPUS-2-D01"
CORPUS_MANIFEST_PROFILE = "ORL-CHAT-CORPUS-MANIFEST-2-D01"
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
BOUNDARY_STATES = ("OPEN", "SEALED")


class StrictJSONError(ValueError):
    pass


class DuplicateKeyError(StrictJSONError):
    pass


def canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_artifact_text(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    ) + "\n"


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def identity(prefix, profile, value):
    return prefix + "_" + sha256_text(canonical_json({"profile": profile, "value": value}))


def reject_duplicate_object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError("duplicate JSON object key: " + key)
        result[key] = value
    return result


def reject_float(value):
    raise StrictJSONError("floating-point JSON numbers are not supported: " + value)


def reject_constant(value):
    raise StrictJSONError("non-standard JSON numeric constant is not supported: " + value)


def parse_exact_integer(value):
    digits = value[1:] if value.startswith("-") else value
    magnitude = digits.lstrip("0") or "0"
    maximum = str(MAX_SAFE_INTEGER)
    if len(magnitude) > len(maximum) or (len(magnitude) == len(maximum) and magnitude > maximum):
        raise StrictJSONError("integer exceeds exact interoperable range: " + value)
    return int(value)


def strict_json_loads(text):
    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_object_pairs,
            parse_int=parse_exact_integer,
            parse_float=reject_float,
            parse_constant=reject_constant,
        )
    except StrictJSONError:
        raise
    except json.JSONDecodeError as exc:
        raise StrictJSONError("invalid JSON: " + str(exc)) from exc


def read_json_document(path, strict_canonical=False, max_bytes=MAX_INPUT_BYTES):
    path = Path(path)
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise StrictJSONError("JSON document exceeds maximum byte length")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictJSONError("JSON document must be strict UTF-8") from exc
    if text.startswith("\ufeff"):
        raise StrictJSONError("UTF-8 BOM is not supported")
    value = strict_json_loads(text)
    if strict_canonical:
        expected = canonical_artifact_text(value)
        if text != expected:
            raise StrictJSONError("JSON document is not in canonical artifact form with sorted keys, two-space indentation, and one LF terminator")
    return value


def write_json_document(path, value, compact=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = canonical_json(value) + "\n"
    else:
        text = canonical_artifact_text(value)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


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


def contains_forbidden_identifier_character(value):
    for char in value:
        code_point = ord(char)
        if is_frozen_control_code_point(code_point) or is_frozen_format_code_point(code_point) or is_surrogate_code_point(code_point):
            return True
    return False


def contains_forbidden_text_character(value):
    for char in value:
        code_point = ord(char)
        if code_point in (0x0009, 0x000A):
            continue
        if is_frozen_control_code_point(code_point) or is_frozen_format_code_point(code_point) or is_surrogate_code_point(code_point):
            return True
    return False


def exact_fields(record, expected_fields, label):
    if not isinstance(record, dict):
        return [label + ": must be an object"]
    actual = set(record.keys())
    expected = set(expected_fields)
    errors = []
    for field in sorted(expected - actual):
        errors.append(label + ": missing field " + field)
    for field in sorted(actual - expected):
        errors.append(label + ": unsupported field " + field)
    return errors


def validate_identifier(value, label):
    if not isinstance(value, str):
        return [label + ": must be a string"]
    errors = []
    if value == "":
        errors.append(label + ": must not be empty")
    if len(value) > MAX_IDENTIFIER_LENGTH:
        errors.append(label + ": exceeds maximum length")
    if has_frozen_boundary_whitespace(value):
        errors.append(label + ": leading or trailing whitespace is not allowed")
    if contains_forbidden_identifier_character(value):
        errors.append(label + ": control, format, and surrogate characters are not allowed")
    return errors


def validate_presentation(value, label):
    if not isinstance(value, str):
        return [label + ": must be a string"]
    errors = []
    if len(value) > MAX_PRESENTATION_LENGTH:
        errors.append(label + ": exceeds maximum length")
    if contains_forbidden_text_character(value):
        errors.append(label + ": unsupported control, format, carriage-return, or surrogate character")
    return errors


def validate_declared_value(value, label="declared_value"):
    errors = []
    node_count = [0]

    def walk(item, path, depth):
        node_count[0] += 1
        if node_count[0] > MAX_VALUE_NODES:
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
            if contains_forbidden_text_character(item):
                errors.append(path + ": unsupported control, format, carriage-return, or surrogate character")
            return
        if isinstance(item, list):
            if len(item) > MAX_ARRAY_LENGTH:
                errors.append(path + ": array exceeds maximum length")
                return
            for index, child in enumerate(item):
                walk(child, path + "[" + str(index) + "]", depth + 1)
            return
        if isinstance(item, dict):
            if len(item) > MAX_OBJECT_FIELDS:
                errors.append(path + ": object exceeds maximum field count")
                return
            for key in sorted(item.keys()):
                key_errors = validate_identifier(key, path + ".<key>")
                errors.extend(key_errors)
                walk(item[key], path + "." + key, depth + 1)
            return
        errors.append(path + ": unsupported value type")

    walk(value, label, 0)
    return errors


def validate_identifier_array(value, label, maximum):
    if not isinstance(value, list):
        return [label + ": must be an array"]
    errors = []
    if len(value) > maximum:
        errors.append(label + ": exceeds maximum length")
    for index, item in enumerate(value):
        errors.extend(validate_identifier(item, label + "[" + str(index) + "]"))
    if len(value) != len(set(value)):
        errors.append(label + ": duplicate values are not allowed")
    return errors


def validate_participation(record):
    fields = ["schema", "profile", "participants", "required_endorsers", "threshold"]
    errors = exact_fields(record, fields, "participation")
    if errors:
        return errors
    if record["schema"] != PARTICIPATION_SCHEMA:
        errors.append("participation.schema: unsupported schema")
    if record["profile"] not in PARTICIPATION_PROFILES:
        errors.append("participation.profile: unsupported profile")
    errors.extend(validate_identifier_array(record["participants"], "participation.participants", MAX_PARTICIPANTS))
    errors.extend(validate_identifier_array(record["required_endorsers"], "participation.required_endorsers", MAX_PARTICIPANTS))
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
        if record["participants"] or record["required_endorsers"] or threshold != 0:
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


def validate_context(record):
    fields = [
        "schema",
        "conversation_id",
        "purpose_id",
        "ruleset_profile",
        "participation",
        "execution_authority",
    ]
    errors = exact_fields(record, fields, "context")
    if errors:
        return errors
    if record["schema"] != CONTEXT_SCHEMA:
        errors.append("context.schema: unsupported schema")
    errors.extend(validate_identifier(record["conversation_id"], "context.conversation_id"))
    errors.extend(validate_identifier(record["purpose_id"], "context.purpose_id"))
    if record["ruleset_profile"] != RULESET_PROFILE:
        errors.append("context.ruleset_profile: unsupported ruleset profile")
    errors.extend(validate_participation(record["participation"]))
    if record["execution_authority"] != EXECUTION_AUTHORITY:
        errors.append("context.execution_authority: must be NONE")
    return errors


def validate_action(record):
    fields = [
        "schema",
        "action_ref",
        "conversation_id",
        "topic_id",
        "actor",
        "kind",
        "declared_value",
        "targets",
    ]
    errors = exact_fields(record, fields, "action")
    if errors:
        return errors
    if record["schema"] != ACTION_SCHEMA:
        errors.append("action.schema: unsupported schema")
    errors.extend(validate_identifier(record["action_ref"], "action.action_ref"))
    errors.extend(validate_identifier(record["conversation_id"], "action.conversation_id"))
    errors.extend(validate_identifier(record["topic_id"], "action.topic_id"))
    errors.extend(validate_identifier(record["actor"], "action.actor"))
    kind = record["kind"]
    if kind not in ACTION_KINDS:
        errors.append("action.kind: unsupported kind")
    errors.extend(validate_identifier_array(record["targets"], "action.targets", 1))
    if kind in PROPOSAL_KINDS:
        if record["declared_value"] is None:
            errors.append("action.declared_value: proposal-producing actions require a non-null value")
        else:
            errors.extend(validate_declared_value(record["declared_value"], "action.declared_value"))
    elif kind in ("WITHDRAW", "ENDORSE", "OBJECT"):
        if record["declared_value"] is not None:
            errors.append("action.declared_value: relation-only actions require null")
    if kind == "PROPOSE" and record["targets"] != []:
        errors.append("action.targets: PROPOSE requires no targets")
    if kind in RELATION_KINDS and len(record["targets"]) != 1:
        errors.append("action.targets: relation action requires exactly one target")
    return errors


def validate_observation(record):
    fields = ["schema", "observation_ref", "source", "presentation", "action"]
    errors = exact_fields(record, fields, "observation")
    if errors:
        return errors
    if record["schema"] != OBSERVATION_SCHEMA:
        errors.append("observation.schema: unsupported schema")
    errors.extend(validate_identifier(record["observation_ref"], "observation.observation_ref"))
    errors.extend(validate_identifier(record["source"], "observation.source"))
    errors.extend(validate_presentation(record["presentation"], "observation.presentation"))
    errors.extend(validate_action(record["action"]))
    return errors


def validate_boundary(record):
    fields = ["schema", "state", "expected_observation_refs"]
    errors = exact_fields(record, fields, "boundary")
    if errors:
        return errors
    if record["schema"] != BOUNDARY_SCHEMA:
        errors.append("boundary.schema: unsupported schema")
    if record["state"] not in BOUNDARY_STATES:
        errors.append("boundary.state: must be OPEN or SEALED")
    errors.extend(validate_identifier_array(record["expected_observation_refs"], "boundary.expected_observation_refs", MAX_OBSERVATIONS))
    if record["state"] == "OPEN" and record["expected_observation_refs"]:
        errors.append("boundary.expected_observation_refs: OPEN boundary requires an empty list")
    return errors


def canonical_participation(record):
    return {
        "schema": PARTICIPATION_SCHEMA,
        "profile": record["profile"],
        "participants": sorted(record["participants"]),
        "required_endorsers": sorted(record["required_endorsers"]),
        "threshold": record["threshold"],
    }


def canonical_context(record):
    return {
        "schema": CONTEXT_SCHEMA,
        "conversation_id": record["conversation_id"],
        "purpose_id": record["purpose_id"],
        "ruleset_profile": RULESET_PROFILE,
        "participation": canonical_participation(record["participation"]),
        "execution_authority": EXECUTION_AUTHORITY,
    }


def canonical_action(record):
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


def canonical_observation(record):
    return {
        "schema": OBSERVATION_SCHEMA,
        "observation_ref": record["observation_ref"],
        "source": record["source"],
        "presentation": record["presentation"],
        "action": canonical_action(record["action"]),
    }


def canonical_boundary(record):
    return {
        "schema": BOUNDARY_SCHEMA,
        "state": record["state"],
        "expected_observation_refs": sorted(record["expected_observation_refs"]),
    }


def context_id(record):
    return identity("context", CONTEXT_SCHEMA, canonical_context(record))


def action_id(record):
    return identity("action", ACTION_SCHEMA, canonical_action(record))


def observation_id(record):
    action = canonical_action(record["action"])
    basis = {
        "schema": OBSERVATION_SCHEMA,
        "observation_ref": record["observation_ref"],
        "source": record["source"],
        "presentation": record["presentation"],
        "action_id": action_id(action),
    }
    return identity("observation", OBSERVATION_SCHEMA, basis)


def make_participation(profile, participants=None, required_endorsers=None, threshold=0):
    return {
        "schema": PARTICIPATION_SCHEMA,
        "profile": profile,
        "participants": list(participants or []),
        "required_endorsers": list(required_endorsers or []),
        "threshold": threshold,
    }


def make_context(conversation_id, purpose_id, participation):
    return {
        "schema": CONTEXT_SCHEMA,
        "conversation_id": conversation_id,
        "purpose_id": purpose_id,
        "ruleset_profile": RULESET_PROFILE,
        "participation": deepcopy(participation),
        "execution_authority": EXECUTION_AUTHORITY,
    }


def make_action(action_ref, conversation_id, topic_id, actor, kind, declared_value=None, targets=None):
    return {
        "schema": ACTION_SCHEMA,
        "action_ref": action_ref,
        "conversation_id": conversation_id,
        "topic_id": topic_id,
        "actor": actor,
        "kind": kind,
        "declared_value": deepcopy(declared_value),
        "targets": list(targets or []),
    }


def make_observation(observation_ref, source, action, presentation=""):
    return {
        "schema": OBSERVATION_SCHEMA,
        "observation_ref": observation_ref,
        "source": source,
        "presentation": presentation,
        "action": deepcopy(action),
    }


def make_boundary(state="OPEN", expected_observation_refs=None):
    return {
        "schema": BOUNDARY_SCHEMA,
        "state": state,
        "expected_observation_refs": list(expected_observation_refs or []),
    }


def make_input(context, observations, boundary):
    return {
        "context": deepcopy(context),
        "observations": deepcopy(observations),
        "boundary": deepcopy(boundary),
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
    refusal["refusal_id"] = identity("refusal", PRIVATE_BUNDLE_PROFILE, refusal)
    return refusal


def prepare_context(record):
    errors = validate_context(record)
    if errors:
        return {"validation_state": "REFUSED", "errors": errors}
    canonical = canonical_context(record)
    return {
        "validation_state": "ACCEPTED",
        "context": canonical,
        "context_id": context_id(canonical),
    }


def prepare_observations(observations, context):
    if not isinstance(observations, list):
        return {"validation_state": "REFUSED", "errors": ["observations: must be an array"]}
    if len(observations) > MAX_OBSERVATIONS:
        return {"validation_state": "REFUSED", "errors": ["observations: exceeds maximum length"]}

    errors = []
    validated = []
    for index, record in enumerate(observations):
        found = validate_observation(record)
        if found:
            errors.extend("observations[" + str(index) + "]: " + item for item in found)
        else:
            canonical = canonical_observation(record)
            if canonical["action"]["conversation_id"] != context["conversation_id"]:
                errors.append("observations[" + str(index) + "]: action.conversation_id does not match context")
            else:
                validated.append(canonical)
    if errors:
        return {"validation_state": "REFUSED", "errors": errors}

    by_observation_id = {}
    by_observation_ref = defaultdict(dict)
    for record in validated:
        oid = observation_id(record)
        by_observation_id[oid] = record
        by_observation_ref[record["observation_ref"]][oid] = record

    conflicts = []
    for ref in sorted(by_observation_ref.keys()):
        ids = sorted(by_observation_ref[ref].keys())
        if len(ids) > 1:
            conflicts.append({"observation_ref": ref, "observation_ids": ids})
    if conflicts:
        return {
            "validation_state": "REFUSED",
            "errors": ["observation_ref content conflict: " + item["observation_ref"] for item in conflicts],
            "observation_ref_conflicts": conflicts,
        }

    by_action_ref = defaultdict(dict)
    action_observations = defaultdict(list)
    action_sources = defaultdict(set)
    action_presentations = defaultdict(list)
    action_records = {}

    for oid in sorted(by_observation_id.keys()):
        observation = by_observation_id[oid]
        action = observation["action"]
        aid = action_id(action)
        ref = action["action_ref"]
        by_action_ref[ref][aid] = action
        action_records[aid] = action
        action_observations[aid].append(oid)
        action_sources[aid].add(observation["source"])
        action_presentations[aid].append({
            "observation_id": oid,
            "presentation": observation["presentation"],
        })

    action_ref_conflicts = []
    for ref in sorted(by_action_ref.keys()):
        ids = sorted(by_action_ref[ref].keys())
        if len(ids) > 1:
            action_ref_conflicts.append({"action_ref": ref, "action_ids": ids})
    if action_ref_conflicts:
        return {
            "validation_state": "REFUSED",
            "errors": ["action_ref content conflict: " + item["action_ref"] for item in action_ref_conflicts],
            "action_ref_conflicts": action_ref_conflicts,
        }

    action_entries = []
    action_ref_to_id = {}
    for aid in sorted(action_records.keys()):
        action = action_records[aid]
        action_ref_to_id[action["action_ref"]] = aid
        action_entries.append({
            "action_id": aid,
            "action": deepcopy(action),
            "observation_ids": sorted(action_observations[aid]),
            "sources": sorted(action_sources[aid]),
            "observation_count": len(action_observations[aid]),
            "presentations": sorted(action_presentations[aid], key=lambda item: item["observation_id"]),
        })

    observation_entries = []
    for oid in sorted(by_observation_id.keys()):
        observation = by_observation_id[oid]
        observation_entries.append({
            "observation_id": oid,
            "observation_ref": observation["observation_ref"],
            "source": observation["source"],
            "presentation": observation["presentation"],
            "action_id": action_id(observation["action"]),
        })

    action_set_basis = {
        "profile": ACTION_SCHEMA,
        "action_ids": sorted(action_records.keys()),
    }
    observation_set_basis = {
        "profile": OBSERVATION_SCHEMA,
        "observation_ids": sorted(by_observation_id.keys()),
    }

    return {
        "validation_state": "ACCEPTED",
        "raw_observation_count": len(observations),
        "unique_observation_count": len(by_observation_id),
        "exact_observation_duplicate_count": len(observations) - len(by_observation_id),
        "unique_action_count": len(action_records),
        "observation_multiplicity_count": len(by_observation_id) - len(action_records),
        "actions": action_entries,
        "observations": observation_entries,
        "action_ref_to_id": action_ref_to_id,
        "action_set_id": identity("action_set", ACTION_SCHEMA, action_set_basis),
        "observation_set_id": identity("observation_set", OBSERVATION_SCHEMA, observation_set_basis),
    }


def build_graph(evidence, context):
    action_by_ref = {}
    action_id_by_ref = {}
    action_entry_by_ref = {}
    for entry in evidence["actions"]:
        action = entry["action"]
        ref = action["action_ref"]
        action_by_ref[ref] = action
        action_id_by_ref[ref] = entry["action_id"]
        action_entry_by_ref[ref] = entry

    errors = []
    missing_dependencies = []
    edges = []
    participant_set = set(context["participation"]["participants"])

    for ref in sorted(action_by_ref.keys()):
        action = action_by_ref[ref]
        if action["kind"] in ("ENDORSE", "OBJECT") and action["actor"] not in participant_set:
            errors.append("action " + ref + ": actor is not admitted by the participation profile")
        if action["kind"] in RELATION_KINDS:
            target_ref = action["targets"][0]
            if target_ref == ref:
                errors.append("action " + ref + ": self-target is not supported")
                continue
            if target_ref not in action_by_ref:
                missing_dependencies.append({
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

    cycle_refs = set()
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
            cycle_refs.update(path[path_index[current]:])
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

    graph_basis = {
        "profile": GRAPH_PROFILE,
        "nodes": nodes,
        "edges": sorted(edges, key=lambda item: (item["source_action_id"], item["relation"], item["target_action_id"])),
        "missing_dependencies": sorted(missing_dependencies, key=lambda item: (item["action_ref"], item["missing_target_ref"])),
        "cycle_action_refs": sorted(cycle_refs),
    }

    return {
        "validation_state": "ACCEPTED",
        "profile": GRAPH_PROFILE,
        "nodes": graph_basis["nodes"],
        "edges": graph_basis["edges"],
        "missing_dependencies": graph_basis["missing_dependencies"],
        "cycle_action_refs": graph_basis["cycle_action_refs"],
        "graph_root": identity("graph", GRAPH_PROFILE, graph_basis),
        "action_by_ref": action_by_ref,
        "action_id_by_ref": action_id_by_ref,
        "action_entry_by_ref": action_entry_by_ref,
    }


def dependency_ready_map(action_by_ref, cycle_refs):
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
            if current in cycle_refs or current in path_refs:
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


def evaluate_participation(participation, endorsers):
    profile = participation["profile"]
    participant_set = set(participation["participants"])
    endorser_set = set(endorsers)
    required = set(participation["required_endorsers"])
    threshold = participation["threshold"]

    if profile == "NO_ENDORSEMENT_REQUIRED":
        satisfied = True
        missing = []
        surplus = sorted(endorser_set)
    elif profile == "SINGLE_DECLARED_ENDORSER":
        satisfied = len(endorser_set) >= 1
        missing = [] if satisfied else ["ONE_DECLARED_ENDORSER"]
        surplus = []
    elif profile == "ALL_DECLARED_PARTICIPANTS":
        missing = sorted(participant_set - endorser_set)
        surplus = sorted(endorser_set - participant_set)
        satisfied = not missing and not surplus
    elif profile == "EXACT_DECLARED_PARTICIPANT_SET":
        missing = sorted(required - endorser_set)
        surplus = sorted(endorser_set - required)
        satisfied = not missing and not surplus
    else:
        missing_count = max(0, threshold - len(endorser_set))
        missing = [] if missing_count == 0 else ["ADDITIONAL_ENDORSERS_REQUIRED:" + str(missing_count)]
        surplus = sorted(endorser_set - participant_set)
        satisfied = len(endorser_set) >= threshold and not surplus

    return {
        "profile": profile,
        "participants": sorted(participant_set),
        "required_endorsers": sorted(required),
        "threshold": threshold,
        "endorsers": sorted(endorser_set),
        "endorsement_count": len(endorser_set),
        "missing": missing,
        "surplus": surplus,
        "satisfied": satisfied,
    }


def make_topic_receipt(topic_id, actions, action_id_by_ref, graph, context):
    action_by_ref = {action["action_ref"]: action for action in actions}
    cycle_refs = set(graph["cycle_action_refs"]) & set(action_by_ref.keys())
    missing = [item for item in graph["missing_dependencies"] if item["action_ref"] in action_by_ref]
    ready_map = dependency_ready_map(action_by_ref, cycle_refs)

    proposal_refs = sorted(ref for ref, action in action_by_ref.items() if action["kind"] in PROPOSAL_KINDS and ready_map.get(ref, False))
    superseded_refs = set()
    withdrawn_refs = set()

    for ref in sorted(action_by_ref.keys()):
        action = action_by_ref[ref]
        if not ready_map.get(ref, False):
            continue
        if action["kind"] == "AMEND":
            superseded_refs.add(action["targets"][0])
        elif action["kind"] == "WITHDRAW":
            withdrawn_refs.add(action["targets"][0])

    defeated_refs = superseded_refs | withdrawn_refs
    active_refs = sorted(ref for ref in proposal_refs if ref not in defeated_refs)
    endorsements_by_target = defaultdict(set)
    objections_by_target = defaultdict(set)
    signal_actions = defaultdict(list)

    for ref in sorted(action_by_ref.keys()):
        action = action_by_ref[ref]
        if not ready_map.get(ref, False):
            continue
        if action["kind"] == "ENDORSE":
            target = action["targets"][0]
            endorsements_by_target[target].add(action["actor"])
            signal_actions[(target, action["actor"])].append(("ENDORSE", ref))
        elif action["kind"] == "OBJECT":
            target = action["targets"][0]
            objections_by_target[target].add(action["actor"])
            signal_actions[(target, action["actor"])].append(("OBJECT", ref))

    signal_conflicts = []
    for key in sorted(signal_actions.keys()):
        kinds = {item[0] for item in signal_actions[key]}
        if kinds == {"ENDORSE", "OBJECT"}:
            signal_conflicts.append({
                "target_action_ref": key[0],
                "actor": key[1],
                "signal_action_refs": sorted(item[1] for item in signal_actions[key]),
            })
    active_signal_conflicts = [
        item for item in signal_conflicts
        if item["target_action_ref"] in active_refs
    ]

    state = None
    reason_code = None
    resolved_action_ref = None
    resolved_action_id = None
    resolved_declared_value = None
    participation_result = None
    active_endorsers = []
    active_objectors = []

    if cycle_refs:
        state = "ABSTAIN"
        reason_code = "DEPENDENCY_CYCLE"
    elif active_signal_conflicts:
        state = "ABSTAIN"
        reason_code = "PARTICIPANT_SIGNAL_CONFLICT"
    elif len(active_refs) > 1:
        state = "ABSTAIN"
        reason_code = "MULTIPLE_ACTIVE_PROPOSALS"
    elif missing:
        state = "INCOMPLETE"
        reason_code = "MISSING_DEPENDENCY"
    elif len(active_refs) == 0:
        state = "INCOMPLETE"
        reason_code = "NO_ACTIVE_PROPOSAL"
    else:
        active_ref = active_refs[0]
        active_endorsers = sorted(endorsements_by_target.get(active_ref, set()))
        active_objectors = sorted(objections_by_target.get(active_ref, set()))
        participation_result = evaluate_participation(context["participation"], active_endorsers)
        if active_objectors:
            state = "ABSTAIN"
            reason_code = "ACTIVE_PROPOSAL_OBJECTED"
        elif participation_result["satisfied"]:
            state = "RESOLVED"
            reason_code = "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED"
            resolved_action_ref = active_ref
            resolved_action_id = action_id_by_ref[active_ref]
            resolved_declared_value = deepcopy(action_by_ref[active_ref]["declared_value"])
        else:
            state = "INCOMPLETE"
            reason_code = "PARTICIPATION_INCOMPLETE"

    action_summaries = []
    for ref in sorted(action_by_ref.keys()):
        action = action_by_ref[ref]
        action_summaries.append({
            "action_ref": ref,
            "action_id": action_id_by_ref[ref],
            "actor": action["actor"],
            "kind": action["kind"],
            "targets": list(action["targets"]),
            "dependency_ready": bool(ready_map.get(ref, False)),
            "active_proposal": ref in active_refs,
            "superseded": ref in superseded_refs,
            "withdrawn": ref in withdrawn_refs,
            "declared_value": deepcopy(action["declared_value"]),
        })

    receipt_without_id = {
        "profile": TOPIC_RECEIPT_PROFILE,
        "ruleset_profile": RULESET_PROFILE,
        "topic_id": topic_id,
        "state": state,
        "reason_code": reason_code,
        "action_ids": sorted(action_id_by_ref[ref] for ref in action_by_ref.keys()),
        "active_action_refs": active_refs,
        "active_action_ids": sorted(action_id_by_ref[ref] for ref in active_refs),
        "superseded_action_refs": sorted(superseded_refs),
        "withdrawn_action_refs": sorted(withdrawn_refs),
        "missing_dependencies": sorted(missing, key=lambda item: (item["action_ref"], item["missing_target_ref"])),
        "cycle_action_refs": sorted(cycle_refs),
        "signal_conflicts": signal_conflicts,
        "active_signal_conflicts": active_signal_conflicts,
        "active_endorsers": active_endorsers,
        "active_objectors": active_objectors,
        "participation": participation_result,
        "resolved_action_ref": resolved_action_ref,
        "resolved_action_id": resolved_action_id,
        "resolved_declared_value": resolved_declared_value,
        "actions": action_summaries,
        "execution_authority": EXECUTION_AUTHORITY,
    }
    receipt = deepcopy(receipt_without_id)
    receipt["topic_receipt_id"] = identity("topic_receipt", TOPIC_RECEIPT_PROFILE, receipt_without_id)
    return receipt


def resolve_topics(evidence, graph, context):
    actions_by_topic = defaultdict(list)
    action_id_by_ref = graph["action_id_by_ref"]
    for entry in evidence["actions"]:
        action = entry["action"]
        actions_by_topic[action["topic_id"]].append(action)

    receipts = []
    for topic_id in sorted(actions_by_topic.keys()):
        receipts.append(make_topic_receipt(
            topic_id,
            actions_by_topic[topic_id],
            action_id_by_ref,
            graph,
            context,
        ))

    counts = Counter(receipt["state"] for receipt in receipts)
    root_basis = {
        "profile": TOPIC_RECEIPT_PROFILE,
        "topic_receipt_ids": sorted(receipt["topic_receipt_id"] for receipt in receipts),
    }
    return {
        "receipts": receipts,
        "state_counts": {
            "RESOLVED": counts.get("RESOLVED", 0),
            "INCOMPLETE": counts.get("INCOMPLETE", 0),
            "ABSTAIN": counts.get("ABSTAIN", 0),
        },
        "topic_receipt_root": identity("topic_receipt_root", TOPIC_RECEIPT_PROFILE, root_basis),
    }


def make_boundary_receipt(boundary, evidence):
    observed_refs = sorted(item["observation_ref"] for item in evidence["observations"])
    expected_refs = sorted(boundary["expected_observation_refs"])
    if boundary["state"] == "OPEN":
        state = "OPEN"
        missing_refs = []
        unexpected_refs = []
    else:
        missing_refs = sorted(set(expected_refs) - set(observed_refs))
        unexpected_refs = sorted(set(observed_refs) - set(expected_refs))
        if not missing_refs and not unexpected_refs:
            state = "SEALED"
        elif missing_refs and not unexpected_refs:
            state = "INCOMPLETE"
        else:
            state = "CONFLICT"

    receipt_without_id = {
        "profile": BOUNDARY_RECEIPT_PROFILE,
        "declared_state": boundary["state"],
        "state": state,
        "observed_observation_refs": observed_refs,
        "expected_observation_refs": expected_refs,
        "missing_observation_refs": missing_refs,
        "unexpected_observation_refs": unexpected_refs,
        "observed_observation_set_id": evidence["observation_set_id"],
    }
    receipt = deepcopy(receipt_without_id)
    receipt["boundary_receipt_id"] = identity("boundary_receipt", BOUNDARY_RECEIPT_PROFILE, receipt_without_id)
    return receipt


def public_topic_summary(receipt):
    return {
        "topic_id": receipt["topic_id"],
        "state": receipt["state"],
        "reason_code": receipt["reason_code"],
        "active_action_ids": list(receipt["active_action_ids"]),
        "resolved_action_id": receipt["resolved_action_id"],
        "active_endorser_count": len(receipt["active_endorsers"]),
        "active_objector_count": len(receipt["active_objectors"]),
        "participation_satisfied": None if receipt["participation"] is None else receipt["participation"]["satisfied"],
        "topic_receipt_id": receipt["topic_receipt_id"],
        "execution_authority": EXECUTION_AUTHORITY,
    }


def build_public_receipt(context_result, evidence, graph, topics, boundary_receipt, conversation_resolution_id):
    topic_summaries = [public_topic_summary(receipt) for receipt in topics["receipts"]]
    receipt_without_id = {
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
        "topic_summaries": topic_summaries,
        "conversation_resolution_id": conversation_resolution_id,
        "execution_authority": EXECUTION_AUTHORITY,
    }
    receipt = deepcopy(receipt_without_id)
    receipt["public_receipt_id"] = identity("public_receipt", PUBLIC_RECEIPT_PROFILE, receipt_without_id)
    return receipt


def bundle_without_self_verification(bundle):
    result = deepcopy(bundle)
    result.pop("self_verification", None)
    return result


def resolve_conversation_bundle(context, observations, boundary, run_self_verify=True):
    intake_errors = []
    if not isinstance(context, dict):
        intake_errors.append("context: must be an object")
    if not isinstance(observations, list):
        intake_errors.append("observations: must be an array")
    if not isinstance(boundary, dict):
        intake_errors.append("boundary: must be an object")
    if intake_errors:
        return make_refusal(intake_errors)

    context_result = prepare_context(context)
    boundary_errors = validate_boundary(boundary)
    if context_result["validation_state"] == "REFUSED" or boundary_errors:
        errors = []
        if context_result["validation_state"] == "REFUSED":
            errors.extend(context_result["errors"])
        errors.extend(boundary_errors)
        return make_refusal(errors)

    canonical_boundary_record = canonical_boundary(boundary)
    evidence = prepare_observations(observations, context_result["context"])
    if evidence["validation_state"] == "REFUSED":
        return make_refusal(evidence["errors"])

    graph = build_graph(evidence, context_result["context"])
    if graph["validation_state"] == "REFUSED":
        return make_refusal(graph["errors"])

    topics = resolve_topics(evidence, graph, context_result["context"])
    boundary_receipt = make_boundary_receipt(canonical_boundary_record, evidence)

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
    conversation_resolution_id = identity("conversation_resolution", PRIVATE_BUNDLE_PROFILE, resolution_basis)
    public_receipt = build_public_receipt(
        context_result,
        evidence,
        graph,
        topics,
        boundary_receipt,
        conversation_resolution_id,
    )
    bundle_basis = {
        "profile": PRIVATE_BUNDLE_PROFILE,
        "conversation_resolution_id": conversation_resolution_id,
        "observation_set_id": evidence["observation_set_id"],
        "public_receipt_id": public_receipt["public_receipt_id"],
    }
    private_bundle_id = identity("private_bundle", PRIVATE_BUNDLE_PROFILE, bundle_basis)

    public_graph = {
        "profile": graph["profile"],
        "nodes": deepcopy(graph["nodes"]),
        "edges": deepcopy(graph["edges"]),
        "missing_dependencies": deepcopy(graph["missing_dependencies"]),
        "cycle_action_refs": deepcopy(graph["cycle_action_refs"]),
        "graph_root": graph["graph_root"],
    }

    bundle = {
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
    if run_self_verify:
        bundle["self_verification"] = verify_bundle(bundle)
    return bundle


def verify_bundle(bundle):
    if not isinstance(bundle, dict):
        return {"profile": VERIFICATION_PROFILE, "valid": False, "errors": ["bundle must be an object"]}
    if bundle.get("result") != "ACCEPTED":
        return {"profile": VERIFICATION_PROFILE, "valid": False, "errors": ["only accepted bundles are verifiable"]}
    inputs = bundle.get("inputs")
    if not isinstance(inputs, dict):
        return {"profile": VERIFICATION_PROFILE, "valid": False, "errors": ["missing inputs"]}

    expected = resolve_conversation_bundle(
        inputs.get("context"),
        inputs.get("observations"),
        inputs.get("boundary"),
        run_self_verify=False,
    )
    errors = []
    if expected.get("result") != "ACCEPTED":
        errors.append("embedded inputs do not reconstruct an accepted bundle")
    elif canonical_json(bundle_without_self_verification(bundle)) != canonical_json(expected):
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
        if not errors:
            errors.append("bundle content mismatch")

    return {
        "profile": VERIFICATION_PROFILE,
        "valid": not errors,
        "errors": errors,
        "expected_conversation_resolution_id": expected.get("conversation_resolution_id"),
        "expected_private_bundle_id": expected.get("private_bundle_id"),
        "expected_public_receipt_id": expected.get("public_receipt", {}).get("public_receipt_id"),
    }


def merge_observation_sets(*observation_sets):
    merged = {}
    observation_refs = {}
    action_refs = {}
    for observation_set in observation_sets:
        if not isinstance(observation_set, list):
            raise ValueError("observation sets must be arrays")
        for observation in observation_set:
            errors = validate_observation(observation)
            if errors:
                raise ValueError("cannot merge invalid observation: " + "; ".join(errors))
            canonical = canonical_observation(observation)
            oid = observation_id(canonical)
            observation_ref = canonical["observation_ref"]
            aid = action_id(canonical["action"])
            action_ref = canonical["action"]["action_ref"]
            if observation_ref in observation_refs and observation_refs[observation_ref] != oid:
                raise ValueError("observation_ref content conflict: " + observation_ref)
            if action_ref in action_refs and action_refs[action_ref] != aid:
                raise ValueError("action_ref content conflict: " + action_ref)
            observation_refs[observation_ref] = oid
            action_refs[action_ref] = aid
            merged[oid] = canonical
    return [deepcopy(merged[oid]) for oid in sorted(merged.keys())]


def topic_state_map(bundle):
    return {receipt["topic_id"]: receipt["state"] for receipt in bundle.get("topics", {}).get("receipts", [])}


def topic_reason_map(bundle):
    return {receipt["topic_id"]: receipt["reason_code"] for receipt in bundle.get("topics", {}).get("receipts", [])}


def topic_value_map(bundle):
    return {receipt["topic_id"]: receipt["resolved_declared_value"] for receipt in bundle.get("topics", {}).get("receipts", [])}


def scenario_corrected_instruction():
    participation = make_participation(
        "ALL_DECLARED_PARTICIPANTS",
        participants=["alice", "bob"],
        threshold=2,
    )
    context = make_context("conversation-corrected-instruction", "active-instruction", participation)
    actions = [
        make_action("a-open", context["conversation_id"], "meeting-time", "alice", "PROPOSE", "4 PM"),
        make_action("a-amend", context["conversation_id"], "meeting-time", "alice", "AMEND", "5 PM", ["a-open"]),
        make_action("a-endorse-alice", context["conversation_id"], "meeting-time", "alice", "ENDORSE", None, ["a-amend"]),
        make_action("a-endorse-bob", context["conversation_id"], "meeting-time", "bob", "ENDORSE", None, ["a-amend"]),
    ]
    observations = [
        make_observation("obs-open", "node-a", actions[0], "Meet at 4 PM."),
        make_observation("obs-amend", "node-b", actions[1], "Correction: meet at 5 PM."),
        make_observation("obs-endorse-alice", "node-a", actions[2], "Alice confirms the correction."),
        make_observation("obs-endorse-bob", "node-b", actions[3], "Bob confirms the correction."),
    ]
    boundary = make_boundary("SEALED", [item["observation_ref"] for item in observations])
    return make_input(context, observations, boundary)


def scenario_missing_endorsement():
    data = scenario_corrected_instruction()
    data["context"]["conversation_id"] = "conversation-missing-endorsement"
    for observation in data["observations"]:
        observation["action"]["conversation_id"] = data["context"]["conversation_id"]
    data["observations"] = [item for item in data["observations"] if item["action"]["action_ref"] != "a-endorse-bob"]
    data["boundary"] = make_boundary("SEALED", [item["observation_ref"] for item in data["observations"]])
    return data


def scenario_competing_proposals():
    participation = make_participation(
        "SINGLE_DECLARED_ENDORSER",
        participants=["alice", "bob"],
        threshold=1,
    )
    context = make_context("conversation-competing-proposals", "active-instruction", participation)
    actions = [
        make_action("proposal-a", context["conversation_id"], "location", "alice", "PROPOSE", "Room A"),
        make_action("proposal-b", context["conversation_id"], "location", "bob", "PROPOSE", "Room B"),
        make_action("endorse-a", context["conversation_id"], "location", "alice", "ENDORSE", None, ["proposal-a"]),
    ]
    observations = [
        make_observation("obs-proposal-a", "node-a", actions[0], "Use Room A."),
        make_observation("obs-proposal-b", "node-b", actions[1], "Use Room B."),
        make_observation("obs-endorse-a", "node-a", actions[2], "Alice endorses Room A."),
    ]
    return make_input(context, observations, make_boundary("OPEN"))


def scenario_withdrawal_repair():
    participation = make_participation(
        "ALL_DECLARED_PARTICIPANTS",
        participants=["alice", "bob"],
        threshold=2,
    )
    context = make_context("conversation-withdrawal-repair", "active-instruction", participation)
    actions = [
        make_action("proposal-a", context["conversation_id"], "location", "alice", "PROPOSE", "Room A"),
        make_action("proposal-b", context["conversation_id"], "location", "bob", "PROPOSE", "Room B"),
        make_action("withdraw-b", context["conversation_id"], "location", "bob", "WITHDRAW", None, ["proposal-b"]),
        make_action("endorse-a-alice", context["conversation_id"], "location", "alice", "ENDORSE", None, ["proposal-a"]),
        make_action("endorse-a-bob", context["conversation_id"], "location", "bob", "ENDORSE", None, ["proposal-a"]),
    ]
    observations = [
        make_observation("obs-proposal-a", "node-a", actions[0], "Use Room A."),
        make_observation("obs-proposal-b", "node-b", actions[1], "Use Room B."),
        make_observation("obs-withdraw-b", "node-b", actions[2], "Room B proposal withdrawn."),
        make_observation("obs-endorse-a-alice", "node-a", actions[3], "Alice endorses Room A."),
        make_observation("obs-endorse-a-bob", "node-b", actions[4], "Bob endorses Room A."),
    ]
    return make_input(context, observations, make_boundary("SEALED", [item["observation_ref"] for item in observations]))


def scenario_observation_multiplicity():
    data = scenario_corrected_instruction()
    data["context"]["conversation_id"] = "conversation-observation-multiplicity"
    for observation in data["observations"]:
        observation["action"]["conversation_id"] = data["context"]["conversation_id"]
    relay = deepcopy(data["observations"][1])
    relay["observation_ref"] = "obs-amend-relay"
    relay["source"] = "node-c"
    relay["presentation"] = "Relayed correction record."
    data["observations"].append(relay)
    exact_duplicate = deepcopy(data["observations"][0])
    data["observations"].append(exact_duplicate)
    data["boundary"] = make_boundary("SEALED", sorted(set(item["observation_ref"] for item in data["observations"])))
    return data


def scenario_missing_dependency():
    participation = make_participation("NO_ENDORSEMENT_REQUIRED", threshold=0)
    context = make_context("conversation-missing-dependency", "active-instruction", participation)
    action = make_action("amend-missing", context["conversation_id"], "instruction", "alice", "AMEND", "New value", ["unknown-proposal"])
    observations = [make_observation("obs-amend-missing", "node-a", action, "Amend an unavailable proposal.")]
    return make_input(context, observations, make_boundary("OPEN"))


def scenario_cycle():
    participation = make_participation("NO_ENDORSEMENT_REQUIRED", threshold=0)
    context = make_context("conversation-cycle", "active-instruction", participation)
    action_a = make_action("amend-a", context["conversation_id"], "instruction", "alice", "AMEND", "A", ["amend-b"])
    action_b = make_action("amend-b", context["conversation_id"], "instruction", "bob", "AMEND", "B", ["amend-a"])
    observations = [
        make_observation("obs-amend-a", "node-a", action_a, "Amendment A."),
        make_observation("obs-amend-b", "node-b", action_b, "Amendment B."),
    ]
    return make_input(context, observations, make_boundary("OPEN"))


def scenario_objected():
    participation = make_participation(
        "ALL_DECLARED_PARTICIPANTS",
        participants=["alice", "bob"],
        threshold=2,
    )
    context = make_context("conversation-objected", "active-instruction", participation)
    actions = [
        make_action("proposal", context["conversation_id"], "instruction", "alice", "PROPOSE", "Proceed"),
        make_action("endorse-alice", context["conversation_id"], "instruction", "alice", "ENDORSE", None, ["proposal"]),
        make_action("object-bob", context["conversation_id"], "instruction", "bob", "OBJECT", None, ["proposal"]),
    ]
    observations = [
        make_observation("obs-proposal", "node-a", actions[0], "Proceed."),
        make_observation("obs-endorse-alice", "node-a", actions[1], "Alice endorses."),
        make_observation("obs-object-bob", "node-b", actions[2], "Bob objects."),
    ]
    return make_input(context, observations, make_boundary("OPEN"))


def scenario_signal_conflict():
    participation = make_participation(
        "SINGLE_DECLARED_ENDORSER",
        participants=["alice"],
        threshold=1,
    )
    context = make_context("conversation-signal-conflict", "active-instruction", participation)
    actions = [
        make_action("proposal", context["conversation_id"], "instruction", "alice", "PROPOSE", "Proceed"),
        make_action("endorse", context["conversation_id"], "instruction", "alice", "ENDORSE", None, ["proposal"]),
        make_action("object", context["conversation_id"], "instruction", "alice", "OBJECT", None, ["proposal"]),
    ]
    observations = [
        make_observation("obs-proposal", "node-a", actions[0], "Proceed."),
        make_observation("obs-endorse", "node-a", actions[1], "Alice endorses."),
        make_observation("obs-object", "node-a", actions[2], "Alice objects."),
    ]
    return make_input(context, observations, make_boundary("OPEN"))


def scenario_inactive_signal_conflict():
    participation = make_participation(
        "ALL_DECLARED_PARTICIPANTS",
        participants=["alice", "bob"],
        threshold=2,
    )
    context = make_context("conversation-inactive-signal-conflict", "active-instruction", participation)
    actions = [
        make_action("active", context["conversation_id"], "topic", "alice", "PROPOSE", "A"),
        make_action("inactive", context["conversation_id"], "topic", "bob", "PROPOSE", "B"),
        make_action("withdraw-inactive", context["conversation_id"], "topic", "bob", "WITHDRAW", None, ["inactive"]),
        make_action("endorse-active-a", context["conversation_id"], "topic", "alice", "ENDORSE", None, ["active"]),
        make_action("endorse-active-b", context["conversation_id"], "topic", "bob", "ENDORSE", None, ["active"]),
        make_action("endorse-inactive", context["conversation_id"], "topic", "bob", "ENDORSE", None, ["inactive"]),
        make_action("object-inactive", context["conversation_id"], "topic", "bob", "OBJECT", None, ["inactive"]),
    ]
    observations = [
        make_observation("inactive-conflict-" + str(index), "node", action, "")
        for index, action in enumerate(actions)
    ]
    return make_input(context, observations, make_boundary("OPEN"))


def scenario_exact_participant_set():
    participation = make_participation(
        "EXACT_DECLARED_PARTICIPANT_SET",
        participants=["alice", "bob", "carol"],
        required_endorsers=["alice", "carol"],
        threshold=2,
    )
    context = make_context("conversation-exact-participant-set", "active-instruction", participation)
    actions = [
        make_action("proposal", context["conversation_id"], "instruction", "bob", "PROPOSE", {"mode": "bounded", "value": 7}),
        make_action("endorse-alice", context["conversation_id"], "instruction", "alice", "ENDORSE", None, ["proposal"]),
        make_action("endorse-carol", context["conversation_id"], "instruction", "carol", "ENDORSE", None, ["proposal"]),
    ]
    observations = [
        make_observation("obs-proposal", "node-b", actions[0], "Use bounded mode with value 7."),
        make_observation("obs-endorse-alice", "node-a", actions[1], "Alice endorses."),
        make_observation("obs-endorse-carol", "node-c", actions[2], "Carol endorses."),
    ]
    return make_input(context, observations, make_boundary("SEALED", [item["observation_ref"] for item in observations]))


def scenario_multi_topic():
    participation = make_participation(
        "SINGLE_DECLARED_ENDORSER",
        participants=["alice", "bob"],
        threshold=1,
    )
    context = make_context("conversation-multi-topic", "active-instructions", participation)
    actions = [
        make_action("time-proposal", context["conversation_id"], "time", "alice", "PROPOSE", "5 PM"),
        make_action("time-endorse", context["conversation_id"], "time", "bob", "ENDORSE", None, ["time-proposal"]),
        make_action("room-a", context["conversation_id"], "room", "alice", "PROPOSE", "Room A"),
        make_action("room-b", context["conversation_id"], "room", "bob", "PROPOSE", "Room B"),
    ]
    observations = [
        make_observation("obs-time-proposal", "node-a", actions[0], "Meet at 5 PM."),
        make_observation("obs-time-endorse", "node-b", actions[1], "Bob endorses 5 PM."),
        make_observation("obs-room-a", "node-a", actions[2], "Use Room A."),
        make_observation("obs-room-b", "node-b", actions[3], "Use Room B."),
    ]
    return make_input(context, observations, make_boundary("OPEN"))


def scenario_identifier_conflict():
    participation = make_participation("NO_ENDORSEMENT_REQUIRED", threshold=0)
    context = make_context("conversation-identifier-conflict", "active-instruction", participation)
    action_a = make_action("proposal", context["conversation_id"], "instruction", "alice", "PROPOSE", "A")
    action_b = make_action("proposal", context["conversation_id"], "instruction", "alice", "PROPOSE", "B")
    observations = [
        make_observation("obs-a", "node-a", action_a, "A"),
        make_observation("obs-b", "node-b", action_b, "B"),
    ]
    return make_input(context, observations, make_boundary("OPEN"))


def get_scenario(name):
    scenarios = {
        "corrected-instruction": scenario_corrected_instruction,
        "missing-endorsement": scenario_missing_endorsement,
        "competing-proposals": scenario_competing_proposals,
        "withdrawal-repair": scenario_withdrawal_repair,
        "observation-multiplicity": scenario_observation_multiplicity,
        "missing-dependency": scenario_missing_dependency,
        "cycle": scenario_cycle,
        "objected": scenario_objected,
        "signal-conflict": scenario_signal_conflict,
        "inactive-signal-conflict": scenario_inactive_signal_conflict,
        "exact-participant-set": scenario_exact_participant_set,
        "multi-topic": scenario_multi_topic,
        "identifier-conflict": scenario_identifier_conflict,
    }
    if name not in scenarios:
        raise ValueError("unknown scenario: " + name)
    return scenarios[name]()


def scenario_names():
    return [
        "corrected-instruction",
        "missing-endorsement",
        "competing-proposals",
        "withdrawal-repair",
        "observation-multiplicity",
        "missing-dependency",
        "cycle",
        "objected",
        "signal-conflict",
        "inactive-signal-conflict",
        "exact-participant-set",
        "multi-topic",
        "identifier-conflict",
    ]


class AuditRunner:
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

    def raises(self, group, label, function, expected_exception=Exception):
        try:
            function()
        except expected_exception:
            self.check(group, label, True)
        except Exception:
            self.check(group, label, False)
        else:
            self.check(group, label, False)

    def summary(self):
        result = {}
        for group in sorted(self.groups.keys()):
            item = self.groups[group]
            result[group] = {
                "pass": item["pass"],
                "fail": item["fail"],
                "total": item["pass"] + item["fail"],
                "failures": list(item["failures"]),
            }
        return result


def audit_validation(audit):
    valid = scenario_corrected_instruction()
    audit.equal("VALIDATION", "valid context", validate_context(valid["context"]), [])
    audit.equal("VALIDATION", "valid boundary", validate_boundary(valid["boundary"]), [])
    for index, observation in enumerate(valid["observations"]):
        audit.equal("VALIDATION", "valid observation " + str(index), validate_observation(observation), [])

    bad_context = deepcopy(valid["context"])
    bad_context["unsupported"] = True
    audit.check("VALIDATION", "context unknown field", bool(validate_context(bad_context)))
    bad_context = deepcopy(valid["context"])
    bad_context["execution_authority"] = "EXECUTE"
    audit.check("VALIDATION", "execution authority bounded", bool(validate_context(bad_context)))
    bad_context = deepcopy(valid["context"])
    bad_context["conversation_id"] = " bad"
    audit.check("VALIDATION", "identifier whitespace", bool(validate_context(bad_context)))
    bad_context = deepcopy(valid["context"])
    bad_context["conversation_id"] = "e\u0301"
    audit.equal("VALIDATION", "exact decomposed identifier accepted", validate_context(bad_context), [])
    bad_context = deepcopy(valid["context"])
    bad_context["conversation_id"] = "bad\u200bidentifier"
    audit.check("VALIDATION", "frozen format identifier refused", bool(validate_context(bad_context)))
    bad_context = deepcopy(valid["context"])
    bad_context["participation"]["participants"].append("alice")
    audit.check("VALIDATION", "duplicate participant", bool(validate_context(bad_context)))
    bad_context = deepcopy(valid["context"])
    bad_context["participation"]["threshold"] = True
    audit.check("VALIDATION", "boolean threshold", bool(validate_context(bad_context)))

    action = deepcopy(valid["observations"][0]["action"])
    for kind in ACTION_KINDS:
        sample = deepcopy(action)
        sample["kind"] = kind
        if kind == "PROPOSE":
            sample["targets"] = []
            sample["declared_value"] = "x"
        elif kind == "AMEND":
            sample["targets"] = ["target"]
            sample["declared_value"] = "x"
        else:
            sample["targets"] = ["target"]
            sample["declared_value"] = None
        audit.equal("VALIDATION", "supported action kind " + kind, validate_action(sample), [])

    bad = deepcopy(action)
    bad["kind"] = "UNKNOWN"
    audit.check("VALIDATION", "unknown action kind", bool(validate_action(bad)))
    bad = deepcopy(action)
    bad["targets"] = ["x"]
    audit.check("VALIDATION", "propose target refused", bool(validate_action(bad)))
    bad = deepcopy(action)
    bad["declared_value"] = None
    audit.check("VALIDATION", "proposal null refused", bool(validate_action(bad)))
    bad = deepcopy(action)
    bad["declared_value"] = 2 ** 54
    audit.check("VALIDATION", "large integer refused", bool(validate_action(bad)))
    bad = deepcopy(action)
    bad["declared_value"] = 1.25
    audit.check("VALIDATION", "float refused", bool(validate_action(bad)))
    bad_observation = deepcopy(valid["observations"][0])
    bad_observation["presentation"] = "a\rb"
    audit.check("VALIDATION", "carriage return refused", bool(validate_observation(bad_observation)))
    bad_boundary = make_boundary("OPEN", ["unexpected"])
    audit.check("VALIDATION", "open expected list refused", bool(validate_boundary(bad_boundary)))



def audit_text_profile(audit):
    audit.equal("TEXT_PROFILE", "declared profile", TEXT_PROFILE, "ORL-CHAT-UNICODE-SCALAR-EXACT-2-D01")
    audit.equal("TEXT_PROFILE", "decomposed identifier accepted", validate_identifier("cafe\u0301", "identifier"), [])
    audit.equal("TEXT_PROFILE", "composed identifier accepted", validate_identifier("café", "identifier"), [])
    audit.check("TEXT_PROFILE", "canonical equivalents remain distinct", canonical_json("cafe\u0301") != canonical_json("café"))
    audit.check("TEXT_PROFILE", "frozen format refused", bool(validate_identifier("a\u200bb", "identifier")))
    audit.check("TEXT_PROFILE", "surrogate refused", bool(validate_identifier("a\ud800b", "identifier")))
    audit.check("TEXT_PROFILE", "frozen boundary whitespace refused", bool(validate_identifier("\u3000identifier", "identifier")))
    audit.equal("TEXT_PROFILE", "multiline text accepted", validate_presentation("line one\nline two\tvalue", "presentation"), [])


def audit_strict_json(audit):
    audit.equal("STRICT_JSON", "valid strict JSON", strict_json_loads('{"a":1}'), {"a": 1})
    audit.equal("STRICT_JSON", "maximum positive integer", strict_json_loads('{"a":9007199254740991}'), {"a": 9007199254740991})
    audit.equal("STRICT_JSON", "maximum negative integer", strict_json_loads('{"a":-9007199254740991}'), {"a": -9007199254740991})
    audit.raises("STRICT_JSON", "integer above exact range", lambda: strict_json_loads('{"a":9007199254740992}'), StrictJSONError)
    audit.raises("STRICT_JSON", "integer below exact range", lambda: strict_json_loads('{"a":-9007199254740992}'), StrictJSONError)
    audit.raises("STRICT_JSON", "extreme integer token", lambda: strict_json_loads('{"a":' + '9' * 1024 + '}'), StrictJSONError)
    audit.raises("STRICT_JSON", "duplicate key", lambda: strict_json_loads('{"a":1,"a":2}'), DuplicateKeyError)
    audit.raises("STRICT_JSON", "float", lambda: strict_json_loads('{"a":1.2}'), StrictJSONError)
    audit.raises("STRICT_JSON", "NaN", lambda: strict_json_loads('{"a":NaN}'), StrictJSONError)
    audit.raises("STRICT_JSON", "Infinity", lambda: strict_json_loads('{"a":Infinity}'), StrictJSONError)
    audit.raises("STRICT_JSON", "trailing comma", lambda: strict_json_loads('{"a":1,}'), StrictJSONError)


def audit_identity(audit):
    data = scenario_corrected_instruction()
    action = data["observations"][0]["action"]
    same = deepcopy(action)
    audit.equal("IDENTITY", "same action identity", action_id(action), action_id(same))
    changed = deepcopy(action)
    changed["declared_value"] = "5 PM"
    audit.check("IDENTITY", "value changes action identity", action_id(action) != action_id(changed))
    observation = data["observations"][0]
    changed_presentation = deepcopy(observation)
    changed_presentation["presentation"] = "Different presentation"
    audit.equal("IDENTITY", "presentation does not change action identity", action_id(observation["action"]), action_id(changed_presentation["action"]))
    audit.check("IDENTITY", "presentation changes observation identity", observation_id(observation) != observation_id(changed_presentation))
    changed_source = deepcopy(observation)
    changed_source["source"] = "node-z"
    audit.check("IDENTITY", "source changes observation identity", observation_id(observation) != observation_id(changed_source))
    canonical_a = {"b": 2, "a": 1}
    canonical_b = {"a": 1, "b": 2}
    audit.equal("IDENTITY", "canonical key order", canonical_json(canonical_a), canonical_json(canonical_b))


def audit_reference_scenarios(audit):
    expectations = {
        "corrected-instruction": ("ACCEPTED", {"meeting-time": "RESOLVED"}, {"meeting-time": "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED"}),
        "missing-endorsement": ("ACCEPTED", {"meeting-time": "INCOMPLETE"}, {"meeting-time": "PARTICIPATION_INCOMPLETE"}),
        "competing-proposals": ("ACCEPTED", {"location": "ABSTAIN"}, {"location": "MULTIPLE_ACTIVE_PROPOSALS"}),
        "withdrawal-repair": ("ACCEPTED", {"location": "RESOLVED"}, {"location": "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED"}),
        "observation-multiplicity": ("ACCEPTED", {"meeting-time": "RESOLVED"}, {"meeting-time": "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED"}),
        "missing-dependency": ("ACCEPTED", {"instruction": "INCOMPLETE"}, {"instruction": "MISSING_DEPENDENCY"}),
        "cycle": ("ACCEPTED", {"instruction": "ABSTAIN"}, {"instruction": "DEPENDENCY_CYCLE"}),
        "objected": ("ACCEPTED", {"instruction": "ABSTAIN"}, {"instruction": "ACTIVE_PROPOSAL_OBJECTED"}),
        "signal-conflict": ("ACCEPTED", {"instruction": "ABSTAIN"}, {"instruction": "PARTICIPANT_SIGNAL_CONFLICT"}),
        "inactive-signal-conflict": ("ACCEPTED", {"topic": "RESOLVED"}, {"topic": "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED"}),
        "exact-participant-set": ("ACCEPTED", {"instruction": "RESOLVED"}, {"instruction": "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED"}),
        "multi-topic": ("ACCEPTED", {"room": "ABSTAIN", "time": "RESOLVED"}, {"room": "MULTIPLE_ACTIVE_PROPOSALS", "time": "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED"}),
        "identifier-conflict": ("REFUSED", {}, {}),
    }
    for name in scenario_names():
        data = get_scenario(name)
        bundle = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"])
        expected_result, expected_states, expected_reasons = expectations[name]
        audit.equal("REFERENCE", name + " result", bundle["result"], expected_result)
        if expected_result == "ACCEPTED":
            audit.equal("REFERENCE", name + " states", topic_state_map(bundle), expected_states)
            audit.equal("REFERENCE", name + " reasons", topic_reason_map(bundle), expected_reasons)
            audit.check("REFERENCE", name + " self verification", bundle["self_verification"]["valid"])
            audit.equal("REFERENCE", name + " execution authority", bundle["execution_authority"], "NONE")
        else:
            audit.check("REFERENCE", name + " refusal id", bundle.get("refusal_id", "").startswith("refusal_"))

    corrected = resolve_conversation_bundle(**get_scenario("corrected-instruction"))
    audit.equal("REFERENCE", "corrected value", topic_value_map(corrected)["meeting-time"], "5 PM")
    multiplicity = resolve_conversation_bundle(**get_scenario("observation-multiplicity"))
    audit.equal("REFERENCE", "one exact observation duplicate", multiplicity["evidence"]["exact_observation_duplicate_count"], 1)
    audit.equal("REFERENCE", "relay observation multiplicity", multiplicity["evidence"]["observation_multiplicity_count"], 1)
    audit.equal("REFERENCE", "sealed boundary", corrected["boundary"]["state"], "SEALED")


def audit_permutations(audit):
    names = [
        "corrected-instruction",
        "missing-endorsement",
        "competing-proposals",
        "withdrawal-repair",
        "missing-dependency",
        "cycle",
        "objected",
        "signal-conflict",
        "inactive-signal-conflict",
        "exact-participant-set",
        "multi-topic",
    ]
    for name in names:
        data = get_scenario(name)
        baseline = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"], run_self_verify=False)
        baseline_resolution = baseline["conversation_resolution_id"]
        baseline_public = baseline["public_receipt"]["public_receipt_id"]
        baseline_states = topic_state_map(baseline)
        observations = data["observations"]
        permutation_limit = 720
        for index, permutation in enumerate(itertools.permutations(observations)):
            if index >= permutation_limit:
                break
            result = resolve_conversation_bundle(data["context"], list(permutation), data["boundary"], run_self_verify=False)
            audit.equal("PERMUTATION", name + " resolution " + str(index), result["conversation_resolution_id"], baseline_resolution)
            audit.equal("PERMUTATION", name + " public receipt " + str(index), result["public_receipt"]["public_receipt_id"], baseline_public)
            audit.equal("PERMUTATION", name + " states " + str(index), topic_state_map(result), baseline_states)


def audit_merge_algebra(audit):
    data = scenario_corrected_instruction()
    observations = data["observations"]
    sets = [observations[:1], observations[1:2], observations[2:]]
    a, b, c = sets
    audit.equal("MERGE", "commutative", merge_observation_sets(a, b), merge_observation_sets(b, a))
    audit.equal(
        "MERGE",
        "associative",
        merge_observation_sets(merge_observation_sets(a, b), c),
        merge_observation_sets(a, merge_observation_sets(b, c)),
    )
    audit.equal("MERGE", "idempotent", merge_observation_sets(a, a), merge_observation_sets(a))
    merged = merge_observation_sets(a, b, c)
    bundle = resolve_conversation_bundle(data["context"], merged, data["boundary"], run_self_verify=False)
    baseline = resolve_conversation_bundle(data["context"], observations, data["boundary"], run_self_verify=False)
    audit.equal("MERGE", "merged resolution", bundle["conversation_resolution_id"], baseline["conversation_resolution_id"])
    conflict_data = scenario_identifier_conflict()
    audit.raises("MERGE", "identifier conflict merge", lambda: merge_observation_sets(conflict_data["observations"][:1], conflict_data["observations"][1:]), ValueError)


def audit_node_partitions(audit):
    data = scenario_withdrawal_repair()
    observations = data["observations"]
    baseline = resolve_conversation_bundle(data["context"], observations, data["boundary"], run_self_verify=False)
    n = len(observations)
    for mask in range(1 << n):
        left = [observations[index] for index in range(n) if mask & (1 << index)]
        right = [observations[index] for index in range(n) if not mask & (1 << index)]
        merged = merge_observation_sets(left, right)
        result = resolve_conversation_bundle(data["context"], merged, data["boundary"], run_self_verify=False)
        audit.equal("PARTITION", "partition " + str(mask), result["conversation_resolution_id"], baseline["conversation_resolution_id"])


def audit_boundary(audit):
    data = scenario_corrected_instruction()
    open_bundle = resolve_conversation_bundle(data["context"], data["observations"], make_boundary("OPEN"), run_self_verify=False)
    audit.equal("BOUNDARY", "open state", open_bundle["boundary"]["state"], "OPEN")
    exact = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"], run_self_verify=False)
    audit.equal("BOUNDARY", "sealed exact", exact["boundary"]["state"], "SEALED")
    refs = [item["observation_ref"] for item in data["observations"]]
    incomplete = resolve_conversation_bundle(data["context"], data["observations"][:-1], make_boundary("SEALED", refs), run_self_verify=False)
    audit.equal("BOUNDARY", "sealed missing", incomplete["boundary"]["state"], "INCOMPLETE")
    conflict = resolve_conversation_bundle(data["context"], data["observations"], make_boundary("SEALED", refs[:-1]), run_self_verify=False)
    audit.equal("BOUNDARY", "sealed unexpected", conflict["boundary"]["state"], "CONFLICT")
    both = resolve_conversation_bundle(data["context"], data["observations"], make_boundary("SEALED", refs[:-1] + ["obs-unknown"]), run_self_verify=False)
    audit.equal("BOUNDARY", "sealed missing and unexpected", both["boundary"]["state"], "CONFLICT")


def audit_privacy(audit):
    data = scenario_corrected_instruction()
    bundle = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"], run_self_verify=False)
    public_text = canonical_json(bundle["public_receipt"])
    audit.check("PRIVACY", "public receipt omits presentation", "Meet at 4 PM" not in public_text and "Correction" not in public_text)
    audit.check("PRIVACY", "public receipt omits declared value", '"5 PM"' not in public_text)
    audit.check("PRIVACY", "private bundle retains presentation", "Correction: meet at 5 PM." in canonical_json(bundle))
    audit.check("PRIVACY", "public receipt bound", bundle["public_receipt"]["public_receipt_id"].startswith("public_receipt_"))
    audit.equal("PRIVACY", "execution authority public", bundle["public_receipt"]["execution_authority"], "NONE")


def audit_tamper(audit):
    data = scenario_corrected_instruction()
    bundle = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"])
    mutations = []

    tampered = deepcopy(bundle)
    tampered["topics"]["receipts"][0]["state"] = "ABSTAIN"
    mutations.append(("topic state", tampered))
    tampered = deepcopy(bundle)
    tampered["topics"]["receipts"][0]["reason_code"] = "FORGED"
    mutations.append(("reason code", tampered))
    tampered = deepcopy(bundle)
    tampered["graph"]["graph_root"] = "graph_forged"
    mutations.append(("graph root", tampered))
    tampered = deepcopy(bundle)
    tampered["boundary"]["state"] = "OPEN"
    mutations.append(("boundary state", tampered))
    tampered = deepcopy(bundle)
    tampered["public_receipt"]["public_receipt_id"] = "public_receipt_forged"
    mutations.append(("public receipt", tampered))
    tampered = deepcopy(bundle)
    tampered["conversation_resolution_id"] = "conversation_resolution_forged"
    mutations.append(("resolution id", tampered))
    tampered = deepcopy(bundle)
    tampered["private_bundle_id"] = "private_bundle_forged"
    mutations.append(("bundle id", tampered))
    tampered = deepcopy(bundle)
    tampered["inputs"]["observations"][1]["action"]["declared_value"] = "6 PM"
    mutations.append(("embedded input", tampered))

    for label, candidate in mutations:
        audit.check("TAMPER", label, not verify_bundle(candidate)["valid"])


def audit_regressions(audit):
    conflict = scenario_identifier_conflict()
    result = resolve_conversation_bundle(conflict["context"], conflict["observations"], conflict["boundary"], run_self_verify=False)
    audit.equal("REGRESSION", "action ref conflict refused", result["result"], "REFUSED")

    data = scenario_competing_proposals()
    result = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"], run_self_verify=False)
    audit.equal("REGRESSION", "confirmed proposal does not defeat competitor", topic_state_map(result)["location"], "ABSTAIN")

    data = scenario_corrected_instruction()
    duplicate_ref = deepcopy(data["observations"][0])
    duplicate_ref["source"] = "node-z"
    duplicate_ref["presentation"] = "Changed observation with reused ref"
    data["observations"].append(duplicate_ref)
    result = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"], run_self_verify=False)
    audit.equal("REGRESSION", "observation ref conflict refused", result["result"], "REFUSED")

    data = scenario_corrected_instruction()
    bad_target = deepcopy(data["observations"][2])
    bad_target["action"]["targets"] = ["a-endorse-bob"]
    data["observations"][2] = bad_target
    result = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"], run_self_verify=False)
    audit.equal("REGRESSION", "relation target kind refused", result["result"], "REFUSED")

    data = scenario_corrected_instruction()
    cross_topic = deepcopy(data["observations"][2])
    cross_topic["action"]["topic_id"] = "other-topic"
    data["observations"][2] = cross_topic
    result = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"], run_self_verify=False)
    audit.equal("REGRESSION", "cross topic target refused", result["result"], "REFUSED")

    data = scenario_corrected_instruction()
    self_target = deepcopy(data["observations"][1])
    self_target["action"]["targets"] = [self_target["action"]["action_ref"]]
    data["observations"][1] = self_target
    result = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"], run_self_verify=False)
    audit.equal("REGRESSION", "self target refused", result["result"], "REFUSED")

    data = scenario_inactive_signal_conflict()
    result = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"], run_self_verify=False)
    audit.equal("REGRESSION", "inactive signal conflict does not block active proposal", topic_state_map(result)["topic"], "RESOLVED")


def audit_participation_profiles(audit):
    profiles = [
        make_participation("NO_ENDORSEMENT_REQUIRED", threshold=0),
        make_participation("SINGLE_DECLARED_ENDORSER", ["a", "b"], threshold=1),
        make_participation("ALL_DECLARED_PARTICIPANTS", ["a", "b"], threshold=2),
        make_participation("EXACT_DECLARED_PARTICIPANT_SET", ["a", "b", "c"], ["a", "c"], 2),
        make_participation("DECLARED_THRESHOLD", ["a", "b", "c"], threshold=2),
    ]
    for profile in profiles:
        audit.equal("PARTICIPATION", profile["profile"] + " validates", validate_participation(profile), [])

    audit.check("PARTICIPATION", "none satisfied", evaluate_participation(profiles[0], [])["satisfied"])
    audit.check("PARTICIPATION", "single incomplete", not evaluate_participation(profiles[1], [])["satisfied"])
    audit.check("PARTICIPATION", "single satisfied", evaluate_participation(profiles[1], ["a"])["satisfied"])
    audit.check("PARTICIPATION", "all incomplete", not evaluate_participation(profiles[2], ["a"])["satisfied"])
    audit.check("PARTICIPATION", "all satisfied", evaluate_participation(profiles[2], ["a", "b"])["satisfied"])
    audit.check("PARTICIPATION", "exact satisfied", evaluate_participation(profiles[3], ["a", "c"])["satisfied"])
    audit.check("PARTICIPATION", "exact surplus fails", not evaluate_participation(profiles[3], ["a", "b", "c"])["satisfied"])
    audit.check("PARTICIPATION", "threshold incomplete", not evaluate_participation(profiles[4], ["a"])["satisfied"])
    audit.check("PARTICIPATION", "threshold satisfied", evaluate_participation(profiles[4], ["a", "c"])["satisfied"])


def run_audit():
    audit = AuditRunner()
    audit_validation(audit)
    audit_text_profile(audit)
    audit_strict_json(audit)
    audit_identity(audit)
    audit_reference_scenarios(audit)
    audit_permutations(audit)
    audit_merge_algebra(audit)
    audit_node_partitions(audit)
    audit_boundary(audit)
    audit_privacy(audit)
    audit_tamper(audit)
    audit_regressions(audit)
    audit_participation_profiles(audit)
    groups = audit.summary()
    passed = sum(item["pass"] for item in groups.values())
    failed = sum(item["fail"] for item in groups.values())
    return {
        "profile": AUDIT_PROFILE,
        "version": VERSION,
        "pass": passed,
        "fail": failed,
        "total": passed + failed,
        "groups": groups,
    }


def write_examples(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name in scenario_names():
        data = get_scenario(name)
        input_path = directory / ("ORL_Chat_" + name.replace("-", "_") + "_Input_v2_0_0.json")
        write_json_document(input_path, data)
        written.append(str(input_path))
        bundle = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"])
        bundle_path = directory / ("ORL_Chat_" + name.replace("-", "_") + "_Bundle_v2_0_0.json")
        write_json_document(bundle_path, bundle)
        written.append(str(bundle_path))
    return written


def write_corpus(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    entries = []
    for name in scenario_names():
        data = get_scenario(name)
        bundle = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"])
        filename = "ORL_Chat_" + name.replace("-", "_") + "_Bundle_v2_0_0.json"
        path = directory / filename
        write_json_document(path, bundle)
        raw = path.read_bytes()
        entries.append({
            "scenario": name,
            "file": filename,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "result": bundle["result"],
            "conversation_resolution_id": bundle.get("conversation_resolution_id"),
            "private_bundle_id": bundle.get("private_bundle_id"),
            "public_receipt_id": bundle.get("public_receipt", {}).get("public_receipt_id"),
        })
    manifest_without_id = {
        "profile": CORPUS_MANIFEST_PROFILE,
        "version": VERSION,
        "corpus_profile": CORPUS_PROFILE,
        "entries": entries,
    }
    manifest = deepcopy(manifest_without_id)
    manifest["manifest_id"] = identity("corpus_manifest", CORPUS_MANIFEST_PROFILE, manifest_without_id)
    path = directory / "ORL_Chat_Frozen_Corpus_Manifest_v2_0_0.json"
    write_json_document(path, manifest)
    return str(path)


def print_bundle_summary(bundle):
    print("ORL-Chat v" + VERSION)
    print("Deterministic bounded conversation-evidence reconciliation")
    print("")
    print("result: " + bundle.get("result", "UNKNOWN"))
    if bundle.get("result") == "REFUSED":
        for error in bundle.get("errors", []):
            print("error: " + error)
        print("refusal_id: " + bundle.get("refusal_id", ""))
        return
    print("conversation_resolution_id: " + bundle["conversation_resolution_id"])
    print("private_bundle_id: " + bundle["private_bundle_id"])
    print("public_receipt_id: " + bundle["public_receipt"]["public_receipt_id"])
    print("boundary_state: " + bundle["boundary"]["state"])
    print("execution_authority: " + bundle["execution_authority"])
    print("")
    for receipt in bundle["topics"]["receipts"]:
        print(receipt["topic_id"] + ": " + receipt["state"] + " / " + receipt["reason_code"])
        if receipt["state"] == "RESOLVED":
            print("  resolved_action_ref: " + receipt["resolved_action_ref"])
            print("  resolved_declared_value: " + canonical_json(receipt["resolved_declared_value"]))
    print("")
    print("producer_self_verification: " + ("PASS" if bundle.get("self_verification", {}).get("valid") else "FAIL"))


def print_audit(audit):
    for group in sorted(audit["groups"].keys()):
        item = audit["groups"][group]
        print(group + ": " + str(item["pass"]) + "/" + str(item["total"]) + " PASS")
        for failure in item["failures"]:
            print("  FAIL: " + failure)
    print("TOTAL: " + str(audit["pass"]) + "/" + str(audit["total"]) + " PASS")


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="ORL_Chat_Reference_Kernel_v2_0_0.py")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--scenario", choices=scenario_names(), default="corrected-instruction")
    parser.add_argument("--input")
    parser.add_argument("--canonicalize")
    parser.add_argument("--output")
    parser.add_argument("--public-receipt-output")
    parser.add_argument("--write-examples")
    parser.add_argument("--write-corpus")
    parser.add_argument("--strict-canonical-input", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])

    if args.self_test:
        audit = run_audit()
        if args.json:
            print(json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2))
        else:
            print_audit(audit)
        return 0 if audit["fail"] == 0 else 1

    if args.write_examples:
        written = write_examples(args.write_examples)
        for path in written:
            print(path)
        return 0

    if args.write_corpus:
        print(write_corpus(args.write_corpus))
        return 0

    if args.canonicalize:
        if not args.output:
            print("ERROR: --canonicalize requires --output", file=sys.stderr)
            return 2
        try:
            value = read_json_document(args.canonicalize, strict_canonical=False)
            write_json_document(args.output, value)
        except (OSError, StrictJSONError, ValueError) as exc:
            print("ERROR: " + str(exc), file=sys.stderr)
            return 2
        print("ORL-Chat canonicalization")
        print("text_profile: " + TEXT_PROFILE)
        print("output: " + str(args.output))
        print("result: PASS")
        return 0

    try:
        if args.input:
            data = read_json_document(args.input, strict_canonical=args.strict_canonical_input)
            input_errors = exact_fields(data, ["context", "observations", "boundary"], "input")
            if input_errors:
                bundle = make_refusal(input_errors)
            else:
                bundle = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"])
        else:
            data = get_scenario(args.scenario)
            bundle = resolve_conversation_bundle(data["context"], data["observations"], data["boundary"])
    except (OSError, StrictJSONError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2

    if args.output:
        write_json_document(args.output, bundle)
    if args.public_receipt_output and bundle.get("result") == "ACCEPTED":
        write_json_document(args.public_receipt_output, bundle["public_receipt"])

    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print_bundle_summary(bundle)
    return 0 if bundle.get("result") == "ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
