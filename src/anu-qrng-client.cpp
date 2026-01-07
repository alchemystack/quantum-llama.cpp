#include "anu-qrng-client.h"
#include <stdexcept>
#include <sstream>
#include <cstring>
#include <algorithm>
#include <thread>
#include <chrono>
#include <cstdio>
#include <array>

// Platform-specific HTTP client
#ifdef _WIN32
    #define WIN32_LEAN_AND_MEAN
    #define NOMINMAX
    #include <windows.h>
    #include <winhttp.h>
    #pragma comment(lib, "winhttp.lib")
#else
    #include <curl/curl.h>
#endif

// Debug logging - set to 1 to enable verbose debug output
#define ANU_DEBUG 0
#if ANU_DEBUG
#define ANU_LOG(fmt, ...) fprintf(stderr, "[ANU-QRNG] " fmt "\n", ##__VA_ARGS__)
#else
#define ANU_LOG(fmt, ...) ((void)0)
#endif

// ANU QRNG API endpoint
static const char* ANU_API_HOST = "api.quantumnumbers.anu.edu.au";
static const wchar_t* ANU_API_HOST_W = L"api.quantumnumbers.anu.edu.au";

ANUQRNGClient::ANUQRNGClient(const Config& config)
    : config(config), stats(), initialized(false) {
    // API key must be provided via Config (set from ANU_API_KEY environment variable)
    // No default key - security best practice
}

ANUQRNGClient::~ANUQRNGClient() {
}

int ANUQRNGClient::initialize() {
    std::lock_guard<std::mutex> lock(mutex);

    ANU_LOG("Initializing ANU QRNG client...");

    // Test connection with a small hex16 request
    std::vector<uint8_t> test_values;
    int result = http_request_hex16(test_values);

    if (result != 0 || test_values.empty()) {
        ANU_LOG("Connection test FAILED");
        return -1;
    }

    initialized = true;
    ANU_LOG("ANU QRNG initialized successfully! Got %zu uint8 values from test", test_values.size());
    return 0;
}

bool ANUQRNGClient::is_healthy() const {
    return initialized;
}

int ANUQRNGClient::get_random_value(double* output) {
    std::lock_guard<std::mutex> lock(mutex);

    if (!initialized) {
        return -1;
    }

    uint8_t mode_value;
    int result = fetch_and_find_mode(&mode_value);

    if (result != 0) {
        return -1;
    }

    // Store mode value for color-coding
    last_mode = mode_value;

    // Convert uint8 mode to double in [0, 1)
    *output = static_cast<double>(mode_value) / 256.0;

    stats.total_samples++;
    ANU_LOG("Quantum random value: mode=%u, output=%.6f", mode_value, *output);

    return 0;
}

int ANUQRNGClient::fetch_and_find_mode(uint8_t* mode_out) {
    // Try up to max_retries times in case of ties
    for (uint32_t attempt = 0; attempt < config.max_retries; ++attempt) {
        std::vector<uint8_t> uint8_values;
        int result = http_request_hex16(uint8_values);

        if (result != 0 || uint8_values.empty()) {
            stats.failed_requests++;
            ANU_LOG("HTTP request failed (attempt %u)", attempt + 1);
            std::this_thread::sleep_for(std::chrono::milliseconds(100 * (1 << attempt)));
            continue;
        }

        // Find mode and count
        size_t mode_count = 0;
        if (find_mode(uint8_values, mode_out, &mode_count)) {
            last_mode_count = mode_count;  // Store the count for later retrieval
            ANU_LOG("Found unique mode: %u with count %zu (from %zu values)", *mode_out, mode_count, uint8_values.size());
            return 0;
        }

        // Tie detected - retry
        stats.tie_retries++;
        ANU_LOG("Mode tie detected (attempt %u), retrying...", attempt + 1);
    }

    ANU_LOG("Failed to find unique mode after %u attempts", config.max_retries);
    return -1;
}

bool ANUQRNGClient::find_mode(const std::vector<uint8_t>& values, uint8_t* mode_out, size_t* count_out) {
    if (values.empty()) {
        return false;
    }

    // Count occurrences of each byte value
    std::array<size_t, 256> counts = {};
    for (uint8_t val : values) {
        counts[val]++;
    }

    // Find maximum count
    size_t max_count = 0;
    for (size_t i = 0; i < 256; ++i) {
        if (counts[i] > max_count) {
            max_count = counts[i];
        }
    }

    // Check for ties and find the mode
    uint8_t mode = 0;
    size_t num_with_max = 0;
    for (size_t i = 0; i < 256; ++i) {
        if (counts[i] == max_count) {
            mode = static_cast<uint8_t>(i);
            num_with_max++;
        }
    }

    if (num_with_max > 1) {
        ANU_LOG("Tie detected: %zu values have count %zu", num_with_max, max_count);
        return false;  // Tie - caller should retry
    }

    *mode_out = mode;
    if (count_out) {
        *count_out = max_count;
    }
    return true;
}

// Parse hex16 JSON response
// Response format: {"success":true,"type":"hex16","length":"N","data":["hex_string1","hex_string2",...]}
// Each string is raw hex data (2 hex chars per byte)
bool ANUQRNGClient::parse_hex16_response(const std::vector<uint8_t>& json_data,
                                         std::vector<uint8_t>& uint8_values) {
    std::string json(json_data.begin(), json_data.end());

    ANU_LOG("Parsing hex16 JSON response (%zu bytes)", json.size());

    // Check for success
    if (json.find("\"success\":true") == std::string::npos &&
        json.find("\"success\": true") == std::string::npos) {
        ANU_LOG("Response does not contain success:true");
        return false;
    }

    // Find "data" array
    size_t data_pos = json.find("\"data\"");
    if (data_pos == std::string::npos) {
        ANU_LOG("No 'data' field found in response");
        return false;
    }

    // Find the opening bracket of the data array
    size_t array_start = json.find('[', data_pos);
    if (array_start == std::string::npos) {
        ANU_LOG("No array start found after 'data'");
        return false;
    }

    uint8_values.clear();

    // Parse each hex string in the data array
    size_t pos = array_start;
    while ((pos = json.find('"', pos)) != std::string::npos) {
        size_t start = pos + 1;
        size_t end = json.find('"', start);
        if (end == std::string::npos) break;

        std::string hex_string = json.substr(start, end - start);
        pos = end + 1;

        // Check if it's a valid hex string (even length, all hex chars)
        if (hex_string.length() >= 2 && hex_string.length() % 2 == 0) {
            bool is_hex = true;
            for (char c : hex_string) {
                if (!std::isxdigit(static_cast<unsigned char>(c))) {
                    is_hex = false;
                    break;
                }
            }

            if (is_hex) {
                // Convert hex string to bytes (2 hex chars = 1 byte)
                for (size_t i = 0; i < hex_string.length(); i += 2) {
                    std::string byte_str = hex_string.substr(i, 2);
                    unsigned int byte_val = 0;
                    std::istringstream(byte_str) >> std::hex >> byte_val;
                    uint8_values.push_back(static_cast<uint8_t>(byte_val));
                }
            }
        }
    }

    ANU_LOG("Extracted %zu uint8 values from hex data", uint8_values.size());
    return !uint8_values.empty();
}

#ifdef _WIN32
// Windows implementation using WinHTTP
int ANUQRNGClient::http_request_hex16(std::vector<uint8_t>& uint8_values) {
    // Build URL path: ?length=1024&size=10&type=hex16
    std::wstring urlPath = L"/?length=1024&size=10&type=hex16";

    ANU_LOG("Requesting hex16 data from ANU QRNG (length=1024, size=10)...");

    stats.total_requests++;

    // Open session
    HINTERNET hSession = WinHttpOpen(
        L"ANU-QRNG-Client/2.0",
        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
        WINHTTP_NO_PROXY_NAME,
        WINHTTP_NO_PROXY_BYPASS,
        0
    );

    if (!hSession) {
        ANU_LOG("WinHttpOpen failed: %lu", GetLastError());
        return -1;
    }

    // Set timeouts
    WinHttpSetTimeouts(hSession, config.timeout_ms, config.timeout_ms,
                      config.timeout_ms, config.timeout_ms);

    // Connect
    HINTERNET hConnect = WinHttpConnect(
        hSession,
        ANU_API_HOST_W,
        INTERNET_DEFAULT_HTTPS_PORT,
        0
    );

    if (!hConnect) {
        ANU_LOG("WinHttpConnect failed: %lu", GetLastError());
        WinHttpCloseHandle(hSession);
        return -1;
    }

    // Open request
    HINTERNET hRequest = WinHttpOpenRequest(
        hConnect,
        L"GET",
        urlPath.c_str(),
        NULL,
        WINHTTP_NO_REFERER,
        WINHTTP_DEFAULT_ACCEPT_TYPES,
        WINHTTP_FLAG_SECURE
    );

    if (!hRequest) {
        ANU_LOG("WinHttpOpenRequest failed: %lu", GetLastError());
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return -1;
    }

    // Add API key header
    std::wstring api_key_header = L"x-api-key: ";
    api_key_header += std::wstring(config.api_key.begin(), config.api_key.end());

    if (!WinHttpAddRequestHeaders(hRequest, api_key_header.c_str(), -1, WINHTTP_ADDREQ_FLAG_ADD)) {
        ANU_LOG("Failed to add API key header: %lu", GetLastError());
    }

    // Send request
    BOOL bResults = WinHttpSendRequest(
        hRequest,
        WINHTTP_NO_ADDITIONAL_HEADERS,
        0,
        WINHTTP_NO_REQUEST_DATA,
        0,
        0,
        0
    );

    if (!bResults) {
        ANU_LOG("WinHttpSendRequest failed: %lu", GetLastError());
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return -1;
    }

    // Receive response
    bResults = WinHttpReceiveResponse(hRequest, NULL);
    if (!bResults) {
        ANU_LOG("WinHttpReceiveResponse failed: %lu", GetLastError());
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return -1;
    }

    // Check status code
    DWORD statusCode = 0;
    DWORD statusCodeSize = sizeof(statusCode);
    WinHttpQueryHeaders(hRequest,
        WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
        WINHTTP_HEADER_NAME_BY_INDEX, &statusCode, &statusCodeSize, WINHTTP_NO_HEADER_INDEX);

    ANU_LOG("HTTP status code: %lu", statusCode);

    if (statusCode != 200) {
        ANU_LOG("HTTP request failed with status %lu", statusCode);
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return -1;
    }

    // Read response
    std::vector<uint8_t> json_response;
    DWORD dwSize = 0;
    DWORD dwDownloaded = 0;
    BYTE buffer[8192];

    do {
        dwSize = 0;
        if (!WinHttpQueryDataAvailable(hRequest, &dwSize)) break;
        if (dwSize == 0) break;

        DWORD bytesToRead = (std::min)(static_cast<DWORD>(dwSize), static_cast<DWORD>(sizeof(buffer)));
        if (!WinHttpReadData(hRequest, buffer, bytesToRead, &dwDownloaded)) break;

        json_response.insert(json_response.end(), buffer, buffer + dwDownloaded);
    } while (dwSize > 0);

    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);

    // Parse response
    if (!parse_hex16_response(json_response, uint8_values)) {
        ANU_LOG("Failed to parse hex16 response");
        return -1;
    }

    return 0;
}

#else
// Linux/Mac implementation using libcurl
static size_t curl_write_callback(void* contents, size_t size, size_t nmemb, void* userp) {
    size_t total_size = size * nmemb;
    std::vector<uint8_t>* vec = static_cast<std::vector<uint8_t>*>(userp);
    const uint8_t* data = static_cast<const uint8_t*>(contents);
    vec->insert(vec->end(), data, data + total_size);
    return total_size;
}

int ANUQRNGClient::http_request_hex16(std::vector<uint8_t>& uint8_values) {
    CURL* curl = curl_easy_init();
    if (!curl) {
        return -1;
    }

    stats.total_requests++;

    // Build URL: ?length=1024&size=10&type=hex16
    std::string url = "https://";
    url += ANU_API_HOST;
    url += "?length=1024&size=10&type=hex16";

    ANU_LOG("Requesting hex16 data from ANU QRNG (length=1024, size=10)...");

    std::vector<uint8_t> json_response;

    // Set up headers
    struct curl_slist* headers = NULL;
    std::string api_key_header = "x-api-key: " + config.api_key;
    headers = curl_slist_append(headers, api_key_header.c_str());

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &json_response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, config.timeout_ms);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);

    CURLcode res = curl_easy_perform(curl);

    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    if (res != CURLE_OK) {
        ANU_LOG("curl_easy_perform failed: %s", curl_easy_strerror(res));
        return -1;
    }

    // Parse response
    if (!parse_hex16_response(json_response, uint8_values)) {
        return -1;
    }

    return 0;
}
#endif

void ANUQRNGClient::reset_statistics() {
    std::lock_guard<std::mutex> lock(mutex);
    stats = Statistics();
}

const ANUQRNGClient::Statistics& ANUQRNGClient::get_statistics() const {
    return stats;
}
