# Technical Specification: Z-Score Quantum Consciousness Sampling

## Difficulty: Hard

This is a fundamental algorithm change that replaces the mode-based signal amplification with z-score based sampling. It affects the core sampling pipeline, the QRNG client interface, the data structures that propagate quantum metadata, and all color-coding display logic across multiple tools.

## Technical Context

- **Language**: C++ (C++17)
- **Build**: CMake with `-DLLAMA_CURL=OFF`
- **Platform-specific HTTP**: WinHTTP (Windows), libcurl (Linux/Mac)
- **Key dependencies**: `<cmath>` for `erf()`, standard C++ STL

## Summary of Changes

Replace the **mode-based** signal amplification (find most frequent byte in 20,480 QRNG samples, use `mode/256` as uniform float) with a **z-score-based** approach (compute sample mean of 20,480 bytes, convert to z-score, map through normal CDF to get uniform float). Also replace mode-count-based color coding with z-score-magnitude-based color coding, and build a **probability-ordered descending CDF** for token selection.

## Current Architecture (Mode-Based)

1. **ANUQRNGClient** fetches 20,480 uint8 values from ANU API
2. `find_mode()` finds the single most frequent byte value (retries on ties)
3. Returns `mode / 256.0` as the uniform random float in [0, 1)
4. Color coding is based on `mode_count` (how many times the mode appeared): <106 = white, 106-108 = pink, 109-111 = red, 112+ = purple
5. Token selection uses standard ascending CDF (tokens in whatever order they arrive)

## New Architecture (Z-Score-Based)

1. **ANUQRNGClient** fetches 20,480 uint8 values from ANU API (unchanged)
2. Compute sample mean M = sum / 20480
3. Compute z-score: `z = (M - 127.5) / 0.51433`
4. Convert to uniform via normal CDF: `u = 0.5 * (1 + erf(z / sqrt(2)))`
5. Clamp: `u = clamp(u, 1e-10, 1 - 1e-10)`
6. Color coding based on z-score magnitude (not mode count)
7. Token selection uses **probability-ordered descending CDF** (highest prob first)

### Key Constants
| Parameter | Value | Derivation |
|---|---|---|
| n (sample count) | 20,480 | Existing batch size from API (length=1024, size=10, hex16) |
| Population mean (mu) | 127.5 | (0 + 255) / 2 |
| Population std (sigma) | 73.6116 | sqrt((256^2 - 1) / 12) |
| Std error of mean (sigma_m) | 0.51433 | sigma / sqrt(n) |

### New Color Scheme (Z-Score Based)

| Z-Score Range | Color | ANSI Code | Meaning |
|---|---|---|---|
| N/A (greedy) | Grey | `\033[90m` | Deterministic (no QRNG) |
| \|z\| < 1.0 | White | `\033[37m` | Near expected mean |
| z in [-2, -1) | Light Blue | `\033[94m` | Mild negative shift |
| z < -2 | Blue | `\033[34m` | Strong negative shift |
| z in (1, 2] | Light Pink | `\033[38;5;218m` | Mild positive shift |
| z > 2 | Red | `\033[31m` | Strong positive shift |

Purple is removed entirely.

### New Sampling: Probability-Ordered Descending CDF

The current code samples against a CDF built from tokens in their existing order. The new algorithm requires:
1. Collect all tokens with nonzero probability
2. Sort by probability in **descending** order (highest first)
3. Build CDF over this sorted order
4. Use `u` from the z-score transform to select via this CDF

This gives the consciousness lever a coherent meaning: higher u (positive z) selects less probable tokens (more surprising), lower u (negative z) selects more probable tokens (more conventional).

## Files to Modify

### 1. `src/anu-qrng-client.h` and `src/anu-qrng-client.cpp`

**Changes:**
- Remove `find_mode()` static method
- Remove `fetch_and_find_mode()` method
- Remove `last_mode` (uint8_t) and `last_mode_count` (size_t) member variables
- Remove `get_last_mode()` and `get_last_mode_count()` accessors
- Add `last_z_score` (double) member variable (default 0.0)
- Add `get_last_z_score()` accessor returning `double`
- Add new method `fetch_and_compute_zscore(double * z_out)` that:
  1. Calls `http_request_hex16()` to get raw bytes (no retry loop for ties needed)
  2. Computes mean M = sum / 20480
  3. Computes z = (M - 127.5) / 0.51433
  4. Stores in `last_z_score`
  5. Converts to u via `0.5 * (1.0 + erf(z / sqrt(2.0)))`
  6. Clamps u to [1e-10, 1 - 1e-10]
  7. Returns 0 on success
- Modify `get_random_value(double * output)` to call `fetch_and_compute_zscore` instead of `fetch_and_find_mode`, and set `*output = u`
- Update `Statistics` struct: remove `tie_retries` field (ties no longer relevant)

### 2. `src/psirngclient-manager.h` and `src/psirngclient-manager.cpp`

**Changes:**
- Replace `get_last_mode()` (uint8_t) with `get_last_z_score()` (double)
- Remove `get_last_mode_count()` method
- Update the color legend printed at startup (replace mode-count legend with z-score legend)
- Default return for uninitialized: 0.0 (neutral z-score)

### 3. `src/llama-sampling.h`

**Changes:**
- Update `llama_sampler_dist_get_last_info` signature:
  - Remove `uint8_t * mode_out` and `size_t * count_out` parameters
  - Add `double * z_score_out` parameter
  - New signature: `bool llama_sampler_dist_get_last_info(const struct llama_sampler * smpl, double * z_score_out)`

### 4. `src/llama-sampling.cpp`

**Changes to `llama_sampler_dist` struct:**
- Replace `uint8_t last_mode` and `size_t last_mode_count` with `double last_z_score` (default 0.0)

**Changes to `llama_sampler_dist_apply()`:**
- After successful QRNG call: store `psirngclient_manager::get_last_z_score()` instead of mode/count
- Update verbose logging: print z-score and computed u value, classify by z-score ranges instead of mode count
- **Implement probability-ordered descending CDF sampling:**
  1. After softmax computation (with EDT temperature), collect indices of all tokens with p > 0
  2. Sort indices by probability descending
  3. Build cumulative distribution over sorted order
  4. Use `u` (the QRNG uniform float, already returned by `get_random_value()`) to find the first index where CDF >= u
  5. Set `cur_p->selected` to that token's original index in `cur_p->data`

**Changes to `llama_sampler_init_dist()`:**
- Replace `last_mode = 128, last_mode_count = 80` with `last_z_score = 0.0`

**Changes to `llama_sampler_dist_get_last_info()`:**
- New signature: return z_score instead of mode+count

**Changes to statistics printing:**
- No changes needed (already prints greedy/quantum counts, no mode-specific stats)

### 5. `common/sampling.h` and `common/sampling.cpp`

**Changes:**
- Rename `common_sampler_get_last_quantum_mode()` to `common_sampler_get_last_quantum_info()`
- New signature: `bool common_sampler_get_last_quantum_info(const struct common_sampler * gsmpl, double * z_score_out)`
- Remove `uint8_t * mode_out, size_t * count_out` parameters

### 6. `tools/cli/cli.cpp`

**Changes:**
- Replace mode-count color logic with z-score color logic
- Replace `res_partial->quantum_mode_count` with `res_partial->quantum_z_score`
- New color mapping:
  ```
  if (!was_quantum)           → grey \033[90m]
  else if (z < -2.0)          → blue \033[34m]
  else if (z < -1.0)          → light blue \033[94m]
  else if (z <= 1.0)          → white \033[37m]
  else if (z <= 2.0)          → light pink \033[38;5;218m]
  else                        → red \033[31m]
  ```

### 7. `tools/completion/completion.cpp`

**Changes:**
- Same color logic update as cli.cpp
- Replace `common_sampler_get_last_quantum_mode()` with `common_sampler_get_last_quantum_info()`

### 8. `tools/server/server-task.h`

**Changes:**
- Replace `uint8_t quantum_mode = 0` and `size_t quantum_mode_count = 80` with `double quantum_z_score = 0.0`

### 9. `tools/server/server-context.cpp`

**Changes:**
- Update the code that populates quantum info into the server response
- Use `common_sampler_get_last_quantum_info()` and store z_score instead of mode/count

### 10. `README.md`

**Changes:**
- Update the Token Color-Coding table to reflect z-score based colors
- Update the description of signal amplification from mode-based to z-score-based

### 11. `CLAUDE.md`

**Changes:**
- Update the Quantum RNG Flow section to reflect z-score algorithm
- Update color legend description
- Update the "Key principle" note (no longer about mode, but about z-score)

## Implementation Plan (3 steps)

### Step 1: Core Algorithm Change (QRNG client + manager + sampling engine)

Modify the QRNG data pipeline from mode-based to z-score-based:

- `src/anu-qrng-client.h` / `.cpp`: Replace mode logic with z-score computation
- `src/psirngclient-manager.h` / `.cpp`: Replace mode accessors with z-score, update startup legend
- `src/llama-sampling.h`: Update `get_last_info` signature
- `src/llama-sampling.cpp`: Replace struct fields, implement descending-probability CDF sampling, update verbose logging

### Step 2: Propagation Layer + Color Coding (common + tools)

Update all consumers of quantum metadata:

- `common/sampling.h` / `.cpp`: Update accessor function signature
- `tools/server/server-task.h`: Replace mode/count fields with z_score
- `tools/server/server-context.cpp`: Update population code
- `tools/cli/cli.cpp`: New z-score color mapping
- `tools/completion/completion.cpp`: New z-score color mapping

### Step 3: Documentation + Build Verification

- Update `README.md` color table and algorithm description
- Update `CLAUDE.md` flow diagram and color legend
- Build: `cmake -B build -DLLAMA_CURL=OFF && cmake --build build --config Release -j`
- Run: `ctest --test-dir build --output-on-failure -j`

## Verification Approach

1. **Build verification**: Compile successfully with `cmake -B build -DLLAMA_CURL=OFF && cmake --build build --config Release -j`
2. **Test suite**: Run `ctest --test-dir build --output-on-failure -j`
3. **Code formatting**: Run `git clang-format` before committing
4. **Manual verification** (if API key available): Run `llama-cli` with a model and `--quantum-verbose` to confirm z-score values are printed and color coding works

## Risk Assessment

- **No tie retries needed**: The z-score approach never produces ties (it's a continuous value), simplifying the code and reducing latency per token
- **Backward compatibility**: The change modifies internal APIs (`llama_sampler_dist_get_last_info`, `common_sampler_get_last_quantum_mode`), but these are only used within the project, not in the public `include/llama.h` API
- **Numerical stability**: `erf()` is well-defined for all finite inputs; clamping prevents edge cases
- **Same API call format**: The HTTP request to ANU is unchanged (`length=1024&size=10&type=hex16`), only the post-processing of the raw bytes changes
