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

---

## Workflow Steps

### [x] Step: Technical Specification
<!-- chat-id: c46d4226-005f-416a-8ff2-f0c3b2663fe4 -->

Assess the task's difficulty, as underestimating it leads to poor outcomes.
- easy: Straightforward implementation, trivial bug fix or feature
- medium: Moderate complexity, some edge cases or caveats to consider
- hard: Complex logic, many caveats, architectural considerations, or high-risk changes

Create a technical specification for the task that is appropriate for the complexity level:
- Review the existing codebase architecture and identify reusable components.
- Define the implementation approach based on established patterns in the project.
- Identify all source code files that will be created or modified.
- Define any necessary data model, API, or interface changes.
- Describe verification steps using the project's test and lint commands.

Save the output to `{@artifacts_path}/spec.md` with:
- Technical context (language, dependencies)
- Implementation approach
- Source code structure changes
- Data model / API / interface changes
- Verification approach

If the task is complex enough, create a detailed implementation plan based on `{@artifacts_path}/spec.md`:
- Break down the work into concrete tasks (incrementable, testable milestones)
- Each task should reference relevant contracts and include verification steps
- Replace the Implementation step below with the planned tasks

Rule of thumb for step size: each step should represent a coherent unit of work (e.g., implement a component, add an API endpoint, write tests for a module). Avoid steps that are too granular (single function).

Important: unit tests must be part of each implementation task, not separate tasks. Each task should implement the code and its tests together, if relevant.

Save to `{@artifacts_path}/plan.md`. If the feature is trivial and doesn't warrant this breakdown, keep the Implementation step below as is.

---

### [x] Step: Parameterize ANUQRNGClient and update manager
<!-- chat-id: 47fd3343-7dc1-47a1-bc18-8d177caaf310 -->

Modify the QRNG client and manager to support multiple API providers by parameterizing the hostname and API key source. This is the core implementation step.

1. **`src/anu-qrng-client.h`**: Add `std::string api_host` to `ANUQRNGClient::Config` with default `"api.quantumnumbers.anu.edu.au"`
2. **`src/anu-qrng-client.cpp`**: Replace hardcoded `ANU_API_HOST` / `ANU_API_HOST_W` with `config.api_host` in both WinHTTP and libcurl paths. For WinHTTP, convert `config.api_host` to `std::wstring`.
3. **`src/psirngclient-manager.h`**: Add `static void configure(const std::string & qrng_api)` public method and `static std::string s_qrng_api` private static member.
4. **`src/psirngclient-manager.cpp`**: Implement `configure()`. Update constructor to branch on `s_qrng_api`: when `"qbert"`, read `QBERT_API_KEY` env var and set `config.api_host = "qbert.cipherstone.co"`; when `"anu"` (default), keep existing behavior. Update error/success messages to be provider-aware.
5. Build and verify compilation succeeds.

### [x] Step: Add CLI argument and wire through config
<!-- chat-id: 55804954-571c-4838-aaac-25accde938c5 -->

Add the `--qrng-api` CLI flag and connect it to the manager.

1. **`common/common.h`**: Add `std::string quantum_qrng_api = "anu"` to `common_params_sampling`.
2. **`common/arg.cpp`**: Add `--qrng-api` argument that accepts `{anu,qbert}` and sets `params.sampling.quantum_qrng_api`. Place it near the other `--quantum-*` args.
3. **`common/sampling.cpp`**: Call `psirngclient_manager::configure(params.quantum_qrng_api)` before `llama_sampler_init_dist()`.
4. Build, run `git clang-format`, verify compilation.

### [x] Step: Set env var, update docs, and write report
<!-- chat-id: 9dafb2ad-8a7f-4a69-8672-d5f4965c7a8b -->

1. Set `QBERT_API_KEY` environment variable with the user's key.
2. **`CLAUDE.md`**: Add `--qrng-api` to the CLI arguments table, add Qbert setup instructions alongside ANU.
3. Build full project: `cmake -B build -DLLAMA_CURL=OFF && cmake --build build --config Release -j`
4. Run `git clang-format` for code formatting.
5. Write `{@artifacts_path}/report.md` with implementation summary, testing notes, and any issues encountered.
