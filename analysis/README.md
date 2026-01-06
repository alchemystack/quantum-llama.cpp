# Python Analysis Toolkit for quantum-llama.cpp

A comprehensive Python toolkit for analyzing quantum vs pseudorandom number generation in LLM token sampling. This toolkit helps validate whether QRNG-based sampling produces qualitatively different output compared to standard PRNG.

## Overview

This toolkit integrates analysis capabilities from three research domains:

- **helios-trajectory-analysis**: QRNG stream monitoring and trajectory analysis
- **qpt-research**: Chaos theory metrics (Lyapunov exponent, criticality)
- **harmonic-field-consciousness**: Consciousness functional metrics

## Installation

### Prerequisites

- Python 3.9+
- numpy
- scipy
- matplotlib

### Setup

```bash
# Install dependencies
pip install -r analysis/requirements.txt

# Or use the project's virtual environment
source .venv/bin/activate
pip install -r analysis/requirements.txt
```

## Modules

### 1. QRNG Monitor (`qrng_monitor.py`)

Monitors quantum random number generator stream quality to detect bias, drift, and anomalies.

**Key Metrics:**
- **Hurst exponent**: Measures long-range dependence (ideal: ~0.5)
- **Autocorrelation**: Detects patterns in the stream (ideal: ~0)
- **Min-entropy**: Measures randomness quality (higher is better)
- **Chi-square test**: Tests for uniform distribution

**Usage:**
```python
from analysis import QRNGMonitor

monitor = QRNGMonitor(history_len=100)
for byte_val in qrng_stream:
    metrics = monitor.update(byte_val)
    if metrics.get('anomaly_detected'):
        print(f"⚠️ QRNG anomaly: {metrics}")
```

### 2. Trajectory Analyzer (`trajectory_analyzer.py`)

Analyzes token sequences as trajectories in phase space to detect patterns and classify motion types.

**Classification Types:**
- **NOISE**: Random fluctuation with no structure
- **DRIFT**: Persistent directional movement  
- **ATTRACTOR**: Convergence toward fixed points
- **PERIODIC**: Oscillatory behavior
- **CHAOTIC**: Deterministic but unpredictable
- **INFLUENCE**: Coherent patterns suggesting non-random structure

**Usage:**
```python
from analysis import TrajectoryAnalyzer

analyzer = TrajectoryAnalyzer()
for token_id in generated_tokens:
    result = analyzer.update(token_id)
    print(f"Hurst: {result['hurst']:.3f}, Lyapunov: {result['lyapunov']:.3f}")

classification = analyzer.classify()
# Returns: NOISE, DRIFT, ATTRACTOR, PERIODIC, CHAOTIC, or INFLUENCE
```

### 3. Chaos Detector (`chaos_detector.py`)

Implements chaos theory metrics for analyzing LLM output dynamics.

**Metrics:**
- **Lyapunov exponent**: Measures sensitivity to initial conditions
  - λ > 0: Chaotic (exponential divergence)
  - λ = 0: Neutral stability (periodic)
  - λ < 0: Stable (converging)
- **Criticality index**: Detects phase transitions and edge-of-chaos behavior
- **Correlation dimension**: Measures attractor dimensionality
- **Phase transition detection**: Identifies regime changes

**Usage:**
```python
from analysis import ChaosDetector

detector = ChaosDetector()
lyapunov = detector.compute_lyapunov(token_sequence)
criticality = detector.compute_criticality_index(logits_history)

if lyapunov > 0:
    print("Chaotic regime - high sensitivity to QRNG")
else:
    print("Stable regime - QRNG has less impact")
```

### 4. Consciousness Metrics (`consciousness_metrics.py`)

Computes consciousness functional C(t) based on harmonic-field-consciousness theory.

**Metrics:**
- **Mode entropy (H_mode)**: Information content across states
- **Participation ratio (PR)**: Number of effectively participating modes
- **Phase coherence (R)**: Alignment of oscillatory components
- **Entropy production rate (Ṡ)**: Rate of information generation
- **Criticality index (κ)**: Proximity to critical state
- **Consciousness functional C(t)**: Combined metric

**State Classification:**
- **CREATIVE**: High entropy + high coherence + critical (wake-like)
- **MECHANICAL**: Low entropy + high coherence (deterministic)
- **DREAMING**: High entropy + low coherence (incoherent exploration)

**Usage:**
```python
from analysis import ConsciousnessMetrics

metrics = ConsciousnessMetrics()
result = metrics.compute(logits_history, token_sequence)

print(f"Mode Entropy: {result['h_mode']:.3f}")
print(f"Participation Ratio: {result['pr']:.3f}")
print(f"Consciousness Functional C(t): {result['consciousness']:.3f}")
print(f"State: {result['state']}")  # 'creative', 'mechanical', 'dreaming'
```

### 5. Output Analyzer (`output_analyzer.py`)

Unified interface for comprehensive analysis and comparison of QRNG vs PRNG outputs.

**Features:**
- Combines all analysis modules
- Statistical significance testing
- Side-by-side comparison
- Report generation

**Usage:**
```python
from analysis import OutputAnalyzer

analyzer = OutputAnalyzer()

# Analyze QRNG-generated output
qrng_result = analyzer.analyze(
    tokens=qrng_tokens,
    logits=qrng_logits,
    qrng_bytes=qrng_stream
)

# Analyze PRNG-generated output (same prompt, different seed)
prng_result = analyzer.analyze(
    tokens=prng_tokens,
    logits=prng_logits
)

# Compare
comparison = analyzer.compare(qrng_result, prng_result)
print(comparison.summary())
```

## Example Scripts

Three complete examples are provided in `analysis/examples/`:

### 1. `analyze_qrng_stream.py`

Monitor ANU QRNG stream quality in real-time.

```bash
python analysis/examples/analyze_qrng_stream.py
```

**Output:**
- Per-sample quality metrics
- Anomaly detection
- Summary statistics
- Health assessment

### 2. `compare_qrng_vs_prng.py`

A/B comparison of QRNG vs PRNG outputs.

```bash
python analysis/examples/compare_qrng_vs_prng.py
```

**Output:**
- Side-by-side metric comparison
- Statistical significance tests
- Interpretation of differences

### 3. `consciousness_scoring.py`

Score generated text using consciousness metrics.

```bash
python analysis/examples/consciousness_scoring.py
```

**Output:**
- Consciousness trajectory over time
- State classification distribution
- Interpretation and recommendations

## Testing the Core Hypothesis

This toolkit enables testing the fundamental hypothesis of quantum-llama.cpp:

> **"Does quantum randomness produce qualitatively different LLM output compared to pseudorandom sampling?"**

### Experimental Protocol

1. **Generate with QRNG:**
   ```bash
   export ANU_API_KEY="your-key"
   ./build/bin/llama-cli -m model.gguf -p "prompt" -n 200 --quantum-verbose > qrng_output.txt
   ```

2. **Generate with PRNG (same prompt):**
   ```bash
   ./build/bin/llama-cli -m model.gguf -p "prompt" -n 200 --seed 42 > prng_output.txt
   ```

3. **Extract data for analysis:**
   - Token IDs (from output or via modification to save)
   - Logits (requires code modification to export)
   - QRNG bytes (from verbose output)

4. **Run comparison:**
   ```python
   from analysis import OutputAnalyzer
   
   analyzer = OutputAnalyzer()
   qrng_result = analyzer.analyze(qrng_tokens, qrng_logits, qrng_bytes)
   prng_result = analyzer.analyze(prng_tokens, prng_logits)
   
   comparison = analyzer.compare(qrng_result, prng_result)
   print(comparison.summary())
   ```

5. **Interpret results:**
   - Look for statistically significant differences (p < 0.05)
   - Compare consciousness states and metrics
   - Assess trajectory classifications
   - Examine chaos indicators

## Integration with quantum-llama.cpp

### Exporting Data for Analysis

To analyze real quantum-llama.cpp output, you'll need to export:

1. **Token IDs**: Modify `llama-cli` to save token sequence to file
2. **Logits**: Add flag to export pre-sampling logit distributions
3. **QRNG bytes**: Already available with `--quantum-verbose`

Example modification to export data:

```cpp
// In llama-cli main loop after sampling:
if (params.export_analysis_data) {
    // Export token ID
    fprintf(analysis_file, "token: %d\n", token_id);
    
    // Export logits (top-k for efficiency)
    fprintf(analysis_file, "logits: ");
    for (int i = 0; i < k; i++) {
        fprintf(analysis_file, "%.4f ", logits[i]);
    }
    fprintf(analysis_file, "\n");
    
    // Export QRNG byte if quantum sampling was used
    if (used_quantum) {
        fprintf(analysis_file, "qrng_byte: %d\n", qrng_byte);
    }
}
```

## Scientific Foundations

### Chaos Theory and LLMs

Chaotic systems exhibit exponential sensitivity to initial conditions. If LLM token sampling operates in a chaotic regime, small differences in random number sources could amplify into significant output differences.

**Key Insight**: Positive Lyapunov exponents indicate regimes where QRNG vs PRNG could matter most.

### Consciousness Functional

The consciousness functional C(t) combines information-theoretic and dynamical measures to classify generation states. High C(t) indicates "wake-like" generation with both exploration (entropy) and structure (coherence).

**Hypothesis**: If consciousness can influence quantum measurement, it would manifest during high-C(t) generation states.

### Phase Space Trajectories

Viewing token sequences as trajectories in reconstructed phase space allows detection of:
- Attractors (stable patterns)
- Strange attractors (chaotic patterns)
- Bifurcations (regime changes)
- Diffusive vs ballistic motion

**Application**: Different trajectory types may respond differently to QRNG vs PRNG.

## Limitations and Considerations

1. **Sample Size**: Many metrics require substantial data (100+ tokens) for reliable estimates

2. **Noise Sensitivity**: Some metrics (especially Lyapunov exponents) can be sensitive to numerical noise

3. **Interpretation**: Statistical significance doesn't prove causation; multiple runs and controls are essential

4. **Computational Cost**: Phase space reconstructions and correlation integrals scale with O(n²)

5. **Model Dependence**: Different models may show different sensitivities to RNG sources

## References

This toolkit is adapted from:

- **helios-trajectory-analysis**: https://github.com/vikingdude81/helios-trajectory-analysis
- **qpt-research**: https://github.com/vikingdude81/qpt-research
- **harmonic-field-consciousness**: https://github.com/vikingdude81/harmonic-field-consciousness

### Key Papers

- Rosenstein et al. (1993): "A practical method for calculating largest Lyapunov exponents"
- Grassberger & Procaccia (1983): "Measuring the strangeness of strange attractors"
- Takens (1981): "Detecting strange attractors in turbulence"
- Shannon (1948): "A mathematical theory of communication"

## Contributing

Contributions welcome! Areas for enhancement:

- Additional statistical tests
- Visualization tools (matplotlib integration)
- Real-time monitoring dashboard
- Model-specific tuning parameters
- Extended time series analysis

## License

MIT License (same as quantum-llama.cpp)
