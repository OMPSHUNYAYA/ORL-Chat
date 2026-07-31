(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.ORLChat = api;
  }
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const VERSION = "2.0.0";
  const ARCHITECTURE_PROFILE = "ORL-CHAT-ARCH-2-D01";
  const RULESET_PROFILE = "ORL-CHAT-RULES-2-D01";
  const TEXT_PROFILE = "ORL-CHAT-UNICODE-SCALAR-EXACT-2-D01";
  const CONTEXT_SCHEMA = "ORL-CHAT-CONTEXT-2-D01";
  const PARTICIPATION_SCHEMA = "ORL-CHAT-PARTICIPATION-2-D01";
  const ACTION_SCHEMA = "ORL-CHAT-ACTION-2-D01";
  const OBSERVATION_SCHEMA = "ORL-CHAT-OBSERVATION-2-D01";
  const BOUNDARY_SCHEMA = "ORL-CHAT-BOUNDARY-2-D01";
  const GRAPH_PROFILE = "ORL-CHAT-GRAPH-2-D01";
  const TOPIC_RECEIPT_PROFILE = "ORL-CHAT-TOPIC-RECEIPT-2-D01";
  const BOUNDARY_RECEIPT_PROFILE = "ORL-CHAT-BOUNDARY-RECEIPT-2-D01";
  const PUBLIC_RECEIPT_PROFILE = "ORL-CHAT-PUBLIC-RECEIPT-2-D01";
  const PRIVATE_BUNDLE_PROFILE = "ORL-CHAT-PRIVATE-BUNDLE-2-D01";
  const VERIFICATION_PROFILE = "ORL-CHAT-BROWSER-VERIFICATION-2-D01";
  const EXECUTION_AUTHORITY = "NONE";
  const MAX_INPUT_BYTES = 16 * 1024 * 1024;
  const MAX_IDENTIFIER_LENGTH = 128;
  const MAX_PRESENTATION_LENGTH = 8192;
  const MAX_VALUE_STRING_LENGTH = 8192;
  const MAX_VALUE_DEPTH = 16;
  const MAX_VALUE_NODES = 4096;
  const MAX_ARRAY_LENGTH = 256;
  const MAX_OBJECT_FIELDS = 256;
  const MAX_OBSERVATIONS = 4096;
  const MAX_PARTICIPANTS = 256;
  const MAX_GRAPH_DEPTH = 256;
  const MAX_SAFE_INTEGER = 9007199254740991;
  const FROZEN_BOUNDARY_WHITESPACE_RANGES = [
    [0x0009, 0x000D],
    [0x0020, 0x0020],
    [0x0085, 0x0085],
    [0x00A0, 0x00A0],
    [0x1680, 0x1680],
    [0x2000, 0x200A],
    [0x2028, 0x2029],
    [0x202F, 0x202F],
    [0x205F, 0x205F],
    [0x3000, 0x3000]
  ];
  const FROZEN_FORMAT_RANGES = [
    [0x00AD, 0x00AD],
    [0x0600, 0x0605],
    [0x061C, 0x061C],
    [0x06DD, 0x06DD],
    [0x070F, 0x070F],
    [0x0890, 0x0891],
    [0x08E2, 0x08E2],
    [0x180E, 0x180E],
    [0x200B, 0x200F],
    [0x202A, 0x202E],
    [0x2060, 0x2064],
    [0x2066, 0x206F],
    [0xFEFF, 0xFEFF],
    [0xFFF9, 0xFFFB],
    [0x110BD, 0x110BD],
    [0x110CD, 0x110CD],
    [0x13430, 0x1343F],
    [0x1BCA0, 0x1BCA3],
    [0x1D173, 0x1D17A],
    [0xE0001, 0xE0001],
    [0xE0020, 0xE007F]
  ];
  const ACTION_KINDS = ["PROPOSE", "AMEND", "WITHDRAW", "ENDORSE", "OBJECT"];
  const PROPOSAL_KINDS = ["PROPOSE", "AMEND"];
  const RELATION_KINDS = ["AMEND", "WITHDRAW", "ENDORSE", "OBJECT"];
  const PARTICIPATION_PROFILES = [
    "NO_ENDORSEMENT_REQUIRED",
    "SINGLE_DECLARED_ENDORSER",
    "ALL_DECLARED_PARTICIPANTS",
    "EXACT_DECLARED_PARTICIPANT_SET",
    "DECLARED_THRESHOLD"
  ];
  const BOUNDARY_STATES = ["OPEN", "SEALED"];

  class StrictJSONError extends Error {
    constructor(message) {
      super(message);
      this.name = "StrictJSONError";
    }
  }

  class DuplicateKeyError extends StrictJSONError {
    constructor(message) {
      super(message);
      this.name = "DuplicateKeyError";
    }
  }

  function compareCodePoints(left, right) {
    if (left === right) {
      return 0;
    }
    const a = Array.from(left);
    const b = Array.from(right);
    const n = Math.min(a.length, b.length);
    for (let i = 0; i < n; i += 1) {
      const ac = a[i].codePointAt(0);
      const bc = b[i].codePointAt(0);
      if (ac < bc) {
        return -1;
      }
      if (ac > bc) {
        return 1;
      }
    }
    return a.length < b.length ? -1 : 1;
  }

  function sortedStrings(values) {
    return Array.from(values).sort(compareCodePoints);
  }

  function isPlainObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function deepCopy(value) {
    if (Array.isArray(value)) {
      return value.map(deepCopy);
    }
    if (isPlainObject(value)) {
      const result = {};
      for (const key of Object.keys(value)) {
        result[key] = deepCopy(value[key]);
      }
      return result;
    }
    return value;
  }

  function canonicalJson(value) {
    if (value === null) {
      return "null";
    }
    if (value === true) {
      return "true";
    }
    if (value === false) {
      return "false";
    }
    if (typeof value === "number") {
      if (!Number.isFinite(value) || !Number.isInteger(value) || !Number.isSafeInteger(value)) {
        throw new StrictJSONError("canonical JSON supports exact interoperable integers only");
      }
      return Object.is(value, -0) ? "0" : String(value);
    }
    if (typeof value === "string") {
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
      return "[" + value.map(canonicalJson).join(",") + "]";
    }
    if (isPlainObject(value)) {
      const keys = Object.keys(value).sort(compareCodePoints);
      return "{" + keys.map(function (key) {
        return JSON.stringify(key) + ":" + canonicalJson(value[key]);
      }).join(",") + "}";
    }
    throw new StrictJSONError("unsupported canonical JSON value type");
  }

  function canonicalArtifactText(value) {
    function render(item, depth) {
      if (item === null || typeof item === "boolean" || typeof item === "number" || typeof item === "string") {
        return canonicalJson(item);
      }
      const indent = "  ".repeat(depth);
      const childIndent = "  ".repeat(depth + 1);
      if (Array.isArray(item)) {
        if (item.length === 0) {
          return "[]";
        }
        return "[\n" + item.map(function (child) {
          return childIndent + render(child, depth + 1);
        }).join(",\n") + "\n" + indent + "]";
      }
      if (isPlainObject(item)) {
        const keys = Object.keys(item).sort(compareCodePoints);
        if (keys.length === 0) {
          return "{}";
        }
        return "{\n" + keys.map(function (key) {
          return childIndent + JSON.stringify(key) + ": " + render(item[key], depth + 1);
        }).join(",\n") + "\n" + indent + "}";
      }
      throw new StrictJSONError("unsupported canonical JSON value type");
    }
    return render(value, 0) + "\n";
  }

  function sha256Text(text) {
    const bytes = new TextEncoder().encode(text);
    const words = [];
    const bitLength = bytes.length * 8;
    for (let i = 0; i < bytes.length; i += 1) {
      words[i >> 2] = (words[i >> 2] || 0) | (bytes[i] << (24 - (i % 4) * 8));
    }
    words[bytes.length >> 2] = (words[bytes.length >> 2] || 0) | (0x80 << (24 - (bytes.length % 4) * 8));
    const lengthIndex = (((bytes.length + 8) >> 6) + 1) * 16 - 2;
    words[lengthIndex] = Math.floor(bitLength / 0x100000000);
    words[lengthIndex + 1] = bitLength >>> 0;
    const k = [
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
      0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
      0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
      0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
      0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
      0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ];
    let h0 = 0x6a09e667;
    let h1 = 0xbb67ae85;
    let h2 = 0x3c6ef372;
    let h3 = 0xa54ff53a;
    let h4 = 0x510e527f;
    let h5 = 0x9b05688c;
    let h6 = 0x1f83d9ab;
    let h7 = 0x5be0cd19;
    function rotr(value, shift) {
      return (value >>> shift) | (value << (32 - shift));
    }
    for (let offset = 0; offset < words.length; offset += 16) {
      const w = new Array(64);
      for (let i = 0; i < 16; i += 1) {
        w[i] = words[offset + i] | 0;
      }
      for (let i = 16; i < 64; i += 1) {
        const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
        const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
      }
      let a = h0;
      let b = h1;
      let c = h2;
      let d = h3;
      let e = h4;
      let f = h5;
      let g = h6;
      let h = h7;
      for (let i = 0; i < 64; i += 1) {
        const s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        const ch = (e & f) ^ ((~e) & g);
        const temp1 = (h + s1 + ch + k[i] + w[i]) | 0;
        const s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        const maj = (a & b) ^ (a & c) ^ (b & c);
        const temp2 = (s0 + maj) | 0;
        h = g;
        g = f;
        f = e;
        e = (d + temp1) | 0;
        d = c;
        c = b;
        b = a;
        a = (temp1 + temp2) | 0;
      }
      h0 = (h0 + a) | 0;
      h1 = (h1 + b) | 0;
      h2 = (h2 + c) | 0;
      h3 = (h3 + d) | 0;
      h4 = (h4 + e) | 0;
      h5 = (h5 + f) | 0;
      h6 = (h6 + g) | 0;
      h7 = (h7 + h) | 0;
    }
    return [h0, h1, h2, h3, h4, h5, h6, h7].map(function (value) {
      return (value >>> 0).toString(16).padStart(8, "0");
    }).join("");
  }

  function identity(prefix, profile, value) {
    return prefix + "_" + sha256Text(canonicalJson({profile: profile, value: value}));
  }

  class StrictParser {
    constructor(text) {
      this.text = text;
      this.index = 0;
    }

    error(message) {
      throw new StrictJSONError(message + " at position " + this.index);
    }

    skipWhitespace() {
      while (this.index < this.text.length && /[\x20\x09\x0a\x0d]/.test(this.text[this.index])) {
        this.index += 1;
      }
    }

    parse() {
      this.skipWhitespace();
      const value = this.parseValue();
      this.skipWhitespace();
      if (this.index !== this.text.length) {
        this.error("unexpected trailing content");
      }
      return value;
    }

    parseValue() {
      if (this.index >= this.text.length) {
        this.error("unexpected end of JSON");
      }
      const char = this.text[this.index];
      if (char === "{") {
        return this.parseObject();
      }
      if (char === "[") {
        return this.parseArray();
      }
      if (char === "\"") {
        return this.parseString();
      }
      if (char === "t" && this.text.slice(this.index, this.index + 4) === "true") {
        this.index += 4;
        return true;
      }
      if (char === "f" && this.text.slice(this.index, this.index + 5) === "false") {
        this.index += 5;
        return false;
      }
      if (char === "n" && this.text.slice(this.index, this.index + 4) === "null") {
        this.index += 4;
        return null;
      }
      if (char === "-" || /[0-9]/.test(char)) {
        return this.parseNumber();
      }
      this.error("invalid JSON value");
    }

    parseObject() {
      const result = {};
      const seen = new Set();
      this.index += 1;
      this.skipWhitespace();
      if (this.text[this.index] === "}") {
        this.index += 1;
        return result;
      }
      while (true) {
        this.skipWhitespace();
        if (this.text[this.index] !== "\"") {
          this.error("object key must be a string");
        }
        const key = this.parseString();
        if (seen.has(key)) {
          throw new DuplicateKeyError("duplicate JSON object key: " + key);
        }
        seen.add(key);
        this.skipWhitespace();
        if (this.text[this.index] !== ":") {
          this.error("expected colon");
        }
        this.index += 1;
        this.skipWhitespace();
        result[key] = this.parseValue();
        this.skipWhitespace();
        const char = this.text[this.index];
        if (char === "}") {
          this.index += 1;
          return result;
        }
        if (char !== ",") {
          this.error("expected comma or closing brace");
        }
        this.index += 1;
      }
    }

    parseArray() {
      const result = [];
      this.index += 1;
      this.skipWhitespace();
      if (this.text[this.index] === "]") {
        this.index += 1;
        return result;
      }
      while (true) {
        this.skipWhitespace();
        result.push(this.parseValue());
        this.skipWhitespace();
        const char = this.text[this.index];
        if (char === "]") {
          this.index += 1;
          return result;
        }
        if (char !== ",") {
          this.error("expected comma or closing bracket");
        }
        this.index += 1;
      }
    }

    parseString() {
      const start = this.index;
      this.index += 1;
      let escaped = false;
      while (this.index < this.text.length) {
        const char = this.text[this.index];
        if (!escaped && char === "\"") {
          this.index += 1;
          const token = this.text.slice(start, this.index);
          try {
            return JSON.parse(token);
          } catch (error) {
            this.error("invalid JSON string");
          }
        }
        if (!escaped && char === "\\") {
          escaped = true;
          this.index += 1;
          continue;
        }
        escaped = false;
        this.index += 1;
      }
      this.error("unterminated JSON string");
    }

    parseNumber() {
      const start = this.index;
      if (this.text[this.index] === "-") {
        this.index += 1;
      }
      if (this.text[this.index] === "0") {
        this.index += 1;
        if (/[0-9]/.test(this.text[this.index] || "")) {
          this.error("leading zeros are not supported");
        }
      } else {
        if (!/[1-9]/.test(this.text[this.index] || "")) {
          this.error("invalid number");
        }
        while (/[0-9]/.test(this.text[this.index] || "")) {
          this.index += 1;
        }
      }
      if (this.text[this.index] === "." || this.text[this.index] === "e" || this.text[this.index] === "E") {
        while (this.index < this.text.length && /[0-9eE+\-.]/.test(this.text[this.index])) {
          this.index += 1;
        }
        throw new StrictJSONError("floating-point JSON numbers are not supported: " + this.text.slice(start, this.index));
      }
      const token = this.text.slice(start, this.index);
      const digits = token.startsWith("-") ? token.slice(1) : token;
      const magnitude = digits.replace(/^0+/, "") || "0";
      const maximum = String(MAX_SAFE_INTEGER);
      if (magnitude.length > maximum.length || (magnitude.length === maximum.length && magnitude > maximum)) {
        throw new StrictJSONError("integer exceeds exact interoperable range: " + token);
      }
      return Number(token);
    }
  }

  function strictJsonLoads(text, strictCanonical) {
    if (typeof text !== "string") {
      throw new StrictJSONError("JSON document must be text");
    }
    if (new TextEncoder().encode(text).length > MAX_INPUT_BYTES) {
      throw new StrictJSONError("JSON document exceeds maximum byte length");
    }
    if (text.startsWith("\ufeff")) {
      throw new StrictJSONError("UTF-8 BOM is not supported");
    }
    const value = new StrictParser(text).parse();
    if (strictCanonical && text !== canonicalArtifactText(value)) {
      throw new StrictJSONError("JSON document is not in canonical artifact form with sorted keys, two-space indentation, and one LF terminator");
    }
    return value;
  }

  function isFrozenBoundaryWhitespace(codePoint) {
    return FROZEN_BOUNDARY_WHITESPACE_RANGES.some(function (range) {
      return range[0] <= codePoint && codePoint <= range[1];
    });
  }

  function hasFrozenBoundaryWhitespace(value) {
    const characters = Array.from(value);
    if (characters.length === 0) {
      return false;
    }
    return isFrozenBoundaryWhitespace(characters[0].codePointAt(0)) || isFrozenBoundaryWhitespace(characters[characters.length - 1].codePointAt(0));
  }

  function isFrozenFormatCodePoint(codePoint) {
    return FROZEN_FORMAT_RANGES.some(function (range) {
      return range[0] <= codePoint && codePoint <= range[1];
    });
  }

  function isFrozenControlCodePoint(codePoint) {
    return (0x0000 <= codePoint && codePoint <= 0x001F) || (0x007F <= codePoint && codePoint <= 0x009F);
  }

  function isSurrogateCodePoint(codePoint) {
    return 0xD800 <= codePoint && codePoint <= 0xDFFF;
  }

  function containsForbiddenIdentifierCharacter(value) {
    for (let index = 0; index < value.length; index += 1) {
      const codePoint = value.codePointAt(index);
      if (codePoint > 0xFFFF) {
        index += 1;
      }
      if (isFrozenControlCodePoint(codePoint) || isFrozenFormatCodePoint(codePoint) || isSurrogateCodePoint(codePoint)) {
        return true;
      }
    }
    return false;
  }

  function containsForbiddenTextCharacter(value) {
    for (let index = 0; index < value.length; index += 1) {
      const codePoint = value.codePointAt(index);
      if (codePoint > 0xFFFF) {
        index += 1;
      }
      if (codePoint === 0x0009 || codePoint === 0x000A) {
        continue;
      }
      if (isFrozenControlCodePoint(codePoint) || isFrozenFormatCodePoint(codePoint) || isSurrogateCodePoint(codePoint)) {
        return true;
      }
    }
    return false;
  }

  function exactFields(record, expectedFields, label) {
    if (!isPlainObject(record)) {
      return [label + ": must be an object"];
    }
    const actual = new Set(Object.keys(record));
    const expected = new Set(expectedFields);
    const errors = [];
    for (const field of sortedStrings(Array.from(expected).filter(function (item) { return !actual.has(item); }))) {
      errors.push(label + ": missing field " + field);
    }
    for (const field of sortedStrings(Array.from(actual).filter(function (item) { return !expected.has(item); }))) {
      errors.push(label + ": unsupported field " + field);
    }
    return errors;
  }

  function validateIdentifier(value, label) {
    if (typeof value !== "string") {
      return [label + ": must be a string"];
    }
    const errors = [];
    if (value === "") {
      errors.push(label + ": must not be empty");
    }
    if (Array.from(value).length > MAX_IDENTIFIER_LENGTH) {
      errors.push(label + ": exceeds maximum length");
    }
    if (hasFrozenBoundaryWhitespace(value)) {
      errors.push(label + ": leading or trailing whitespace is not allowed");
    }
    if (containsForbiddenIdentifierCharacter(value)) {
      errors.push(label + ": control, format, and surrogate characters are not allowed");
    }
    return errors;
  }

  function validatePresentation(value, label) {
    if (typeof value !== "string") {
      return [label + ": must be a string"];
    }
    const errors = [];
    if (Array.from(value).length > MAX_PRESENTATION_LENGTH) {
      errors.push(label + ": exceeds maximum length");
    }
    if (containsForbiddenTextCharacter(value)) {
      errors.push(label + ": unsupported control, format, carriage-return, or surrogate character");
    }
    return errors;
  }

  function validateDeclaredValue(value, label) {
    const errors = [];
    let nodeCount = 0;
    function walk(item, path, depth) {
      nodeCount += 1;
      if (nodeCount > MAX_VALUE_NODES) {
        errors.push(label + ": exceeds maximum node count");
        return;
      }
      if (depth > MAX_VALUE_DEPTH) {
        errors.push(path + ": exceeds maximum nesting depth");
        return;
      }
      if (item === null || typeof item === "boolean") {
        return;
      }
      if (typeof item === "number") {
        if (!Number.isInteger(item)) {
          errors.push(path + ": floating-point values are not supported");
        } else if (!Number.isSafeInteger(item) || Math.abs(item) > MAX_SAFE_INTEGER) {
          errors.push(path + ": integer exceeds exact interoperable range");
        }
        return;
      }
      if (typeof item === "string") {
        if (Array.from(item).length > MAX_VALUE_STRING_LENGTH) {
          errors.push(path + ": string exceeds maximum length");
        }
        if (containsForbiddenTextCharacter(item)) {
          errors.push(path + ": unsupported control, format, carriage-return, or surrogate character");
        }
        return;
      }
      if (Array.isArray(item)) {
        if (item.length > MAX_ARRAY_LENGTH) {
          errors.push(path + ": array exceeds maximum length");
          return;
        }
        item.forEach(function (child, index) {
          walk(child, path + "[" + index + "]", depth + 1);
        });
        return;
      }
      if (isPlainObject(item)) {
        const keys = Object.keys(item).sort(compareCodePoints);
        if (keys.length > MAX_OBJECT_FIELDS) {
          errors.push(path + ": object exceeds maximum field count");
          return;
        }
        for (const key of keys) {
          errors.push.apply(errors, validateIdentifier(key, path + ".<key>"));
          walk(item[key], path + "." + key, depth + 1);
        }
        return;
      }
      errors.push(path + ": unsupported value type");
    }
    walk(value, label || "declared_value", 0);
    return errors;
  }

  function validateIdentifierArray(value, label, maximum) {
    if (!Array.isArray(value)) {
      return [label + ": must be an array"];
    }
    const errors = [];
    if (value.length > maximum) {
      errors.push(label + ": exceeds maximum length");
    }
    value.forEach(function (item, index) {
      errors.push.apply(errors, validateIdentifier(item, label + "[" + index + "]"));
    });
    if (value.length !== new Set(value).size) {
      errors.push(label + ": duplicate values are not allowed");
    }
    return errors;
  }

  function validateParticipation(record) {
    const fields = ["schema", "profile", "participants", "required_endorsers", "threshold"];
    const errors = exactFields(record, fields, "participation");
    if (errors.length) {
      return errors;
    }
    if (record.schema !== PARTICIPATION_SCHEMA) {
      errors.push("participation.schema: unsupported schema");
    }
    if (!PARTICIPATION_PROFILES.includes(record.profile)) {
      errors.push("participation.profile: unsupported profile");
    }
    errors.push.apply(errors, validateIdentifierArray(record.participants, "participation.participants", MAX_PARTICIPANTS));
    errors.push.apply(errors, validateIdentifierArray(record.required_endorsers, "participation.required_endorsers", MAX_PARTICIPANTS));
    const threshold = record.threshold;
    if (!Number.isInteger(threshold)) {
      errors.push("participation.threshold: must be an integer");
    } else if (threshold < 0 || threshold > MAX_PARTICIPANTS) {
      errors.push("participation.threshold: out of supported range");
    }
    if (errors.length) {
      return errors;
    }
    const participants = new Set(record.participants);
    const required = new Set(record.required_endorsers);
    const profile = record.profile;
    for (const item of required) {
      if (!participants.has(item)) {
        errors.push("participation.required_endorsers: must be a subset of participants");
        break;
      }
    }
    if (profile === "NO_ENDORSEMENT_REQUIRED") {
      if (record.participants.length || record.required_endorsers.length || threshold !== 0) {
        errors.push("participation: NO_ENDORSEMENT_REQUIRED requires empty participant fields and threshold 0");
      }
    } else if (profile === "SINGLE_DECLARED_ENDORSER") {
      if (!participants.size) {
        errors.push("participation: SINGLE_DECLARED_ENDORSER requires participants");
      }
      if (required.size || threshold !== 1) {
        errors.push("participation: SINGLE_DECLARED_ENDORSER requires empty required_endorsers and threshold 1");
      }
    } else if (profile === "ALL_DECLARED_PARTICIPANTS") {
      if (!participants.size) {
        errors.push("participation: ALL_DECLARED_PARTICIPANTS requires participants");
      }
      if (required.size || threshold !== participants.size) {
        errors.push("participation: ALL_DECLARED_PARTICIPANTS requires empty required_endorsers and threshold equal to participant count");
      }
    } else if (profile === "EXACT_DECLARED_PARTICIPANT_SET") {
      if (!participants.size || !required.size) {
        errors.push("participation: EXACT_DECLARED_PARTICIPANT_SET requires participants and required_endorsers");
      }
      if (threshold !== required.size) {
        errors.push("participation: EXACT_DECLARED_PARTICIPANT_SET requires threshold equal to required_endorsers count");
      }
    } else if (profile === "DECLARED_THRESHOLD") {
      if (!participants.size) {
        errors.push("participation: DECLARED_THRESHOLD requires participants");
      }
      if (required.size) {
        errors.push("participation: DECLARED_THRESHOLD requires empty required_endorsers");
      }
      if (threshold < 1 || threshold > participants.size) {
        errors.push("participation: DECLARED_THRESHOLD threshold must be within participant count");
      }
    }
    return errors;
  }

  function validateContext(record) {
    const fields = ["schema", "conversation_id", "purpose_id", "ruleset_profile", "participation", "execution_authority"];
    const errors = exactFields(record, fields, "context");
    if (errors.length) {
      return errors;
    }
    if (record.schema !== CONTEXT_SCHEMA) {
      errors.push("context.schema: unsupported schema");
    }
    errors.push.apply(errors, validateIdentifier(record.conversation_id, "context.conversation_id"));
    errors.push.apply(errors, validateIdentifier(record.purpose_id, "context.purpose_id"));
    if (record.ruleset_profile !== RULESET_PROFILE) {
      errors.push("context.ruleset_profile: unsupported ruleset profile");
    }
    errors.push.apply(errors, validateParticipation(record.participation));
    if (record.execution_authority !== EXECUTION_AUTHORITY) {
      errors.push("context.execution_authority: must be NONE");
    }
    return errors;
  }

  function validateAction(record) {
    const fields = ["schema", "action_ref", "conversation_id", "topic_id", "actor", "kind", "declared_value", "targets"];
    const errors = exactFields(record, fields, "action");
    if (errors.length) {
      return errors;
    }
    if (record.schema !== ACTION_SCHEMA) {
      errors.push("action.schema: unsupported schema");
    }
    errors.push.apply(errors, validateIdentifier(record.action_ref, "action.action_ref"));
    errors.push.apply(errors, validateIdentifier(record.conversation_id, "action.conversation_id"));
    errors.push.apply(errors, validateIdentifier(record.topic_id, "action.topic_id"));
    errors.push.apply(errors, validateIdentifier(record.actor, "action.actor"));
    const kind = record.kind;
    if (!ACTION_KINDS.includes(kind)) {
      errors.push("action.kind: unsupported kind");
    }
    errors.push.apply(errors, validateIdentifierArray(record.targets, "action.targets", 1));
    if (PROPOSAL_KINDS.includes(kind)) {
      if (record.declared_value === null) {
        errors.push("action.declared_value: proposal-producing actions require a non-null value");
      } else {
        errors.push.apply(errors, validateDeclaredValue(record.declared_value, "action.declared_value"));
      }
    } else if (["WITHDRAW", "ENDORSE", "OBJECT"].includes(kind)) {
      if (record.declared_value !== null) {
        errors.push("action.declared_value: relation-only actions require null");
      }
    }
    if (kind === "PROPOSE" && canonicalJson(record.targets) !== "[]") {
      errors.push("action.targets: PROPOSE requires no targets");
    }
    if (RELATION_KINDS.includes(kind) && record.targets.length !== 1) {
      errors.push("action.targets: relation action requires exactly one target");
    }
    return errors;
  }

  function validateObservation(record) {
    const fields = ["schema", "observation_ref", "source", "presentation", "action"];
    const errors = exactFields(record, fields, "observation");
    if (errors.length) {
      return errors;
    }
    if (record.schema !== OBSERVATION_SCHEMA) {
      errors.push("observation.schema: unsupported schema");
    }
    errors.push.apply(errors, validateIdentifier(record.observation_ref, "observation.observation_ref"));
    errors.push.apply(errors, validateIdentifier(record.source, "observation.source"));
    errors.push.apply(errors, validatePresentation(record.presentation, "observation.presentation"));
    errors.push.apply(errors, validateAction(record.action));
    return errors;
  }

  function validateBoundary(record) {
    const fields = ["schema", "state", "expected_observation_refs"];
    const errors = exactFields(record, fields, "boundary");
    if (errors.length) {
      return errors;
    }
    if (record.schema !== BOUNDARY_SCHEMA) {
      errors.push("boundary.schema: unsupported schema");
    }
    if (!BOUNDARY_STATES.includes(record.state)) {
      errors.push("boundary.state: must be OPEN or SEALED");
    }
    errors.push.apply(errors, validateIdentifierArray(record.expected_observation_refs, "boundary.expected_observation_refs", MAX_OBSERVATIONS));
    if (record.state === "OPEN" && record.expected_observation_refs.length) {
      errors.push("boundary.expected_observation_refs: OPEN boundary requires an empty list");
    }
    return errors;
  }

  function canonicalParticipation(record) {
    return {
      schema: PARTICIPATION_SCHEMA,
      profile: record.profile,
      participants: sortedStrings(record.participants),
      required_endorsers: sortedStrings(record.required_endorsers),
      threshold: record.threshold
    };
  }

  function canonicalContext(record) {
    return {
      schema: CONTEXT_SCHEMA,
      conversation_id: record.conversation_id,
      purpose_id: record.purpose_id,
      ruleset_profile: RULESET_PROFILE,
      participation: canonicalParticipation(record.participation),
      execution_authority: EXECUTION_AUTHORITY
    };
  }

  function canonicalAction(record) {
    return {
      schema: ACTION_SCHEMA,
      action_ref: record.action_ref,
      conversation_id: record.conversation_id,
      topic_id: record.topic_id,
      actor: record.actor,
      kind: record.kind,
      declared_value: deepCopy(record.declared_value),
      targets: sortedStrings(record.targets)
    };
  }

  function canonicalObservation(record) {
    return {
      schema: OBSERVATION_SCHEMA,
      observation_ref: record.observation_ref,
      source: record.source,
      presentation: record.presentation,
      action: canonicalAction(record.action)
    };
  }

  function canonicalBoundary(record) {
    return {
      schema: BOUNDARY_SCHEMA,
      state: record.state,
      expected_observation_refs: sortedStrings(record.expected_observation_refs)
    };
  }

  function contextId(record) {
    return identity("context", CONTEXT_SCHEMA, canonicalContext(record));
  }

  function actionId(record) {
    return identity("action", ACTION_SCHEMA, canonicalAction(record));
  }

  function observationId(record) {
    const action = canonicalAction(record.action);
    const basis = {
      schema: OBSERVATION_SCHEMA,
      observation_ref: record.observation_ref,
      source: record.source,
      presentation: record.presentation,
      action_id: actionId(action)
    };
    return identity("observation", OBSERVATION_SCHEMA, basis);
  }

  function makeRefusal(errors) {
    const refusal = {
      profile: PRIVATE_BUNDLE_PROFILE,
      version: VERSION,
      result: "REFUSED",
      architecture_profile: ARCHITECTURE_PROFILE,
      ruleset_profile: RULESET_PROFILE,
      execution_authority: EXECUTION_AUTHORITY,
      errors: Array.from(errors)
    };
    refusal.refusal_id = identity("refusal", PRIVATE_BUNDLE_PROFILE, refusal);
    return refusal;
  }

  function prepareContext(record) {
    const errors = validateContext(record);
    if (errors.length) {
      return {validation_state: "REFUSED", errors: errors};
    }
    const canonical = canonicalContext(record);
    return {validation_state: "ACCEPTED", context: canonical, context_id: contextId(canonical)};
  }

  function prepareObservations(observations, context) {
    if (!Array.isArray(observations)) {
      return {validation_state: "REFUSED", errors: ["observations: must be an array"]};
    }
    if (observations.length > MAX_OBSERVATIONS) {
      return {validation_state: "REFUSED", errors: ["observations: exceeds maximum length"]};
    }
    const errors = [];
    const validated = [];
    observations.forEach(function (record, index) {
      const found = validateObservation(record);
      if (found.length) {
        for (const item of found) {
          errors.push("observations[" + index + "]: " + item);
        }
      } else {
        const canonical = canonicalObservation(record);
        if (canonical.action.conversation_id !== context.conversation_id) {
          errors.push("observations[" + index + "]: action.conversation_id does not match context");
        } else {
          validated.push(canonical);
        }
      }
    });
    if (errors.length) {
      return {validation_state: "REFUSED", errors: errors};
    }

    const byObservationId = new Map();
    const byObservationRef = new Map();
    for (const record of validated) {
      const oid = observationId(record);
      byObservationId.set(oid, record);
      if (!byObservationRef.has(record.observation_ref)) {
        byObservationRef.set(record.observation_ref, new Map());
      }
      byObservationRef.get(record.observation_ref).set(oid, record);
    }
    const conflicts = [];
    for (const ref of sortedStrings(byObservationRef.keys())) {
      const ids = sortedStrings(byObservationRef.get(ref).keys());
      if (ids.length > 1) {
        conflicts.push({observation_ref: ref, observation_ids: ids});
      }
    }
    if (conflicts.length) {
      return {
        validation_state: "REFUSED",
        errors: conflicts.map(function (item) { return "observation_ref content conflict: " + item.observation_ref; }),
        observation_ref_conflicts: conflicts
      };
    }

    const byActionRef = new Map();
    const actionObservations = new Map();
    const actionSources = new Map();
    const actionPresentations = new Map();
    const actionRecords = new Map();
    for (const oid of sortedStrings(byObservationId.keys())) {
      const observation = byObservationId.get(oid);
      const action = observation.action;
      const aid = actionId(action);
      const ref = action.action_ref;
      if (!byActionRef.has(ref)) {
        byActionRef.set(ref, new Map());
      }
      byActionRef.get(ref).set(aid, action);
      actionRecords.set(aid, action);
      if (!actionObservations.has(aid)) {
        actionObservations.set(aid, []);
        actionSources.set(aid, new Set());
        actionPresentations.set(aid, []);
      }
      actionObservations.get(aid).push(oid);
      actionSources.get(aid).add(observation.source);
      actionPresentations.get(aid).push({observation_id: oid, presentation: observation.presentation});
    }
    const actionRefConflicts = [];
    for (const ref of sortedStrings(byActionRef.keys())) {
      const ids = sortedStrings(byActionRef.get(ref).keys());
      if (ids.length > 1) {
        actionRefConflicts.push({action_ref: ref, action_ids: ids});
      }
    }
    if (actionRefConflicts.length) {
      return {
        validation_state: "REFUSED",
        errors: actionRefConflicts.map(function (item) { return "action_ref content conflict: " + item.action_ref; }),
        action_ref_conflicts: actionRefConflicts
      };
    }

    const actionEntries = [];
    const actionRefToId = {};
    for (const aid of sortedStrings(actionRecords.keys())) {
      const action = actionRecords.get(aid);
      actionRefToId[action.action_ref] = aid;
      actionEntries.push({
        action_id: aid,
        action: deepCopy(action),
        observation_ids: sortedStrings(actionObservations.get(aid)),
        sources: sortedStrings(actionSources.get(aid)),
        observation_count: actionObservations.get(aid).length,
        presentations: actionPresentations.get(aid).slice().sort(function (a, b) { return compareCodePoints(a.observation_id, b.observation_id); })
      });
    }
    const observationEntries = [];
    for (const oid of sortedStrings(byObservationId.keys())) {
      const observation = byObservationId.get(oid);
      observationEntries.push({
        observation_id: oid,
        observation_ref: observation.observation_ref,
        source: observation.source,
        presentation: observation.presentation,
        action_id: actionId(observation.action)
      });
    }
    const actionSetBasis = {profile: ACTION_SCHEMA, action_ids: sortedStrings(actionRecords.keys())};
    const observationSetBasis = {profile: OBSERVATION_SCHEMA, observation_ids: sortedStrings(byObservationId.keys())};
    return {
      validation_state: "ACCEPTED",
      raw_observation_count: observations.length,
      unique_observation_count: byObservationId.size,
      exact_observation_duplicate_count: observations.length - byObservationId.size,
      unique_action_count: actionRecords.size,
      observation_multiplicity_count: byObservationId.size - actionRecords.size,
      actions: actionEntries,
      observations: observationEntries,
      action_ref_to_id: actionRefToId,
      action_set_id: identity("action_set", ACTION_SCHEMA, actionSetBasis),
      observation_set_id: identity("observation_set", OBSERVATION_SCHEMA, observationSetBasis)
    };
  }

  function buildGraph(evidence, context) {
    const actionByRef = new Map();
    const actionIdByRef = new Map();
    const actionEntryByRef = new Map();
    for (const entry of evidence.actions) {
      const action = entry.action;
      actionByRef.set(action.action_ref, action);
      actionIdByRef.set(action.action_ref, entry.action_id);
      actionEntryByRef.set(action.action_ref, entry);
    }
    const errors = [];
    const missingDependencies = [];
    const edges = [];
    const participantSet = new Set(context.participation.participants);
    for (const ref of sortedStrings(actionByRef.keys())) {
      const action = actionByRef.get(ref);
      if (["ENDORSE", "OBJECT"].includes(action.kind) && !participantSet.has(action.actor)) {
        errors.push("action " + ref + ": actor is not admitted by the participation profile");
      }
      if (RELATION_KINDS.includes(action.kind)) {
        const targetRef = action.targets[0];
        if (targetRef === ref) {
          errors.push("action " + ref + ": self-target is not supported");
          continue;
        }
        if (!actionByRef.has(targetRef)) {
          missingDependencies.push({action_ref: ref, action_id: actionIdByRef.get(ref), missing_target_ref: targetRef});
          continue;
        }
        const target = actionByRef.get(targetRef);
        if (target.conversation_id !== action.conversation_id) {
          errors.push("action " + ref + ": cross-conversation target is not supported");
          continue;
        }
        if (target.topic_id !== action.topic_id) {
          errors.push("action " + ref + ": cross-topic target is not supported");
          continue;
        }
        if (!PROPOSAL_KINDS.includes(target.kind)) {
          errors.push("action " + ref + ": target must be PROPOSE or AMEND");
          continue;
        }
        edges.push({
          source_action_ref: ref,
          source_action_id: actionIdByRef.get(ref),
          relation: action.kind,
          target_action_ref: targetRef,
          target_action_id: actionIdByRef.get(targetRef)
        });
      }
    }
    if (errors.length) {
      return {validation_state: "REFUSED", errors: errors};
    }
    const adjacency = new Map();
    for (const edge of edges) {
      if (!adjacency.has(edge.source_action_ref)) {
        adjacency.set(edge.source_action_ref, []);
      }
      adjacency.get(edge.source_action_ref).push(edge.target_action_ref);
    }
    for (const startRef of sortedStrings(actionByRef.keys())) {
      const seen = new Set([startRef]);
      let current = startRef;
      let depth = 0;
      while (adjacency.has(current) && adjacency.get(current).length) {
        current = adjacency.get(current)[0];
        if (seen.has(current)) {
          break;
        }
        seen.add(current);
        depth += 1;
        if (depth > MAX_GRAPH_DEPTH) {
          errors.push("action " + startRef + ": dependency chain exceeds maximum depth");
          break;
        }
      }
      if (errors.length) {
        break;
      }
    }
    if (errors.length) {
      return {validation_state: "REFUSED", errors: errors};
    }
    const cycleRefs = new Set();
    const completed = new Set();
    for (const startRef of sortedStrings(actionByRef.keys())) {
      if (completed.has(startRef)) {
        continue;
      }
      const path = [];
      const pathIndex = new Map();
      let current = startRef;
      while (!completed.has(current) && !pathIndex.has(current)) {
        pathIndex.set(current, path.length);
        path.push(current);
        const targets = adjacency.get(current) || [];
        if (!targets.length) {
          current = null;
          break;
        }
        current = targets[0];
      }
      if (current !== null && pathIndex.has(current)) {
        for (const item of path.slice(pathIndex.get(current))) {
          cycleRefs.add(item);
        }
      }
      for (const item of path) {
        completed.add(item);
      }
    }
    const nodes = [];
    for (const ref of sortedStrings(actionByRef.keys())) {
      const action = actionByRef.get(ref);
      nodes.push({action_ref: ref, action_id: actionIdByRef.get(ref), topic_id: action.topic_id, actor: action.actor, kind: action.kind});
    }
    const sortedEdges = edges.slice().sort(function (a, b) {
      return compareCodePoints(a.source_action_id, b.source_action_id) || compareCodePoints(a.relation, b.relation) || compareCodePoints(a.target_action_id, b.target_action_id);
    });
    const sortedMissing = missingDependencies.slice().sort(function (a, b) {
      return compareCodePoints(a.action_ref, b.action_ref) || compareCodePoints(a.missing_target_ref, b.missing_target_ref);
    });
    const graphBasis = {
      profile: GRAPH_PROFILE,
      nodes: nodes,
      edges: sortedEdges,
      missing_dependencies: sortedMissing,
      cycle_action_refs: sortedStrings(cycleRefs)
    };
    return {
      validation_state: "ACCEPTED",
      profile: GRAPH_PROFILE,
      nodes: graphBasis.nodes,
      edges: graphBasis.edges,
      missing_dependencies: graphBasis.missing_dependencies,
      cycle_action_refs: graphBasis.cycle_action_refs,
      graph_root: identity("graph", GRAPH_PROFILE, graphBasis),
      action_by_ref: actionByRef,
      action_id_by_ref: actionIdByRef,
      action_entry_by_ref: actionEntryByRef
    };
  }

  function dependencyReadyMap(actionByRef, cycleRefs) {
    const memo = new Map();
    for (const startRef of sortedStrings(actionByRef.keys())) {
      if (memo.has(startRef)) {
        continue;
      }
      const path = [];
      const pathRefs = new Set();
      let current = startRef;
      let result = false;
      while (true) {
        if (memo.has(current)) {
          result = memo.get(current);
          break;
        }
        if (cycleRefs.has(current) || pathRefs.has(current)) {
          result = false;
          break;
        }
        const action = actionByRef.get(current);
        if (action.kind === "PROPOSE") {
          memo.set(current, true);
          result = true;
          break;
        }
        const targetRef = action.targets[0];
        if (!actionByRef.has(targetRef)) {
          memo.set(current, false);
          result = false;
          break;
        }
        path.push(current);
        pathRefs.add(current);
        current = targetRef;
      }
      for (let index = path.length - 1; index >= 0; index -= 1) {
        memo.set(path[index], result);
      }
    }
    return memo;
  }

  function evaluateParticipation(participation, endorsers) {
    const profile = participation.profile;
    const participantSet = new Set(participation.participants);
    const endorserSet = new Set(endorsers);
    const required = new Set(participation.required_endorsers);
    const threshold = participation.threshold;
    let satisfied;
    let missing;
    let surplus;
    if (profile === "NO_ENDORSEMENT_REQUIRED") {
      satisfied = true;
      missing = [];
      surplus = sortedStrings(endorserSet);
    } else if (profile === "SINGLE_DECLARED_ENDORSER") {
      satisfied = endorserSet.size >= 1;
      missing = satisfied ? [] : ["ONE_DECLARED_ENDORSER"];
      surplus = [];
    } else if (profile === "ALL_DECLARED_PARTICIPANTS") {
      missing = sortedStrings(Array.from(participantSet).filter(function (item) { return !endorserSet.has(item); }));
      surplus = sortedStrings(Array.from(endorserSet).filter(function (item) { return !participantSet.has(item); }));
      satisfied = !missing.length && !surplus.length;
    } else if (profile === "EXACT_DECLARED_PARTICIPANT_SET") {
      missing = sortedStrings(Array.from(required).filter(function (item) { return !endorserSet.has(item); }));
      surplus = sortedStrings(Array.from(endorserSet).filter(function (item) { return !required.has(item); }));
      satisfied = !missing.length && !surplus.length;
    } else {
      const missingCount = Math.max(0, threshold - endorserSet.size);
      missing = missingCount === 0 ? [] : ["ADDITIONAL_ENDORSERS_REQUIRED:" + missingCount];
      surplus = sortedStrings(Array.from(endorserSet).filter(function (item) { return !participantSet.has(item); }));
      satisfied = endorserSet.size >= threshold && !surplus.length;
    }
    return {
      profile: profile,
      participants: sortedStrings(participantSet),
      required_endorsers: sortedStrings(required),
      threshold: threshold,
      endorsers: sortedStrings(endorserSet),
      endorsement_count: endorserSet.size,
      missing: missing,
      surplus: surplus,
      satisfied: satisfied
    };
  }

  function makeTopicReceipt(topicId, actions, actionIdByRef, graph, context) {
    const actionByRef = new Map(actions.map(function (action) { return [action.action_ref, action]; }));
    const cycleRefs = new Set(graph.cycle_action_refs.filter(function (ref) { return actionByRef.has(ref); }));
    const missing = graph.missing_dependencies.filter(function (item) { return actionByRef.has(item.action_ref); });
    const readyMap = dependencyReadyMap(actionByRef, cycleRefs);
    const proposalRefs = sortedStrings(Array.from(actionByRef.keys()).filter(function (ref) {
      return PROPOSAL_KINDS.includes(actionByRef.get(ref).kind) && readyMap.get(ref);
    }));
    const supersededRefs = new Set();
    const withdrawnRefs = new Set();
    for (const ref of sortedStrings(actionByRef.keys())) {
      const action = actionByRef.get(ref);
      if (!readyMap.get(ref)) {
        continue;
      }
      if (action.kind === "AMEND") {
        supersededRefs.add(action.targets[0]);
      } else if (action.kind === "WITHDRAW") {
        withdrawnRefs.add(action.targets[0]);
      }
    }
    const defeatedRefs = new Set(Array.from(supersededRefs).concat(Array.from(withdrawnRefs)));
    const activeRefs = proposalRefs.filter(function (ref) { return !defeatedRefs.has(ref); });
    const endorsementsByTarget = new Map();
    const objectionsByTarget = new Map();
    const signalActions = new Map();
    function getSet(map, key) {
      if (!map.has(key)) {
        map.set(key, new Set());
      }
      return map.get(key);
    }
    function signalKey(target, actor) {
      return canonicalJson([target, actor]);
    }
    for (const ref of sortedStrings(actionByRef.keys())) {
      const action = actionByRef.get(ref);
      if (!readyMap.get(ref)) {
        continue;
      }
      if (action.kind === "ENDORSE") {
        const target = action.targets[0];
        getSet(endorsementsByTarget, target).add(action.actor);
        const key = signalKey(target, action.actor);
        if (!signalActions.has(key)) {
          signalActions.set(key, {target: target, actor: action.actor, items: []});
        }
        signalActions.get(key).items.push(["ENDORSE", ref]);
      } else if (action.kind === "OBJECT") {
        const target = action.targets[0];
        getSet(objectionsByTarget, target).add(action.actor);
        const key = signalKey(target, action.actor);
        if (!signalActions.has(key)) {
          signalActions.set(key, {target: target, actor: action.actor, items: []});
        }
        signalActions.get(key).items.push(["OBJECT", ref]);
      }
    }
    const signalConflicts = [];
    const signalEntries = Array.from(signalActions.values()).sort(function (a, b) {
      return compareCodePoints(a.target, b.target) || compareCodePoints(a.actor, b.actor);
    });
    for (const entry of signalEntries) {
      const kinds = new Set(entry.items.map(function (item) { return item[0]; }));
      if (kinds.has("ENDORSE") && kinds.has("OBJECT") && kinds.size === 2) {
        signalConflicts.push({
          target_action_ref: entry.target,
          actor: entry.actor,
          signal_action_refs: sortedStrings(entry.items.map(function (item) { return item[1]; }))
        });
      }
    }
    const activeSignalConflicts = signalConflicts.filter(function (item) { return activeRefs.includes(item.target_action_ref); });
    let state = null;
    let reasonCode = null;
    let resolvedActionRef = null;
    let resolvedActionId = null;
    let resolvedDeclaredValue = null;
    let participationResult = null;
    let activeEndorsers = [];
    let activeObjectors = [];
    if (cycleRefs.size) {
      state = "ABSTAIN";
      reasonCode = "DEPENDENCY_CYCLE";
    } else if (activeSignalConflicts.length) {
      state = "ABSTAIN";
      reasonCode = "PARTICIPANT_SIGNAL_CONFLICT";
    } else if (activeRefs.length > 1) {
      state = "ABSTAIN";
      reasonCode = "MULTIPLE_ACTIVE_PROPOSALS";
    } else if (missing.length) {
      state = "INCOMPLETE";
      reasonCode = "MISSING_DEPENDENCY";
    } else if (activeRefs.length === 0) {
      state = "INCOMPLETE";
      reasonCode = "NO_ACTIVE_PROPOSAL";
    } else {
      const activeRef = activeRefs[0];
      activeEndorsers = sortedStrings(endorsementsByTarget.get(activeRef) || []);
      activeObjectors = sortedStrings(objectionsByTarget.get(activeRef) || []);
      participationResult = evaluateParticipation(context.participation, activeEndorsers);
      if (activeObjectors.length) {
        state = "ABSTAIN";
        reasonCode = "ACTIVE_PROPOSAL_OBJECTED";
      } else if (participationResult.satisfied) {
        state = "RESOLVED";
        reasonCode = "ONE_ACTIVE_PROPOSAL_AND_PARTICIPATION_SATISFIED";
        resolvedActionRef = activeRef;
        resolvedActionId = actionIdByRef.get(activeRef);
        resolvedDeclaredValue = deepCopy(actionByRef.get(activeRef).declared_value);
      } else {
        state = "INCOMPLETE";
        reasonCode = "PARTICIPATION_INCOMPLETE";
      }
    }
    const actionSummaries = [];
    for (const ref of sortedStrings(actionByRef.keys())) {
      const action = actionByRef.get(ref);
      actionSummaries.push({
        action_ref: ref,
        action_id: actionIdByRef.get(ref),
        actor: action.actor,
        kind: action.kind,
        targets: Array.from(action.targets),
        dependency_ready: Boolean(readyMap.get(ref)),
        active_proposal: activeRefs.includes(ref),
        superseded: supersededRefs.has(ref),
        withdrawn: withdrawnRefs.has(ref),
        declared_value: deepCopy(action.declared_value)
      });
    }
    const receiptWithoutId = {
      profile: TOPIC_RECEIPT_PROFILE,
      ruleset_profile: RULESET_PROFILE,
      topic_id: topicId,
      state: state,
      reason_code: reasonCode,
      action_ids: sortedStrings(Array.from(actionByRef.keys()).map(function (ref) { return actionIdByRef.get(ref); })),
      active_action_refs: activeRefs,
      active_action_ids: sortedStrings(activeRefs.map(function (ref) { return actionIdByRef.get(ref); })),
      superseded_action_refs: sortedStrings(supersededRefs),
      withdrawn_action_refs: sortedStrings(withdrawnRefs),
      missing_dependencies: missing.slice().sort(function (a, b) { return compareCodePoints(a.action_ref, b.action_ref) || compareCodePoints(a.missing_target_ref, b.missing_target_ref); }),
      cycle_action_refs: sortedStrings(cycleRefs),
      signal_conflicts: signalConflicts,
      active_signal_conflicts: activeSignalConflicts,
      active_endorsers: activeEndorsers,
      active_objectors: activeObjectors,
      participation: participationResult,
      resolved_action_ref: resolvedActionRef,
      resolved_action_id: resolvedActionId,
      resolved_declared_value: resolvedDeclaredValue,
      actions: actionSummaries,
      execution_authority: EXECUTION_AUTHORITY
    };
    const receipt = deepCopy(receiptWithoutId);
    receipt.topic_receipt_id = identity("topic_receipt", TOPIC_RECEIPT_PROFILE, receiptWithoutId);
    return receipt;
  }

  function resolveTopics(evidence, graph, context) {
    const actionsByTopic = new Map();
    for (const entry of evidence.actions) {
      const action = entry.action;
      if (!actionsByTopic.has(action.topic_id)) {
        actionsByTopic.set(action.topic_id, []);
      }
      actionsByTopic.get(action.topic_id).push(action);
    }
    const receipts = [];
    for (const topicId of sortedStrings(actionsByTopic.keys())) {
      receipts.push(makeTopicReceipt(topicId, actionsByTopic.get(topicId), graph.action_id_by_ref, graph, context));
    }
    const counts = {RESOLVED: 0, INCOMPLETE: 0, ABSTAIN: 0};
    for (const receipt of receipts) {
      counts[receipt.state] += 1;
    }
    const rootBasis = {profile: TOPIC_RECEIPT_PROFILE, topic_receipt_ids: sortedStrings(receipts.map(function (receipt) { return receipt.topic_receipt_id; }))};
    return {receipts: receipts, state_counts: counts, topic_receipt_root: identity("topic_receipt_root", TOPIC_RECEIPT_PROFILE, rootBasis)};
  }

  function makeBoundaryReceipt(boundary, evidence) {
    const observedRefs = sortedStrings(evidence.observations.map(function (item) { return item.observation_ref; }));
    const expectedRefs = sortedStrings(boundary.expected_observation_refs);
    let state;
    let missingRefs;
    let unexpectedRefs;
    if (boundary.state === "OPEN") {
      state = "OPEN";
      missingRefs = [];
      unexpectedRefs = [];
    } else {
      const observedSet = new Set(observedRefs);
      const expectedSet = new Set(expectedRefs);
      missingRefs = sortedStrings(expectedRefs.filter(function (item) { return !observedSet.has(item); }));
      unexpectedRefs = sortedStrings(observedRefs.filter(function (item) { return !expectedSet.has(item); }));
      if (!missingRefs.length && !unexpectedRefs.length) {
        state = "SEALED";
      } else if (missingRefs.length && !unexpectedRefs.length) {
        state = "INCOMPLETE";
      } else {
        state = "CONFLICT";
      }
    }
    const receiptWithoutId = {
      profile: BOUNDARY_RECEIPT_PROFILE,
      declared_state: boundary.state,
      state: state,
      observed_observation_refs: observedRefs,
      expected_observation_refs: expectedRefs,
      missing_observation_refs: missingRefs,
      unexpected_observation_refs: unexpectedRefs,
      observed_observation_set_id: evidence.observation_set_id
    };
    const receipt = deepCopy(receiptWithoutId);
    receipt.boundary_receipt_id = identity("boundary_receipt", BOUNDARY_RECEIPT_PROFILE, receiptWithoutId);
    return receipt;
  }

  function publicTopicSummary(receipt) {
    return {
      topic_id: receipt.topic_id,
      state: receipt.state,
      reason_code: receipt.reason_code,
      active_action_ids: Array.from(receipt.active_action_ids),
      resolved_action_id: receipt.resolved_action_id,
      active_endorser_count: receipt.active_endorsers.length,
      active_objector_count: receipt.active_objectors.length,
      participation_satisfied: receipt.participation === null ? null : receipt.participation.satisfied,
      topic_receipt_id: receipt.topic_receipt_id,
      execution_authority: EXECUTION_AUTHORITY
    };
  }

  function buildPublicReceipt(contextResult, evidence, graph, topics, boundaryReceipt, conversationResolutionId) {
    const topicSummaries = topics.receipts.map(publicTopicSummary);
    const receiptWithoutId = {
      profile: PUBLIC_RECEIPT_PROFILE,
      version: VERSION,
      architecture_profile: ARCHITECTURE_PROFILE,
      ruleset_profile: RULESET_PROFILE,
      context_id: contextResult.context_id,
      conversation_id: contextResult.context.conversation_id,
      purpose_id: contextResult.context.purpose_id,
      action_set_id: evidence.action_set_id,
      graph_root: graph.graph_root,
      topic_receipt_root: topics.topic_receipt_root,
      boundary_receipt_id: boundaryReceipt.boundary_receipt_id,
      boundary_state: boundaryReceipt.state,
      state_counts: deepCopy(topics.state_counts),
      topic_summaries: topicSummaries,
      conversation_resolution_id: conversationResolutionId,
      execution_authority: EXECUTION_AUTHORITY
    };
    const receipt = deepCopy(receiptWithoutId);
    receipt.public_receipt_id = identity("public_receipt", PUBLIC_RECEIPT_PROFILE, receiptWithoutId);
    return receipt;
  }

  function bundleWithoutSelfVerification(bundle) {
    const result = deepCopy(bundle);
    delete result.self_verification;
    return result;
  }

  function resolveConversationBundle(context, observations, boundary, runSelfVerify) {
    const intakeErrors = [];
    if (!isPlainObject(context)) {
      intakeErrors.push("context: must be an object");
    }
    if (!Array.isArray(observations)) {
      intakeErrors.push("observations: must be an array");
    }
    if (!isPlainObject(boundary)) {
      intakeErrors.push("boundary: must be an object");
    }
    if (intakeErrors.length) {
      return makeRefusal(intakeErrors);
    }
    const contextResult = prepareContext(context);
    const boundaryErrors = validateBoundary(boundary);
    if (contextResult.validation_state === "REFUSED" || boundaryErrors.length) {
      const errors = [];
      if (contextResult.validation_state === "REFUSED") {
        errors.push.apply(errors, contextResult.errors);
      }
      errors.push.apply(errors, boundaryErrors);
      return makeRefusal(errors);
    }
    const canonicalBoundaryRecord = canonicalBoundary(boundary);
    const evidence = prepareObservations(observations, contextResult.context);
    if (evidence.validation_state === "REFUSED") {
      return makeRefusal(evidence.errors);
    }
    const graph = buildGraph(evidence, contextResult.context);
    if (graph.validation_state === "REFUSED") {
      return makeRefusal(graph.errors);
    }
    const topics = resolveTopics(evidence, graph, contextResult.context);
    const boundaryReceipt = makeBoundaryReceipt(canonicalBoundaryRecord, evidence);
    const resolutionBasis = {
      profile: PRIVATE_BUNDLE_PROFILE,
      version: VERSION,
      architecture_profile: ARCHITECTURE_PROFILE,
      ruleset_profile: RULESET_PROFILE,
      context_id: contextResult.context_id,
      action_set_id: evidence.action_set_id,
      graph_root: graph.graph_root,
      topic_receipt_root: topics.topic_receipt_root,
      boundary_receipt_id: boundaryReceipt.boundary_receipt_id
    };
    const conversationResolutionId = identity("conversation_resolution", PRIVATE_BUNDLE_PROFILE, resolutionBasis);
    const publicReceipt = buildPublicReceipt(contextResult, evidence, graph, topics, boundaryReceipt, conversationResolutionId);
    const bundleBasis = {
      profile: PRIVATE_BUNDLE_PROFILE,
      conversation_resolution_id: conversationResolutionId,
      observation_set_id: evidence.observation_set_id,
      public_receipt_id: publicReceipt.public_receipt_id
    };
    const privateBundleId = identity("private_bundle", PRIVATE_BUNDLE_PROFILE, bundleBasis);
    const publicGraph = {
      profile: graph.profile,
      nodes: deepCopy(graph.nodes),
      edges: deepCopy(graph.edges),
      missing_dependencies: deepCopy(graph.missing_dependencies),
      cycle_action_refs: deepCopy(graph.cycle_action_refs),
      graph_root: graph.graph_root
    };
    const bundle = {
      profile: PRIVATE_BUNDLE_PROFILE,
      version: VERSION,
      result: "ACCEPTED",
      architecture_profile: ARCHITECTURE_PROFILE,
      ruleset_profile: RULESET_PROFILE,
      execution_authority: EXECUTION_AUTHORITY,
      inputs: {context: deepCopy(context), observations: deepCopy(observations), boundary: deepCopy(boundary)},
      context: contextResult,
      evidence: evidence,
      graph: publicGraph,
      topics: topics,
      boundary: boundaryReceipt,
      public_receipt: publicReceipt,
      conversation_resolution_id: conversationResolutionId,
      private_bundle_id: privateBundleId
    };
    if (runSelfVerify !== false) {
      bundle.self_verification = verifyBundle(bundle);
    }
    return bundle;
  }

  function verifyBundle(bundle) {
    if (!isPlainObject(bundle)) {
      return {profile: VERIFICATION_PROFILE, valid: false, errors: ["bundle must be an object"]};
    }
    if (bundle.result !== "ACCEPTED") {
      return {profile: VERIFICATION_PROFILE, valid: false, errors: ["only accepted bundles are verifiable"]};
    }
    const inputs = bundle.inputs;
    if (!isPlainObject(inputs)) {
      return {profile: VERIFICATION_PROFILE, valid: false, errors: ["missing inputs"]};
    }
    const expected = resolveConversationBundle(inputs.context, inputs.observations, inputs.boundary, false);
    const errors = [];
    if (expected.result !== "ACCEPTED") {
      errors.push("embedded inputs do not reconstruct an accepted bundle");
    } else if (canonicalJson(bundleWithoutSelfVerification(bundle)) !== canonicalJson(expected)) {
      for (const field of ["conversation_resolution_id", "private_bundle_id"]) {
        if (bundle[field] !== expected[field]) {
          errors.push(field + " mismatch");
        }
      }
      const nestedChecks = [
        ["context", "context_id"],
        ["evidence", "action_set_id"],
        ["evidence", "observation_set_id"],
        ["graph", "graph_root"],
        ["topics", "topic_receipt_root"],
        ["boundary", "boundary_receipt_id"],
        ["public_receipt", "public_receipt_id"]
      ];
      for (const pair of nestedChecks) {
        if (!bundle[pair[0]] || !expected[pair[0]] || bundle[pair[0]][pair[1]] !== expected[pair[0]][pair[1]]) {
          errors.push(pair[0] + "." + pair[1] + " mismatch");
        }
      }
      if (!errors.length) {
        errors.push("bundle content mismatch");
      }
    }
    return {
      profile: VERIFICATION_PROFILE,
      valid: !errors.length,
      errors: errors,
      expected_conversation_resolution_id: expected.conversation_resolution_id,
      expected_private_bundle_id: expected.private_bundle_id,
      expected_public_receipt_id: expected.public_receipt ? expected.public_receipt.public_receipt_id : undefined
    };
  }

  function mergeObservationSets() {
    const observationSets = Array.from(arguments);
    const merged = new Map();
    const observationRefs = new Map();
    const actionRefs = new Map();
    for (const observationSet of observationSets) {
      if (!Array.isArray(observationSet)) {
        throw new Error("observation sets must be arrays");
      }
      for (const observation of observationSet) {
        const errors = validateObservation(observation);
        if (errors.length) {
          throw new Error("cannot merge invalid observation: " + errors.join("; "));
        }
        const canonical = canonicalObservation(observation);
        const oid = observationId(canonical);
        const observationRef = canonical.observation_ref;
        const aid = actionId(canonical.action);
        const actionRef = canonical.action.action_ref;
        if (observationRefs.has(observationRef) && observationRefs.get(observationRef) !== oid) {
          throw new Error("observation_ref content conflict: " + observationRef);
        }
        if (actionRefs.has(actionRef) && actionRefs.get(actionRef) !== aid) {
          throw new Error("action_ref content conflict: " + actionRef);
        }
        observationRefs.set(observationRef, oid);
        actionRefs.set(actionRef, aid);
        merged.set(oid, canonical);
      }
    }
    return sortedStrings(merged.keys()).map(function (oid) { return deepCopy(merged.get(oid)); });
  }

  function resolveDocument(document, runSelfVerify) {
    if (!isPlainObject(document)) {
      return makeRefusal(["input: must be an object"]);
    }
    const fields = exactFields(document, ["context", "observations", "boundary"], "input");
    if (fields.length) {
      return makeRefusal(fields);
    }
    return resolveConversationBundle(document.context, document.observations, document.boundary, runSelfVerify);
  }

  function topicStateMap(bundle) {
    const result = {};
    const receipts = bundle && bundle.topics && Array.isArray(bundle.topics.receipts) ? bundle.topics.receipts : [];
    for (const receipt of receipts) {
      result[receipt.topic_id] = receipt.state;
    }
    return result;
  }

  function topicReasonMap(bundle) {
    const result = {};
    const receipts = bundle && bundle.topics && Array.isArray(bundle.topics.receipts) ? bundle.topics.receipts : [];
    for (const receipt of receipts) {
      result[receipt.topic_id] = receipt.reason_code;
    }
    return result;
  }

  function topicValueMap(bundle) {
    const result = {};
    const receipts = bundle && bundle.topics && Array.isArray(bundle.topics.receipts) ? bundle.topics.receipts : [];
    for (const receipt of receipts) {
      result[receipt.topic_id] = deepCopy(receipt.resolved_declared_value);
    }
    return result;
  }

  function bundleCanonicalSha256(bundle) {
    return sha256Text(canonicalJson(bundleWithoutSelfVerification(bundle)));
  }

  return {
    VERSION: VERSION,
    LIMITS: {max_graph_depth: MAX_GRAPH_DEPTH},
    PROFILES: {
      architecture: ARCHITECTURE_PROFILE,
      ruleset: RULESET_PROFILE,
      text: TEXT_PROFILE,
      context: CONTEXT_SCHEMA,
      participation: PARTICIPATION_SCHEMA,
      action: ACTION_SCHEMA,
      observation: OBSERVATION_SCHEMA,
      boundary: BOUNDARY_SCHEMA,
      graph: GRAPH_PROFILE,
      topic_receipt: TOPIC_RECEIPT_PROFILE,
      boundary_receipt: BOUNDARY_RECEIPT_PROFILE,
      public_receipt: PUBLIC_RECEIPT_PROFILE,
      private_bundle: PRIVATE_BUNDLE_PROFILE
    },
    StrictJSONError: StrictJSONError,
    DuplicateKeyError: DuplicateKeyError,
    canonicalJson: canonicalJson,
    canonicalArtifactText: canonicalArtifactText,
    sha256Text: sha256Text,
    identity: identity,
    strictJsonLoads: strictJsonLoads,
    validateContext: validateContext,
    validateObservation: validateObservation,
    validateBoundary: validateBoundary,
    canonicalContext: canonicalContext,
    canonicalAction: canonicalAction,
    canonicalObservation: canonicalObservation,
    canonicalBoundary: canonicalBoundary,
    contextId: contextId,
    actionId: actionId,
    observationId: observationId,
    prepareObservations: prepareObservations,
    buildGraph: buildGraph,
    evaluateParticipation: evaluateParticipation,
    resolveConversationBundle: resolveConversationBundle,
    resolveDocument: resolveDocument,
    verifyBundle: verifyBundle,
    mergeObservationSets: mergeObservationSets,
    topicStateMap: topicStateMap,
    topicReasonMap: topicReasonMap,
    topicValueMap: topicValueMap,
    bundleWithoutSelfVerification: bundleWithoutSelfVerification,
    bundleCanonicalSha256: bundleCanonicalSha256,
    deepCopy: deepCopy,
    compareCodePoints: compareCodePoints
  };
}));
