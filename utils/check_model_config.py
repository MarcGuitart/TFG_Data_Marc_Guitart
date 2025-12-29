#!/usr/bin/env python3
"""
Quick test to verify model names from config
"""
import json

# Load config
with open("/Users/marcg/Desktop/projectes/TFG_Agente_Data/services/agent/hypermodel/model_config.json", "r") as f:
    cfg = json.load(f)

print("=" * 80)
print("MODEL CONFIGURATION LOADED")
print("=" * 80)
print()

model_names = []
for i, m in enumerate(cfg.get("models", []), 1):
    mtype = m["type"]
    name = m["name"]
    model_names.append(name)
    print(f"{i}. Type: {mtype:15s} → Name: {name:15s}")

print()
print(f"Total models in config: {len(model_names)}")
print(f"Model names: {model_names}")
print()

# Frontend expects
frontend_expected = ["linear", "poly", "alphabeta", "kalman", "naive"]
print("Frontend expects:", frontend_expected)
print()

# Check
missing_from_config = set(frontend_expected) - set(model_names)
extra_in_config = set(model_names) - set(frontend_expected)

if missing_from_config:
    print(f"❌ MISSING FROM CONFIG: {missing_from_config}")
if extra_in_config:
    print(f"❌ EXTRA IN CONFIG (not in frontend): {extra_in_config}")
if not missing_from_config and not extra_in_config:
    print("✅ PERFECT MATCH between config and frontend expectations")
