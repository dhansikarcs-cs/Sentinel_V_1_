"""Run all tests."""
import os
import sys
import subprocess
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if __name__ == "__main__":
    test_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["SENTINEL_DB_PATH"] = tempfile.mktemp(suffix=".db")

    test_files = [
        os.path.join(test_dir, f)
        for f in os.listdir(test_dir)
        if f.startswith("test_") and f.endswith(".py") and f != "test_all.py"
    ]

    results = {"passed": 0, "failed": 0, "errors": []}
    for tf in sorted(test_files):
        name = os.path.basename(tf)
        print(f"\n{'='*60}")
        print(f"  Running: {name}")
        print(f"{'='*60}")
        result = subprocess.run([sys.executable, "-m", "pytest", tf, "-v", "--tb=short", "-x"],
                                capture_output=True, text=True, cwd=os.path.join(test_dir, ".."))
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        if result.returncode != 0:
            print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
            results["failed"] += 1
            results["errors"].append(name)
        else:
            results["passed"] += 1

    total = results["passed"] + results["failed"]
    print(f"\n{'='*60}")
    print(f"  Results: {results['passed']}/{total} passed")
    if results["failed"]:
        print(f"  Failed: {', '.join(results['errors'])}")
    print(f"{'='*60}")
    sys.exit(1 if results["failed"] else 0)