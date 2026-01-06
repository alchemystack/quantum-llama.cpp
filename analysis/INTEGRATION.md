# Integrating Analysis Toolkit with quantum-llama.cpp

This guide explains how to export data from quantum-llama.cpp for analysis with the Python toolkit.

## Quick Start with Simulated Data

All example scripts include simulated data, so you can test immediately:

```bash
# Install dependencies
pip install -r analysis/requirements.txt

# Run examples
python analysis/examples/analyze_qrng_stream.py
python analysis/examples/compare_qrng_vs_prng.py
python analysis/examples/consciousness_scoring.py
```

## Analyzing Real Output

To analyze real quantum-llama.cpp output, you need to export three types of data:

### 1. QRNG Bytes (Already Available)

Use `--quantum-verbose` to see QRNG byte values:

```bash
./build/bin/llama-cli -m model.gguf -p "prompt" -n 100 --quantum-verbose 2>&1 | grep "mode=" > qrng_bytes.txt
```

Parse the output to extract byte values:
```python
qrng_bytes = []
with open('qrng_bytes.txt') as f:
    for line in f:
        # Parse lines like: "Quantum random value: mode=127, output=0.496094"
        if 'mode=' in line:
            mode = int(line.split('mode=')[1].split(',')[0])
            qrng_bytes.append(mode)
```

### 2. Token IDs (Manual Export Required)

**Option A: Parse generated text**

If you have the detokenizer, you can reverse the process, but this is lossy.

**Option B: Modify llama-cli (Recommended)**

Add token export to `examples/main/main.cpp`:

```cpp
// After token sampling in the generation loop:
if (params.export_tokens) {
    fprintf(params.token_file, "%d\n", token);
}
```

Then compile and run:
```bash
./build/bin/llama-cli -m model.gguf -p "prompt" -n 100 --export-tokens tokens.txt
```

### 3. Logits (Manual Export Required)

Logits are needed for consciousness metrics and criticality analysis.

**Modify llama-cli to export logits:**

```cpp
// In the sampling code, before token selection:
if (params.export_logits) {
    const float* logits = llama_get_logits(ctx);
    const int n_vocab = llama_n_vocab(model);
    
    // Export top-k logits for efficiency (e.g., k=100)
    std::vector<std::pair<float, int>> top_logits;
    for (int i = 0; i < n_vocab; i++) {
        top_logits.push_back({logits[i], i});
    }
    std::partial_sort(top_logits.begin(), top_logits.begin() + 100, 
                     top_logits.end(), std::greater<>());
    
    for (int i = 0; i < 100; i++) {
        fprintf(params.logits_file, "%.6f ", top_logits[i].first);
    }
    fprintf(params.logits_file, "\n");
}
```

## Full Analysis Pipeline

Once you have all three data sources:

```python
from analysis import OutputAnalyzer
import numpy as np

# Load your exported data
tokens = np.loadtxt('tokens.txt', dtype=int).tolist()
qrng_bytes = []  # Parse from verbose output
logits = []      # Parse from logits file
for line in open('logits.txt'):
    logits.append(np.array([float(x) for x in line.strip().split()]))

# Analyze QRNG run
analyzer = OutputAnalyzer()
qrng_result = analyzer.analyze(
    tokens=tokens,
    logits=logits,
    qrng_bytes=qrng_bytes
)

# Compare with PRNG run (same prompt, --seed N)
prng_tokens = np.loadtxt('prng_tokens.txt', dtype=int).tolist()
prng_logits = []  # Load PRNG logits
for line in open('prng_logits.txt'):
    prng_logits.append(np.array([float(x) for x in line.strip().split()]))

analyzer.reset()
prng_result = analyzer.analyze(
    tokens=prng_tokens,
    logits=prng_logits
)

# Compare
comparison = analyzer.compare(qrng_result, prng_result)
print(comparison.summary())
```

## Minimal C++ Modifications

If you want to add export capabilities without extensive changes:

### 1. Add CLI Arguments

In `common/common.cpp`, add new parameters:

```cpp
struct common_params {
    // ... existing fields ...
    std::string export_tokens_file;
    std::string export_logits_file;
    bool export_analysis_data = false;
};
```

Parse arguments:
```cpp
if (arg == "--export-tokens") {
    params.export_tokens_file = argv[++i];
    params.export_analysis_data = true;
}
if (arg == "--export-logits") {
    params.export_logits_file = argv[++i];
    params.export_analysis_data = true;
}
```

### 2. Open Export Files

```cpp
FILE* token_file = nullptr;
FILE* logits_file = nullptr;

if (!params.export_tokens_file.empty()) {
    token_file = fopen(params.export_tokens_file.c_str(), "w");
}
if (!params.export_logits_file.empty()) {
    logits_file = fopen(params.export_logits_file.c_str(), "w");
}
```

### 3. Export During Generation

```cpp
// In generation loop:

// Export logits BEFORE sampling
if (logits_file) {
    const float* logits = llama_get_logits(ctx);
    const int n_vocab = llama_n_vocab(model);
    
    // Export all logits or top-k
    for (int i = 0; i < std::min(n_vocab, 100); i++) {
        fprintf(logits_file, "%.6f ", logits[i]);
    }
    fprintf(logits_file, "\n");
}

// Sample token
llama_token token = llama_sample_token(ctx, &ctx_sampling);

// Export token AFTER sampling
if (token_file) {
    fprintf(token_file, "%d\n", token);
}
```

### 4. Close Files

```cpp
if (token_file) fclose(token_file);
if (logits_file) fclose(logits_file);
```

## Usage Example

```bash
# Run with QRNG and export data
export ANU_API_KEY="your-key"
./build/bin/llama-cli \
    -m model.gguf \
    -p "Tell me about consciousness" \
    -n 200 \
    --quantum-verbose \
    --export-tokens qrng_tokens.txt \
    --export-logits qrng_logits.txt \
    > qrng_output.txt 2>&1

# Extract QRNG bytes from verbose output
grep "mode=" qrng_output.txt | sed 's/.*mode=\([0-9]*\).*/\1/' > qrng_bytes.txt

# Run with PRNG for comparison
./build/bin/llama-cli \
    -m model.gguf \
    -p "Tell me about consciousness" \
    -n 200 \
    --seed 42 \
    --export-tokens prng_tokens.txt \
    --export-logits prng_logits.txt \
    > prng_output.txt

# Analyze with Python
python your_analysis_script.py
```

## Alternative: JSON Export

For cleaner data exchange, consider JSON format:

```cpp
// Export as JSON for easier parsing
if (params.export_json) {
    nlohmann::json j;
    j["tokens"].push_back(token);
    j["logits"].push_back(logits_vector);
    if (used_quantum) {
        j["qrng_bytes"].push_back(qrng_byte);
    }
    // Write JSON to file
}
```

Then parse in Python:
```python
import json

with open('export.json') as f:
    data = json.load(f)
    tokens = data['tokens']
    logits = data['logits']
    qrng_bytes = data.get('qrng_bytes', [])
```

## Best Practices

1. **Always use the same prompt** for QRNG vs PRNG comparison
2. **Generate sufficient tokens** (100+ for most metrics, 200+ for phase transitions)
3. **Run multiple trials** to establish statistical confidence
4. **Control for randomness** by using fixed seeds for PRNG baseline
5. **Monitor QRNG quality** - anomalies in the stream can affect results

## Troubleshooting

**Q: The analysis says "not enough data"**
- Most metrics need 50-100+ tokens to be meaningful
- Generate longer sequences with `-n 200` or higher

**Q: No significant differences detected**
- Try prompts with higher inherent entropy
- Ensure QRNG is actually being used (check `--quantum-verbose`)
- Some models may be more sensitive than others

**Q: High anomaly rate in QRNG stream**
- This is expected with simulated data in examples
- Real ANU QRNG typically shows <5% anomaly rate
- High rates may indicate API issues or biased stream

## Future Enhancements

Contributions welcome for:
- Native C++ analysis integration
- Real-time monitoring dashboard
- Automated A/B testing framework
- Integration with llama.cpp logging system
- Visualization tools for trajectories and phase spaces
