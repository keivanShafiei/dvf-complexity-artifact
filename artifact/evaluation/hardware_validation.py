import os, sys
def main():
    required = {"OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "DVF_STRICT_NUMERICS": "1"}
    ok = True
    for k, v in required.items():
        if os.environ.get(k) != v:
            print(f"WARN: {k} != {v} (got {os.environ.get(k)})")
            ok = False
    if not ok:
        sys.exit("Environment does not satisfy reproducibility policy.")
    print("Hardware/environment OK.")
if __name__ == "__main__":
    main()
