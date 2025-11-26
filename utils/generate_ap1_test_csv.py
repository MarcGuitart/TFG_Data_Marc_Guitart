#!/usr/bin/env python3
"""
Generate test CSV with multiple patterns to showcase model differences.

This creates a time series with:
- Linear trends (where linear_8 excels)
- Smooth curves (where ab_fast excels) 
- Polynomial transitions (where poly2_12 excels)
- Some noise to test robustness

Usage:
    python utils/generate_ap1_test_csv.py
    
Output:
    data/ap1_test_data.csv
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_ap1_test_data(n_points=100, start_hour=0):
    """
    Generate test data with varied patterns.
    
    Args:
        n_points: Number of data points
        start_hour: Starting hour (0-23)
    
    Returns:
        DataFrame with columns: timestamp, id, var
    """
    np.random.seed(42)  # Reproducible
    
    times = []
    values = []
    
    # Base time: today at start_hour
    base = datetime.now().replace(hour=start_hour, minute=0, second=0, microsecond=0)
    
    for i in range(n_points):
        t = base + timedelta(minutes=30 * i)
        times.append(t.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Composite signal with multiple patterns
        x = i / n_points  # normalized time [0, 1]
        
        # 1. Linear trend (for linear_8 to shine)
        linear = 0.1 + 0.05 * i / n_points
        
        # 2. Smooth sinusoidal (for ab_fast to shine)
        smooth = 0.15 * np.sin(2 * np.pi * x * 2)
        
        # 3. Polynomial curve (for poly2_12 to shine)
        poly = 0.1 * (x - 0.5) ** 2
        
        # 4. Small noise
        noise = np.random.normal(0, 0.005)
        
        # Combine patterns with weights changing over time
        if x < 0.33:
            # Early: mostly linear
            value = 0.7 * linear + 0.2 * smooth + 0.1 * poly + noise
        elif x < 0.66:
            # Middle: mostly smooth curves
            value = 0.2 * linear + 0.6 * smooth + 0.2 * poly + noise
        else:
            # Late: mostly polynomial
            value = 0.2 * linear + 0.2 * smooth + 0.6 * poly + noise
        
        # Keep values in reasonable range [0.05, 0.35]
        value = np.clip(value + 0.15, 0.05, 0.35)
        values.append(value)
    
    df = pd.DataFrame({
        'timestamp': times,
        'id': 'TestSeries',
        'var': values
    })
    
    return df

def main():
    print("🧪 Generating AP1 Test Data...")
    print("=" * 50)
    
    # Generate data
    df = generate_ap1_test_data(n_points=100, start_hour=8)
    
    # Save
    output_path = "data/ap1_test_data.csv"
    df.to_csv(output_path, index=False)
    
    print(f"✅ Created: {output_path}")
    print(f"   Points: {len(df)}")
    print(f"   Time range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    print(f"   Value range: {df['var'].min():.4f} to {df['var'].max():.4f}")
    print()
    print("📊 Pattern Distribution:")
    print("   0-33%:  Linear trend dominant")
    print("   33-66%: Smooth curves dominant")
    print("   66-100%: Polynomial curves dominant")
    print()
    print("🎯 Expected Model Performance:")
    print("   - linear_8 should excel in first third")
    print("   - ab_fast should excel in middle third")
    print("   - poly2_12 should excel in last third")
    print("   - Combined should be consistently best overall")
    print()
    print("Next steps:")
    print("1. Upload this CSV in the frontend")
    print("2. Run the agent")
    print("3. Load backend series (per-model)")
    print("4. Observe how each model performs in its optimal zone")
    print("5. Take screenshots for AP1 deliverable")

if __name__ == "__main__":
    main()
