# Technical Specification: Z-Score Quantum Consciousness Sampling (Additive)

## Difficulty: Hard

This change **adds** a new z-score-based signal amplification method alongside the existing mode-based method. The z-score method becomes the **default**, but users can switch back to the original mode-based method via `--quantum-method mode`. This affects the core sampling pipeline, the QRNG client interface, metadata propagation, color-coding display, CLI argument parsing, and documentation.

## Technical Context

- **Language**: C++ (C++17)
- **Build**: CMake with `-DLLAMA_CURL=OFF`
- **Platform-specific HTTP**: WinHTTP (Windows), libcurl (Linux/Mac)
- **Key dependencies**: `<cmath>` for `erf()`, standard C++ STL

## Design Philosophy

**Additive, not destructive.** The mode-based method is retained in full and selectable at runtime. This allows:
1. A/B comparison between mode and z-score methods
2. Backward compatibility for users who prefer the original behavior
3. Clean separation via a strategy-like dispatch on the `quantum_method` parameter

## Summary of Changes

Add a **z-score-based** signal amplification method (compute sample mean of 20,480 bytes, convert to z-score, map through normal CDF to get uniform float, use probability-ordered descending CDF for token selection) as the **new default**. The existing **mode-based** method (find most frequent byte, use `mode/256.0`) remains available via `--quantum-method mode`. Color coding adapts based on which method is active: z-score magnitude for z-score mode, mode-count rarity for mode.

## Current Architecture (Mode-Based, retained as `--quantum-method mode`)

1. **ANUQRNGClient** fetches 20,480 uint8 values from ANU/Qbert API
2. `find_mode()` finds the single most frequent byte value (retries on ties)
3. Returns `mode / 256.0` as the uniform random float in [0, 1)
4. Color coding based on `mode_count`: <106 = white, 106-108 = pink, 109-111 = red, 112+ = purple
5. Token selection uses standard ascending CDF (tokens in existing order)

## New Architecture (Z-Score-Based, default: `--quantum-method zscore`)

1. **ANUQRNGClient** fetches 20,480 uint8 values from ANU/Qbert API (same HTTP call)
2. Compute sample mean: `M = sum / 20480`
3. Compute z-score: `z = (M - 127.5) / 0.51433`
4. Convert to uniform via normal CDF: `u = 0.5 * (1 + erf(z / sqrt(2)))`
5. Clamp: `u = clamp(u, 1e-10, 1 - 1e-10)`
6. Color coding based on **z-score magnitude** (not mode count)
7. Token selection uses **probability-ordered descending CDF** (highest prob first)

### Key Constants

| Parameter | Value | Derivation |
|---|---|---|
| n (sample count) | 20,480 | Existing batch size (length=1024, size=10, hex16) |
| Population mean (mu) | 127.5 | (0 + 255) / 2 |
| Population std (sigma) | 73.6116 | sqrt((256^2 - 1) / 12) |
| Std error of mean (sigma_m) | 0.51433 | sigma / sqrt(n) |

### Z-Score Color Scheme (active when `quantum_method == "zscore"`)

| Z-Score Range | Color | ANSI Code | Meaning |
|---|---|---|---|
| N/A (greedy) | Grey | `\033[90m` | Deterministic (no QRNG) |
| \|z\| < 1.0 | White | `\033[37m` | Near expected mean |
| z in [-2, -1) | Light Blue | `\033[94m` | Mild negative shift |
| z < -2 | Blue | `\033[34m` | Strong negative shift |
| z in (1, 2] | Light Pink | `\033[38;5;218m` | Mild positive shift |
| z > 2 | Red | `\033[31m` | Strong positive shift |

### Mode-Count Color Scheme (active when `quantum_method == "mode"`, unchanged)

| Mode Count | Color | ANSI Code | Meaning |
|---|---|---|---|
| N/A (greedy) | Grey | `\033[90m` | Deterministic |
| count < 106 | White | `\033[37m` | Common |
| 106-108 | Pink | `\033[38;5;218m` | Above average |
| 109-111 | Red | `\033[31m` | Rare |
| 112+ | Purple | `\033[1;38;5;135m` | Mythic rare |

### Z-Score Sampling: Probability-Ordered Descending CDF

When `quantum_method == "zscore"`, the token selection uses a sorted CDF:

1. Collect all tokens with nonzero probability
2. Sort by probability in **descending** order (highest first)
3. Build CDF over this sorted order
4. Use `u` from the z-score transform to select via this CDF

This gives the consciousness lever a coherent meaning: higher u (positive z) selects less probable tokens (more surprising), lower u (negative z) selects more probable tokens (more conventional).

When `quantum_method == "mode"`, the existing ascending CDF sampling is used unchanged.

## New CLI Argument

| Argument | Description | Default |
|---|---|---|
| `--quantum-method {zscore,mode}` | Select signal amplification method | `zscore` |

## Files to Modify

### 1. `common/common.h`

**Changes to `common_params_sampling`:**
- Add field: `std::string quantum_method = "zscore";` — selects between "zscore" (new default) and "mode" (legacy)
- Place it after `quantum_qrng_api`
- Update comment on the quantum section to note both methods

### 2. `common/arg.cpp`

**Changes:**
- Add new CLI argument `--quantum-method` (string, accepts "zscore" or "mode")
- Place it near `--qrng-api` in the quantum arguments block
- Sets `params.sampling.quantum_method`

### 3. `src/anu-qrng-client.h`

**Changes:**
- **Keep all existing mode methods**: `find_mode()`, `fetch_and_find_mode()`, `get_last_mode()`, `get_last_mode_count()`, `last_mode`, `last_mode_count` — all unchanged
- **Keep** `tie_retries` in Statistics — unchanged
- **Add** `last_z_score` (double, default 0.0) member variable
- **Add** `get_last_z_score()` accessor returning `double`
- **Add** `fetch_and_compute_zscore(double * u_out)` method that computes mean, z-score, normal CDF, clamp, stores z-score, returns uniform value via output param

### 4. `src/anu-qrng-client.cpp`

**Changes:**
- **Keep** `find_mode()`, `fetch_and_find_mode()` — unchanged
- **Add** `fetch_and_compute_zscore(double * u_out)` implementation:
  1. Call `http_request_hex16()` to get raw bytes (no retry loop needed — z-score is continuous)
  2. Compute `M = sum / 20480.0`
  3. Compute `z = (M - 127.5) / 0.51433`
  4. Store in `last_z_score`
  5. Compute `u = 0.5 * (1.0 + erf(z / sqrt(2.0)))`
  6. Clamp `u` to `[1e-10, 1 - 1e-10]`
  7. Set `*u_out = u`, return 0 on success
- **Modify** `get_random_value(double * output)`: Accept a `method` parameter (or use a stored method string) to dispatch between `fetch_and_find_mode()` (mode/256.0) and `fetch_and_compute_zscore()`. The simplest approach: add a second overload or a method parameter.

**Design decision for `get_random_value` dispatch:**

Add a `std::string sampling_method` member variable (default `"zscore"`) set during construction or via a setter `set_sampling_method(const std::string &)`. Then `get_random_value()` dispatches:
- `"mode"` → existing `fetch_and_find_mode()` path
- `"zscore"` → new `fetch_and_compute_zscore()` path

### 5. `src/psirngclient-manager.h`

**Changes:**
- **Keep** `get_last_mode()` and `get_last_mode_count()` — unchanged
- **Add** `get_last_z_score()` accessor (double)
- **Add** `static void set_sampling_method(const std::string & method)` — configures which method the client uses
- **Add** `static std::string get_sampling_method()` — returns current method

### 6. `src/psirngclient-manager.cpp`

**Changes:**
- **Add** static `s_quantum_method` string (default `"zscore"`)
- **Add** `set_sampling_method()` / `get_sampling_method()` implementations
- **Forward** `set_sampling_method()` to the ANUQRNGClient during construction
- **Keep** `get_last_mode()` / `get_last_mode_count()` — delegate to anu_client
- **Add** `get_last_z_score()` — delegate to anu_client
- **Update startup color legend**: Print z-score legend when method is "zscore", mode-count legend when method is "mode"

### 7. `src/llama-sampling.h`

**Changes:**
- **Keep** existing `llama_sampler_dist_get_last_info` signature (mode+count) — remains available
- **Add** new function: `bool llama_sampler_dist_get_last_zscore_info(const struct llama_sampler * smpl, double * z_score_out)`
- **Add** new function: `std::string llama_sampler_dist_get_quantum_method(const struct llama_sampler * smpl)` — returns which method was used
- **Update** `llama_sampler_dist_set_quantum_params()` signature to include `const std::string & quantum_method`

### 8. `src/llama-sampling.cpp`

**Changes to `llama_sampler_dist` struct:**
- **Keep** `uint8_t last_mode` and `size_t last_mode_count` — used when method is "mode"
- **Add** `double last_z_score = 0.0` — used when method is "zscore"
- **Add** `std::string quantum_method = "zscore"` — which method is active

**Changes to `llama_sampler_dist_apply()`:**
- After successful QRNG call:
  - If `quantum_method == "zscore"`: store `psirngclient_manager::get_last_z_score()` in `last_z_score`, then perform **descending-probability CDF sampling**
  - If `quantum_method == "mode"`: store mode/count from `psirngclient_manager::get_last_mode()` / `get_last_mode_count()`, then perform existing ascending CDF sampling (unchanged)
- Update verbose logging to print z-score info when method is "zscore", mode info when method is "mode"

**Descending-probability CDF sampling (zscore method only):**
1. After EDT temperature-scaled softmax: collect indices of all tokens with p > 0
2. Sort indices by probability **descending**
3. Build cumulative distribution over sorted order
4. Use `u` (the uniform float from QRNG) to find first index where CDF >= u
5. Select that token

**Changes to `llama_sampler_init_dist()`:**
- Initialize `last_z_score = 0.0` alongside existing `last_mode = 128, last_mode_count = 80`

**Add `llama_sampler_dist_get_last_zscore_info()`:**
- Returns `last_was_quantum` flag
- Sets `*z_score_out = last_z_score`

**Add `llama_sampler_dist_get_quantum_method()`:**
- Returns `quantum_method` string from the struct

**Changes to `llama_sampler_dist_set_quantum_params()`:**
- Accept and store `quantum_method` parameter
- Forward to `psirngclient_manager::set_sampling_method()` so the client dispatches correctly

### 9. `common/sampling.h`

**Changes:**
- **Keep** `common_sampler_get_last_quantum_mode()` — unchanged, works for mode method
- **Add** `bool common_sampler_get_last_quantum_zscore(const struct common_sampler * gsmpl, double * z_score_out)` — for z-score method
- **Add** `std::string common_sampler_get_quantum_method(const struct common_sampler * gsmpl)` — returns active method

### 10. `common/sampling.cpp`

**Changes:**
- **Keep** `common_sampler_get_last_quantum_mode()` — unchanged
- **Add** `common_sampler_get_last_quantum_zscore()`: find "dist" sampler, call `llama_sampler_dist_get_last_zscore_info()`
- **Add** `common_sampler_get_quantum_method()`: find "dist" sampler, call `llama_sampler_dist_get_quantum_method()`
- **Update** `common_sampler_init()` (or wherever `llama_sampler_dist_set_quantum_params` is called): pass `quantum_method` from params

### 11. `tools/cli/cli.cpp`

**Changes:**
- Replace current color logic block with method-aware dispatch:
  ```
  std::string method = common_sampler_get_quantum_method(smpl);
  if (method == "zscore") {
      double z = 0.0;
      bool was_quantum = common_sampler_get_last_quantum_zscore(smpl, &z);
      // z-score color mapping
      if (!was_quantum)        → grey
      else if (z < -2.0)       → blue
      else if (z < -1.0)       → light blue
      else if (z <= 1.0)       → white
      else if (z <= 2.0)       → pink
      else                     → red
  } else {
      // existing mode-count color mapping (unchanged)
      uint8_t mode = 0; size_t count = 80;
      bool was_quantum = common_sampler_get_last_quantum_mode(smpl, &mode, &count);
      // original color logic
  }
  ```

### 12. `tools/completion/completion.cpp`

**Changes:**
- Same method-aware color dispatch as cli.cpp

### 13. `tools/server/server-task.h`

**Changes:**
- **Keep** `quantum_mode` and `quantum_mode_count` — used for mode method
- **Add** `double quantum_z_score = 0.0` — used for z-score method
- **Add** `std::string quantum_method = "zscore"` — which method produced this result

### 14. `tools/server/server-context.cpp`

**Changes:**
- Update population code to query method:
  ```
  std::string method = common_sampler_get_quantum_method(smpl);
  res->quantum_method = method;
  if (method == "zscore") {
      double z = 0.0;
      bool was_quantum = common_sampler_get_last_quantum_zscore(smpl, &z);
      res->quantum_was_quantum = was_quantum;
      res->quantum_z_score = z;
  } else {
      uint8_t mode = 0; size_t count = 80;
      bool was_quantum = common_sampler_get_last_quantum_mode(smpl, &mode, &count);
      res->quantum_was_quantum = was_quantum;
      res->quantum_mode = mode;
      res->quantum_mode_count = count;
  }
  ```

### 15. `README.md`

**Changes:**
- Add `--quantum-method` to the CLI arguments table
- Add z-score color table alongside mode-count color table
- Add brief description of the z-score algorithm
- Note that z-score is now the default

### 16. `CLAUDE.md`

**Changes:**
- Add `--quantum-method` to the CLI arguments table
- Update Quantum RNG Flow to show both paths
- Update color legend to include both schemes
- Note default is now z-score

## Implementation Plan (3 steps)

### Step 1: Core Algorithm + Infrastructure

Add the z-score method to the QRNG client and sampling engine, plus CLI argument:

- `common/common.h`: Add `quantum_method` field
- `common/arg.cpp`: Add `--quantum-method` argument
- `src/anu-qrng-client.h` / `.cpp`: Add z-score methods, dispatch in `get_random_value()`
- `src/psirngclient-manager.h` / `.cpp`: Add z-score accessor, method config, update startup legend
- `src/llama-sampling.h`: Add z-score info function, method accessor, update params signature
- `src/llama-sampling.cpp`: Add z-score struct field, descending CDF sampling, method-aware dispatch, verbose logging

### Step 2: Propagation Layer + Color Coding

Wire z-score metadata through common layer and update display:

- `common/sampling.h` / `.cpp`: Add z-score accessor, method accessor, pass method to params
- `tools/server/server-task.h`: Add z-score field, method field
- `tools/server/server-context.cpp`: Method-aware population
- `tools/cli/cli.cpp`: Method-aware color coding
- `tools/completion/completion.cpp`: Method-aware color coding

### Step 3: Documentation + Build Verification

- Update `README.md` and `CLAUDE.md`
- Build: `cmake -B build -DLLAMA_CURL=OFF && cmake --build build --config Release -j`
- Test: `ctest --test-dir build --output-on-failure -j`

## Verification Approach

1. **Build verification**: Compile successfully with `cmake -B build -DLLAMA_CURL=OFF && cmake --build build --config Release -j`
2. **Test suite**: Run `ctest --test-dir build --output-on-failure -j`
3. **Code formatting**: Run `git clang-format` before committing
4. **Manual verification (zscore default)**: Run `llama-cli` with `--quantum-verbose` — confirm z-score values are printed, new color coding active
5. **Manual verification (mode fallback)**: Run `llama-cli` with `--quantum-method mode --quantum-verbose` — confirm mode/count values printed, original color coding active

## Risk Assessment

- **No breaking changes**: Mode method is fully preserved, just no longer the default
- **Backward compatibility**: All existing CLI arguments work unchanged. Only addition: `--quantum-method`
- **Internal APIs**: New functions are added; existing ones kept. No callers break.
- **Same API call format**: The HTTP request to ANU/Qbert is unchanged; only post-processing differs
- **Numerical stability**: `erf()` is well-defined for all finite inputs; clamping prevents edge cases
- **No tie retries needed for z-score**: Continuous value, never ties — simpler and lower latency
