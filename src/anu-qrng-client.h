#pragma once

#include <string>
#include <vector>
#include <cstdint>
#include <mutex>

/**
 * ANU Quantum Random Number Generator Client
 *
 * Connects to Australian National University Quantum Random Numbers API
 * https://quantumnumbers.anu.edu.au
 *
 * IMPORTANT: Never buffers quantum data. Each call makes a fresh API request
 * to preserve temporal correlation between consciousness and token selection.
 *
 * Algorithm (z-score based):
 * 1. Fetch hex16 data from ANU API (length=1024, size=10)
 * 2. Convert hex16 values to binary, split into 8-bit chunks (uint8)
 * 3. Compute sample mean of all ~20,480 bytes
 * 4. Compute z-score: z = (mean - 127.5) / 0.51433
 * 5. Map through normal CDF: u = Phi(z)
 * 6. Clamp u to (1e-10, 1 - 1e-10)
 * 7. Return u for use in sampling
 */

class ANUQRNGClient {
public:
    struct Config {
        std::string api_key;           // API key (from ANU_API_KEY or QBERT_API_KEY env var)
        std::string api_host;          // API hostname (default: ANU)
        uint32_t timeout_ms;           // HTTP request timeout (default: 30000ms)
        uint32_t max_retries;          // Max retry attempts for failures (default: 10)

        Config() :
            api_host("api.quantumnumbers.anu.edu.au"),
            timeout_ms(30000),
            max_retries(10) {}
    };

    ANUQRNGClient(const Config& config);
    ~ANUQRNGClient();

    /**
     * Initialize connection to ANU QRNG API
     * Tests connectivity with a small request
     * @return 0 on success, -1 on failure
     */
    int initialize();

    /**
     * Check if service is connected and healthy
     */
    bool is_healthy() const;

    /**
     * Get a quantum random value for token sampling
     *
     * Makes a fresh HTTP request to ANU API (no buffering).
     * Computes z-score from 20,480 byte sample mean, maps through
     * normal CDF to get uniform float in (0, 1).
     *
     * @param output Pointer to store the random value (0.0 to 1.0)
     * @return 0 on success, -1 on failure
     */
    int get_random_value(double* output);

    /**
     * Statistics for monitoring
     */
    struct Statistics {
        size_t total_requests;           // HTTP requests made
        size_t failed_requests;          // Failed requests
        size_t total_samples;            // Successful samples returned

        Statistics() : total_requests(0), failed_requests(0),
                      total_samples(0) {}
    };

    const Statistics& get_statistics() const;
    void reset_statistics();

    /**
     * Get the z-score from the last QRNG sample
     * z = (sample_mean - 127.5) / 0.51433
     * |z| < 1 is typical, |z| > 2 is notable
     */
    double get_last_z_score() const { return last_z_score; }

private:
    Config config;
    Statistics stats;
    mutable std::mutex mutex;
    bool initialized;
    double last_z_score = 0.0;         // Last z-score from QRNG sample

    // Fetch hex16 data and compute z-score, returning uniform value via u_out
    int fetch_and_compute_zscore(double* u_out);

    // HTTP request to ANU API
    int http_request_hex16(std::vector<uint8_t>& uint8_values);

    // Parse hex16 JSON response into uint8 values
    static bool parse_hex16_response(const std::vector<uint8_t>& json_data,
                                     std::vector<uint8_t>& uint8_values);
};
