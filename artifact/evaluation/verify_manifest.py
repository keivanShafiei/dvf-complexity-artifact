import argparse
import hashlib
import json
import pathlib
import sys

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--targets", nargs="+", required=True)
    a = ap.parse_args()
    m = json.load(open(a.manifest))["checksums"]
    fails = 0
    for rel, expected in m.items():
        if not pathlib.Path(rel).exists():
            print(f"MISSING {rel}")
            fails += 1
            continue
        got = sha256(rel)
        if got != expected:
            print(f"MISMATCH {rel}")
            fails += 1
    if fails:
        print(f"Verification failed: {fails} file(s) mismatched or missing.")
        sys.exit(1)
    else:
        print("✅ All checksums verified successfully.")

if __name__ == "__main__":
    main()
