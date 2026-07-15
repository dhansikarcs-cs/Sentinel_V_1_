"""Test all import chains for the journal tab."""
import sys, os
os.environ["SENTINEL_DB_BACKEND"] = "sqlite"
os.chdir(os.path.join(os.path.dirname(__file__), "software"))
sys.path.insert(0, ".")

# This is the chain that patient_portal_ uses
try:
    from patient_journal_ import render_patient_journal
    print("render_patient_journal imported OK")
except Exception as e:
    print(f"IMPORT FAILED: {e}")
    import traceback
    traceback.print_exc()

# Check that patient_shared_ imports fine
try:
    from patient_shared_ import safe as safe_fn
    print("patient_shared_.safe imported OK")
except Exception as e:
    print(f"patient_shared_ IMPORT FAILED: {e}")
