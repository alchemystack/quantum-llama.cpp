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
 * Algorithm:
 * 1. Fetch hex16 data from ANU API (length=1024, size=10)
 * 2. Convert hex16 values to binary, split into 8-bit chunks (uint8)
 * 3. Find the mode (most frequent byte value 0-255)
 * 4. If there's a tie, repeat API call until single winner
 * 5. Return mode value for use in sampling
 */

class ANUQRNGClient {
public:
    struct Config {
        std::string api_key;           // ANU API key
        uint32_t timeout_ms;           // HTTP request timeout (default: 30000ms)
        uint32_t max_retries;          // Max retry attempts for ties/failures (default: 10)

        Config() :
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
     * Returns the mode (most frequent byte value) from the quantum data.
     * Automatically retries if there's a tie for most frequent value.
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
        size_t tie_retries;              // Retries due to mode ties
        size_t total_samples;            // Successful samples returned

        Statistics() : total_requests(0), failed_requests(0),
                      tie_retries(0), total_samples(0) {}
    };

    const Statistics& get_statistics() const;
    void reset_statistics();

private:
    Config config;
    Statistics stats;
    mutable std::mutex mutex;
    bool initialized;

    // Fetch hex16 data and find mode
    int fetch_and_find_mode(uint8_t* mode_out);

    // HTTP request to ANU API
    int http_request_hex16(std::vector<uint8_t>& uint8_values);

    // Parse hex16 JSON response into uint8 values
    static bool parse_hex16_response(const std::vector<uint8_t>& json_data,
                                     std::vector<uint8_t>& uint8_values);

    // Find mode (most frequent value) - returns false if tie
    static bool find_mode(const std::vector<uint8_t>& values, uint8_t* mode_out);
};
