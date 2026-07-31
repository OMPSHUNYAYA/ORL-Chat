(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./ORL_Chat_Browser_Resolver_v2_0_0.js"));
  } else {
    root.ORLChatCapsule = factory(root.ORLChatResolver || root.ORLChat);
  }
}(typeof self !== "undefined" ? self : this, function (Resolver) {
  "use strict";

  if (!Resolver) {
    throw new Error("ORLChatResolver is required");
  }

  const VERSION = "2.0.0";
  const CAPSULE_PROFILE = "ORL-CHAT-CONVERSATION-STATE-CAPSULE-2-C01";
  const COMPARISON_PROFILE = "ORL-CHAT-CAPSULE-COMPARISON-2-C01";
  const VALUE_COMMITMENT_PROFILE = "ORL-CHAT-CAPSULE-VALUE-COMMITMENT-2-C01";
  const EXECUTION_AUTHORITY = "NONE";
  const CAPSULE_FIELDS = [
    "profile", "version", "architecture_profile", "ruleset_profile", "context_id",
    "conversation_id", "purpose_id", "conversation_resolution_id", "source_public_receipt_id",
    "source_private_bundle_id", "boundary_state", "boundary_receipt_id", "action_set_id",
    "observation_set_id", "action_ids", "observation_ids", "graph_root", "relationship_edges",
    "topics", "state_counts", "execution_authority", "capsule_id"
  ].sort();
  const TOPIC_FIELDS = [
    "topic_id", "state", "reason_code", "active_action_ids", "resolved_action_id",
    "resolved_value_commitment", "topic_receipt_id", "participation_satisfied",
    "active_endorser_count", "active_objector_count", "witness_codes"
  ].sort();

  function deepCopy(value) {
    return Resolver.deepCopy(value);
  }

  function identity(prefix, profile, value) {
    return Resolver.identity(prefix, profile, value);
  }

  function keysEqual(object, expected) {
    if (!object || typeof object !== "object" || Array.isArray(object)) return false;
    const actual = Object.keys(object).sort();
    if (actual.length !== expected.length) return false;
    for (let i = 0; i < actual.length; i += 1) if (actual[i] !== expected[i]) return false;
    return true;
  }

  function isIdentity(value, prefix) {
    return typeof value === "string" && new RegExp("^" + prefix + "_[0-9a-f]{64}$").test(value);
  }

  function sortedUnique(values) {
    return Array.from(new Set(values)).sort(Resolver.compareCodePoints);
  }

  function valueCommitment(value) {
    return identity("declared_value", VALUE_COMMITMENT_PROFILE, value);
  }

  function witnessCodes(receipt, boundaryState) {
    const codes = [
      "STATE_" + receipt.state,
      "REASON_" + receipt.reason_code,
      "BOUNDARY_" + boundaryState
    ];
    if (receipt.participation === null) codes.push("PARTICIPATION_NOT_EVALUATED");
    else if (receipt.participation.satisfied) codes.push("PARTICIPATION_SATISFIED");
    else codes.push("PARTICIPATION_INCOMPLETE");
    codes.push(receipt.active_action_ids.length ? "ACTIVE_FRONTIER_PRESENT" : "ACTIVE_FRONTIER_EMPTY");
    if (receipt.missing_dependencies.length) codes.push("MISSING_DEPENDENCY_PRESENT");
    if (receipt.cycle_action_refs.length) codes.push("DEPENDENCY_CYCLE_PRESENT");
    if (receipt.active_signal_conflicts.length) codes.push("ACTIVE_SIGNAL_CONFLICT_PRESENT");
    if (receipt.active_objectors.length) codes.push("ACTIVE_OBJECTION_PRESENT");
    return sortedUnique(codes);
  }

  function validateSourceBundle(bundle) {
    const errors = [];
    if (!bundle || typeof bundle !== "object" || Array.isArray(bundle)) return ["bundle must be an object"];
    if (bundle.result !== "ACCEPTED") errors.push("bundle result must be ACCEPTED");
    if (bundle.execution_authority !== EXECUTION_AUTHORITY) errors.push("bundle execution_authority must be NONE");
    const required = ["architecture_profile", "ruleset_profile", "context", "evidence", "graph", "topics", "boundary", "public_receipt", "conversation_resolution_id", "private_bundle_id"];
    required.forEach(function (field) { if (!(field in bundle)) errors.push("bundle missing field " + field); });
    if (errors.length) return errors;
    if (!isIdentity(bundle.context.context_id, "context")) errors.push("invalid context_id");
    if (!isIdentity(bundle.evidence.action_set_id, "action_set")) errors.push("invalid action_set_id");
    if (!isIdentity(bundle.evidence.observation_set_id, "observation_set")) errors.push("invalid observation_set_id");
    if (!isIdentity(bundle.graph.graph_root, "graph")) errors.push("invalid graph_root");
    if (!isIdentity(bundle.conversation_resolution_id, "conversation_resolution")) errors.push("invalid conversation_resolution_id");
    if (!isIdentity(bundle.private_bundle_id, "private_bundle")) errors.push("invalid private_bundle_id");
    if (!isIdentity(bundle.public_receipt.public_receipt_id, "public_receipt")) errors.push("invalid public_receipt_id");
    if (bundle.public_receipt.conversation_resolution_id !== bundle.conversation_resolution_id) errors.push("public receipt conversation_resolution_id mismatch");
    if (bundle.public_receipt.execution_authority !== EXECUTION_AUTHORITY) errors.push("public receipt execution_authority must be NONE");
    const actions = bundle.evidence.actions.map(function (entry) { return entry.action_id; });
    const observations = bundle.evidence.observations.map(function (entry) { return entry.observation_id; });
    if (actions.length !== new Set(actions).size || actions.some(function (item) { return !isIdentity(item, "action"); })) errors.push("invalid or duplicate action identity");
    if (observations.length !== new Set(observations).size || observations.some(function (item) { return !isIdentity(item, "observation"); })) errors.push("invalid or duplicate observation identity");
    bundle.topics.receipts.forEach(function (receipt) {
      if (!["RESOLVED", "INCOMPLETE", "ABSTAIN"].includes(receipt.state)) errors.push("unsupported topic state");
      if (!isIdentity(receipt.topic_receipt_id, "topic_receipt")) errors.push("invalid topic_receipt_id");
      if (receipt.execution_authority !== EXECUTION_AUTHORITY) errors.push("topic execution_authority must be NONE");
      if (receipt.state === "RESOLVED" && (receipt.resolved_action_id === null || receipt.resolved_declared_value === null)) errors.push("resolved topic lacks resolved action or value");
    });
    return errors;
  }

  function createCapsule(bundle) {
    const errors = validateSourceBundle(bundle);
    if (errors.length) throw new Error("source bundle is not capsule-admissible: " + errors.join("; "));
    const publicReceipt = bundle.public_receipt;
    const topics = bundle.topics.receipts.slice().sort(function (a, b) { return Resolver.compareCodePoints(a.topic_id, b.topic_id); }).map(function (receipt) {
      return {
        topic_id: receipt.topic_id,
        state: receipt.state,
        reason_code: receipt.reason_code,
        active_action_ids: receipt.active_action_ids.slice().sort(Resolver.compareCodePoints),
        resolved_action_id: receipt.resolved_action_id,
        resolved_value_commitment: receipt.state === "RESOLVED" ? valueCommitment(receipt.resolved_declared_value) : null,
        topic_receipt_id: receipt.topic_receipt_id,
        participation_satisfied: receipt.participation === null ? null : Boolean(receipt.participation.satisfied),
        active_endorser_count: receipt.active_endorsers.length,
        active_objector_count: receipt.active_objectors.length,
        witness_codes: witnessCodes(receipt, bundle.boundary.state)
      };
    });
    const edges = bundle.graph.edges.map(function (edge) {
      return { source_action_id: edge.source_action_id, relation: edge.relation, target_action_id: edge.target_action_id };
    }).sort(function (a, b) {
      return Resolver.compareCodePoints(a.source_action_id, b.source_action_id) || Resolver.compareCodePoints(a.relation, b.relation) || Resolver.compareCodePoints(a.target_action_id, b.target_action_id);
    });
    const basis = {
      profile: CAPSULE_PROFILE,
      version: VERSION,
      architecture_profile: bundle.architecture_profile,
      ruleset_profile: bundle.ruleset_profile,
      context_id: bundle.context.context_id,
      conversation_id: publicReceipt.conversation_id,
      purpose_id: publicReceipt.purpose_id,
      conversation_resolution_id: bundle.conversation_resolution_id,
      source_public_receipt_id: publicReceipt.public_receipt_id,
      source_private_bundle_id: bundle.private_bundle_id,
      boundary_state: bundle.boundary.state,
      boundary_receipt_id: bundle.boundary.boundary_receipt_id,
      action_set_id: bundle.evidence.action_set_id,
      observation_set_id: bundle.evidence.observation_set_id,
      action_ids: bundle.evidence.actions.map(function (item) { return item.action_id; }).sort(Resolver.compareCodePoints),
      observation_ids: bundle.evidence.observations.map(function (item) { return item.observation_id; }).sort(Resolver.compareCodePoints),
      graph_root: bundle.graph.graph_root,
      relationship_edges: edges,
      topics: topics,
      state_counts: deepCopy(bundle.topics.state_counts),
      execution_authority: EXECUTION_AUTHORITY
    };
    const capsule = deepCopy(basis);
    capsule.capsule_id = identity("conversation_state_capsule", CAPSULE_PROFILE, basis);
    return capsule;
  }

  function withoutCapsuleId(capsule) {
    const result = deepCopy(capsule);
    delete result.capsule_id;
    return result;
  }

  function verifyCapsule(capsule) {
    const errors = [];
    if (!keysEqual(capsule, CAPSULE_FIELDS)) return { profile: CAPSULE_PROFILE, valid: false, errors: ["capsule field set is invalid"] };
    if (capsule.profile !== CAPSULE_PROFILE) errors.push("unsupported capsule profile");
    if (capsule.version !== VERSION) errors.push("unsupported capsule version");
    if (capsule.execution_authority !== EXECUTION_AUTHORITY) errors.push("execution_authority must be NONE");
    [
      ["context_id", "context"], ["conversation_resolution_id", "conversation_resolution"],
      ["source_public_receipt_id", "public_receipt"], ["source_private_bundle_id", "private_bundle"],
      ["boundary_receipt_id", "boundary_receipt"], ["action_set_id", "action_set"],
      ["observation_set_id", "observation_set"], ["graph_root", "graph"], ["capsule_id", "conversation_state_capsule"]
    ].forEach(function (pair) { if (!isIdentity(capsule[pair[0]], pair[1])) errors.push("invalid " + pair[0]); });
    if (!["OPEN", "SEALED", "INCOMPLETE", "CONFLICT"].includes(capsule.boundary_state)) errors.push("unsupported boundary_state");
    [["action_ids", "action"], ["observation_ids", "observation"]].forEach(function (pair) {
      const values = capsule[pair[0]];
      if (!Array.isArray(values) || JSON.stringify(values) !== JSON.stringify(sortedUnique(values)) || values.some(function (item) { return !isIdentity(item, pair[1]); })) errors.push(pair[0] + " must be a sorted unique identity array");
    });
    if (!Array.isArray(capsule.relationship_edges)) errors.push("relationship_edges must be an array");
    else capsule.relationship_edges.forEach(function (edge) {
      if (!keysEqual(edge, ["relation", "source_action_id", "target_action_id"].sort())) errors.push("relationship edge field set is invalid");
      else {
        if (!["AMEND", "WITHDRAW", "ENDORSE", "OBJECT"].includes(edge.relation)) errors.push("unsupported relationship edge");
        if (!capsule.action_ids.includes(edge.source_action_id) || !capsule.action_ids.includes(edge.target_action_id)) errors.push("relationship edge references an absent action");
      }
    });
    if (!Array.isArray(capsule.topics)) errors.push("topics must be an array");
    else {
      const topicIds = [];
      capsule.topics.forEach(function (topic) {
        if (!keysEqual(topic, TOPIC_FIELDS)) { errors.push("topic field set is invalid"); return; }
        topicIds.push(topic.topic_id);
        if (!["RESOLVED", "INCOMPLETE", "ABSTAIN"].includes(topic.state)) errors.push("unsupported topic state");
        if (JSON.stringify(topic.active_action_ids) !== JSON.stringify(sortedUnique(topic.active_action_ids))) errors.push("active_action_ids must be sorted and unique");
        if (topic.active_action_ids.some(function (item) { return !capsule.action_ids.includes(item); })) errors.push("active action is absent from capsule action set");
        if (topic.state === "RESOLVED") {
          if (!isIdentity(topic.resolved_action_id, "action")) errors.push("resolved topic has invalid resolved_action_id");
          if (!isIdentity(topic.resolved_value_commitment, "declared_value")) errors.push("resolved topic has invalid value commitment");
        } else if (topic.resolved_action_id !== null || topic.resolved_value_commitment !== null) errors.push("unresolved topic must not carry a resolved action or value commitment");
        if (!isIdentity(topic.topic_receipt_id, "topic_receipt")) errors.push("invalid topic_receipt_id");
        if (![true, false, null].includes(topic.participation_satisfied)) errors.push("invalid participation_satisfied value");
        if (!Number.isSafeInteger(topic.active_endorser_count) || topic.active_endorser_count < 0) errors.push("invalid active_endorser_count");
        if (!Number.isSafeInteger(topic.active_objector_count) || topic.active_objector_count < 0) errors.push("invalid active_objector_count");
        if (!Array.isArray(topic.witness_codes) || JSON.stringify(topic.witness_codes) !== JSON.stringify(sortedUnique(topic.witness_codes))) errors.push("witness_codes must be sorted and unique");
      });
      if (JSON.stringify(topicIds) !== JSON.stringify(sortedUnique(topicIds))) errors.push("topics must be sorted and unique by topic_id");
    }
    const counts = { RESOLVED: 0, INCOMPLETE: 0, ABSTAIN: 0 };
    if (Array.isArray(capsule.topics)) capsule.topics.forEach(function (topic) { if (topic && counts.hasOwnProperty(topic.state)) counts[topic.state] += 1; });
    if (Resolver.canonicalJson(capsule.state_counts) !== Resolver.canonicalJson(counts)) errors.push("state_counts mismatch");
    const expected = identity("conversation_state_capsule", CAPSULE_PROFILE, withoutCapsuleId(capsule));
    if (capsule.capsule_id !== expected) errors.push("capsule_id mismatch");
    return { profile: CAPSULE_PROFILE, valid: errors.length === 0, errors: errors, expected_capsule_id: expected };
  }

  function topicMap(capsule) {
    const result = {};
    capsule.topics.forEach(function (item) { result[item.topic_id] = item; });
    return result;
  }

  function resolvedCompatible(left, right) {
    const a = topicMap(left), b = topicMap(right);
    return Object.keys(a).filter(function (key) { return Object.prototype.hasOwnProperty.call(b, key); }).every(function (key) {
      return !(a[key].state === "RESOLVED" && b[key].state === "RESOLVED" && a[key].resolved_value_commitment !== b[key].resolved_value_commitment);
    });
  }

  function materiallyChangesState(left, right) {
    const a = topicMap(left), b = topicMap(right);
    const keys = sortedUnique(Object.keys(a).concat(Object.keys(b)));
    return keys.some(function (key) {
      if (!a[key] || !b[key]) return true;
      const sa = [a[key].state, a[key].reason_code, a[key].active_action_ids, a[key].resolved_value_commitment];
      const sb = [b[key].state, b[key].reason_code, b[key].active_action_ids, b[key].resolved_value_commitment];
      return Resolver.canonicalJson(sa) !== Resolver.canonicalJson(sb);
    });
  }

  function isSuperset(a, b) {
    for (const item of b) if (!a.has(item)) return false;
    return true;
  }

  function compareCapsules(left, right) {
    const lv = verifyCapsule(left), rv = verifyCapsule(right);
    let relation, reasons;
    if (!lv.valid || !rv.valid) {
      relation = "UNSUPPORTED";
      reasons = sortedUnique(lv.errors.concat(rv.errors));
    } else if (left.capsule_id === right.capsule_id) {
      relation = "IDENTICAL";
      reasons = ["CAPSULE_IDENTITIES_MATCH"];
    } else {
      const comparableFields = ["architecture_profile", "ruleset_profile", "context_id", "conversation_id", "purpose_id"];
      const mismatches = comparableFields.filter(function (field) { return left[field] !== right[field]; });
      if (mismatches.length) {
        relation = "INCOMPARABLE";
        reasons = mismatches.map(function (field) { return "COMPARISON_CONTEXT_DIFFERS:" + field; });
      } else if (!resolvedCompatible(left, right)) {
        relation = "DIVERGES";
        reasons = ["RESOLVED_VALUE_COMMITMENT_DIVERGES"];
      } else {
        const la = new Set(left.action_ids), ra = new Set(right.action_ids);
        const lo = new Set(left.observation_ids), ro = new Set(right.observation_ids);
        const actionSuperset = ra.size > la.size && isSuperset(ra, la);
        const observationSuperset = ro.size > lo.size && isSuperset(ro, lo);
        const reverseObservationSuperset = lo.size > ro.size && isSuperset(lo, ro);
        if (actionSuperset && materiallyChangesState(left, right)) {
          relation = "SUPERSEDES";
          reasons = ["RIGHT_ACTION_SET_STRICTLY_EXTENDS_LEFT", "STRUCTURAL_STATE_CHANGED_WITHOUT_RESOLVED_VALUE_DIVERGENCE"];
        } else if (ra.size === la.size && isSuperset(ra, la) && (observationSuperset || reverseObservationSuperset)) {
          relation = "COMPATIBLE";
          reasons = ["SAME_ACTION_SET_WITH_DIFFERENT_OBSERVATION_COVERAGE"];
        } else if (isSuperset(ra, la) || isSuperset(la, ra)) {
          relation = "COMPATIBLE";
          reasons = ["NESTED_ACTION_EVIDENCE_WITHOUT_RESOLVED_VALUE_DIVERGENCE"];
        } else {
          relation = "COMPATIBLE";
          reasons = ["SAME_CONTEXT_WITHOUT_RESOLVED_VALUE_DIVERGENCE"];
        }
      }
    }
    const basis = {
      profile: COMPARISON_PROFILE,
      relation: relation,
      left_capsule_id: left && left.capsule_id ? left.capsule_id : null,
      right_capsule_id: right && right.capsule_id ? right.capsule_id : null,
      left_valid: lv.valid,
      right_valid: rv.valid,
      reasons: reasons
    };
    const result = deepCopy(basis);
    result.comparison_id = identity("capsule_comparison", COMPARISON_PROFILE, basis);
    return result;
  }

  function explainWitnessCode(code) {
    const fixed = {
      BOUNDARY_OPEN: "The observed evidence set is declared open.",
      BOUNDARY_SEALED: "The declared evidence boundary exactly matches the observed references.",
      BOUNDARY_INCOMPLETE: "The requested sealed boundary is missing declared observations.",
      BOUNDARY_CONFLICT: "The requested sealed boundary contains unexpected observations or mixed boundary differences.",
      PARTICIPATION_SATISFIED: "The declared participation profile is satisfied for the active proposal.",
      PARTICIPATION_INCOMPLETE: "The declared participation profile is not yet satisfied.",
      PARTICIPATION_NOT_EVALUATED: "Participation is not evaluated because no single eligible active proposal reached that stage.",
      ACTIVE_FRONTIER_PRESENT: "At least one active proposal remains on the structural frontier.",
      ACTIVE_FRONTIER_EMPTY: "No active proposal remains on the structural frontier.",
      MISSING_DEPENDENCY_PRESENT: "At least one relationship action refers to an unavailable declared dependency.",
      DEPENDENCY_CYCLE_PRESENT: "The topic contains a declared relationship cycle.",
      ACTIVE_SIGNAL_CONFLICT_PRESENT: "The same admitted actor both endorsed and objected to an active proposal.",
      ACTIVE_OBJECTION_PRESENT: "At least one admitted objection targets the active proposal."
    };
    if (fixed[code]) return fixed[code];
    if (code.indexOf("STATE_") === 0) return "The bounded topic state is " + code.slice(6) + ".";
    if (code.indexOf("REASON_") === 0) return "The governing resolver reason is " + code.slice(7) + ".";
    return "Unsupported witness code: " + code;
  }

  return {
    VERSION: VERSION,
    CAPSULE_PROFILE: CAPSULE_PROFILE,
    COMPARISON_PROFILE: COMPARISON_PROFILE,
    VALUE_COMMITMENT_PROFILE: VALUE_COMMITMENT_PROFILE,
    createCapsule: createCapsule,
    verifyCapsule: verifyCapsule,
    compareCapsules: compareCapsules,
    explainWitnessCode: explainWitnessCode,
    valueCommitment: valueCommitment
  };
}));
