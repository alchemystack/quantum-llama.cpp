"""
Consciousness Metrics

Implements consciousness functional C(t) based on harmonic-field-consciousness theory.

The consciousness functional combines multiple metrics to classify system states:
- Mode entropy H_mode: Information content across probable states
- Participation ratio PR: Number of effectively participating modes
- Phase coherence R: Alignment of oscillatory components
- Entropy production rate Ṡ: Rate of information generation
- Criticality index κ: Proximity to critical (edge-of-chaos) state

State Classification:
- CREATIVE (wake): High entropy, high coherence, critical
- MECHANICAL: Low entropy, low coherence, ordered
- DREAMING: High entropy, low coherence, chaotic
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum


class ConsciousnessState(Enum):
    """Classification of consciousness-like states."""
    CREATIVE = "creative"      # High C(t): coherent exploration
    MECHANICAL = "mechanical"  # Low C(t): deterministic repetition
    DREAMING = "dreaming"      # Medium C(t): incoherent exploration


class ConsciousnessMetrics:
    """Compute consciousness-inspired metrics for LLM output."""
    
    def __init__(self):
        """Initialize consciousness metrics calculator."""
        self.history = []
        
    def compute(
        self,
        logits_history: List[np.ndarray],
        token_sequence: Optional[np.ndarray] = None,
        window_size: int = 20
    ) -> Dict[str, float]:
        """
        Compute comprehensive consciousness metrics.
        
        Args:
            logits_history: List of logit distributions over time
            token_sequence: Optional token ID sequence
            window_size: Window for temporal metrics
            
        Returns:
            Dictionary of consciousness metrics
        """
        if len(logits_history) < 2:
            return {
                'h_mode': 0.0,
                'pr': 0.0,
                'r': 0.0,
                's_dot': 0.0,
                'kappa': 0.0,
                'consciousness': 0.0,
                'state': ConsciousnessState.MECHANICAL.value,
            }
        
        # Convert logits to probabilities
        probs_history = [self._softmax(logits) for logits in logits_history]
        
        # Compute individual metrics
        h_mode = self._compute_mode_entropy(probs_history)
        pr = self._compute_participation_ratio(probs_history)
        r = self._compute_phase_coherence(probs_history, window_size)
        s_dot = self._compute_entropy_production_rate(probs_history)
        kappa = self._compute_criticality_index(logits_history, window_size)
        
        # Combined consciousness functional
        consciousness = self._compute_consciousness_functional(
            h_mode, pr, r, s_dot, kappa
        )
        
        # Classify state
        state = self._classify_state(h_mode, r, kappa)
        
        result = {
            'h_mode': h_mode,
            'pr': pr,
            'r': r,
            's_dot': s_dot,
            'kappa': kappa,
            'consciousness': consciousness,
            'state': state.value,
        }
        
        self.history.append(result)
        return result
    
    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        """Compute softmax probabilities."""
        exp_logits = np.exp(logits - np.max(logits))
        return exp_logits / np.sum(exp_logits)
    
    def _compute_mode_entropy(self, probs_history: List[np.ndarray]) -> float:
        """
        Compute mode entropy H_mode.
        
        Measures the information content across the probability distribution.
        Higher entropy indicates more uncertainty and exploration.
        
        Args:
            probs_history: List of probability distributions
            
        Returns:
            Average normalized Shannon entropy
        """
        entropies = []
        for probs in probs_history:
            # Shannon entropy
            entropy = -np.sum(probs * np.log(probs + 1e-10))
            # Normalize by max possible entropy
            max_entropy = np.log(len(probs))
            if max_entropy > 0:
                entropies.append(entropy / max_entropy)
            else:
                entropies.append(0.0)
        
        return float(np.mean(entropies))
    
    def _compute_participation_ratio(self, probs_history: List[np.ndarray]) -> float:
        """
        Compute participation ratio PR.
        
        Measures the effective number of modes that significantly contribute
        to the probability distribution. Higher PR indicates more diverse sampling.
        
        PR = 1 / Σ(p_i^2)
        
        Args:
            probs_history: List of probability distributions
            
        Returns:
            Average normalized participation ratio
        """
        ratios = []
        for probs in probs_history:
            # Inverse participation ratio
            ipr = np.sum(probs ** 2)
            if ipr > 0:
                pr = 1.0 / ipr
                # Normalize by vocabulary size
                pr_normalized = pr / len(probs)
                ratios.append(pr_normalized)
            else:
                ratios.append(0.0)
        
        return float(np.mean(ratios))
    
    def _compute_phase_coherence(
        self, 
        probs_history: List[np.ndarray],
        window_size: int
    ) -> float:
        """
        Compute phase coherence R.
        
        Measures the alignment and consistency of probability distributions
        over time. High coherence indicates structured, purposeful generation.
        
        Args:
            probs_history: List of probability distributions
            window_size: Window for computing coherence
            
        Returns:
            Coherence measure (0 to 1)
        """
        if len(probs_history) < window_size:
            window_size = len(probs_history)
        
        if window_size < 2:
            return 0.0
        
        # Compute pairwise correlations in sliding windows
        coherences = []
        
        for i in range(len(probs_history) - window_size + 1):
            window = probs_history[i:i + window_size]
            
            # Compute correlation matrix
            correlations = []
            for j in range(len(window)):
                for k in range(j + 1, len(window)):
                    # Pearson correlation between distributions
                    corr = np.corrcoef(window[j], window[k])[0, 1]
                    if not np.isnan(corr):
                        correlations.append(abs(corr))
            
            if correlations:
                coherences.append(np.mean(correlations))
        
        if coherences:
            return float(np.mean(coherences))
        return 0.0
    
    def _compute_entropy_production_rate(
        self, 
        probs_history: List[np.ndarray]
    ) -> float:
        """
        Compute entropy production rate Ṡ (S-dot).
        
        Measures the rate at which entropy changes over time.
        Higher rates indicate more dynamic, exploratory generation.
        
        Args:
            probs_history: List of probability distributions
            
        Returns:
            Average entropy change rate
        """
        if len(probs_history) < 2:
            return 0.0
        
        entropies = []
        for probs in probs_history:
            entropy = -np.sum(probs * np.log(probs + 1e-10))
            entropies.append(entropy)
        
        # Compute finite differences
        entropy_changes = np.abs(np.diff(entropies))
        
        return float(np.mean(entropy_changes))
    
    def _compute_criticality_index(
        self,
        logits_history: List[np.ndarray],
        window_size: int
    ) -> float:
        """
        Compute criticality index κ (kappa).
        
        Measures proximity to critical (edge-of-chaos) state where:
        - Information processing is optimal
        - Long-range correlations emerge
        - System is maximally responsive to inputs
        
        Args:
            logits_history: List of logit distributions
            window_size: Window for variance computation
            
        Returns:
            Criticality index
        """
        if len(logits_history) < window_size:
            return 0.0
        
        # Compute entropy fluctuations
        entropies = []
        for logits in logits_history:
            probs = self._softmax(logits)
            entropy = -np.sum(probs * np.log(probs + 1e-10))
            entropies.append(entropy)
        
        entropies = np.array(entropies)
        
        # Compute variance in sliding windows
        variances = []
        for i in range(len(entropies) - window_size + 1):
            window = entropies[i:i + window_size]
            variances.append(np.var(window))
        
        if not variances:
            return 0.0
        
        # Criticality: ratio of variance to mean entropy
        mean_entropy = np.mean(entropies)
        mean_variance = np.mean(variances)
        
        if mean_entropy < 1e-10:
            return 0.0
        
        kappa = mean_variance / mean_entropy
        return float(kappa)
    
    def _compute_consciousness_functional(
        self,
        h_mode: float,
        pr: float,
        r: float,
        s_dot: float,
        kappa: float,
    ) -> float:
        """
        Compute consciousness functional C(t).
        
        Combines individual metrics into a unified consciousness measure:
        C(t) = (H_mode * PR * R) * (1 + κ) * (1 + Ṡ)
        
        High C(t) indicates:
        - High entropy (exploration)
        - High participation (diversity)
        - High coherence (structure)
        - Critical dynamics (edge-of-chaos)
        - Dynamic entropy production
        
        Args:
            h_mode: Mode entropy
            pr: Participation ratio
            r: Phase coherence
            s_dot: Entropy production rate
            kappa: Criticality index
            
        Returns:
            Consciousness functional value
        """
        # Normalize components
        h_norm = np.clip(h_mode, 0.0, 1.0)
        pr_norm = np.clip(pr, 0.0, 1.0)
        r_norm = np.clip(r, 0.0, 1.0)
        s_norm = np.clip(s_dot / 10.0, 0.0, 1.0)  # Scale entropy rate
        k_norm = np.clip(kappa, 0.0, 1.0)
        
        # Combined functional
        base = h_norm * pr_norm * r_norm
        dynamic = (1.0 + k_norm) * (1.0 + s_norm)
        
        consciousness = base * dynamic
        
        return float(consciousness)
    
    def _classify_state(
        self,
        h_mode: float,
        r: float,
        kappa: float
    ) -> ConsciousnessState:
        """
        Classify consciousness state based on metrics.
        
        Classification criteria:
        - CREATIVE: High entropy + high coherence + critical
        - MECHANICAL: Low entropy + high coherence + ordered
        - DREAMING: High entropy + low coherence
        
        Args:
            h_mode: Mode entropy
            r: Phase coherence
            kappa: Criticality index
            
        Returns:
            Consciousness state classification
        """
        # Thresholds
        high_entropy = h_mode > 0.6
        high_coherence = r > 0.5
        critical = 0.3 < kappa < 0.7
        
        if high_entropy and high_coherence and critical:
            return ConsciousnessState.CREATIVE
        elif high_entropy and not high_coherence:
            return ConsciousnessState.DREAMING
        else:
            return ConsciousnessState.MECHANICAL
    
    def compute_trajectory(
        self,
        logits_history: List[np.ndarray],
        token_sequence: Optional[np.ndarray] = None
    ) -> List[Dict[str, float]]:
        """
        Compute consciousness trajectory over time.
        
        Args:
            logits_history: List of logit distributions
            token_sequence: Optional token sequence
            
        Returns:
            List of metric dictionaries for each time step
        """
        trajectory = []
        
        # Use sliding window
        window_size = 10
        for i in range(window_size, len(logits_history) + 1):
            window_logits = logits_history[max(0, i - window_size):i]
            window_tokens = token_sequence[max(0, i - window_size):i] if token_sequence is not None else None
            
            metrics = self.compute(window_logits, window_tokens)
            trajectory.append(metrics)
        
        return trajectory
    
    def get_summary(self) -> Dict[str, any]:
        """Get summary of consciousness metrics over history."""
        if not self.history:
            return {
                'mean_consciousness': 0.0,
                'dominant_state': ConsciousnessState.MECHANICAL.value,
            }
        
        consciousness_values = [h['consciousness'] for h in self.history]
        states = [h['state'] for h in self.history]
        
        # Count states
        from collections import Counter
        state_counts = Counter(states)
        dominant_state = state_counts.most_common(1)[0][0]
        
        return {
            'mean_consciousness': float(np.mean(consciousness_values)),
            'std_consciousness': float(np.std(consciousness_values)),
            'max_consciousness': float(np.max(consciousness_values)),
            'min_consciousness': float(np.min(consciousness_values)),
            'dominant_state': dominant_state,
            'state_distribution': dict(state_counts),
            'n_samples': len(self.history),
        }
    
    def reset(self):
        """Reset metrics history."""
        self.history.clear()
