#!/usr/bin/env node

"use strict";

const fs = require("fs");
const path = require("path");
const Resolver = require("../demo/ORL_Chat_Browser_Resolver_v2_0_0.js");
const Capsule = require("../demo/ORL_Chat_Conversation_State_Capsule_v2_0_0.js");

const ROOT = path.resolve(__dirname, "..");
const DEFAULT_VECTOR = path.join(ROOT, "capsules", "ORL_Chat_Conversation_State_Capsule_Vectors_v2_0_0.json");
const VECTOR_PROFILE = "ORL-CHAT-CAPSULE-VECTOR-SET-2-C01";

function readJson(file) {
  return Resolver.strictJsonLoads(fs.readFileSync(file, "utf8"), true);
}

function withoutField(value, field) {
  const result = Resolver.deepCopy(value);
  delete result[field];
  return result;
}

function rotate(values, count) {
  if (!values.length) return [];
  const k = count % values.length;
  return values.slice(k).concat(values.slice(0, k));
}

function orderVariants(observations) {
  const variants = [];
  variants.push(observations.slice());
  variants.push(observations.slice().reverse());
  variants.push(observations.slice().sort(function (a, b) { return Resolver.compareCodePoints(a.observation_ref, b.observation_ref); }));
  variants.push(observations.slice().sort(function (a, b) { return Resolver.compareCodePoints(b.observation_ref, a.observation_ref); }));
  for (let i = 1; i <= Math.min(6, observations.length); i += 1) variants.push(rotate(observations, i));
  const unique = new Map();
  variants.forEach(function (variant) { unique.set(Resolver.canonicalJson(variant), variant); });
  return Array.from(unique.values());
}

function partitionVariants(observations) {
  const variants = [];
  for (let width = 2; width <= 5; width += 1) {
    const parts = Array.from({ length: width }, function () { return []; });
    observations.forEach(function (observation, index) { parts[index % width].push(observation); });
    variants.push(parts);
    variants.push(parts.slice().reverse());
  }
  return variants;
}

function mutateCapsule(capsule, index) {
  const result = Resolver.deepCopy(capsule);
  const hex = String(index % 10).repeat(64);
  const mutations = [
    function () { result.capsule_id = "conversation_state_capsule_" + hex; },
    function () { result.boundary_state = result.boundary_state === "OPEN" ? "SEALED" : "OPEN"; },
    function () { result.graph_root = "graph_" + hex; },
    function () { result.action_set_id = "action_set_" + hex; },
    function () { result.observation_set_id = "observation_set_" + hex; },
    function () { if (result.topics.length) result.topics[0].witness_codes = ["STATE_RESOLVED"]; else result.execution_authority = "EXECUTE"; },
    function () { if (result.topics.length) result.topics[0].state = result.topics[0].state === "RESOLVED" ? "ABSTAIN" : "RESOLVED"; else result.state_counts.RESOLVED = 1; },
    function () { result.execution_authority = "EXECUTE"; }
  ];
  mutations[index % mutations.length]();
  return result;
}

function run(vectorPath) {
  const vectorSet = readJson(vectorPath);
  const groups = new Map();
  const failures = [];

  function check(group, name, condition) {
    if (!groups.has(group)) groups.set(group, { pass: 0, total: 0 });
    const item = groups.get(group);
    item.total += 1;
    if (condition) item.pass += 1;
    else failures.push(group + ": " + name);
  }

  const expectedVectorId = Resolver.identity("capsule_vector_set", VECTOR_PROFILE, withoutField(vectorSet, "vector_set_id"));
  check("VECTOR_SET", "profile", vectorSet.profile === VECTOR_PROFILE);
  check("VECTOR_SET", "identity", vectorSet.vector_set_id === expectedVectorId);
  check("VECTOR_SET", "authority", vectorSet.execution_authority === "NONE");

  const capsules = {};
  vectorSet.capsules.forEach(function (entry) {
    const input = readJson(path.join(ROOT, entry.input_file));
    const frozenBundle = readJson(path.join(ROOT, entry.bundle_file));
    const frozenCapsule = readJson(path.join(ROOT, entry.capsule_file));
    const bundle = Resolver.resolveDocument(input, true);
    const capsule = Capsule.createCapsule(bundle);
    capsules[entry.name] = capsule;
    const verification = Capsule.verifyCapsule(capsule);
    check("CAPSULE", entry.name + "-accepted", bundle.result === "ACCEPTED");
    check("CAPSULE", entry.name + "-bundle-parity", Resolver.canonicalJson(Resolver.bundleWithoutSelfVerification(bundle)) === Resolver.canonicalJson(Resolver.bundleWithoutSelfVerification(frozenBundle)));
    check("CAPSULE", entry.name + "-capsule-parity", Resolver.canonicalJson(capsule) === Resolver.canonicalJson(frozenCapsule));
    check("CAPSULE", entry.name + "-identity", capsule.capsule_id === entry.capsule_id);
    check("CAPSULE", entry.name + "-verification", verification.valid);
    check("CAPSULE", entry.name + "-authority", capsule.execution_authority === "NONE");

    const capsuleText = Resolver.canonicalJson(capsule);
    const declaredValues = [];
    const presentations = [];
    const actors = [];
    input.observations.forEach(function (observation) {
      if (observation.action.declared_value !== null && typeof observation.action.declared_value === "string") declaredValues.push(observation.action.declared_value);
      if (observation.presentation) presentations.push(observation.presentation);
      if (observation.action.actor) actors.push(observation.action.actor);
    });
    check("PRIVACY", entry.name + "-values", declaredValues.every(function (value) { return capsuleText.indexOf(value) === -1; }));
    check("PRIVACY", entry.name + "-presentations", presentations.every(function (value) { return capsuleText.indexOf(value) === -1; }));
    check("PRIVACY", entry.name + "-actors", actors.every(function (value) { return capsuleText.indexOf('"' + value + '"') === -1; }));

    orderVariants(input.observations).forEach(function (variant, index) {
      const document = Resolver.deepCopy(input);
      document.observations = variant;
      const variantCapsule = Capsule.createCapsule(Resolver.resolveDocument(document, true));
      check("ORDER", entry.name + "-" + index, variantCapsule.capsule_id === capsule.capsule_id);
    });

    partitionVariants(input.observations).forEach(function (parts, index) {
      let merged;
      try {
        merged = Resolver.mergeObservationSets.apply(null, parts);
      } catch (error) {
        merged = null;
      }
      if (merged === null) {
        check("PARTITION", entry.name + "-" + index, false);
      } else {
        const document = Resolver.deepCopy(input);
        document.observations = merged;
        const variantCapsule = Capsule.createCapsule(Resolver.resolveDocument(document, true));
        check("PARTITION", entry.name + "-" + index, variantCapsule.capsule_id === capsule.capsule_id);
      }
    });

    for (let index = 0; index < 8; index += 1) {
      check("TAMPER", entry.name + "-" + index, !Capsule.verifyCapsule(mutateCapsule(capsule, index)).valid);
    }

    capsule.topics.forEach(function (topic) {
      topic.witness_codes.forEach(function (code) {
        check("WITNESS", entry.name + "-" + code, Capsule.explainWitnessCode(code).indexOf("Unsupported") !== 0);
      });
    });
  });

  vectorSet.comparisons.forEach(function (entry) {
    const left = capsules[entry.left];
    const right = entry.right === "tampered-capsule"
      ? readJson(path.join(ROOT, "capsules", "artifacts", "tampered-capsule_v2_0_0.json"))
      : capsules[entry.right];
    const result = Capsule.compareCapsules(left, right);
    const frozen = readJson(path.join(ROOT, entry.comparison_file));
    check("COMPARISON", entry.name + "-relation", result.relation === entry.expected_relation);
    check("COMPARISON", entry.name + "-identity", result.comparison_id === entry.comparison_id);
    check("COMPARISON", entry.name + "-parity", Resolver.canonicalJson(result) === Resolver.canonicalJson(frozen));
  });

  let total = 0, passed = 0;
  Array.from(groups.keys()).sort().forEach(function (group) {
    const item = groups.get(group);
    total += item.total;
    passed += item.pass;
    console.log(group + ": " + item.pass + "/" + item.total + (item.pass === item.total ? " PASS" : " FAIL"));
  });
  failures.forEach(function (failure) { console.log("  FAIL: " + failure); });
  console.log("TOTAL: " + passed + "/" + total + (passed === total ? " PASS" : " FAIL"));
  return passed === total ? 0 : 1;
}

function main() {
  const args = process.argv.slice(2);
  let vectorPath = DEFAULT_VECTOR;
  const vectorIndex = args.indexOf("--vectors");
  if (vectorIndex >= 0 && args[vectorIndex + 1]) vectorPath = path.resolve(args[vectorIndex + 1]);
  if (!args.includes("--self-test") && vectorIndex < 0) {
    console.error("Use --self-test or --vectors <path>");
    return 2;
  }
  console.log("ORL-Chat C3 capsule and cross-language verification");
  console.log("vectors: " + path.relative(process.cwd(), vectorPath));
  return run(vectorPath);
}

process.exitCode = main();
