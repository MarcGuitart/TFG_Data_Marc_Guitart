#!/usr/bin/env python3
"""
Debug script to check what model names are being stored in InfluxDB and what the frontend expects
"""

import json
import sys

# Frontend expects
frontend_expected = ["linear", "poly", "alphabeta", "kalman", "naive"]

# What the backend writes (from window_collector):
# It writes whatever is in enriched["hyper_models"] which comes from preds_by_model

# What the agent sends depends on what the models return
# Let me check the agent models file

print("=" * 80)
print("DEBUG: Model Names Mismatch Analysis")
print("=" * 80)
print()

print("✅ FRONTEND EXPECTS (from constants/models.js):")
print(f"   {frontend_expected}")
print()

print("📝 BACKEND WRITES (from window_collector):")
print("   Whatever is in enriched['hyper_models'] dict keys")
print()

print("🔍 INVESTIGATION POINTS:")
print()
print("1. Agent's hyper_models key from preds_by_model")
print("   - This comes from HyperModel.predict()")
print("   - Returns dict with model names as keys")
print()

print("2. Window Collector receives and writes:")
print("   - For each key in enriched['hyper_models']")
print("   - Writes to InfluxDB with tag 'model' = key")
print()

print("3. Orchestrator queries back:")
print("   - Gets model names from the 'model' tag in InfluxDB")
print("   - Builds yhat_by_model dict")
print()

print("4. Frontend counts:")
print("   - Iterates points[].keys()")
print("   - Checks if key in ALL_MODELS list")
print("   - If yes, adds to modelKeys set")
print()

print("⚠️  LIKELY ISSUE:")
print("   If a model is stored with a different name in InfluxDB,")
print("   the frontend won't recognize it and won't count it.")
print()
print("   Example: if stored as 'base' but frontend expects 'naive'")
print()

print("=" * 80)
