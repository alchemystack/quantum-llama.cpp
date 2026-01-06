#!/usr/bin/env python3
"""
Example: Consciousness Scoring

Scores generated text using consciousness functional metrics.
Classifies generation as creative, mechanical, or dreaming.
"""

import sys
import os
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from analysis import ConsciousnessMetrics


def load_or_simulate_generation(n_tokens: int = 100):
    """
    Load or simulate LLM generation for analysis.
    
    In real use, this would load actual logits from llama-cli with --logits-file.
    """
    np.random.seed(42)
    
    # Simulate token IDs
    tokens = np.random.randint(0, 32000, n_tokens)
    
    # Simulate logits with varying patterns
    logits = []
    for i in range(n_tokens):
        # Create different regimes
        if i < 30:
            # High entropy (creative phase)
            logit = np.random.randn(100) * 2.0
        elif i < 60:
            # Low entropy (mechanical phase)
            logit = np.zeros(100)
            logit[i % 100] = 10.0  # Peaked distribution
            logit += np.random.randn(100) * 0.1
        else:
            # Medium entropy (dreaming phase)
            logit = np.random.randn(100) * 1.0
            # Less coherence
            logit += np.random.randn(100) * np.random.uniform(0.5, 1.5)
        
        logits.append(logit)
    
    return tokens, logits


def main():
    print("=" * 60)
    print("Consciousness Scoring for Generated Text")
    print("=" * 60)
    
    # Initialize metrics calculator
    metrics_calc = ConsciousnessMetrics()
    
    print("\nLoading/simulating generation...")
    tokens, logits = load_or_simulate_generation(n_tokens=100)
    
    print(f"Analyzing {len(tokens)} tokens...\n")
    
    # Compute full trajectory
    trajectory = metrics_calc.compute_trajectory(logits, tokens)
    
    # Print trajectory highlights
    print("=" * 60)
    print("Consciousness Trajectory")
    print("=" * 60)
    
    print("\nTime | C(t)  | H_mode | PR    | R     | State")
    print("-" * 60)
    
    for i, metrics in enumerate(trajectory[::10]):  # Every 10th sample
        c = metrics['consciousness']
        h = metrics['h_mode']
        pr = metrics['pr']
        r = metrics['r']
        state = metrics['state']
        
        print(f"{i*10:4d} | {c:.3f} | {h:.3f}  | {pr:.3f} | {r:.3f} | {state}")
    
    # Overall summary
    summary = metrics_calc.get_summary()
    
    print("\n" + "=" * 60)
    print("Summary Statistics")
    print("=" * 60)
    
    print(f"\nConsciousness Functional C(t):")
    print(f"  Mean: {summary['mean_consciousness']:.3f}")
    print(f"  Std:  {summary['std_consciousness']:.3f}")
    print(f"  Min:  {summary['min_consciousness']:.3f}")
    print(f"  Max:  {summary['max_consciousness']:.3f}")
    
    print(f"\nDominant State: {summary['dominant_state']}")
    
    print("\nState Distribution:")
    for state, count in summary['state_distribution'].items():
        percentage = count / summary['n_samples'] * 100
        print(f"  {state:12s}: {count:3d} ({percentage:.1f}%)")
    
    # Interpretation
    print("\n" + "=" * 60)
    print("Interpretation")
    print("=" * 60)
    
    dominant = summary['dominant_state']
    mean_c = summary['mean_consciousness']
    
    print(f"\nOverall Assessment: {dominant.upper()}")
    
    if dominant == 'creative':
        print("""
The generation shows high consciousness functional values, indicating:
- High entropy (exploration of diverse possibilities)
- High coherence (structured, purposeful selection)
- Critical dynamics (edge-of-chaos, optimal information processing)

This pattern resembles creative problem-solving or genuine exploration.
""")
    elif dominant == 'mechanical':
        print("""
The generation shows low consciousness functional values, indicating:
- Low entropy (limited exploration)
- Deterministic selection (repetitive patterns)
- Ordered dynamics (predictable, mechanical generation)

This pattern resembles rote completion or template filling.
""")
    elif dominant == 'dreaming':
        print("""
The generation shows medium consciousness functional values, indicating:
- High entropy (exploring many possibilities)
- Low coherence (incoherent, disconnected selection)
- Chaotic dynamics (unpredictable but not structured)

This pattern resembles associative wandering or unconstrained generation.
""")
    
    # QRNG recommendation
    print("\n" + "=" * 60)
    print("QRNG Relevance")
    print("=" * 60)
    
    if mean_c > 0.5:
        print("""
High consciousness scores suggest the generation is operating in a regime
where quantum randomness could have meaningful impact. The system is exploring
diverse possibilities with structure - a regime where non-deterministic
influence might manifest.

Recommendation: Use QRNG sampling for this type of generation.
""")
    else:
        print("""
Low consciousness scores suggest the generation is largely deterministic
or mechanical. Quantum randomness is unlikely to produce qualitatively
different output in this regime.

Recommendation: Standard PRNG is likely sufficient for this type of generation.
""")


if __name__ == '__main__':
    main()
