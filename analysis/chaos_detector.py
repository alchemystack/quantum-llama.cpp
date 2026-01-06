"""
Chaos Detector

Implements chaos theory metrics for analyzing LLM output dynamics.
Based on qpt-research repository.

Metrics:
- Lyapunov exponent: Measures sensitivity to initial conditions
- Criticality index: Detects phase transitions and edge-of-chaos behavior
- Feigenbaum analysis: Identifies bifurcation points
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


class ChaosDetector:
    """Detect chaotic dynamics and phase transitions in token sequences."""
    
    def __init__(self):
        """Initialize chaos detector."""
        self.lyapunov_history = []
        
    def compute_lyapunov(
        self, 
        sequence: np.ndarray, 
        embedding_dim: int = 3,
        tau: int = 1,
        max_steps: int = 10
    ) -> float:
        """
        Compute largest Lyapunov exponent using Rosenstein algorithm.
        
        The Lyapunov exponent quantifies the rate of separation of infinitesimally
        close trajectories:
        - λ > 0: Chaotic (exponential divergence)
        - λ = 0: Neutral stability (periodic)
        - λ < 0: Stable (converging)
        
        Args:
            sequence: Time series data (e.g., token IDs or logit values)
            embedding_dim: Dimension for phase space reconstruction
            tau: Time delay for embedding
            max_steps: Number of steps to track divergence
            
        Returns:
            Largest Lyapunov exponent
        """
        if len(sequence) < embedding_dim * tau + max_steps + 10:
            return 0.0
        
        # Normalize sequence
        if np.std(sequence) > 0:
            sequence = (sequence - np.mean(sequence)) / np.std(sequence)
        
        # Create phase space embedding
        embedded = self._time_delay_embedding(sequence, embedding_dim, tau)
        
        if len(embedded) < max_steps + 10:
            return 0.0
        
        # Rosenstein algorithm
        n_points = len(embedded)
        log_divergence = np.zeros(max_steps)
        count = np.zeros(max_steps)
        
        for i in range(n_points - max_steps):
            # Find nearest neighbor with temporal separation > mean period
            distances = np.linalg.norm(embedded - embedded[i], axis=1)
            
            # Exclude nearby points in time (prevent temporal correlation)
            min_temporal_sep = max(1, len(sequence) // 10)
            for j in range(max(0, i - min_temporal_sep), 
                          min(n_points, i + min_temporal_sep)):
                distances[j] = np.inf
            
            if np.all(np.isinf(distances)):
                continue
            
            nearest_idx = np.argmin(distances)
            d0 = distances[nearest_idx]
            
            if d0 < 1e-10:
                continue
            
            # Track divergence over time
            for step in range(max_steps):
                if i + step >= n_points or nearest_idx + step >= n_points:
                    break
                
                d_step = np.linalg.norm(embedded[i + step] - embedded[nearest_idx + step])
                
                if d_step > 1e-10:
                    log_divergence[step] += np.log(d_step / d0)
                    count[step] += 1
        
        # Average log divergence
        valid_steps = count > 0
        if not np.any(valid_steps):
            return 0.0
        
        avg_log_div = log_divergence[valid_steps] / count[valid_steps]
        steps = np.arange(max_steps)[valid_steps]
        
        # Fit linear slope
        if len(steps) < 2:
            return 0.0
        
        try:
            lyapunov = np.polyfit(steps, avg_log_div, 1)[0]
            return float(lyapunov)
        except (ValueError, np.linalg.LinAlgError):
            return 0.0
    
    def _time_delay_embedding(
        self, 
        data: np.ndarray, 
        embedding_dim: int, 
        tau: int
    ) -> np.ndarray:
        """
        Create time-delay embedding for phase space reconstruction.
        
        Args:
            data: 1D time series
            embedding_dim: Embedding dimension
            tau: Time delay
            
        Returns:
            Embedded trajectory of shape (n_points, embedding_dim)
        """
        n = len(data)
        m = embedding_dim
        
        if n < m * tau:
            return np.array([])
        
        embedded = np.zeros((n - (m-1) * tau, m))
        for i in range(m):
            embedded[:, i] = data[i*tau : n - (m-1-i)*tau]
        
        return embedded
    
    def compute_criticality_index(
        self, 
        logits_history: List[np.ndarray],
        window_size: int = 10
    ) -> float:
        """
        Compute criticality index κ (kappa).
        
        Systems at criticality (edge of chaos) exhibit:
        - Power-law distributions
        - Long-range correlations
        - Optimal information processing
        
        The criticality index measures how close the system is to a critical point.
        
        Args:
            logits_history: List of logit distributions over time
            window_size: Window for computing variance
            
        Returns:
            Criticality index κ (0 = subcritical, 1 = critical, >1 = supercritical)
        """
        if len(logits_history) < window_size:
            return 0.0
        
        # Compute entropy fluctuations
        entropies = []
        for logits in logits_history:
            # Convert logits to probabilities
            probs = self._softmax(logits)
            # Compute Shannon entropy
            entropy = -np.sum(probs * np.log(probs + 1e-10))
            entropies.append(entropy)
        
        entropies = np.array(entropies)
        
        # Compute variance of entropy in sliding windows
        variances = []
        for i in range(len(entropies) - window_size + 1):
            window = entropies[i:i + window_size]
            variances.append(np.var(window))
        
        if not variances:
            return 0.0
        
        # Criticality index: ratio of variance to mean entropy
        mean_entropy = np.mean(entropies)
        mean_variance = np.mean(variances)
        
        if mean_entropy < 1e-10:
            return 0.0
        
        kappa = mean_variance / mean_entropy
        return float(kappa)
    
    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        """Compute softmax probabilities."""
        exp_logits = np.exp(logits - np.max(logits))
        return exp_logits / np.sum(exp_logits)
    
    def detect_phase_transition(
        self,
        sequence: np.ndarray,
        window_size: int = 50
    ) -> Dict[str, any]:
        """
        Detect phase transitions in the sequence.
        
        Phase transitions manifest as sudden changes in:
        - Order parameters (variance, correlation length)
        - Entropy
        - Lyapunov exponents
        
        Args:
            sequence: Time series data
            window_size: Window for local analysis
            
        Returns:
            Dictionary with transition detection results
        """
        if len(sequence) < 2 * window_size:
            return {
                'transition_detected': False,
                'transition_points': [],
                'phase_regions': [],
            }
        
        # Compute local statistics in sliding windows
        n_windows = len(sequence) - window_size + 1
        local_variance = np.zeros(n_windows)
        local_entropy = np.zeros(n_windows)
        
        for i in range(n_windows):
            window = sequence[i:i + window_size]
            local_variance[i] = np.var(window)
            
            # Discrete entropy
            hist, _ = np.histogram(window, bins=20, density=True)
            hist = hist[hist > 0]
            local_entropy[i] = -np.sum(hist * np.log(hist))
        
        # Detect jumps in variance and entropy
        variance_changes = np.abs(np.diff(local_variance))
        entropy_changes = np.abs(np.diff(local_entropy))
        
        # Normalize
        if np.std(variance_changes) > 0:
            variance_changes = variance_changes / np.std(variance_changes)
        if np.std(entropy_changes) > 0:
            entropy_changes = entropy_changes / np.std(entropy_changes)
        
        # Combined change signal
        change_signal = variance_changes + entropy_changes
        
        # Threshold for transition detection
        threshold = np.mean(change_signal) + 2 * np.std(change_signal)
        
        transition_points = np.where(change_signal > threshold)[0]
        
        return {
            'transition_detected': len(transition_points) > 0,
            'transition_points': transition_points.tolist(),
            'n_transitions': len(transition_points),
            'max_change': float(np.max(change_signal)) if len(change_signal) > 0 else 0.0,
        }
    
    def feigenbaum_analysis(
        self,
        parameter_sequence: np.ndarray,
        values_sequence: np.ndarray,
    ) -> Dict[str, any]:
        """
        Perform Feigenbaum analysis to detect bifurcations.
        
        Bifurcations occur when a small change in a parameter causes a sudden
        qualitative change in system behavior. The Feigenbaum constant δ ≈ 4.669
        describes the universal rate of period-doubling bifurcations.
        
        Args:
            parameter_sequence: Control parameter values
            values_sequence: Corresponding system output values
            
        Returns:
            Dictionary with bifurcation analysis
        """
        if len(parameter_sequence) < 10 or len(values_sequence) < 10:
            return {
                'bifurcation_detected': False,
                'bifurcation_points': [],
            }
        
        # Detect sudden changes in the distribution of values
        window_size = max(5, len(values_sequence) // 20)
        bifurcation_points = []
        
        for i in range(len(values_sequence) - 2 * window_size):
            window1 = values_sequence[i:i + window_size]
            window2 = values_sequence[i + window_size:i + 2 * window_size]
            
            # Statistical test: are the distributions different?
            mean1, std1 = np.mean(window1), np.std(window1)
            mean2, std2 = np.mean(window2), np.std(window2)
            
            # Normalized change
            mean_change = abs(mean2 - mean1) / (abs(mean1) + 1e-10)
            std_change = abs(std2 - std1) / (abs(std1) + 1e-10)
            
            if mean_change > 0.5 or std_change > 0.5:
                bifurcation_points.append(i + window_size)
        
        return {
            'bifurcation_detected': len(bifurcation_points) > 0,
            'bifurcation_points': bifurcation_points,
            'n_bifurcations': len(bifurcation_points),
        }
    
    def compute_correlation_dimension(
        self,
        sequence: np.ndarray,
        embedding_dim: int = 3,
        tau: int = 1,
    ) -> float:
        """
        Compute correlation dimension (Grassberger-Procaccia algorithm).
        
        The correlation dimension D₂ is a measure of the dimensionality of
        the attractor in phase space. For chaotic systems, D₂ is typically
        non-integer (fractal dimension).
        
        Args:
            sequence: Time series data
            embedding_dim: Embedding dimension
            tau: Time delay
            
        Returns:
            Correlation dimension
        """
        if len(sequence) < embedding_dim * tau + 50:
            return float(embedding_dim)
        
        # Create phase space embedding
        embedded = self._time_delay_embedding(sequence, embedding_dim, tau)
        
        if len(embedded) < 50:
            return float(embedding_dim)
        
        # Compute pairwise distances
        n_points = min(len(embedded), 500)  # Limit for computational efficiency
        embedded_sample = embedded[:n_points]
        
        distances = []
        for i in range(n_points):
            for j in range(i + 1, n_points):
                dist = np.linalg.norm(embedded_sample[i] - embedded_sample[j])
                distances.append(dist)
        
        distances = np.array(distances)
        distances = distances[distances > 1e-10]
        
        if len(distances) == 0:
            return float(embedding_dim)
        
        # Compute correlation integral for different scales
        log_r = np.linspace(np.log(np.min(distances)), 
                           np.log(np.max(distances)), 20)
        log_C = []
        
        for lr in log_r:
            r = np.exp(lr)
            C = np.sum(distances < r) / len(distances)
            if C > 0:
                log_C.append(np.log(C))
            else:
                log_C.append(-np.inf)
        
        # Filter out infinite values
        valid_idx = np.isfinite(log_C)
        if np.sum(valid_idx) < 2:
            return float(embedding_dim)
        
        log_r_valid = log_r[valid_idx]
        log_C_valid = np.array(log_C)[valid_idx]
        
        # Fit slope: log(C) ~ D₂ * log(r)
        try:
            correlation_dim = np.polyfit(log_r_valid, log_C_valid, 1)[0]
            return float(np.clip(correlation_dim, 0.0, float(embedding_dim)))
        except (ValueError, np.linalg.LinAlgError):
            return float(embedding_dim)
