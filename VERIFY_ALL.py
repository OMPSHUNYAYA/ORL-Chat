#!/usr/bin/env python3

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HASH_PATTERN = re.compile(r"^([0-9a-f]{64})  (.+)$")


def run_stage(command):
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    try:
        completed = subprocess.run(command, cwd=ROOT, env=environment)
    except OSError as exc:
        print("ERROR: unable to run " + str(command[0]) + ": " + str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def verify_hashes():
    manifest = ROOT / "hashes" / "SHA256SUMS.txt"
    valid = True
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = HASH_PATTERN.fullmatch(line)
        if not match:
            valid = False
            continue
        expected, relative = match.groups()
        path = ROOT / Path(relative)
        if not path.is_file():
            print("MISSING: " + relative)
            valid = False
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            print("FAIL: " + relative)
            valid = False
    print("SHA-256 selected-file verification: " + ("PASS" if valid else "FAIL"))
    if not valid:
        raise SystemExit(1)


def main():
    python = sys.executable
    stages = [
        [python, "-B", "demo/ORL_Chat_Reference_Kernel_v2_0_0.py", "--self-test"],
        [python, "-B", "verifier/ORL_Chat_Independent_Verifier_v2_0_0.py", "--self-test"],
        [python, "-B", "verifier/ORL_Chat_Independent_Verifier_v2_0_0.py", "--verify-corpus", "corpus/ORL_Chat_Frozen_Corpus_Manifest_v2_0_0.json", "--strict-canonical"],
        [python, "-B", "verifier/ORL_Chat_Cross_Language_Vector_Generator_v2_0_0.py", "--verify-existing"],
        ["node", "verifier/ORL_Chat_Browser_Parity_Verifier_v2_0_0.js", "--self-test"],
        [python, "-B", "verifier/ORL_Chat_Cross_Language_Cross_Check_v2_0_0.py", "--all-examples", "--receipt-output", "VERIFY/ORL_Chat_Cross_Implementation_Receipt_v2_0_0.json"],
        [python, "-B", "verifier/ORL_Chat_Cross_Language_Cross_Check_v2_0_0.py", "--all-parser-cases", "--receipt-output", "VERIFY/ORL_Chat_Parser_Parity_Receipt_v2_0_0.json"],
        [python, "-B", "verifier/ORL_Chat_Seeded_Property_Verifier_v2_0_0.py", "--seed", "20260731", "--cases", "32", "--receipt-output", "VERIFY/ORL_Chat_Seeded_Property_Receipt_v2_0_0.json"],
        [python, "-B", "demo/ORL_Chat_Conversation_State_Capsule_v2_0_0.py", "--self-test"],
        [python, "-B", "verifier/ORL_Chat_Capsule_Vector_Generator_v2_0_0.py"],
        [python, "-B", "verifier/ORL_Chat_C3_Assurance_Verifier_v2_0_0.py", "--self-test", "--write-report"],
        ["node", "verifier/ORL_Chat_Capsule_Parity_Verifier_v2_0_0.js", "--self-test"],
    ]
    for stage in stages:
        run_stage(stage)
    verify_hashes()
    print("ORL-Chat v2.0.0 complete verification: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
