#!/usr/bin/env node

"use strict";

const fs = require("fs");
const path = require("path");
const ORLChat = require(path.join(__dirname, "..", "demo", "ORL_Chat_Browser_Resolver_v2_0_0.js"));

const PROFILE = "ORL-CHAT-CROSS-LANGUAGE-PARITY-2-D01";
const VECTOR_PROFILE = "ORL-CHAT-CROSS-LANGUAGE-VECTOR-2-D01";

class Audit {
  constructor() {
    this.groups = new Map();
    this.failures = [];
  }

  check(group, condition, label) {
    if (!this.groups.has(group)) {
      this.groups.set(group, {passed: 0, total: 0});
    }
    const record = this.groups.get(group);
    record.total += 1;
    if (condition) {
      record.passed += 1;
    } else {
      this.failures.push(group + ": " + label);
    }
  }

  summary() {
    let passed = 0;
    let total = 0;
    for (const group of Array.from(this.groups.keys()).sort()) {
      const record = this.groups.get(group);
      passed += record.passed;
      total += record.total;
      console.log(group + ": " + record.passed + "/" + record.total + " " + (record.passed === record.total ? "PASS" : "FAIL"));
    }
    console.log("TOTAL: " + passed + "/" + total + " " + (passed === total ? "PASS" : "FAIL"));
    if (this.failures.length) {
      for (const failure of this.failures) {
        console.log("FAILURE: " + failure);
      }
    }
    return passed === total;
  }
}

function readCanonicalDocument(filePath) {
  const text = fs.readFileSync(filePath, "utf8");
  return ORLChat.strictJsonLoads(text, true);
}

function expectedTopicReceipts(bundle) {
  if (bundle.result !== "ACCEPTED") {
    return [];
  }
  return bundle.topics.receipts.map(function (receipt) {
    return {
      topic_id: receipt.topic_id,
      state: receipt.state,
      reason_code: receipt.reason_code,
      topic_receipt_id: receipt.topic_receipt_id,
      resolved_action_id: receipt.resolved_action_id,
      resolved_declared_value: receipt.resolved_declared_value
    };
  });
}

function structuralIdentity(bundle) {
  if (bundle.result === "REFUSED") {
    return {result: bundle.result, refusal_id: bundle.refusal_id};
  }
  return {
    result: bundle.result,
    conversation_resolution_id: bundle.conversation_resolution_id,
    private_bundle_id: bundle.private_bundle_id,
    public_receipt_id: bundle.public_receipt.public_receipt_id,
    context_id: bundle.context.context_id,
    action_set_id: bundle.evidence.action_set_id,
    observation_set_id: bundle.evidence.observation_set_id,
    graph_root: bundle.graph.graph_root,
    topic_receipt_root: bundle.topics.topic_receipt_root,
    boundary_receipt_id: bundle.boundary.boundary_receipt_id
  };
}

function compareExpected(bundle, expected, audit, prefix) {
  audit.check("PARITY", bundle.result === expected.result, prefix + " result");
  audit.check("PARITY", ORLChat.bundleCanonicalSha256(bundle) === expected.canonical_bundle_sha256, prefix + " canonical bundle hash");
  if (expected.result === "REFUSED") {
    audit.check("PARITY", bundle.refusal_id === expected.refusal_id, prefix + " refusal id");
    audit.check("PARITY", ORLChat.canonicalJson(bundle.errors) === ORLChat.canonicalJson(expected.errors), prefix + " refusal errors");
    return;
  }
  const checks = [
    [bundle.conversation_resolution_id, expected.conversation_resolution_id, "conversation resolution id"],
    [bundle.private_bundle_id, expected.private_bundle_id, "private bundle id"],
    [bundle.public_receipt.public_receipt_id, expected.public_receipt_id, "public receipt id"],
    [bundle.context.context_id, expected.context_id, "context id"],
    [bundle.evidence.action_set_id, expected.action_set_id, "action set id"],
    [bundle.evidence.observation_set_id, expected.observation_set_id, "observation set id"],
    [bundle.graph.graph_root, expected.graph_root, "graph root"],
    [bundle.topics.topic_receipt_root, expected.topic_receipt_root, "topic receipt root"],
    [bundle.boundary.boundary_receipt_id, expected.boundary_receipt_id, "boundary receipt id"],
    [bundle.boundary.state, expected.boundary_state, "boundary state"]
  ];
  for (const check of checks) {
    audit.check("PARITY", check[0] === check[1], prefix + " " + check[2]);
  }
  audit.check("PARITY", ORLChat.canonicalJson(bundle.topics.state_counts) === ORLChat.canonicalJson(expected.state_counts), prefix + " state counts");
  audit.check("PARITY", ORLChat.canonicalJson(expectedTopicReceipts(bundle)) === ORLChat.canonicalJson(expected.topic_receipts), prefix + " topic receipts");
  audit.check("PARITY", bundle.self_verification && bundle.self_verification.valid === true, prefix + " browser self verification");
}

function variantOrders(observations) {
  const result = [];
  result.push(observations.slice().reverse());
  result.push(observations.slice().sort(function (a, b) { return ORLChat.compareCodePoints(a.observation_ref, b.observation_ref); }));
  if (observations.length > 1) {
    result.push(observations.slice(1).concat(observations[0]));
  } else {
    result.push(observations.slice());
  }
  const odd = [];
  const even = [];
  observations.forEach(function (item, index) {
    (index % 2 ? odd : even).push(item);
  });
  result.push(odd.concat(even));
  return result;
}

function containsKey(value, forbidden) {
  if (Array.isArray(value)) {
    return value.some(function (item) { return containsKey(item, forbidden); });
  }
  if (value && typeof value === "object") {
    for (const key of Object.keys(value)) {
      if (forbidden.has(key) || containsKey(value[key], forbidden)) {
        return true;
      }
    }
  }
  return false;
}

function loadVectors(filePath) {
  const document = readCanonicalDocument(filePath);
  if (document.profile !== PROFILE) {
    throw new Error("unsupported parity profile");
  }
  return document;
}

function runAudit(vectorPath) {
  const document = loadVectors(vectorPath);
  const audit = new Audit();

  audit.check("HASH", ORLChat.sha256Text("abc") === "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "SHA-256 known answer");
  audit.check("PARSER", ORLChat.strictJsonLoads("{\"a\":1}\n", false).a === 1, "strict parser accepts integer JSON");
  audit.check("PARSER", ORLChat.strictJsonLoads("{\"a\":9007199254740991}", false).a === 9007199254740991, "maximum positive integer accepted");
  audit.check("PARSER", ORLChat.strictJsonLoads("{\"a\":-9007199254740991}", false).a === -9007199254740991, "maximum negative integer accepted");
  for (const item of [
    ["integer above exact range", "{\"a\":9007199254740992}"],
    ["integer below exact range", "{\"a\":-9007199254740992}"],
    ["extreme integer token", "{\"a\":" + "9".repeat(1024) + "}"]
  ]) {
    let refused = false;
    try {
      ORLChat.strictJsonLoads(item[1], false);
    } catch (error) {
      refused = error instanceof ORLChat.StrictJSONError && error.message.startsWith("integer exceeds exact interoperable range:");
    }
    audit.check("PARSER", refused, item[0]);
  }
  let duplicateRejected = false;
  try {
    ORLChat.strictJsonLoads("{\"a\":1,\"a\":2}", false);
  } catch (error) {
    duplicateRejected = error instanceof ORLChat.DuplicateKeyError;
  }
  audit.check("PARSER", duplicateRejected, "duplicate key refusal");
  let floatRejected = false;
  try {
    ORLChat.strictJsonLoads("{\"a\":1.5}", false);
  } catch (error) {
    floatRejected = error instanceof ORLChat.StrictJSONError;
  }
  audit.check("PARSER", floatRejected, "floating number refusal");
  const vectorText = fs.readFileSync(vectorPath, "utf8");
  audit.check("PARSER", ORLChat.canonicalArtifactText(document) === vectorText, "canonical parity artifact");
  let noncanonicalRejected = false;
  try {
    ORLChat.strictJsonLoads(JSON.stringify(document), true);
  } catch (error) {
    noncanonicalRejected = error instanceof ORLChat.StrictJSONError;
  }
  audit.check("PARSER", noncanonicalRejected, "noncanonical artifact refusal");
  audit.check("PARSER", document.text_profile === ORLChat.PROFILES.text, "text profile binding");

  const vectorIds = [];
  for (const vector of document.vectors) {
    const basis = {
      profile: VECTOR_PROFILE,
      name: vector.name,
      input: vector.input,
      expected: vector.expected
    };
    const computedVectorId = ORLChat.identity("parity_vector", VECTOR_PROFILE, basis);
    vectorIds.push(computedVectorId);
    audit.check("VECTOR_ID", computedVectorId === vector.vector_id, vector.name);

    const bundle = ORLChat.resolveDocument(ORLChat.deepCopy(vector.input), true);
    compareExpected(bundle, vector.expected, audit, vector.name);

    const baselineIdentity = structuralIdentity(bundle);
    for (const observations of variantOrders(vector.input.observations)) {
      const changed = ORLChat.deepCopy(vector.input);
      changed.observations = ORLChat.deepCopy(observations);
      const variant = ORLChat.resolveDocument(changed, true);
      audit.check("ORDER", ORLChat.canonicalJson(structuralIdentity(variant)) === ORLChat.canonicalJson(baselineIdentity), vector.name);
    }

    if (bundle.result === "ACCEPTED") {
      const partitions = [[], [], []];
      vector.input.observations.forEach(function (item, index) {
        partitions[index % 3].push(ORLChat.deepCopy(item));
      });
      const mergedOrders = [
        [0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]
      ];
      for (const order of mergedOrders) {
        const merged = ORLChat.mergeObservationSets(partitions[order[0]], partitions[order[1]], partitions[order[2]]);
        const changed = ORLChat.deepCopy(vector.input);
        changed.observations = merged;
        const variant = ORLChat.resolveDocument(changed, true);
        audit.check("PARTITION", ORLChat.canonicalJson(structuralIdentity(variant)) === ORLChat.canonicalJson(baselineIdentity), vector.name);
      }

      if (vector.input.observations.length) {
        const changed = ORLChat.deepCopy(vector.input);
        changed.observations.push(ORLChat.deepCopy(changed.observations[0]));
        const variant = ORLChat.resolveDocument(changed, true);
        audit.check("DUPLICATE", variant.conversation_resolution_id === bundle.conversation_resolution_id, vector.name + " conversation resolution");
        audit.check("DUPLICATE", variant.private_bundle_id === bundle.private_bundle_id, vector.name + " private bundle");
        audit.check("DUPLICATE", variant.evidence.exact_observation_duplicate_count === bundle.evidence.exact_observation_duplicate_count + 1, vector.name + " duplicate count");
      }

      const forbiddenKeys = new Set(["presentation", "presentations", "declared_value", "resolved_declared_value", "actor", "active_endorsers", "active_objectors"]);
      audit.check("PRIVACY", !containsKey(bundle.public_receipt, forbiddenKeys), vector.name);
    }
  }

  const manifestBasis = {
    profile: document.profile,
    version: document.version,
    architecture_profile: document.architecture_profile,
    ruleset_profile: document.ruleset_profile,
    text_profile: document.text_profile,
    browser_resolver: document.browser_resolver,
    reference_kernel: document.reference_kernel,
    vector_ids: vectorIds.slice().sort(ORLChat.compareCodePoints)
  };
  audit.check("PARITY_SET", ORLChat.identity("parity_set", PROFILE, manifestBasis) === document.parity_set_id, "parity set identity");

  const acceptedVector = document.vectors.find(function (vector) { return vector.expected.result === "ACCEPTED"; });
  const acceptedBundle = ORLChat.resolveDocument(ORLChat.deepCopy(acceptedVector.input), true);
  const tamperedState = ORLChat.deepCopy(acceptedBundle);
  tamperedState.public_receipt.topic_summaries[0].state = "TAMPERED";
  audit.check("TAMPER", ORLChat.verifyBundle(tamperedState).valid === false, "public state tamper");
  const tamperedId = ORLChat.deepCopy(acceptedBundle);
  tamperedId.private_bundle_id = "private_bundle_" + "0".repeat(64);
  audit.check("TAMPER", ORLChat.verifyBundle(tamperedId).valid === false, "private id tamper");
  const tamperedInput = ORLChat.deepCopy(acceptedBundle);
  tamperedInput.inputs.observations[0].presentation += " altered";
  audit.check("TAMPER", ORLChat.verifyBundle(tamperedInput).valid === false, "embedded input tamper");

  return audit.summary();
}

function parseArgs(argv) {
  let vectorPath = path.join(__dirname, "..", "parity", "ORL_Chat_Cross_Language_Parity_Vectors_v2_0_0.json");
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--verify-vectors" && i + 1 < argv.length) {
      vectorPath = path.resolve(process.cwd(), argv[i + 1]);
      i += 1;
    }
  }
  return {vectorPath: vectorPath};
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  console.log("ORL-Chat browser and cross-language parity verification");
  console.log("vectors: " + path.relative(process.cwd(), args.vectorPath));
  const valid = runAudit(args.vectorPath);
  process.exitCode = valid ? 0 : 1;
}

main();
