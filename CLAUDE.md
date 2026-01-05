# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

quantum-llama.cpp is a modified fork of [llama.cpp](https://github.com/ggml-org/llama.cpp) that integrates Quantum Random Number Generators (QRNGs) into token generation. The core idea: *"the output is co-authored by the universe itself."*

**Key difference from upstream**: Uses true quantum randomness instead of pseudo-random number generation for sampling.

## Build Commands

```bash
# Standard build (MUST use -DLLAMA_CURL=OFF for quantum features)
cmake -B build -DLLAMA_CURL=OFF
cmake --build build --config Release -j

# With CUDA
cmake -B build -DLLAMA_CURL=OFF -DGGML_CUDA=ON
cmake --build build --config Release -j

# Debug build
cmake -B build -DCMAKE_BUILD_TYPE=Debug -DLLAMA_CURL=OFF
cmake --build build
```

Built binaries are placed in `build/bin/`.

## Testing

```bash
# Run test suite
ctest --test-dir build --output-on-failure -j

# Server tests (requires Python venv)
cd tools/server/tests
source ../../../.venv/bin/activate
./tests.sh
```

## Code Formatting

**Always format before committing:**
```bash
git clang-format
```

Key style rules:
- 4-space indentation, 120-column limit
- Pointer/reference: `void * ptr`, `int & a`
- `snake_case` for functions, variables, types
- Enum values: `ENUM_NAME_VALUE` (uppercase with prefix)

## Architecture

### Core Directories
- `src/` - Main llama library (`llama-*.cpp/h` modules)
- `include/llama.h` - Public C API
- `ggml/` - Vendored tensor library
- `tools/` - Executables (`llama-cli`, `llama-server`, etc.)
- `common/` - Shared utilities
- `libpsirngclient/` - Git submodule for gRPC QRNG client

### Quantum Integration (in `src/`)
- `psirngclient-manager.cpp/h` - Singleton managing QRNG connections
- `anu-qrng-client.cpp/h` - HTTP client for ANU QRNG API (hex16 mode-based sampling)
- `llama-sampling.cpp` - Sampling pipeline (integration point for quantum RNG)

### Quantum RNG Flow
```
Token Logits
    ↓
Calculate Entropy (normalized 0-1)
    ↓
[entropy < 0.40?] ─YES─→ GREEDY (no QRNG) → Done
    │
    NO
    ↓
Apply EDT Temperature: T = T₀ × 0.8^(θ/entropy)
    ↓
ANU API call (hex16, length=1024, size=10)
    ↓
Find mode of ~20K uint8 values
    ↓
Use mode/256 for inverse CDF sampling
    ↓
Done
```

**Key principle:** Each token selection makes a fresh API call. No buffering - this preserves temporal correlation between consciousness and token selection.

### Adaptive Entropy-Based Sampling
- **entropy < 0.40** → Greedy sampling (no API call, saves bandwidth)
- **entropy ≥ 0.40** → EDT temperature + QRNG sampling
- Typically saves 50-80% of API calls for predictable text

### EDT (Entropy-based Dynamic Temperature)
- **Formula:** `T = T₀ × 0.8^(θ/entropy)`
- **Defaults:** T₀=2.0, θ=1.0
- Higher entropy → higher temperature (more creative exploration)
- Lower entropy → lower temperature (more focused selection)
- At max entropy (1.0): T ≈ 1.6

## Running with Quantum RNG

### ANU QRNG Setup (Required)

1. Get your FREE API key at: https://quantumnumbers.anu.edu.au/

2. Set the environment variable:
```bash
# Linux/Mac
export ANU_API_KEY="your-api-key-here"

# Windows CMD
set ANU_API_KEY=your-api-key-here

# PowerShell
$env:ANU_API_KEY="your-api-key-here"
```

3. Run:
```bash
./build/bin/llama-cli -m model.gguf -p "prompt" -n 128 -no-cnv
```

### Quantum CLI Arguments
| Argument | Description | Default |
|----------|-------------|---------|
| `--quantum-verbose` | Show entropy/temperature for each token | off |
| `--quantum-statistics` | Print sampling statistics at end | off |
| `--quantum-entropy-threshold N` | Entropy cutoff for greedy vs QRNG | 0.40 |
| `--quantum-edt-t0 N` | EDT upper bound temperature | 2.0 |
| `--quantum-edt-theta N` | EDT entropy sensitivity | 1.0 |
| `--no-quantum-adaptive-sampling` | Always use QRNG (no greedy) | - |
| `--no-quantum-edt` | Use fixed temperature instead of EDT | - |

### psirng Service (Alternative, requires external setup)
```bash
export PSIRNG_HOST=192.0.2.10
export PSIRNG_GRPC_PORT=50051
export PSIRNG_CERT_PATH=/path/to/cert.pem
./build/bin/llama-cli -m model.gguf -p "prompt"
```

## Development Guidelines

- **NEVER buffer quantum random data** - Each token selection MUST use fresh quantum data from a new API call. Buffering destroys the temporal correlation between consciousness and token selection.
- **Never use `-DLLAMA_CURL=ON`** - incompatible with quantum features
- Clone with `--recurse-submodules` to get libpsirngclient
- Avoid adding third-party dependencies
- Use basic C++ patterns, avoid fancy STL constructs
- Vertical alignment for readability
- Tensor storage is row-major (dim 0=columns, 1=rows, 2=matrices)
- Matrix multiplication: `C = ggml_mul_mat(ctx, A, B)` means C^T = AB^T

### Naming Conventions
- Pattern: `<class>_<method>` where method is `<action>_<noun>`
- Examples: `llama_model_init()`, `llama_sampler_chain_remove()`
- Optimize for longest common prefix: `number_small`, `number_big` (not `small_number`)

## Performance Validation

```bash
# Benchmark
./build/bin/llama-bench -m model.gguf

# Evaluate perplexity
./build/bin/llama-perplexity -m model.gguf -f dataset.txt

# Test backend ops
./build/bin/test-backend-ops
```
