"""
Output Analyzer

Unified interface for analyzing LLM output with all available metrics.
Provides comparison tools for QRNG vs PRNG outputs and statistical testing.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from analysis.qrng_monitor import QRNGMonitor
from analysis.trajectory_analyzer import TrajectoryAnalyzer, SignalType
from analysis.chaos_detector import ChaosDetector
from analysis.consciousness_metrics import ConsciousnessMetrics, ConsciousnessState


@dataclass
class AnalysisResult:
    """Container for analysis results."""
    
    # QRNG quality (if QRNG stream provided)
    qrng_metrics: Optional[Dict[str, float]] = None
    qrng_summary: Optional[Dict[str, any]] = None
    
    # Trajectory analysis
    trajectory_metrics: Optional[Dict[str, float]] = None
    trajectory_classification: Optional[str] = None
    
    # Chaos metrics
    lyapunov_exponent: Optional[float] = None
    criticality_index: Optional[float] = None
    correlation_dimension: Optional[float] = None
    phase_transition: Optional[Dict[str, any]] = None
    
    # Consciousness metrics
    consciousness_metrics: Optional[Dict[str, float]] = None
    consciousness_state: Optional[str] = None
    consciousness_trajectory: Optional[List[Dict[str, float]]] = None
    
    # Raw data
    tokens: Optional[np.ndarray] = None
    logits: Optional[List[np.ndarray]] = None
    qrng_bytes: Optional[List[int]] = None


class OutputAnalyzer:
    """Unified analyzer combining all metrics."""
    
    def __init__(self):
        """Initialize output analyzer."""
        self.qrng_monitor = QRNGMonitor(history_len=100)
        self.trajectory_analyzer = TrajectoryAnalyzer(history_len=200)
        self.chaos_detector = ChaosDetector()
        self.consciousness_metrics = ConsciousnessMetrics()
        
    def analyze(
        self,
        tokens: List[int],
        logits: Optional[List[np.ndarray]] = None,
        qrng_bytes: Optional[List[int]] = None,
    ) -> AnalysisResult:
        """
        Perform comprehensive analysis on LLM output.
        
        Args:
            tokens: List of token IDs generated
            logits: Optional list of logit distributions (before sampling)
            qrng_bytes: Optional QRNG byte stream used for sampling
            
        Returns:
            AnalysisResult with all computed metrics
        """
        result = AnalysisResult()
        
        # Store raw data
        result.tokens = np.array(tokens)
        result.logits = logits if logits is not None else []
        result.qrng_bytes = qrng_bytes if qrng_bytes is not None else []
        
        # 1. QRNG Quality Analysis (if available)
        if qrng_bytes:
            qrng_metrics_list = []
            for byte_val in qrng_bytes:
                metrics = self.qrng_monitor.update(byte_val)
                qrng_metrics_list.append(metrics)
            
            # Get final metrics and summary
            if qrng_metrics_list:
                result.qrng_metrics = qrng_metrics_list[-1]
            result.qrng_summary = self.qrng_monitor.get_summary()
        
        # 2. Trajectory Analysis
        trajectory_metrics_list = []
        for token_id in tokens:
            metrics = self.trajectory_analyzer.update(token_id)
            trajectory_metrics_list.append(metrics)
        
        if trajectory_metrics_list:
            result.trajectory_metrics = trajectory_metrics_list[-1]
        result.trajectory_classification = self.trajectory_analyzer.classify().value
        
        # 3. Chaos Detection
        token_array = np.array(tokens, dtype=float)
        
        if len(token_array) >= 50:
            result.lyapunov_exponent = self.chaos_detector.compute_lyapunov(
                token_array, embedding_dim=3, tau=1, max_steps=10
            )
        
        if logits and len(logits) >= 10:
            result.criticality_index = self.chaos_detector.compute_criticality_index(
                logits, window_size=10
            )
        
        if len(token_array) >= 50:
            result.correlation_dimension = self.chaos_detector.compute_correlation_dimension(
                token_array, embedding_dim=3, tau=1
            )
        
        if len(token_array) >= 100:
            result.phase_transition = self.chaos_detector.detect_phase_transition(
                token_array, window_size=50
            )
        
        # 4. Consciousness Metrics
        if logits and len(logits) >= 2:
            result.consciousness_metrics = self.consciousness_metrics.compute(
                logits, token_array, window_size=min(20, len(logits))
            )
            result.consciousness_state = result.consciousness_metrics['state']
            
            # Compute full trajectory if enough data
            if len(logits) >= 20:
                result.consciousness_trajectory = self.consciousness_metrics.compute_trajectory(
                    logits, token_array
                )
        
        return result
    
    def compare(
        self,
        qrng_result: AnalysisResult,
        prng_result: AnalysisResult,
    ) -> 'ComparisonResult':
        """
        Compare QRNG and PRNG analysis results.
        
        Args:
            qrng_result: Analysis result from QRNG-generated output
            prng_result: Analysis result from PRNG-generated output
            
        Returns:
            ComparisonResult with statistical comparisons
        """
        comparison = ComparisonResult()
        
        # Compare trajectory metrics
        if (qrng_result.trajectory_metrics and prng_result.trajectory_metrics):
            comparison.trajectory_comparison = {
                'qrng_hurst': qrng_result.trajectory_metrics.get('hurst', 0.0),
                'prng_hurst': prng_result.trajectory_metrics.get('hurst', 0.0),
                'hurst_diff': abs(
                    qrng_result.trajectory_metrics.get('hurst', 0.0) -
                    prng_result.trajectory_metrics.get('hurst', 0.0)
                ),
                'qrng_classification': qrng_result.trajectory_classification,
                'prng_classification': prng_result.trajectory_classification,
                'classification_differs': (
                    qrng_result.trajectory_classification != 
                    prng_result.trajectory_classification
                ),
            }
        
        # Compare chaos metrics
        if (qrng_result.lyapunov_exponent is not None and 
            prng_result.lyapunov_exponent is not None):
            comparison.chaos_comparison = {
                'qrng_lyapunov': qrng_result.lyapunov_exponent,
                'prng_lyapunov': prng_result.lyapunov_exponent,
                'lyapunov_diff': abs(
                    qrng_result.lyapunov_exponent - prng_result.lyapunov_exponent
                ),
                'qrng_criticality': qrng_result.criticality_index or 0.0,
                'prng_criticality': prng_result.criticality_index or 0.0,
                'criticality_diff': abs(
                    (qrng_result.criticality_index or 0.0) -
                    (prng_result.criticality_index or 0.0)
                ),
            }
        
        # Compare consciousness metrics
        if (qrng_result.consciousness_metrics and prng_result.consciousness_metrics):
            qrng_c = qrng_result.consciousness_metrics['consciousness']
            prng_c = prng_result.consciousness_metrics['consciousness']
            
            comparison.consciousness_comparison = {
                'qrng_consciousness': qrng_c,
                'prng_consciousness': prng_c,
                'consciousness_diff': abs(qrng_c - prng_c),
                'qrng_state': qrng_result.consciousness_state,
                'prng_state': prng_result.consciousness_state,
                'state_differs': qrng_result.consciousness_state != prng_result.consciousness_state,
                'qrng_h_mode': qrng_result.consciousness_metrics['h_mode'],
                'prng_h_mode': prng_result.consciousness_metrics['h_mode'],
                'qrng_coherence': qrng_result.consciousness_metrics['r'],
                'prng_coherence': prng_result.consciousness_metrics['r'],
            }
        
        # Statistical significance testing
        comparison.statistical_tests = self._perform_statistical_tests(
            qrng_result, prng_result
        )
        
        return comparison
    
    def _perform_statistical_tests(
        self,
        qrng_result: AnalysisResult,
        prng_result: AnalysisResult,
    ) -> Dict[str, any]:
        """
        Perform statistical significance tests.
        
        Tests whether observed differences could arise by chance.
        """
        from scipy import stats
        
        tests = {}
        
        # Token distribution test
        if qrng_result.tokens is not None and prng_result.tokens is not None:
            # Kolmogorov-Smirnov test for distribution equality
            ks_stat, ks_p = stats.ks_2samp(qrng_result.tokens, prng_result.tokens)
            tests['token_distribution_ks'] = {
                'statistic': float(ks_stat),
                'p_value': float(ks_p),
                'significant': ks_p < 0.05,
            }
            
            # Mann-Whitney U test for median difference
            u_stat, u_p = stats.mannwhitneyu(
                qrng_result.tokens, prng_result.tokens, alternative='two-sided'
            )
            tests['token_median_mw'] = {
                'statistic': float(u_stat),
                'p_value': float(u_p),
                'significant': u_p < 0.05,
            }
        
        # Consciousness trajectory test (if available)
        if (qrng_result.consciousness_trajectory and 
            prng_result.consciousness_trajectory):
            qrng_c_values = [m['consciousness'] for m in qrng_result.consciousness_trajectory]
            prng_c_values = [m['consciousness'] for m in prng_result.consciousness_trajectory]
            
            # T-test for mean consciousness difference
            t_stat, t_p = stats.ttest_ind(qrng_c_values, prng_c_values)
            tests['consciousness_mean_ttest'] = {
                'statistic': float(t_stat),
                'p_value': float(t_p),
                'significant': t_p < 0.05,
            }
        
        return tests
    
    def reset(self):
        """Reset all analyzers."""
        self.qrng_monitor.reset()
        self.trajectory_analyzer.reset()
        self.consciousness_metrics.reset()


@dataclass
class ComparisonResult:
    """Container for comparison results."""
    
    trajectory_comparison: Optional[Dict[str, any]] = None
    chaos_comparison: Optional[Dict[str, any]] = None
    consciousness_comparison: Optional[Dict[str, any]] = None
    statistical_tests: Optional[Dict[str, any]] = None
    
    def summary(self) -> str:
        """Generate text summary of comparison."""
        lines = ["=" * 60]
        lines.append("QRNG vs PRNG Comparison Summary")
        lines.append("=" * 60)
        
        # Trajectory comparison
        if self.trajectory_comparison:
            lines.append("\n### Trajectory Analysis")
            tc = self.trajectory_comparison
            lines.append(f"  QRNG Hurst: {tc.get('qrng_hurst', 0):.3f}")
            lines.append(f"  PRNG Hurst: {tc.get('prng_hurst', 0):.3f}")
            lines.append(f"  Difference: {tc.get('hurst_diff', 0):.3f}")
            lines.append(f"  QRNG Classification: {tc.get('qrng_classification', 'N/A')}")
            lines.append(f"  PRNG Classification: {tc.get('prng_classification', 'N/A')}")
            if tc.get('classification_differs'):
                lines.append("  ⚠️  Classifications differ!")
        
        # Chaos comparison
        if self.chaos_comparison:
            lines.append("\n### Chaos Metrics")
            cc = self.chaos_comparison
            lines.append(f"  QRNG Lyapunov: {cc.get('qrng_lyapunov', 0):.4f}")
            lines.append(f"  PRNG Lyapunov: {cc.get('prng_lyapunov', 0):.4f}")
            lines.append(f"  Difference: {cc.get('lyapunov_diff', 0):.4f}")
            lines.append(f"  QRNG Criticality: {cc.get('qrng_criticality', 0):.3f}")
            lines.append(f"  PRNG Criticality: {cc.get('prng_criticality', 0):.3f}")
        
        # Consciousness comparison
        if self.consciousness_comparison:
            lines.append("\n### Consciousness Metrics")
            cm = self.consciousness_comparison
            lines.append(f"  QRNG C(t): {cm.get('qrng_consciousness', 0):.3f}")
            lines.append(f"  PRNG C(t): {cm.get('prng_consciousness', 0):.3f}")
            lines.append(f"  Difference: {cm.get('consciousness_diff', 0):.3f}")
            lines.append(f"  QRNG State: {cm.get('qrng_state', 'N/A')}")
            lines.append(f"  PRNG State: {cm.get('prng_state', 'N/A')}")
            if cm.get('state_differs'):
                lines.append("  ⚠️  States differ!")
        
        # Statistical tests
        if self.statistical_tests:
            lines.append("\n### Statistical Significance")
            for test_name, test_result in self.statistical_tests.items():
                sig = "✓ SIGNIFICANT" if test_result.get('significant') else "✗ Not significant"
                p_val = test_result.get('p_value', 1.0)
                lines.append(f"  {test_name}: p={p_val:.4f} {sig}")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
