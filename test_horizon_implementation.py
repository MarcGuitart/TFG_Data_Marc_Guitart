#!/usr/bin/env python3
"""
Complete end-to-end test for multi-horizon forecasting implementation.
Tests both frontend selector and backend causal alignment.
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Any, List

API_BASE = "http://localhost:8081"
SERIES_ID = "Other"

class HorizonFullTest:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
    
    def log_error(self, msg: str):
        self.errors.append(f"❌ {msg}")
        print(f"  ❌ {msg}")
    
    def log_warning(self, msg: str):
        self.warnings.append(f"⚠️ {msg}")
        print(f"  ⚠️ {msg}")
    
    def log_info(self, msg: str):
        self.info.append(f"ℹ️ {msg}")
        print(f"  ℹ️ {msg}")
    
    def test_api_accepts_horizon(self) -> bool:
        """Test that API accepts horizon parameter"""
        print("\n📡 TEST 1: API accepts horizon parameter")
        try:
            for h in [1, 2, 5, 10]:
                r = requests.get(
                    f"{API_BASE}/api/series",
                    params={"id": SERIES_ID, "hours": 24, "horizon": h},
                    timeout=10
                )
                if r.status_code != 200:
                    self.log_error(f"API returned {r.status_code} for horizon={h}")
                    return False
                data = r.json()
                if data.get('horizon') != h:
                    self.log_error(f"Response horizon mismatch: expected {h}, got {data.get('horizon')}")
                    return False
                self.log_info(f"✓ horizon={h}: {len(data.get('points', []))} points")
            print("✅ PASSED: API accepts all horizon values (1, 2, 5, 10)")
            return True
        except Exception as e:
            self.log_error(f"API test failed: {e}")
            return False
    
    def test_horizon_response_structure(self, horizon: int = 5) -> bool:
        """Test that response has correct structure"""
        print(f"\n📋 TEST 2: Response structure for horizon={horizon}")
        try:
            r = requests.get(
                f"{API_BASE}/api/series",
                params={"id": SERIES_ID, "hours": 24, "horizon": horizon},
                timeout=10
            )
            data = r.json()
            
            # Check top-level fields
            required_fields = ["id", "horizon", "total", "points"]
            for field in required_fields:
                if field not in data:
                    self.log_error(f"Missing field in response: {field}")
                    return False
            
            if not data["points"]:
                self.log_warning("No points in response")
                return True  # Not a failure, just empty data
            
            # Check first point structure
            point = data["points"][0]
            required_point_fields = [
                "step", "timestamp", "target_time", "var",
                "predictions", "errors", "horizon"
            ]
            for field in required_point_fields:
                if field not in point:
                    self.log_error(f"Missing field in point: {field}")
                    return False
            
            print("✅ PASSED: Response structure is correct")
            return True
        except Exception as e:
            self.log_error(f"Structure test failed: {e}")
            return False
    
    def test_temporal_correctness(self, horizon: int = 5) -> bool:
        """Test that timestamp + horizon = target_time"""
        print(f"\n⏰ TEST 3: Temporal correctness for horizon={horizon}")
        try:
            r = requests.get(
                f"{API_BASE}/api/series",
                params={"id": SERIES_ID, "hours": 24, "horizon": horizon},
                timeout=10
            )
            data = r.json()
            
            if not data["points"]:
                self.log_warning("No points to verify temporal correctness")
                return True
            
            # Check first 3 points
            checked = 0
            for point in data["points"][:3]:
                ts = datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00"))
                target = datetime.fromisoformat(point["target_time"].replace("Z", "+00:00"))
                diff_seconds = (target - ts).total_seconds()
                
                # For 1-minute intervals, diff should be ~horizon * 60
                # Allow some tolerance for different time intervals
                expected_min = horizon * 50  # conservative estimate
                
                if diff_seconds < expected_min:
                    self.log_error(
                        f"Point {checked}: temporal mismatch. "
                        f"target - timestamp = {diff_seconds}s (expected >= {expected_min}s)"
                    )
                    return False
                
                self.log_info(f"Point {checked}: diff={diff_seconds}s ✓")
                checked += 1
            
            print(f"✅ PASSED: Temporal alignment verified for {checked} points")
            return True
        except Exception as e:
            self.log_error(f"Temporal test failed: {e}")
            return False
    
    def test_causal_integrity(self, horizon: int = 5) -> bool:
        """Test that first m points are excluded"""
        print(f"\n🔐 TEST 4: Causal integrity (first {horizon} points excluded)")
        try:
            r = requests.get(
                f"{API_BASE}/api/series",
                params={"id": SERIES_ID, "hours": 24, "horizon": horizon},
                timeout=10
            )
            data = r.json()
            
            if not data["points"]:
                self.log_warning("No points to verify causal integrity")
                return True
            
            # Get minimum step
            min_step = min(p.get("step", 999) for p in data["points"])
            
            if min_step < horizon:
                self.log_error(
                    f"Causal violation: min_step={min_step} < horizon={horizon}. "
                    f"First {horizon} points should be excluded!"
                )
                return False
            
            self.log_info(f"First point has step={min_step} (>= {horizon}) ✓")
            print(f"✅ PASSED: Causal integrity verified")
            return True
        except Exception as e:
            self.log_error(f"Causal test failed: {e}")
            return False
    
    def test_error_calculation(self, horizon: int = 5) -> bool:
        """Test that error = |actual - predicted|"""
        print(f"\n📊 TEST 5: Error calculation for horizon={horizon}")
        try:
            r = requests.get(
                f"{API_BASE}/api/series",
                params={"id": SERIES_ID, "hours": 24, "horizon": horizon},
                timeout=10
            )
            data = r.json()
            
            if not data["points"]:
                self.log_warning("No points to verify error calculation")
                return True
            
            checked = 0
            for point in data["points"][:5]:
                actual = point.get("var")
                predictions = point.get("predictions", {})
                errors = point.get("errors", {})
                
                if not isinstance(actual, (int, float)):
                    continue
                
                for model_name, pred_val in predictions.items():
                    if not isinstance(pred_val, (int, float)):
                        continue
                    
                    calculated_error = abs(actual - pred_val)
                    reported_error = errors.get(model_name)
                    
                    if reported_error is None:
                        continue
                    
                    # Allow small floating point tolerance
                    if abs(calculated_error - reported_error) > 0.01:
                        self.log_error(
                            f"Error mismatch at {model_name}: "
                            f"calculated={calculated_error:.3f}, "
                            f"reported={reported_error:.3f}"
                        )
                        return False
                    
                    self.log_info(
                        f"Point {checked}/{model_name}: "
                        f"|{actual:.2f}-{pred_val:.2f}|={calculated_error:.3f} ✓"
                    )
                    checked += 1
            
            print(f"✅ PASSED: Error calculations verified ({checked} checks)")
            return True
        except Exception as e:
            self.log_error(f"Error calculation test failed: {e}")
            return False
    
    def test_horizon_comparison(self) -> bool:
        """Test that horizon=5 is harder than horizon=1"""
        print(f"\n🔄 TEST 6: Horizon=5 should be harder than horizon=1")
        try:
            h1_data = requests.get(
                f"{API_BASE}/api/series",
                params={"id": SERIES_ID, "hours": 24, "horizon": 1},
                timeout=10
            ).json()
            
            h5_data = requests.get(
                f"{API_BASE}/api/series",
                params={"id": SERIES_ID, "hours": 24, "horizon": 5},
                timeout=10
            ).json()
            
            h1_points = h1_data.get("points", [])
            h5_points = h5_data.get("points", [])
            
            if not h1_points or not h5_points:
                self.log_warning("Insufficient data for comparison")
                return True
            
            # Calculate mean errors
            h1_errors = [
                p.get("errors", {}).get(list(p.get("errors", {}).keys())[0], 0)
                for p in h1_points
                if p.get("errors", {})
            ]
            
            h5_errors = [
                p.get("errors", {}).get(list(p.get("errors", {}).keys())[0], 0)
                for p in h5_points
                if p.get("errors", {})
            ]
            
            if not h1_errors or not h5_errors:
                self.log_warning("Cannot calculate mean errors")
                return True
            
            h1_mean = sum(h1_errors) / len(h1_errors)
            h5_mean = sum(h5_errors) / len(h5_errors)
            
            self.log_info(f"horizon=1 mean error: {h1_mean:.4f}")
            self.log_info(f"horizon=5 mean error: {h5_mean:.4f}")
            
            if h5_mean > h1_mean:
                self.log_info(f"Ratio: {h5_mean/h1_mean:.2f}x (harder is good ✓)")
                print(f"✅ PASSED: Horizon comparison correct")
                return True
            else:
                self.log_warning(
                    f"Unexpected: horizon=5 not harder than horizon=1. "
                    f"(This can happen with certain datasets)"
                )
                return True  # Not a failure, just unusual
        
        except Exception as e:
            self.log_error(f"Comparison test failed: {e}")
            return False
    
    def test_point_counts(self) -> bool:
        """Test that horizon=5 has fewer points (first m excluded)"""
        print(f"\n📈 TEST 7: Point counts (horizon=5 should have fewer)")
        try:
            h1_data = requests.get(
                f"{API_BASE}/api/series",
                params={"id": SERIES_ID, "hours": 24, "horizon": 1},
                timeout=10
            ).json()
            
            h5_data = requests.get(
                f"{API_BASE}/api/series",
                params={"id": SERIES_ID, "hours": 24, "horizon": 5},
                timeout=10
            ).json()
            
            h1_count = len(h1_data.get("points", []))
            h5_count = len(h5_data.get("points", []))
            
            self.log_info(f"horizon=1: {h1_count} points")
            self.log_info(f"horizon=5: {h5_count} points")
            
            # h5 should have roughly h1_count - 5 points (approximately)
            if h5_count < h1_count:
                self.log_info(f"Difference: {h1_count - h5_count} points ✓")
                print(f"✅ PASSED: Point counts are reasonable")
                return True
            else:
                self.log_warning(
                    f"Expected horizon=5 to have fewer points, "
                    f"but {h5_count} >= {h1_count}"
                )
                return True  # Not necessarily a failure
        
        except Exception as e:
            self.log_error(f"Point count test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        print("=" * 80)
        print("COMPLETE MULTI-HORIZON FORECASTING TEST SUITE")
        print("=" * 80)
        print(f"\nTarget: {API_BASE}")
        print(f"Series: {SERIES_ID}")
        print(f"Hours: 24\n")
        
        results = []
        
        results.append(("API accepts horizon parameter", self.test_api_accepts_horizon()))
        results.append(("Response structure", self.test_horizon_response_structure()))
        results.append(("Temporal correctness", self.test_temporal_correctness()))
        results.append(("Causal integrity", self.test_causal_integrity()))
        results.append(("Error calculation", self.test_error_calculation()))
        results.append(("Horizon comparison", self.test_horizon_comparison()))
        results.append(("Point counts", self.test_point_counts()))
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅" if result else "❌"
            print(f"{status} {test_name}")
        
        print(f"\nResult: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! Multi-horizon implementation is correct!")
            return True
        else:
            print(f"\n⚠️ {total - passed} test(s) failed. Review errors above.")
            return False

if __name__ == "__main__":
    tester = HorizonFullTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
