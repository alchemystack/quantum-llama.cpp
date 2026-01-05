#pragma once

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
     * Get a quantum random value for token sampling
     *
     * @param output Pointer to store the random value (0.0 to 1.0)
     * @return 0 on success, -1 on failure
     */
    static int get_random_value(double* output);

    /**
     * Check if ANU QRNG is connected
     */
    static bool is_healthy();

    /**
     * Get the underlying ANU client for statistics
     */
    static ANUQRNGClient* get_anu_client();

    ~psirngclient_manager();

private:
    psirngclient_manager();

    static psirngclient_manager& get_instance();

    std::unique_ptr<ANUQRNGClient> anu_client;
    bool initialized;
};
