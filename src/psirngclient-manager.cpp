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

psirngclient_manager::~psirngclient_manager() {
    QRNG_LOG("~psirngclient_manager() destroying instance");
    // anu_client is unique_ptr, automatically cleaned up
}

psirngclient_manager::psirngclient_manager() : initialized(false) {
    QRNG_LOG("=== psirngclient_manager constructor starting ===");
    QRNG_LOG("Using ANU Quantum Random Numbers API (quantumnumbers.anu.edu.au)");

    // Require API key from environment variable
    const char* anu_api_key = std::getenv("ANU_API_KEY");

    if (anu_api_key == nullptr || std::strlen(anu_api_key) == 0) {
        fprintf(stderr, "\n");
        fprintf(stderr, "[quantum-llama] ERROR: ANU_API_KEY environment variable not set\n");
        fprintf(stderr, "[quantum-llama] \n");
        fprintf(stderr, "[quantum-llama] To use quantum random sampling, you need an ANU QRNG API key.\n");
        fprintf(stderr, "[quantum-llama] Get your FREE API key at: https://quantumnumbers.anu.edu.au/\n");
        fprintf(stderr, "[quantum-llama] \n");
        fprintf(stderr, "[quantum-llama] Then set it in your environment:\n");
        fprintf(stderr, "[quantum-llama]   export ANU_API_KEY=\"your-api-key-here\"   (Linux/Mac)\n");
        fprintf(stderr, "[quantum-llama]   set ANU_API_KEY=your-api-key-here         (Windows CMD)\n");
        fprintf(stderr, "[quantum-llama]   $env:ANU_API_KEY=\"your-api-key-here\"     (PowerShell)\n");
        fprintf(stderr, "\n");
        fflush(stderr);
        throw std::runtime_error("ANU_API_KEY environment variable required for quantum sampling");
    }

    ANUQRNGClient::Config config;
    config.api_key = anu_api_key;
    QRNG_LOG("Using ANU API key from environment");

    config.timeout_ms = 30000;
    config.max_retries = 10;

    try {
        QRNG_LOG("Creating ANU QRNG client...");
        anu_client = std::make_unique<ANUQRNGClient>(config);

        QRNG_LOG("Calling initialize()...");
        int result = anu_client->initialize();

        if (result == 0) {
            initialized = true;
            QRNG_LOG("ANU QRNG initialized successfully!");
            fprintf(stderr, "[quantum-llama] Connected to ANU QRNG - using true quantum randomness\n");
            fflush(stderr);
        } else {
            QRNG_LOG("ANU QRNG initialization FAILED with code %d", result);
            anu_client.reset();
            throw std::runtime_error("ANU QRNG initialization failed");
        }
    } catch (const std::exception& e) {
        QRNG_LOG("Exception during ANU QRNG init: %s", e.what());
        anu_client.reset();
        throw std::runtime_error("ANU QRNG initialization failed: " + std::string(e.what()));
    }
}
