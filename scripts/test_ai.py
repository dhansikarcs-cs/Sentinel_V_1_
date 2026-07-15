import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'software'))

from ai_kernel_ import summarize_journal

print("Test 1: Patient mode")
result = summarize_journal("Feeling okay today, had a good walk.", "patient")
print(f"  text:    {result.get('text', '')[:80]}")
print(f"  source:  {result.get('source', '')}")
print(f"  emotions: {result.get('emotions', '')}")

print("\nTest 2: Clinical mode")
result2 = summarize_journal("Patient reported anxiety about work deadlines.", "clinical")
print(f"  text:    {result2.get('text', '')[:80]}")
print(f"  source:  {result2.get('source', '')}")
print(f"  emotions: {result2.get('emotions', '')}")

print("\nTest 3: Crisis risk")
from ai_kernel_ import assess_crisis_risk
risk = assess_crisis_risk("I feel completely hopeless. Nothing matters anymore.")
print(f"  risk_score: {risk.get('risk_score')}")
print(f"  triggered:  {risk.get('triggered')}")
print(f"  reasoning:  {risk.get('reasoning', '')[:80]}")
