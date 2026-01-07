#pragma once

// TODO: rename llama-sampling.h/.cpp to llama-sampler.h/.cpp ?

#include "llama.h"

#include <string>
#include <vector>

struct llama_vocab;
struct llama_grammar;

// sampler chain

struct llama_sampler_chain {
    llama_sampler_chain_params params;

    std::vector<struct llama_sampler *> samplers;

    // timing

    mutable int64_t t_sample_us;

    mutable int32_t n_sample;
};

struct llama_sampler * llama_sampler_init_dry_testing(
                         int32_t   context_size,
                           float   dry_multiplier,
                           float   dry_base,
                         int32_t   dry_allowed_length,
                         int32_t   dry_penalty_last_n,
  const std::vector<std::vector<llama_token>>& seq_breakers);

// Configure quantum parameters for dist sampler
// Simplified interface: just entropy-based adaptive sampling with EDT
LLAMA_API void llama_sampler_dist_set_quantum_params(
        struct llama_sampler * smpl,
        bool adaptive_sampling,
        float entropy_threshold,
        bool verbose,
        bool print_statistics,
        // EDT parameters
        bool edt_enabled,
        float edt_t0,
        float edt_theta,
        float edt_base);

// Print quantum sampling statistics
LLAMA_API void llama_sampler_dist_print_stats(struct llama_sampler * smpl);

// Check if statistics should be printed
LLAMA_API bool llama_sampler_dist_should_print_stats(const struct llama_sampler * smpl);

// Get last sample info for token coloring
// Returns true if last sample was quantum, false if greedy
// mode_out receives the mode value (0-255)
// count_out receives how many times the mode appeared (expected ~80)
LLAMA_API bool llama_sampler_dist_get_last_info(const struct llama_sampler * smpl, uint8_t * mode_out, size_t * count_out);
