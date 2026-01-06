#!/usr/bin/env python3
"""
Example: Compare QRNG vs PRNG Output

Performs A/B comparison of LLM outputs generated with quantum vs pseudorandom sampling.
Tests whether quantum randomness produces qualitatively different results.
"""

import sys
import os
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from analysis import OutputAnalyzer


def load_or_simulate_output(output_type: str, n_tokens: int = 150):
    """
    Load or simulate LLM output for comparison.
    
    In real use, this would load actual output from llama-cli runs.
    """
    np.random.seed(42 if output_type == 'qrng' else 123)
    
    # Simulate token IDs (vocabulary of 32000)
    tokens = np.random.randint(0, 32000, n_tokens).tolist()
    
    # Simulate logits (100-dimensional for simplicity)
    logits = []
    for _ in range(n_tokens):
        # Random logits with varying entropy
        logit = np.random.randn(100)
        # Add some structure for QRNG
        if output_type == 'qrng':
            # More entropy variation
            logit *= np.random.uniform(0.5, 2.0)
        logits.append(logit)
    
    # Simulate QRNG bytes for quantum output
    qrng_bytes = None
    if output_type == 'qrng':
        qrng_bytes = np.random.randint(0, 256, n_tokens).tolist()
    
    return tokens, logits, qrng_bytes


def main():
    print("=" * 60)
    print("QRNG vs PRNG Output Comparison")
    print("=" * 60)
    
    # Initialize analyzer
    analyzer = OutputAnalyzer()
    
    print("\nLoading/simulating QRNG output...")
    qrng_tokens, qrng_logits, qrng_bytes = load_or_simulate_output('qrng', n_tokens=150)
    
    print("Analyzing QRNG output...")
    qrng_result = analyzer.analyze(
        tokens=qrng_tokens,
        logits=qrng_logits,
        qrng_bytes=qrng_bytes
    )
    
    # Reset for PRNG analysis
    analyzer.reset()
    
    print("Loading/simulating PRNG output (same prompt, different RNG)...")
    prng_tokens, prng_logits, _ = load_or_simulate_output('prng', n_tokens=150)
    
    print("Analyzing PRNG output...")
    prng_result = analyzer.analyze(
        tokens=prng_tokens,
        logits=prng_logits,
        qrng_bytes=None
    )
    
    # Compare results
    print("\n" + "=" * 60)
    print("Performing Comparison...")
    print("=" * 60)
    
    comparison = analyzer.compare(qrng_result, prng_result)
    
    # Print summary
    print(comparison.summary())
    
    # Additional details
    print("\n" + "=" * 60)
    print("Detailed Analysis")
    print("=" * 60)
    
    if qrng_result.qrng_summary:
        print("\nQRNG Stream Quality:")
        summary = qrng_result.qrng_summary
        print(f"  Total samples: {summary['total_samples']}")
        print(f"  Anomaly rate: {summary['anomaly_rate']:.2%}")
    
    print("\nQRNG Token Trajectory:")
    print(f"  Classification: {qrng_result.trajectory_classification}")
    if qrng_result.trajectory_metrics:
        print(f"  Hurst exponent: {qrng_result.trajectory_metrics.get('hurst', 0):.3f}")
        print(f"  Lyapunov (local): {qrng_result.trajectory_metrics.get('lyapunov', 0):.4f}")
    
    print("\nPRNG Token Trajectory:")
    print(f"  Classification: {prng_result.trajectory_classification}")
    if prng_result.trajectory_metrics:
        print(f"  Hurst exponent: {prng_result.trajectory_metrics.get('hurst', 0):.3f}")
        print(f"  Lyapunov (local): {prng_result.trajectory_metrics.get('lyapunov', 0):.4f}")
    
    # Interpretation
    print("\n" + "=" * 60)
    print("Interpretation")
    print("=" * 60)
    
    if comparison.statistical_tests:
        any_significant = any(
            test.get('significant', False) 
            for test in comparison.statistical_tests.values()
        )
        
        if any_significant:
            print("✓ Statistically significant differences detected!")
            print("  QRNG and PRNG outputs show measurably different properties.")
        else:
            print("✗ No statistically significant differences detected.")
            print("  QRNG and PRNG outputs appear similar by these metrics.")
    
    if comparison.consciousness_comparison:
        cc = comparison.consciousness_comparison
        diff = cc.get('consciousness_diff', 0)
        
        if diff > 0.1:
            print(f"\n⚠️  Large consciousness functional difference: {diff:.3f}")
            print("   This suggests different generation dynamics.")
        
        if cc.get('state_differs'):
            print("\n⚠️  Consciousness states differ:")
            print(f"   QRNG: {cc.get('qrng_state')}")
            print(f"   PRNG: {cc.get('prng_state')}")


if __name__ == '__main__':
    main()
