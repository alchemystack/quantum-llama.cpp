"""
Python Analysis Toolkit for quantum-llama.cpp

This toolkit provides analysis capabilities to validate whether QRNG-based token
sampling produces qualitatively different output compared to PRNG.

Modules:
- qrng_monitor: QRNG stream quality monitoring
- trajectory_analyzer: Token trajectory analysis
- chaos_detector: Chaos theory metrics
- consciousness_metrics: Consciousness functional metrics
- output_analyzer: Combined analysis pipeline
"""

from analysis.qrng_monitor import QRNGMonitor
from analysis.trajectory_analyzer import TrajectoryAnalyzer
from analysis.chaos_detector import ChaosDetector
from analysis.consciousness_metrics import ConsciousnessMetrics
from analysis.output_analyzer import OutputAnalyzer

__all__ = [
    'QRNGMonitor',
    'TrajectoryAnalyzer',
    'ChaosDetector',
    'ConsciousnessMetrics',
    'OutputAnalyzer',
]

__version__ = '1.0.0'
