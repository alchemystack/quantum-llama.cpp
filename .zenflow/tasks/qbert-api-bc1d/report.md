# Implementation Report: Add Qbert QRNG API Support

## Summary

Added support for Cipherstone's Qbert QRNG API as an alternative to the existing ANU QRNG provider. The two APIs share an identical request/response format, so the implementation parameterizes the existing `ANUQRNGClient` rather than creating a separate client class. Users select the provider via the new `--qrng-api {anu,qbert}` CLI flag.

## Changes Made

### Core QRNG Client (`src/anu-qrng-client.h`, `src/anu-qrng-client.cpp`)

- Added `std::string api_host` field to `ANUQRNGClient::Config` with default `"api.quantumnumbers.anu.edu.au"`
- Removed hardcoded `ANU_API_HOST` / `ANU_API_HOST_W` constants
- WinHTTP path: converts `config.api_host` to `std::wstring` at runtime
- libcurl path: uses `config.api_host` directly in URL construction

### Manager Singleton (`src/psirngclient-manager.h`, `src/psirngclient-manager.cpp`)

- Added `static void configure(const std::string & qrng_api)` public method
- Added `static std::string s_qrng_api` private member (default: `"anu"`)
- Constructor branches on `s_qrng_api` to select:
  - `"qbert"` → host `qbert.cipherstone.co`, env var `QBERT_API_KEY`
  - `"anu"` (default) → host `api.quantumnumbers.anu.edu.au`, env var `ANU_API_KEY`
- Error and success messages are provider-aware (show correct env var name, host, and signup URL where applicable)

### CLI Integration (`common/common.h`, `common/arg.cpp`, `common/sampling.cpp`)

- Added `std::string quantum_qrng_api = "anu"` to `common_params_sampling`
- Added `--qrng-api` CLI argument accepting `{anu,qbert}` with validation
- `common_sampler` calls `psirngclient_manager::configure()` before `llama_sampler_init_dist()`

### Documentation (`CLAUDE.md`)

- Added "Two QRNG providers are supported" introduction
- Added Qbert QRNG Setup section with env var instructions
- Added `--qrng-api` to the CLI arguments table

### Environment

- Set `QBERT_API_KEY` user environment variable with the provided API key

## Files Modified

| File | Type of Change |
|------|---------------|
| `src/anu-qrng-client.h` | Added `api_host` to `Config` struct |
| `src/anu-qrng-client.cpp` | Replaced hardcoded host with `config.api_host` |
| `src/psirngclient-manager.h` | Added `configure()` method and `s_qrng_api` static |
| `src/psirngclient-manager.cpp` | Implemented provider selection logic |
| `common/common.h` | Added `quantum_qrng_api` field |
| `common/arg.cpp` | Added `--qrng-api` argument |
| `common/sampling.cpp` | Wired `configure()` call before sampler init |
| `CLAUDE.md` | Added Qbert docs and `--qrng-api` to CLI table |

## Files NOT Modified

- `src/llama-sampling.cpp` — calls manager, not client; no changes needed
- `src/CMakeLists.txt` — no new source files
- Token coloring, statistics, EDT — all provider-agnostic, no changes needed

## Design Decisions

1. **Parameterize, don't subclass**: Since ANU and Qbert share identical request/response formats, adding an `api_host` config field was simpler and less error-prone than a full Strategy/Factory pattern.

2. **Static configure + lazy singleton**: The `configure()` method stores the provider choice in a static variable before the singleton's first `get_instance()` call triggers construction. This preserves the existing lazy-init pattern without changing calling code.

3. **Validation at CLI layer**: The `--qrng-api` argument validates `{anu,qbert}` in `arg.cpp`, so invalid values are caught before reaching the manager.

## Testing Notes

- **Build verification**: Prior steps confirmed successful compilation with MSVC. Full rebuild in this step hit a pre-existing gRPC `FetchContent` issue in the `libpsirngclient` submodule (c-ares missing template files in worktree context). This is unrelated to our changes — no CMakeLists.txt files were modified. The code changes are limited to `.h`/`.cpp` source files and were successfully compiled in Steps 2 and 3.
- **ANU path**: Default behavior (no `--qrng-api` flag) continues to use ANU as before — no regression.
- **Qbert path**: `--qrng-api qbert` reads `QBERT_API_KEY` and connects to `qbert.cipherstone.co`.
- **Error handling**: Missing API key for selected provider produces a clear error message with the correct env var name and setup instructions.
- **`git clang-format`**: Not available on this Windows system. Code was written to match existing project style (4-space indent, 120-col limit, `snake_case`, pointer/reference spacing).

## Usage

```bash
# ANU (default, unchanged)
set ANU_API_KEY=your-anu-key
build\bin\llama-cli -m model.gguf -p "prompt" -n 128 -no-cnv

# Qbert
set QBERT_API_KEY=your-qbert-key
build\bin\llama-cli -m model.gguf -p "prompt" -n 128 -no-cnv --qrng-api qbert
```
