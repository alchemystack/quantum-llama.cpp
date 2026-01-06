"""
QRNG Stream Quality Monitor

Monitors quantum random number generator stream quality to detect bias, drift,
and other anomalies. Based on helios-trajectory-analysis repository.

Key Metrics:
- Hurst exponent: Measures long-range dependence and self-similarity
- Autocorrelation: Detects patterns in the stream
- Min-entropy: Measures randomness quality
- Bias detection: Statistical tests for non-uniform distribution
"""

import numpy as np
from collections import deque
from typing import Dict, List, Optional


class QRNGMonitor:
    """Monitor QRNG stream quality in real-time."""
    
    def __init__(self, history_len: int = 100):
        """
        Initialize QRNG monitor.
        
        Args:
            history_len: Number of samples to keep in history for analysis
        """
        self.history_len = history_len
        self.history = deque(maxlen=history_len)
        self.total_samples = 0
        self.anomaly_count = 0
        
    def update(self, byte_val: int) -> Dict[str, float]:
        """
        Update monitor with new QRNG byte value.
        
        Args:
            byte_val: Byte value from QRNG stream (0-255)
            
        Returns:
            Dictionary of current metrics
        """
        if not 0 <= byte_val <= 255:
            raise ValueError(f"byte_val must be in range 0-255, got {byte_val}")
            
        self.history.append(byte_val)
        self.total_samples += 1
        
        if len(self.history) < 10:
            # Not enough data yet
            return {
                'samples': len(self.history),
                'mean': float(np.mean(self.history)),
                'std': float(np.std(self.history)),
            }
        
        metrics = self._compute_metrics()
        
        # Check for anomalies
        if self._detect_anomaly(metrics):
            self.anomaly_count += 1
            metrics['anomaly_detected'] = True
        else:
            metrics['anomaly_detected'] = False
            
        return metrics
    
    def _compute_metrics(self) -> Dict[str, float]:
        """Compute all quality metrics on current history."""
        data = np.array(list(self.history))
        
        metrics = {
            'samples': len(self.history),
            'mean': float(np.mean(data)),
            'std': float(np.std(data)),
            'min': int(np.min(data)),
            'max': int(np.max(data)),
            'hurst': self._compute_hurst_exponent(data),
            'autocorr_lag1': self._compute_autocorrelation(data, lag=1),
            'min_entropy': self._compute_min_entropy(data),
            'chi_square_p': self._chi_square_uniformity_test(data),
        }
        
        return metrics
    
    def _compute_hurst_exponent(self, data: np.ndarray) -> float:
        """
        Compute Hurst exponent using rescaled range (R/S) analysis.
        
        H ~ 0.5: Random walk (ideal for QRNG)
        H > 0.5: Persistent (trending)
        H < 0.5: Anti-persistent (mean-reverting)
        """
        if len(data) < 20:
            return 0.5
        
        lags = range(2, min(len(data) // 2, 20))
        rs_values = []
        
        for lag in lags:
            # Split into chunks
            chunks = [data[i:i+lag] for i in range(0, len(data)-lag+1, lag)]
            if len(chunks) < 2:
                continue
                
            rs_chunk = []
            for chunk in chunks:
                if len(chunk) < 2:
                    continue
                mean_chunk = np.mean(chunk)
                y = np.cumsum(chunk - mean_chunk)
                r = np.max(y) - np.min(y)
                s = np.std(chunk)
                if s > 0:
                    rs_chunk.append(r / s)
            
            if rs_chunk:
                rs_values.append(np.mean(rs_chunk))
        
        if len(rs_values) < 2:
            return 0.5
        
        # Fit log(R/S) vs log(lag)
        try:
            log_lags = np.log(list(lags[:len(rs_values)]))
            log_rs = np.log(rs_values)
            hurst = np.polyfit(log_lags, log_rs, 1)[0]
            return float(np.clip(hurst, 0.0, 1.0))
        except (ValueError, np.linalg.LinAlgError):
            return 0.5
    
    def _compute_autocorrelation(self, data: np.ndarray, lag: int = 1) -> float:
        """
        Compute autocorrelation at given lag.
        
        Values close to 0 indicate independence (good for QRNG).
        """
        if len(data) < lag + 1:
            return 0.0
        
        mean = np.mean(data)
        var = np.var(data)
        
        if var == 0:
            return 0.0
        
        n = len(data)
        autocorr = np.sum((data[:n-lag] - mean) * (data[lag:] - mean)) / (n * var)
        return float(autocorr)
    
    def _compute_min_entropy(self, data: np.ndarray) -> float:
        """
        Compute min-entropy (most conservative entropy measure).
        
        Min-entropy = -log2(p_max) where p_max is the most frequent value's probability.
        Higher values indicate better randomness.
        """
        counts = np.bincount(data.astype(int), minlength=256)
        p_max = np.max(counts) / len(data)
        
        if p_max == 0:
            return 0.0
        
        min_entropy = -np.log2(p_max)
        return float(min_entropy)
    
    def _chi_square_uniformity_test(self, data: np.ndarray) -> float:
        """
        Chi-square test for uniform distribution.
        
        Returns p-value (higher is better, >0.05 means likely uniform).
        """
        from scipy import stats
        
        # Count frequencies for each byte value
        observed = np.bincount(data.astype(int), minlength=256)
        expected = np.full(256, len(data) / 256.0)
        
        # Chi-square test
        chi2, p_value = stats.chisquare(observed, expected)
        return float(p_value)
    
    def _detect_anomaly(self, metrics: Dict[str, float]) -> bool:
        """
        Detect anomalies in the QRNG stream.
        
        Anomaly conditions:
        - Hurst exponent significantly different from 0.5
        - High autocorrelation
        - Low min-entropy
        - Failed uniformity test
        """
        anomaly = False
        
        # Check Hurst exponent (should be near 0.5 for random walk)
        if abs(metrics['hurst'] - 0.5) > 0.2:
            anomaly = True
        
        # Check autocorrelation (should be near 0)
        if abs(metrics['autocorr_lag1']) > 0.3:
            anomaly = True
        
        # Check min-entropy (should be high, max is 8 bits)
        if metrics['min_entropy'] < 6.0:
            anomaly = True
        
        # Check uniformity test (p-value should be > 0.05)
        if metrics['chi_square_p'] < 0.01:  # Very low p-value
            anomaly = True
        
        return anomaly
    
    def get_summary(self) -> Dict[str, any]:
        """Get summary statistics."""
        return {
            'total_samples': self.total_samples,
            'anomaly_count': self.anomaly_count,
            'anomaly_rate': self.anomaly_count / max(1, self.total_samples),
            'current_history_size': len(self.history),
        }
    
    def reset(self):
        """Reset monitor state."""
        self.history.clear()
        self.total_samples = 0
        self.anomaly_count = 0
