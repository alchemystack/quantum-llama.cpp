# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

If you are blocked and need user clarification, mark the current step with `[!]` in plan.md before stopping.

---

## Workflow Steps

### [x] Step: Technical Specification

Difficulty: **Hard**. Full specification saved to `.zenflow/tasks/z-score-c519/spec.md`.

Replace mode-based signal amplification with z-score-based quantum consciousness sampling across 11 files. Key changes: compute sample mean of 20,480 QRNG bytes, derive z-score, map through normal CDF to uniform float, build probability-ordered descending CDF for token selection, and replace mode-count color coding with z-score-magnitude color coding.

---

### [ ] Step 1: Core Algorithm Change (QRNG client + manager + sampling engine)

Modify the QRNG data pipeline from mode-based to z-score-based:

- `src/anu-qrng-client.h` / `.cpp`:
  - Remove `find_mode()`, `fetch_and_find_mode()`, `last_mode`, `last_mode_count`, `get_last_mode()`, `get_last_mode_count()`
  - Remove `tie_retries` from Statistics
  - Add `last_z_score` (double, default 0.0) and `get_last_z_score()` accessor
  - Add `fetch_and_compute_zscore(double * z_out)`: compute mean, z-score, normal CDF, clamp
  - Update `get_random_value()` to call new method
- `src/psirngclient-manager.h` / `.cpp`:
  - Replace `get_last_mode()` / `get_last_mode_count()` with `get_last_z_score()`
  - Update startup color legend to z-score-based colors
- `src/llama-sampling.h`:
  - Change `llama_sampler_dist_get_last_info` signature: `(smpl, double * z_score_out)`
- `src/llama-sampling.cpp`:
  - Replace `last_mode`/`last_mode_count` with `last_z_score` in struct and init
  - After QRNG call: store z-score, update verbose logging
  - Implement descending-probability CDF sampling (sort tokens by prob desc, build CDF, select via u)
  - Update `llama_sampler_dist_get_last_info()` implementation

### [ ] Step 2: Propagation Layer + Color Coding (common + tools)

Update all consumers of quantum metadata:

- `common/sampling.h` / `.cpp`:
  - Rename `common_sampler_get_last_quantum_mode()` to `common_sampler_get_last_quantum_info()`
  - New signature: `bool common_sampler_get_last_quantum_info(const common_sampler *, double * z_score_out)`
- `tools/server/server-task.h`:
  - Replace `quantum_mode` (uint8_t) and `quantum_mode_count` (size_t) with `quantum_z_score` (double)
- `tools/server/server-context.cpp`:
  - Update population code to use `common_sampler_get_last_quantum_info()`
- `tools/cli/cli.cpp`:
  - Replace mode-count color logic with z-score color logic:
    - greedy → grey, |z|<1 → white, z in [-2,-1) → light blue, z<-2 → blue, z in (1,2] → pink, z>2 → red
- `tools/completion/completion.cpp`:
  - Same z-score color mapping as cli.cpp

### [ ] Step 3: Documentation + Build Verification

- Update `README.md`: color table, algorithm description
- Update `CLAUDE.md`: quantum RNG flow, color legend
- Build: `cmake -B build -DLLAMA_CURL=OFF && cmake --build build --config Release -j`
- Test: `ctest --test-dir build --output-on-failure -j`
- Write report to `.zenflow/tasks/z-score-c519/report.md`
