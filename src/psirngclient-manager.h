#pragma once

#include "llama.h"
#include "anu-qrng-client.h"
#include <memory>

/**
 * Quantum Random Number Generator Manager
 *
 * Manages connection to ANU QRNG (Australian National University Quantum Random Numbers)
 * API endpoint: https://api.quantumnumbers.anu.edu.au
 *
 * Simplified interface - each token selection makes a fresh API call to get
 * true quantum randomness. No buffering to preserve temporal correlation.
 */
class psirngclient_manager {
public:
    /**
     * Configure QRNG API provider before first use.
     * Must be called before get_random_value() / is_healthy() / get_instance().
     *
     * @param qrng_api Provider name: "anu" (default) or "qbert"
     */
    LLAMA_API static void configure(const std::string & qrng_api);

    /**
     * Eagerly trigger singleton construction to catch API issues at startup.
     * Should be called after configure() when quantum sampling is enabled.
     * Throws std::runtime_error if initialization fails.
     */
    LLAMA_API static void ensure_initialized();

    /**
     * Get a quantum random value for token sampling
     *
     * @param output Pointer to store the random value (0.0 to 1.0)
     * @return 0 on success, -1 on failure
     */
    static int get_random_value(double* output);

    /**
     * Check if QRNG is connected
     */
    static bool is_healthy();

    /**
     * Get the underlying ANU client for statistics
     */
    static ANUQRNGClient* get_anu_client();

    /**
     * Get the mode value (0-255) from the last QRNG sample
     */
    static uint8_t get_last_mode();

    /**
     * Get the mode count (appearances) from the last QRNG sample
     * Expected value is ~80 (20480 bytes / 256 values)
     * Higher counts indicate statistical anomalies
     */
    static size_t get_last_mode_count();

    ~psirngclient_manager();

private:
    psirngclient_manager();

    static psirngclient_manager& get_instance();

    static std::string s_qrng_api;  // "anu" or "qbert", set via configure()

    std::unique_ptr<ANUQRNGClient> anu_client;
    bool initialized;
};
