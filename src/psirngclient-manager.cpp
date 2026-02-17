#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <cstdio>

#include "psirngclient-manager.h"

// Diagnostic logging macro
#define QRNG_DEBUG 0
#if QRNG_DEBUG
#define QRNG_LOG(fmt, ...) fprintf(stderr, "[QRNG-DEBUG] " fmt "\n", ##__VA_ARGS__)
#else
#define QRNG_LOG(fmt, ...) ((void)0)
#endif

// Default provider is ANU; call configure() before first get_instance() to change.
std::string psirngclient_manager::s_qrng_api = "anu";

void psirngclient_manager::configure(const std::string & qrng_api) {
    s_qrng_api = qrng_api;
}

void psirngclient_manager::ensure_initialized() {
    // Force the lazy singleton to construct now, triggering the API connectivity
    // check at startup rather than on the first token.  The constructor throws
    // std::runtime_error on failure, which the caller can catch.
    get_instance();
}

psirngclient_manager& psirngclient_manager::get_instance() {
    static psirngclient_manager instance;
    return instance;
}

int psirngclient_manager::get_random_value(double* output) {
    auto& manager = get_instance();

    if (!manager.initialized || !manager.anu_client) {
        QRNG_LOG("ERROR: ANU QRNG not initialized");
        return -1;
    }

    return manager.anu_client->get_random_value(output);
}

bool psirngclient_manager::is_healthy() {
    auto& manager = get_instance();
    return manager.initialized && manager.anu_client && manager.anu_client->is_healthy();
}

ANUQRNGClient* psirngclient_manager::get_anu_client() {
    auto& manager = get_instance();
    return manager.anu_client.get();
}

uint8_t psirngclient_manager::get_last_mode() {
    auto& manager = get_instance();
    if (manager.anu_client) {
        return manager.anu_client->get_last_mode();
    }
    return 128;  // Default midpoint if not initialized
}

size_t psirngclient_manager::get_last_mode_count() {
    auto& manager = get_instance();
    if (manager.anu_client) {
        return manager.anu_client->get_last_mode_count();
    }
    return 80;  // Expected average if not initialized
}

psirngclient_manager::~psirngclient_manager() {
    QRNG_LOG("~psirngclient_manager() destroying instance");
    // anu_client is unique_ptr, automatically cleaned up
}

psirngclient_manager::psirngclient_manager() : initialized(false) {
    QRNG_LOG("=== psirngclient_manager constructor starting ===");

    // Determine provider-specific settings
    const char * env_var_name = nullptr;
    const char * api_host     = nullptr;
    const char * provider_label = nullptr;
    const char * provider_url   = nullptr;

    if (s_qrng_api == "qbert") {
        env_var_name   = "QBERT_API_KEY";
        api_host       = "qbert.cipherstone.co";
        provider_label = "Qbert QRNG (qbert.cipherstone.co)";
        provider_url   = nullptr;  // invite-only, no public signup URL
    } else {
        // Default: ANU
        env_var_name   = "ANU_API_KEY";
        api_host       = "api.quantumnumbers.anu.edu.au";
        provider_label = "ANU QRNG (quantumnumbers.anu.edu.au)";
        provider_url   = "https://quantumnumbers.anu.edu.au/";
    }

    QRNG_LOG("Using %s", provider_label);

    // Require API key from environment variable
    const char * api_key = std::getenv(env_var_name);

    if (api_key == nullptr || std::strlen(api_key) == 0) {
        fprintf(stderr, "\n");
        fprintf(stderr, "[quantum-llama] ERROR: %s environment variable not set\n", env_var_name);
        fprintf(stderr, "[quantum-llama] \n");
        fprintf(stderr, "[quantum-llama] To use quantum random sampling with %s, you need an API key.\n", provider_label);
        if (provider_url) {
            fprintf(stderr, "[quantum-llama] Get your FREE API key at: %s\n", provider_url);
        }
        fprintf(stderr, "[quantum-llama] \n");
        fprintf(stderr, "[quantum-llama] Then set it in your environment:\n");
        fprintf(stderr, "[quantum-llama]   export %s=\"your-api-key-here\"   (Linux/Mac)\n", env_var_name);
        fprintf(stderr, "[quantum-llama]   set %s=your-api-key-here         (Windows CMD)\n", env_var_name);
        fprintf(stderr, "[quantum-llama]   $env:%s=\"your-api-key-here\"     (PowerShell)\n", env_var_name);
        fprintf(stderr, "\n");
        fflush(stderr);

        std::string msg = std::string(env_var_name) + " environment variable required for quantum sampling";
        throw std::runtime_error(msg);
    }

    ANUQRNGClient::Config config;
    config.api_key  = api_key;
    config.api_host = api_host;
    QRNG_LOG("Using API key from %s", env_var_name);

    config.timeout_ms  = 30000;
    config.max_retries = 10;

    try {
        QRNG_LOG("Creating QRNG client for %s...", provider_label);
        anu_client = std::make_unique<ANUQRNGClient>(config);

        QRNG_LOG("Calling initialize()...");
        int result = anu_client->initialize();

        if (result == 0) {
            initialized = true;
            QRNG_LOG("QRNG initialized successfully!");
            fprintf(stderr, "[quantum-llama] Connected to %s - using true quantum randomness\n", provider_label);
            fprintf(stderr, "[quantum-llama] Token color legend (based on mode count, expected ~80):\n");
            fprintf(stderr, "[quantum-llama]   \033[90m■ grey\033[0m - deterministic (no QRNG)\n");
            fprintf(stderr, "[quantum-llama]   \033[37m■ white\033[0m - statistically common (count < 106)\n");
            fprintf(stderr, "[quantum-llama]   \033[38;5;218m■ pink\033[0m - above average frequency (count 106-108)\n");
            fprintf(stderr, "[quantum-llama]   \033[31m■ red\033[0m - rare (count 109-111)\n");
            fprintf(stderr, "[quantum-llama]   \033[38;5;135m■ purple\033[0m - mythic rare (count 112+)\n");
            fflush(stderr);
        } else {
            QRNG_LOG("QRNG initialization FAILED with code %d", result);
            anu_client.reset();
            throw std::runtime_error(std::string(provider_label) + " initialization failed");
        }
    } catch (const std::exception & e) {
        QRNG_LOG("Exception during QRNG init: %s", e.what());
        anu_client.reset();
        throw std::runtime_error(std::string(provider_label) + " initialization failed: " + std::string(e.what()));
    }
}
