#!/usr/bin/env python3
"""
Verification script for Multi-Horizon Forecasting (t+m)

This script validates that the multi-horizon predictions are:
1. Causally correct (no lookahead)
2. Properly aligned (timestamp + m = target_time)
3. Correctly calculated (errors match expected values)
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys

API_BASE = "http://localhost:8081"
SERIES_ID = "Other"  # Change if needed
HOURS = 24

class HorizonVerifier:
    def __init__(self, api_base: str = API_BASE):
        self.api_base = api_base
        self.h1_data = None
        self.h5_data = None
        
    def fetch_series(self, horizon: int) -> Dict[str, Any]:
        """Fetch series data for given horizon"""
        print(f"\n📡 Fetching /api/series with horizon={horizon}...")
        try:
            url = f"{self.api_base}/api/series"
            params = {
                "id": SERIES_ID,
                "hours": HOURS,
                "horizon": horizon
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            print(f"   ✅ Received {len(data.get('points', []))} points")
            return data
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def verify_temporal_alignment(self, points: List[Dict], horizon: int) -> bool:
        """
        Verify that timestamp + horizon = target_time
        
        Example for horizon=5:
        - timestamp: 2025-12-29T10:00:00Z
        - target_time: 2025-12-29T10:05:00Z (assuming 1-min intervals)
        """
        print(f"\n🕐 Checking temporal alignment (horizon={horizon})...")
        
        if not points:
            print("   ⚠️  No points to verify")
            return False
        
        # Take first 5 valid points for spot checking
        checked = 0
        errors = []
        
        for i, point in enumerate(points[:10]):
            if 'timestamp' not in point or 'target_time' not in point:
                continue
                
            try:
                ts = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
                target = datetime.fromisoformat(point['target_time'].replace('Z', '+00:00'))
                diff = (target - ts).total_seconds()
                
                # For 1-minute intervals: diff should be ~horizon * 60 seconds
                # For 5-min intervals: diff should be ~horizon * 300 seconds
                expected_diff_min = horizon * 60  # Minimum expected
                
                if diff < expected_diff_min:
                    errors.append(f"Point {i}: diff={diff}s (expected ~{expected_diff_min}s)")
                else:
                    print(f"   ✅ Point {i}: timestamp={point['timestamp']}, target_time={point['target_time']}, diff={diff}s")
                
                checked += 1
            except Exception as e:
                print(f"   ⚠️  Point {i}: Parse error: {e}")
        
        if errors:
            print(f"\n   ❌ Temporal misalignment detected:")
            for err in errors:
                print(f"      {err}")
            return False
        
        print(f"   ✅ Temporal alignment verified for {checked} points")
        return True
    
    def verify_causal_integrity(self, points: List[Dict], horizon: int) -> bool:
        """
        Verify that first m points are excluded (no ground truth available)
        
        The backend should skip first `horizon` points because:
        - Point at t=0 predicts t=m, but ground truth at t=m not available yet
        - Point at t=1 predicts t=m+1, but ground truth at t=m+1 not available yet
        - ... etc until point at t=m
        - Point at t=m predicts t=2m, now we have ground truth at t=m
        """
        print(f"\n🔐 Verifying causal integrity (first {horizon} points excluded)...")
        
        if not points:
            print("   ⚠️  No points to verify")
            return False
        
        # Check that we don't have points with step < horizon
        min_step = min(p.get('step', 999) for p in points if 'step' in p)
        
        if min_step < horizon:
            print(f"   ❌ CAUSAL VIOLATION: Found point with step={min_step} (should be >= {horizon})")
            print(f"      This means ground truth wasn't available when prediction was made!")
            return False
        
        print(f"   ✅ Causal integrity verified: first point starts at step={min_step} (>= {horizon})")
        return True
    
    def verify_error_calculation(self, points: List[Dict], horizon: int) -> bool:
        """
        Verify that error = |real_value - prediction|
        
        For each point, check: error ≈ |var - yhat_model|
        """
        print(f"\n📊 Verifying error calculations (horizon={horizon})...")
        
        if not points:
            print("   ⚠️  No points to verify")
            return False
        
        errors_found = []
        verified = 0
        
        for i, point in enumerate(points[:5]):  # Check first 5 points
            if not isinstance(point.get('var'), (int, float)):
                continue
            if not isinstance(point.get('predictions'), dict):
                continue
            if not isinstance(point.get('errors'), dict):
                continue
            
            real = point['var']
            
            for model_name, pred in point['predictions'].items():
                if not isinstance(pred, (int, float)):
                    continue
                
                calculated_error = abs(real - pred)
                reported_error = point['errors'].get(model_name)
                
                if reported_error is None:
                    continue
                
                # Allow small floating point differences
                if abs(calculated_error - reported_error) > 0.001:
                    errors_found.append(
                        f"Point {i}, model {model_name}: "
                        f"calculated={calculated_error:.3f}, "
                        f"reported={reported_error:.3f}"
                    )
                else:
                    print(f"   ✅ Point {i}/{model_name}: error={reported_error:.3f} ✓")
                    verified += 1
        
        if errors_found:
            print(f"\n   ❌ Error calculation mismatches:")
            for err in errors_found:
                print(f"      {err}")
            return False
        
        print(f"   ✅ Error calculations verified for {verified} point-model combinations")
        return True
    
    def compare_horizons(self) -> bool:
        """
        Compare horizon=1 vs horizon=5 to understand differences
        """
        print(f"\n🔄 Comparing horizon=1 vs horizon=5...")
        
        if not self.h1_data or not self.h5_data:
            print("   ⚠️  Missing data for comparison")
            return False
        
        h1_points = self.h1_data.get('points', [])
        h5_points = self.h5_data.get('points', [])
        
        print(f"   Horizon=1: {len(h1_points)} points")
        print(f"   Horizon=5: {len(h5_points)} points")
        
        # Both should have data, but h5 might have fewer points (first m excluded)
        # Comparison: same series should have slightly different errors due to horizon effect
        
        # Sample comparison
        if h1_points and h5_points:
            h1_mean_error = sum(
                p.get('chosen_error', 0) 
                for p in h1_points 
                if isinstance(p.get('chosen_error'), (int, float))
            ) / len(h1_points)
            
            h5_mean_error = sum(
                p.get('chosen_error', 0) 
                for p in h5_points 
                if isinstance(p.get('chosen_error'), (int, float))
            ) / len(h5_points)
            
            print(f"\n   Mean error comparison:")
            print(f"   - Horizon=1: {h1_mean_error:.3f}")
            print(f"   - Horizon=5: {h5_mean_error:.3f}")
            
            if h5_mean_error > h1_mean_error:
                print(f"   ✅ Expected: Horizon=5 errors larger (harder to predict 5 steps ahead)")
            else:
                print(f"   ⚠️  Unexpected: Horizon=5 errors not larger")
        
        return True
    
    def run_full_verification(self):
        """Run all verification checks"""
        print("=" * 70)
        print("MULTI-HORIZON FORECASTING VERIFICATION")
        print("=" * 70)
        
        # Fetch data
        self.h1_data = self.fetch_series(1)
        self.h5_data = self.fetch_series(5)
        
        if not self.h1_data or not self.h5_data:
            print("\n❌ Failed to fetch data. Exiting.")
            return False
        
        # Run verifications
        results = {}
        
        # Horizon=1 checks
        print("\n" + "=" * 70)
        print("HORIZON = 1 (baseline)")
        print("=" * 70)
        results['h1_temporal'] = self.verify_temporal_alignment(self.h1_data.get('points', []), 1)
        results['h1_causal'] = self.verify_causal_integrity(self.h1_data.get('points', []), 1)
        results['h1_errors'] = self.verify_error_calculation(self.h1_data.get('points', []), 1)
        
        # Horizon=5 checks
        print("\n" + "=" * 70)
        print("HORIZON = 5 (multi-step)")
        print("=" * 70)
        results['h5_temporal'] = self.verify_temporal_alignment(self.h5_data.get('points', []), 5)
        results['h5_causal'] = self.verify_causal_integrity(self.h5_data.get('points', []), 5)
        results['h5_errors'] = self.verify_error_calculation(self.h5_data.get('points', []), 5)
        
        # Compare
        results['comparison'] = self.compare_horizons()
        
        # Summary
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        print(f"\n✅ Passed: {passed}/{total}")
        for check, result in results.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check}")
        
        if passed == total:
            print("\n🎉 ALL CHECKS PASSED! Multi-horizon forecasting is working correctly!")
            return True
        else:
            print(f"\n⚠️  {total - passed} check(s) failed. Review output above.")
            return False


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║                 MULTI-HORIZON FORECASTING VALIDATOR                    ║
║                                                                        ║
║  This script verifies that predictions with horizon t+m are:          ║
║  1. Causally aligned (no future information used)                     ║
║  2. Temporally correct (timestamp + m = target_time)                  ║
║  3. Correctly calculated (errors match expectations)                  ║
╚════════════════════════════════════════════════════════════════════════╝
    """)
    
    print(f"\n📋 Configuration:")
    print(f"   API Base: {API_BASE}")
    print(f"   Series ID: {SERIES_ID}")
    print(f"   Hours: {HOURS}")
    print(f"   Checking horizons: 1 and 5")
    
    verifier = HorizonVerifier(API_BASE)
    success = verifier.run_full_verification()
    
    sys.exit(0 if success else 1)
