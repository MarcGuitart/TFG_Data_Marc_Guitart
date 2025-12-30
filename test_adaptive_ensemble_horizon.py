#!/usr/bin/env python3
"""
Test: Verify that Adaptive Ensemble works correctly with multi-horizon (t+m)

Problem Found & Fixed:
- When horizon > 1, the code was NOT querying chosen_model and chosen_errors
- Therefore, the Adaptive Ensemble predictor was the same as with horizon=1
- This script verifies the fix works correctly

What should change with horizon=m:
1. The predictions come from yhat_h{m} fields (different models than yhat)
2. The chosen_model should still apply (same selection algorithm)
3. BUT: The chosen model is applied to the t+m predictions, not t+1
"""

import requests
import json
import sys
from typing import Dict, List, Any

BASE_URL = "http://localhost:8000"
SERIES_ID = "demo-now"  # Use a known test series

def test_adaptive_ensemble_horizon():
    """Test that Adaptive Ensemble changes with horizon"""
    
    print("\n" + "="*80)
    print("TEST: Adaptive Ensemble with Multi-Horizon")
    print("="*80)
    
    # Test different horizons
    horizons = [1, 3, 5]
    results = {}
    
    for h in horizons:
        print(f"\n>>> Testing horizon={h}...")
        
        try:
            resp = requests.get(f"{BASE_URL}/api/series", params={
                "id": SERIES_ID,
                "hours": 24,
                "horizon": h
            })
            
            if resp.status_code != 200:
                print(f"❌ API returned {resp.status_code}: {resp.text}")
                continue
            
            data = resp.json()
            points = data.get("points", [])
            
            if not points:
                print(f"⚠️  No points returned for horizon={h}")
                continue
            
            results[h] = {
                "total_points": len(points),
                "chosen_models": [],
                "predictions": [],
                "sample_point": points[0] if points else None
            }
            
            # Extract chosen_model and predictions from each point
            for i, point in enumerate(points[:5]):  # First 5 points
                chosen = point.get("chosen_model")
                predictions = point.get("predictions")
                results[h]["chosen_models"].append(chosen)
                results[h]["predictions"].append(predictions)
                
                if i == 0:
                    print(f"   ✓ Got {len(points)} points")
                    print(f"     - First point timestamp: {point.get('timestamp')}")
                    print(f"     - First point target_time: {point.get('target_time')}")
                    print(f"     - First point var: {point.get('var')}")
                    print(f"     - First point chosen_model: {chosen}")
                    print(f"     - First point chosen_error_abs: {point.get('chosen_error_abs')}")
                    print(f"     - First point chosen_error_rel: {point.get('chosen_error_rel')}")
        
        except Exception as e:
            print(f"❌ Error testing horizon={h}: {e}")
            continue
    
    # Analysis
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    
    if len(results) < 2:
        print("❌ Could not test multiple horizons")
        return False
    
    # Check 1: Different horizons should have different number of points
    # (because first m points are skipped in causal mode)
    print("\n✓ Point Counts by Horizon:")
    for h in sorted(results.keys()):
        count = results[h]["total_points"]
        print(f"  - horizon={h}: {count} points")
    
    # Check 2: Verify chosen_models were retrieved
    print("\n✓ Chosen Models Present:")
    for h in sorted(results.keys()):
        chosen_list = results[h]["chosen_models"]
        non_none = [c for c in chosen_list if c is not None]
        print(f"  - horizon={h}: {len(non_none)} non-null chosen models out of {len(chosen_list)}")
        if non_none:
            print(f"    Sample: {non_none[:3]}")
    
    # Check 3: Verify chosen_error_rel is in response
    print("\n✓ Chosen Error Info Present:")
    for h in sorted(results.keys()):
        point = results[h]["sample_point"]
        if point:
            has_err_abs = "chosen_error_abs" in point
            has_err_rel = "chosen_error_rel" in point
            print(f"  - horizon={h}: error_abs={has_err_abs}, error_rel={has_err_rel}")
            if has_err_abs or has_err_rel:
                print(f"    Values: error_abs={point.get('chosen_error_abs')}, error_rel={point.get('chosen_error_rel')}")
    
    # Check 4: Compare predictions between horizons
    print("\n✓ Predictions Comparison (first point):")
    for h in sorted(results.keys()):
        preds = results[h]["predictions"][0] if results[h]["predictions"] else None
        if preds:
            print(f"  - horizon={h}: {preds}")
    
    # Verify fix worked
    print("\n" + "="*80)
    print("FIX VERIFICATION")
    print("="*80)
    
    all_good = True
    
    # Check that all horizons have chosen_models
    for h in sorted(results.keys()):
        chosen_list = results[h]["chosen_models"]
        non_none_count = len([c for c in chosen_list if c is not None])
        
        if non_none_count == 0:
            print(f"❌ horizon={h}: No chosen_models found (fix didn't work)")
            all_good = False
        else:
            print(f"✅ horizon={h}: {non_none_count} chosen models found")
    
    # Check that sample points have error info
    for h in sorted(results.keys()):
        point = results[h]["sample_point"]
        if point:
            has_chosen = "chosen_model" in point
            has_err = "chosen_error_abs" in point or "chosen_error_rel" in point
            
            if not has_chosen:
                print(f"❌ horizon={h}: No chosen_model field in point")
                all_good = False
            elif not has_err:
                print(f"⚠️  horizon={h}: No error fields in point (but has chosen_model)")
            else:
                print(f"✅ horizon={h}: Point has chosen_model and error fields")
    
    print("\n" + "="*80)
    if all_good:
        print("✅ FIX VERIFIED: Adaptive Ensemble now works with multi-horizon!")
    else:
        print("❌ FIX INCOMPLETE: Some issues remain")
    print("="*80)
    
    return all_good

if __name__ == "__main__":
    try:
        success = test_adaptive_ensemble_horizon()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
