# artifact/evaluation/generate_manifest.py
import hashlib
import json
import glob
from datetime import datetime

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    files = []
    files.extend(glob.glob("figures/*.pdf"))
    files.extend(glob.glob("tables/*.tex"))
    files.extend(glob.glob("experiments/data/results/*.json"))
    
    manifest = {
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "checksums": {f: sha256_file(f) for f in sorted(files)}
    }
    
    with open("artifact/reproducibility_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    main()
