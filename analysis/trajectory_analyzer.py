"""
Token Trajectory Analysis

Analyzes token sequences as trajectories in phase space to detect patterns,
attractors, and classify the type of motion. Based on helios-trajectory-analysis.

Classification Types:
- NOISE: Random fluctuation with no structure
- DRIFT: Persistent directional movement
- ATTRACTOR: Convergence toward fixed points
- PERIODIC: Oscillatory behavior
- CHAOTIC: Deterministic but unpredictable
- INFLUENCE: Coherent patterns suggesting non-random structure
"""

import numpy as np
from collections import deque
from typing import Dict, List, Optional, Tuple
from enum import Enum


class SignalType(Enum):
    """Classification of trajectory behavior."""
    NOISE = "NOISE"
    DRIFT = "DRIFT"
    ATTRACTOR = "ATTRACTOR"
    PERIODIC = "PERIODIC"
    CHAOTIC = "CHAOTIC"
    INFLUENCE = "INFLUENCE"


class TrajectoryAnalyzer:
    """Analyze token sequences as trajectories in phase space."""
    
    def __init__(self, history_len: int = 200, embedding_dim: int = 3):
        """
        Initialize trajectory analyzer.
        
        Args:
            history_len: Number of tokens to keep in history
            embedding_dim: Dimension for phase space embedding
        """
        self.history_len = history_len
        self.embedding_dim = embedding_dim
        self.token_history = deque(maxlen=history_len)
        self.metrics_history = []
        
    def update(self, token_id: int) -> Dict[str, float]:
        """
        Update analyzer with new token.
        
        Args:
            token_id: Token ID from model output
            
        Returns:
            Dictionary of trajectory metrics
        """
        self.token_history.append(token_id)
        
        if len(self.token_history) < self.embedding_dim + 10:
            # Not enough data yet
            return {
                'tokens': len(self.token_history),
                'hurst': 0.5,
                'lyapunov': 0.0,
            }
        
        metrics = self._compute_metrics()
        self.metrics_history.append(metrics)
        
        return metrics
    
    def _compute_metrics(self) -> Dict[str, float]:
        """Compute all trajectory metrics."""
        tokens = np.array(list(self.token_history))
        
        # Normalize token IDs to [0, 1] range
        if len(tokens) > 1 and np.max(tokens) > np.min(tokens):
            tokens_norm = (tokens - np.min(tokens)) / (np.max(tokens) - np.min(tokens))
        else:
            tokens_norm = tokens / (np.max(tokens) + 1e-10)
        
        metrics = {
            'tokens': len(self.token_history),
            'hurst': self._compute_hurst(tokens_norm),
            'lyapunov': self._compute_lyapunov_estimate(tokens_norm),
            'diffusion_coefficient': self._compute_diffusion_coefficient(tokens_norm),
            'attractor_strength': self._compute_attractor_strength(tokens_norm),
            'periodicity_score': self._compute_periodicity_score(tokens_norm),
        }
        
        return metrics
    
    def _compute_hurst(self, data: np.ndarray) -> float:
        """
        Compute Hurst exponent.
        
        H = 0.5: Brownian motion (random walk)
        H > 0.5: Persistent motion (trending)
        H < 0.5: Anti-persistent motion (mean-reverting)
        """
        if len(data) < 20:
            return 0.5
        
        lags = range(2, min(len(data) // 2, 20))
        rs_values = []
        
        for lag in lags:
            chunks = [data[i:i+lag] for i in range(0, len(data)-lag+1, lag)]
            if len(chunks) < 2:
                continue
            
            rs_chunk = []
            for chunk in chunks:
                if len(chunk) < 2:
                    continue
                mean = np.mean(chunk)
                y = np.cumsum(chunk - mean)
                r = np.max(y) - np.min(y)
                s = np.std(chunk)
                if s > 0:
                    rs_chunk.append(r / s)
            
            if rs_chunk:
                rs_values.append(np.mean(rs_chunk))
        
        if len(rs_values) < 2:
            return 0.5
        
        try:
            log_lags = np.log(list(lags[:len(rs_values)]))
            log_rs = np.log(rs_values)
            hurst = np.polyfit(log_lags, log_rs, 1)[0]
            return float(np.clip(hurst, 0.0, 1.0))
        except (ValueError, np.linalg.LinAlgError):
            return 0.5
    
    def _compute_lyapunov_estimate(self, data: np.ndarray) -> float:
        """
        Estimate largest Lyapunov exponent (simplified).
        
        Positive: Chaotic behavior (exponential divergence)
        Zero: Stable periodic
        Negative: Converging to attractor
        """
        if len(data) < 50:
            return 0.0
        
        # Use phase space embedding
        embedding = self._phase_space_embedding(data)
        
        if len(embedding) < 10:
            return 0.0
        
        # Compute divergence rates
        divergences = []
        for i in range(len(embedding) - 5):
            # Find nearest neighbor
            dists = np.linalg.norm(embedding - embedding[i], axis=1)
            dists[i] = np.inf  # Exclude self
            nearest_idx = np.argmin(dists)
            
            if nearest_idx + 5 < len(embedding):
                # Measure divergence after 5 steps
                d0 = dists[nearest_idx]
                d5 = np.linalg.norm(embedding[i+5] - embedding[nearest_idx+5])
                
                if d0 > 1e-10 and d5 > 1e-10:
                    divergences.append(np.log(d5 / d0) / 5)
        
        if not divergences:
            return 0.0
        
        return float(np.median(divergences))
    
    def _phase_space_embedding(self, data: np.ndarray, tau: int = 1) -> np.ndarray:
        """
        Create phase space embedding using time-delay method.
        
        Args:
            data: Time series data
            tau: Time delay
            
        Returns:
            Embedded trajectory of shape (n_points, embedding_dim)
        """
        n = len(data)
        m = self.embedding_dim
        
        if n < m * tau:
            return np.array([])
        
        embedded = np.zeros((n - (m-1) * tau, m))
        for i in range(m):
            embedded[:, i] = data[i*tau : n - (m-1-i)*tau]
        
        return embedded
    
    def _compute_diffusion_coefficient(self, data: np.ndarray) -> float:
        """
        Compute diffusion coefficient (mean squared displacement growth rate).
        
        Higher values indicate more diffusive (random) motion.
        """
        if len(data) < 10:
            return 0.0
        
        lags = range(1, min(len(data) // 2, 20))
        msd_values = []
        
        for lag in lags:
            displacements = data[lag:] - data[:-lag]
            msd = np.mean(displacements ** 2)
            msd_values.append(msd)
        
        if len(msd_values) < 2:
            return 0.0
        
        # Fit MSD ~ lag^alpha to extract diffusion coefficient
        try:
            log_lags = np.log(list(lags[:len(msd_values)]))
            log_msd = np.log(np.array(msd_values) + 1e-10)
            alpha = np.polyfit(log_lags, log_msd, 1)[0]
            return float(np.clip(alpha, 0.0, 2.0))
        except (ValueError, np.linalg.LinAlgError):
            return 1.0
    
    def _compute_attractor_strength(self, data: np.ndarray) -> float:
        """
        Measure strength of attractor dynamics.
        
        Higher values indicate stronger convergence to fixed points.
        """
        if len(data) < 20:
            return 0.0
        
        # Compute return map (x[i+1] vs x[i])
        x = data[:-1]
        y = data[1:]
        
        # Measure correlation
        if np.std(x) > 0 and np.std(y) > 0:
            correlation = np.corrcoef(x, y)[0, 1]
        else:
            correlation = 0.0
        
        # High correlation indicates attractor-like behavior
        return float(abs(correlation))
    
    def _compute_periodicity_score(self, data: np.ndarray) -> float:
        """
        Detect periodic behavior using autocorrelation.
        
        Higher values indicate stronger periodicity.
        """
        if len(data) < 20:
            return 0.0
        
        # Compute autocorrelation for multiple lags
        mean = np.mean(data)
        var = np.var(data)
        
        if var == 0:
            return 0.0
        
        max_lag = min(len(data) // 2, 50)
        autocorr = np.zeros(max_lag)
        
        for lag in range(1, max_lag):
            autocorr[lag] = np.sum((data[:len(data)-lag] - mean) * 
                                   (data[lag:] - mean)) / (len(data) * var)
        
        # Find peaks in autocorrelation (excluding lag 0)
        peaks = []
        for i in range(2, len(autocorr)-2):
            if (autocorr[i] > autocorr[i-1] and autocorr[i] > autocorr[i+1] and
                autocorr[i] > 0.2):
                peaks.append(autocorr[i])
        
        if peaks:
            return float(np.max(peaks))
        return 0.0
    
    def classify(self) -> SignalType:
        """
        Classify the current trajectory.
        
        Returns:
            SignalType classification
        """
        if len(self.token_history) < 50:
            return SignalType.NOISE
        
        metrics = self._compute_metrics()
        
        # Decision tree for classification
        hurst = metrics['hurst']
        lyapunov = metrics['lyapunov']
        diffusion = metrics['diffusion_coefficient']
        attractor = metrics['attractor_strength']
        periodicity = metrics['periodicity_score']
        
        # Chaotic: positive Lyapunov exponent
        if lyapunov > 0.1:
            return SignalType.CHAOTIC
        
        # Periodic: high periodicity score
        if periodicity > 0.5:
            return SignalType.PERIODIC
        
        # Attractor: high attractor strength
        if attractor > 0.7:
            return SignalType.ATTRACTOR
        
        # Drift: high Hurst exponent (persistent)
        if hurst > 0.65:
            return SignalType.DRIFT
        
        # Influence: combination of moderate structure
        if attractor > 0.5 or periodicity > 0.3:
            return SignalType.INFLUENCE
        
        # Default: random noise
        return SignalType.NOISE
    
    def get_summary(self) -> Dict[str, any]:
        """Get trajectory summary."""
        if not self.metrics_history:
            return {'classification': SignalType.NOISE.value}
        
        recent_metrics = self.metrics_history[-10:] if len(self.metrics_history) >= 10 else self.metrics_history
        
        return {
            'classification': self.classify().value,
            'avg_hurst': float(np.mean([m['hurst'] for m in recent_metrics])),
            'avg_lyapunov': float(np.mean([m['lyapunov'] for m in recent_metrics])),
            'total_tokens': len(self.token_history),
        }
    
    def reset(self):
        """Reset analyzer state."""
        self.token_history.clear()
        self.metrics_history.clear()
