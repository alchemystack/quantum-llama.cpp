#include "psirng-wrapper.h"

#include <algorithm>
#include <cstdlib>
#include <stdexcept>
#include <string>

psirng_wrapper & psirng_wrapper::instance() {
    static psirng_wrapper instance;
    return instance;
}

psirng_wrapper::psirng_wrapper() {
    const char* psirng_host      = std::getenv("PSIRNG_HOST");
    const char* psirng_grpc_port = std::getenv("PSIRNG_GRPC_PORT");
    const char* psirng_cert_path = std::getenv("PSIRNG_CERT_PATH");

    bool bool_psijent_fallback = false;
    if (const char * psijent_fallback = std::getenv("PSIJENT_FALLBACK")) {
        std::string str_psijent_fallback(psijent_fallback);
        std::transform(
            str_psijent_fallback.begin(),
            str_psijent_fallback.end(),
            str_psijent_fallback.begin(),
            [](const unsigned char c) {
                return static_cast<char>(std::tolower(c));
            }
        );
        bool_psijent_fallback = str_psijent_fallback == "yes" ||
                                str_psijent_fallback == "on" ||
                                str_psijent_fallback == "true" ||
                                str_psijent_fallback == "1";
    }

    int result;
    bool should_init_psijent = false;

    if (psirng_host && psirng_grpc_port && psirng_cert_path) {
        result = psirngclient_init(&psirngclient_ptr, psirng_host, std::atoi(psirng_grpc_port), psirng_cert_path);
        if (result != PSIRNGCLIENT_RESULT_OK) {
            if (bool_psijent_fallback) {
                should_init_psijent = true;
            } else {
                throw std::runtime_error("failed to initialize psirng client: " + std::to_string(result));
            }
        }

        if (!psirngclient_ishealthy(psirngclient_ptr)) {
            psirngclient_free(psirngclient_ptr);
            if (bool_psijent_fallback) {
                should_init_psijent = true;
            } else {
                throw std::runtime_error("psirng is not healthy");
            }
        }
    } else {
        if (bool_psijent_fallback) {
            should_init_psijent = true;
        } else {
            throw std::runtime_error("psirng is not configured");
        }
    }

    if (should_init_psijent) {
        result = psijent_init(&psijent_ptr);
        if (result != PSIJENT_RESULT_OK) {
            throw std::runtime_error("failed to initialize psijent");
        }

        result = psijent_start(psijent_ptr);
        if (result != PSIJENT_RESULT_OK) {
            psijent_free(psijent_ptr);
            throw std::runtime_error("failed to start psijent");
        }

        if (const char * mantissa_length = std::getenv("PSIJENT_MANTISSA_LENGTH")) {
            psijent_mantissa_length = std::atoi(mantissa_length);
        }
    }
}

psirng_wrapper::~psirng_wrapper() {
    if (psirngclient_ptr) {
        psirngclient_free(psirngclient_ptr);
    }

    if (psijent_ptr) {
        psijent_free(psijent_ptr);
    }
}

double psirng_wrapper::uniform01() {
    const psirng_wrapper & instance = psirng_wrapper::instance();

    int result;
    double value = 0.0;

    if (instance.psijent_ptr) {
        result = psijent_randuniform(instance.psijent_ptr, &value, 1, instance.psijent_mantissa_length);
        if (result != PSIJENT_RESULT_OK) {
            throw std::runtime_error("psijent_randuniform failed: " + std::to_string(result));
        }
    } else {
        result = psirngclient_randuniform(instance.psirngclient_ptr, &value, 1, 0.0, 1.0);
        if (result != PSIRNGCLIENT_RESULT_OK) {
            throw std::runtime_error("psirngclient_randuniform failed: " + std::to_string(result));
        }
    }

    return value;
}
