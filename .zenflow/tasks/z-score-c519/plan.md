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
<!-- chat-id: c98714e5-8518-4615-8645-f97d437ffd96 -->

Difficulty: **Hard**. Full specification saved to `.zenflow/tasks/z-score-c519/spec.md`.

Add z-score-based quantum consciousness sampling as a **new method alongside the existing mode-based method** (not replacing it). The z-score method becomes the default, selectable via `--quantum-method zscore` (default) vs `--quantum-method mode` (legacy). Changes span 16 files: QRNG client gains z-score computation, sampling engine gains descending-probability CDF, metadata propagation carries both method types, color coding dispatches by method, and a new CLI argument selects the method.

---

### [ ] Step 1: Core Algorithm + Infrastructure
<!-- chat-id: 43cba7e7-57e4-4b96-91ac-ed0b9512627a -->

Add the z-score method to the QRNG client and sampling engine, plus the CLI argument for method selection. All existing mode-based code is **preserved unchanged**.

- `common/common.h`: Add `quantum_method = "zscore"` field to `common_params_sampling`
- `common/arg.cpp`: Add `--quantum-method {zscore,mode}` CLI argument
- `src/anu-qrng-client.h`:
  - Keep all mode methods unchanged
  - Add `last_z_score` (double), `get_last_z_score()`, `fetch_and_compute_zscore(double * u_out)`
  - Add `sampling_method` member + `set_sampling_method()` setter
- `src/anu-qrng-client.cpp`:
  - Keep `find_mode()`, `fetch_and_find_mode()` unchanged
  - Add `fetch_and_compute_zscore()`: mean → z-score → erf → clamp
  - Modify `get_random_value()` to dispatch based on `sampling_method`
- `src/psirngclient-manager.h`:
  - Keep `get_last_mode()`, `get_last_mode_count()` unchanged
  - Add `get_last_z_score()`, `set_sampling_method()`, `get_sampling_method()`
- `src/psirngclient-manager.cpp`:
  - Add `s_quantum_method` static, method setters/getters
  - Add `get_last_z_score()` delegating to client
  - Update startup color legend: print z-score legend for "zscore", mode legend for "mode"
- `src/llama-sampling.h`:
  - Keep `llama_sampler_dist_get_last_info()` (mode+count) unchanged
  - Add `llama_sampler_dist_get_last_zscore_info()`, `llama_sampler_dist_get_quantum_method()`
  - Update `llama_sampler_dist_set_quantum_params()` to accept `quantum_method`
- `src/llama-sampling.cpp`:
  - Keep `last_mode`, `last_mode_count` in struct
  - Add `last_z_score`, `quantum_method` to struct
  - In `apply()`: branch on method — zscore uses descending CDF, mode uses existing path
  - Add verbose logging for z-score method
  - Implement `get_last_zscore_info()`, `get_quantum_method()`

### [ ] Step 2: Propagation Layer + Color Coding

Wire z-score metadata through the common layer and update all display code with method-aware dispatch. Existing mode-based paths preserved.

- `common/sampling.h`:
  - Keep `common_sampler_get_last_quantum_mode()` unchanged
  - Add `common_sampler_get_last_quantum_zscore()`, `common_sampler_get_quantum_method()`
- `common/sampling.cpp`:
  - Keep `common_sampler_get_last_quantum_mode()` unchanged
  - Add new functions, pass `quantum_method` to `llama_sampler_dist_set_quantum_params()`
- `tools/server/server-task.h`:
  - Keep `quantum_mode`, `quantum_mode_count` fields
  - Add `quantum_z_score`, `quantum_method` fields
- `tools/server/server-context.cpp`:
  - Query method, populate z-score or mode fields accordingly
- `tools/cli/cli.cpp`:
  - Method-aware color dispatch: z-score colors for "zscore", mode-count colors for "mode"
- `tools/completion/completion.cpp`:
  - Same method-aware color dispatch as cli.cpp

### [ ] Step 3: Documentation + Build Verification

- Update `README.md`: add `--quantum-method` to CLI table, add z-score color table, describe both methods
- Update `CLAUDE.md`: add `--quantum-method` to CLI table, update flow diagram for both paths, update color legend
- Build: `cmake -B build -DLLAMA_CURL=OFF && cmake --build build --config Release -j`
- Test: `ctest --test-dir build --output-on-failure -j`
- Write report to `.zenflow/tasks/z-score-c519/report.md`
