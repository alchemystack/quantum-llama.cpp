# Technical Specification: Add Qbert QRNG API Support

## Difficulty: Easy

The Qbert API uses an identical request/response format to the existing ANU API. The only differences are hostname, API key env var, and the auth header name (which is case-insensitive and thus functionally identical). We reuse the existing `ANUQRNGClient` class by parameterizing the host and API key.

## Technical Context

- **Language**: C++17
- **Platforms**: Windows (WinHTTP), Linux/Mac (libcurl)
- **Build system**: CMake
- **Dependencies**: No new dependencies required

## Current Architecture

```
CLI (arg.cpp)
  → common_params_sampling (common.h)
    → common_sampler (sampling.cpp)
      → llama_sampler_dist (llama-sampling.cpp)
        → psirngclient_manager (singleton)
          → ANUQRNGClient (HTTP to api.quantumnumbers.anu.edu.au)
```

The `psirngclient_manager` singleton is the sole gateway between the sampling pipeline and QRNG providers. All downstream code calls `psirngclient_manager::get_random_value()` and never touches `ANUQRNGClient` directly. This means adding a second provider only requires changes at the manager level and below — the sampling pipeline, token coloring, and statistics code need zero modifications.

## Implementation Approach

### Strategy: Parameterize the existing client

Both APIs share:
- Same query parameters: `?type=hex16&length=1024&size=10`
- Same JSON response: `{"success":true, "data":["hex..."], "type":"hex16"}`
- Same auth mechanism: API key in HTTP header (both use `x-api-key` / `X-API-Key`, case-insensitive)

The only differences:
| | ANU | Qbert |
|---|---|---|
| Host | `api.quantumnumbers.anu.edu.au` | `qbert.cipherstone.co` |
| API key env var | `ANU_API_KEY` | `QBERT_API_KEY` |
| Auth header | `x-api-key` | `X-API-Key` (equivalent) |

### Changes

**1. Add `api_host` field to `ANUQRNGClient::Config`** (`src/anu-qrng-client.h`)

Add `std::string api_host` to the `Config` struct with a default of `"api.quantumnumbers.anu.edu.au"`. This lets the manager pass in `"qbert.cipherstone.co"` when Qbert is selected.

**2. Use `config.api_host` instead of hardcoded host** (`src/anu-qrng-client.cpp`)

Replace the static `ANU_API_HOST` / `ANU_API_HOST_W` constants with `config.api_host` in both the WinHTTP and libcurl code paths. The WinHTTP path needs a `std::wstring` conversion of the host.

**3. Add `--qrng-api` CLI argument** (`common/arg.cpp`)

Add a new argument:
```
--qrng-api {anu,qbert}    Select QRNG API provider (default: anu)
```
Short, memorable, consistent with existing `--quantum-*` flags.

**4. Add `quantum_qrng_api` field to config struct** (`common/common.h`)

Add `std::string quantum_qrng_api = "anu"` to `common_params_sampling`. Valid values: `"anu"`, `"qbert"`.

**5. Pass provider selection to the manager** (`common/sampling.cpp`)

The `common_sampler` code needs to pass the selected API provider to the manager before the first QRNG call. Add a static method `psirngclient_manager::set_provider(provider_string)` that must be called before `get_instance()` first triggers initialization, or modify the manager constructor to read from a static config.

Simpler approach: Add a static `psirngclient_manager::configure(api_name)` method that stores the provider choice in a static variable. The constructor reads this when it initializes. This avoids changing the lazy-init singleton pattern.

**6. Update manager to select provider** (`src/psirngclient-manager.h`, `src/psirngclient-manager.cpp`)

- Add `static void configure(const std::string & qrng_api)` method
- Add static `std::string s_qrng_api` variable (default `"anu"`)
- In constructor: check `s_qrng_api` to decide which host and env var to use
- When `"qbert"`: use host `qbert.cipherstone.co`, read `QBERT_API_KEY` env var
- When `"anu"` (default): use host `api.quantumnumbers.anu.edu.au`, read `ANU_API_KEY` env var
- Update error messages to be provider-aware
- Update the success banner to show which provider is connected

**7. Call configure before sampling starts** (`common/sampling.cpp`)

Before `llama_sampler_init_dist()`, call `psirngclient_manager::configure(params.quantum_qrng_api)`.

**8. Set QBERT_API_KEY environment variable**

Set the user's Qbert API key in their environment. The key provided: `NgypsQRxsj78VAr1Y4vQorEIHxhjFPm2p3i5z_dwnvk`

**9. Update CLAUDE.md documentation**

Add Qbert to the quantum CLI arguments table and running instructions.

## Source Code Changes Summary

| File | Change |
|------|--------|
| `src/anu-qrng-client.h` | Add `api_host` to `Config` struct |
| `src/anu-qrng-client.cpp` | Use `config.api_host` instead of hardcoded host constants |
| `src/psirngclient-manager.h` | Add `static void configure(const std::string &)`, add `static std::string s_qrng_api` |
| `src/psirngclient-manager.cpp` | Implement provider selection logic in constructor based on `s_qrng_api` |
| `common/common.h` | Add `std::string quantum_qrng_api = "anu"` to `common_params_sampling` |
| `common/arg.cpp` | Add `--qrng-api` argument parsing |
| `common/sampling.cpp` | Call `psirngclient_manager::configure()` before sampler init |
| `CLAUDE.md` | Document `--qrng-api` flag and Qbert setup |

## Files NOT Modified

- `src/llama-sampling.cpp` — no changes needed (calls manager, not client)
- `tools/main/main.cpp` — no changes needed (color coding is provider-agnostic)
- `src/CMakeLists.txt` — no changes needed (no new source files)

## Verification

1. **Build**: `cmake -B build -DLLAMA_CURL=OFF && cmake --build build --config Release -j`
2. **Test ANU path**: `set ANU_API_KEY=... && build\bin\llama-cli -m model.gguf -p "test" -n 5 -no-cnv --quantum-verbose` (should work as before)
3. **Test Qbert path**: `set QBERT_API_KEY=... && build\bin\llama-cli -m model.gguf -p "test" -n 5 -no-cnv --qrng-api qbert --quantum-verbose` (should connect to Qbert)
4. **Test default**: Without `--qrng-api`, should default to ANU
5. **Test bad provider**: `--qrng-api invalid` should produce a clear error
6. **Format**: `git clang-format`
