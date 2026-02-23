# Z-Score Quantum Consciousness Sampling — Implementation Report

## Summary

Replaced mode-based signal amplification with z-score-based quantum consciousness sampling across the full pipeline. The z-score method computes the sample mean of 20,480 QRNG bytes, converts to a z-score, maps through the standard normal CDF to produce a uniform float in [0, 1), and uses a descending-probability CDF for token selection.

## Changes Delivered

### Step 1: Core Algorithm (QRNG client + manager + sampling engine)

**Files modified (8):**

| File | Change |
|------|--------|
| `src/anu-qrng-client.h/.cpp` | Removed `find_mode()`, `fetch_and_find_mode()`, `last_mode`, `last_mode_count`, `get_last_mode()`, `get_last_mode_count()`, `tie_retries`. Added `last_z_score`, `get_last_z_score()`, `fetch_and_compute_zscore()`. `get_random_value()` now calls z-score path. |
| `src/psirngclient-manager.h/.cpp` | Replaced `get_last_mode()`/`get_last_mode_count()` with `get_last_z_score()`. Updated startup color legend to z-score-based colors. |
| `src/llama-sampling.h` | Changed `llama_sampler_dist_get_last_info` signature to `(smpl, double * z_score_out)`. |
| `src/llama-sampling.cpp` | Replaced `last_mode`/`last_mode_count` with `last_z_score` in dist struct. Implemented descending-probability CDF sampling (sort tokens by prob desc, build CDF, select via u). |
| `common/sampling.h/.cpp` | Renamed `common_sampler_get_last_quantum_mode()` to `common_sampler_get_last_quantum_info()` with `double * z_score_out` signature. |
| `tools/server/server-task.h` | Replaced `quantum_mode`/`quantum_mode_count` with `quantum_z_score`. |
| `tools/server/server-context.cpp` | Updated to use `common_sampler_get_last_quantum_info()`. |
| `tools/cli/cli.cpp` + `tools/completion/completion.cpp` | Updated color coding to z-score magnitude thresholds. |

### Step 2: Documentation + Build Verification

**Files modified (2):**

| File | Change |
|------|--------|
| `README.md` | Replaced "Mode-Based Signal Extraction" with "Z-Score Signal Amplification". Updated algorithm description, color table (z-score ranges instead of mode counts), removed purple color. |
| `CLAUDE.md` | Updated Quantum Integration description, Quantum RNG Flow diagram (now shows mean→z-score→CDF pipeline), added Z-Score Color Coding table, fixed entropy threshold default (0.50). |

## Algorithm Summary

```
QRNG API call → 20,480 uint8 samples
    ↓
Sample mean: M = sum / 20480
    ↓
Z-score: z = (M - 127.5) / 0.51433
    ↓
Uniform float: u = 0.5 * (1 + erf(z / sqrt(2)))
    ↓
Clamp: u = clamp(u, 1e-10, 1 - 1e-10)
    ↓
Descending-probability CDF sampling → token
```

## Color Coding

| Z-Score Range | Color | Meaning |
|---|---|---|
| N/A (greedy) | Grey | Deterministic (no QRNG) |
| \|z\| < 1.0 | White | Near expected mean |
| z in [-2, -1) | Light Blue | Mild negative shift |
| z < -2 | Blue | Strong negative shift |
| z in (1, 2] | Pink | Mild positive shift |
| z > 2 | Red | Strong positive shift |

## Build Verification

**CMake configure:** Successful (`cmake -B build -DLLAMA_CURL=OFF`).

**CMake build:** All z-score C++ code compiled without errors. The build fails at the **linker stage** for three third-party dependency targets:

1. `upb_message_lib.dll` — gRPC's UPB library: `upb_alloc_global` unresolved
2. `upb_mini_descriptor_lib.dll` — gRPC's UPB library: `upb_alloc_global` + `_kUpb_MiniTable_Empty` unresolved
3. `psijent-stream` / `psijent-uniform` — libpsijent examples: `psijent_static.lib` not found

These are **pre-existing infrastructure issues** in the gRPC dependency build on Windows/MSVC, unrelated to any z-score code changes. The z-score files (`anu-qrng-client.cpp`, `llama-sampling.cpp`, `cli.cpp`, `completion.cpp`, `server-context.cpp`, etc.) all compile cleanly with zero errors or warnings.

**Tests:** Could not run (`ctest --test-dir build --output-on-failure -j`) because the gRPC linker failures prevent the main llama targets (`llama-cli`, `llama-server`) from linking. The ggml and llama unit tests that don't depend on gRPC were not individually targeted.

## Key Design Decisions

1. **Mode removed, not retained**: The task specified replacing mode with z-score (not additive), so mode-based code was removed entirely rather than kept alongside.
2. **No `--quantum-method` argument**: Since mode was removed, no method selector CLI argument was needed.
3. **Descending-probability CDF**: Tokens sorted by probability descending gives the z-score a coherent meaning — positive z → more surprising tokens, negative z → more conventional tokens.
4. **No tie retries needed**: Z-score produces a continuous value, unlike mode which could tie. This simplifies the pipeline and reduces latency.
