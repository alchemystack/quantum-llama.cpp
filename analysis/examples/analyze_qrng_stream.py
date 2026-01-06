#!/usr/bin/env python3
"""
Example: Analyze QRNG Stream Quality

Monitors the ANU QRNG stream for anomalies and quality metrics.
Can be used to verify that the quantum random number source is functioning properly.
"""

import sys
import os
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from analysis import QRNGMonitor


def simulate_qrng_stream(n_samples: int = 200) -> list:
    """
    Simulate QRNG stream for demonstration.
    In real use, this would come from actual ANU API calls.
    """
    # Generate pseudo-random bytes for simulation
    np.random.seed(42)
    return np.random.randint(0, 256, n_samples).tolist()


def main():
    print("=" * 60)
    print("QRNG Stream Quality Monitor")
    print("=" * 60)
    
    # Initialize monitor
    monitor = QRNGMonitor(history_len=100)
    
    # Simulate or load QRNG stream
    print("\nGenerating simulated QRNG stream...")
    qrng_stream = simulate_qrng_stream(200)
    
    print(f"Analyzing {len(qrng_stream)} bytes from QRNG stream...\n")
    
    # Process stream
    anomaly_count = 0
    for i, byte_val in enumerate(qrng_stream):
        metrics = monitor.update(byte_val)
        
        # Print metrics every 20 samples
        if (i + 1) % 20 == 0:
            print(f"Sample {i + 1}:")
            print(f"  Mean: {metrics['mean']:.2f}")
            print(f"  Std: {metrics['std']:.2f}")
            
            if 'hurst' in metrics:
                print(f"  Hurst exponent: {metrics['hurst']:.3f}")
            if 'autocorr_lag1' in metrics:
                print(f"  Autocorrelation: {metrics['autocorr_lag1']:.3f}")
            if 'min_entropy' in metrics:
                print(f"  Min-entropy: {metrics['min_entropy']:.3f} bits")
            if 'chi_square_p' in metrics:
                print(f"  Uniformity p-value: {metrics['chi_square_p']:.4f}")
            
            if metrics.get('anomaly_detected'):
                print("  ⚠️  ANOMALY DETECTED!")
                anomaly_count += 1
            
            print()
    
    # Summary
    summary = monitor.get_summary()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total samples: {summary['total_samples']}")
    print(f"Anomalies detected: {summary['anomaly_count']}")
    print(f"Anomaly rate: {summary['anomaly_rate']:.2%}")
    
    # Interpretation
    print("\n" + "=" * 60)
    print("Interpretation")
    print("=" * 60)
    
    if summary['anomaly_rate'] < 0.05:
        print("✓ QRNG stream appears healthy (low anomaly rate)")
    elif summary['anomaly_rate'] < 0.15:
        print("⚠️  QRNG stream shows some anomalies (moderate concern)")
    else:
        print("❌ QRNG stream shows significant anomalies (high concern)")
    
    print("\nKey Metrics:")
    print("- Hurst ~0.5: Random walk (ideal)")
    print("- Autocorrelation ~0: No patterns (ideal)")
    print("- Min-entropy >6: Good randomness")
    print("- Uniformity p-value >0.05: Uniform distribution")


if __name__ == '__main__':
    main()
