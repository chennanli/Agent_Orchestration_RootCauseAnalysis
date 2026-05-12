#!/usr/bin/env python3
"""
Generate complete baseline statistics from fault0.csv (normal operation data)
This creates features_mean_std.csv with ALL 52 features
"""

import pandas as pd
import os

def generate_baseline():
    """Generate baseline statistics from fault0.csv"""
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "data", "fault0.csv")
    stats_dir = os.path.join(script_dir, "stats")
    output_path = os.path.join(stats_dir, "features_mean_std.csv")
    
    # Create stats directory if it doesn't exist
    os.makedirs(stats_dir, exist_ok=True)
    
    # Load fault0.csv (normal operation data)
    print(f"📂 Loading baseline data from: {data_path}")
    df = pd.read_csv(data_path)
    
    # Remove 'time' column if present
    if 'time' in df.columns:
        df = df.drop(columns=['time'])
    
    print(f"✅ Loaded {len(df)} rows with {len(df.columns)} features")
    
    # Calculate mean and std for each feature
    stats = pd.DataFrame({
        'feature': df.columns,
        'mean': df.mean(),
        'std': df.std()
    })
    
    # Save to CSV
    stats.to_csv(output_path, index=False)
    print(f"✅ Saved baseline statistics to: {output_path}")
    print(f"📊 Features: {len(stats)}")
    
    # Show first few rows
    print("\n📋 First 10 features:")
    print(stats.head(10).to_string(index=False))
    
    # Check for any features with zero std (constant values)
    zero_std = stats[stats['std'] < 1e-6]
    if len(zero_std) > 0:
        print(f"\n⚠️ Warning: {len(zero_std)} features have near-zero std deviation:")
        print(zero_std.to_string(index=False))
    
    return stats

if __name__ == "__main__":
    print("🚀 Generating baseline statistics from fault0.csv...")
    print("=" * 60)
    stats = generate_baseline()
    print("=" * 60)
    print("🎉 Done! Backend will now have complete baseline for all features.")

