#include <cstdlib>
#include <stdexcept>
#include <string>

#include "psirngclient-manager.h"

psirngclient* psirngclient_manager::get_psirngclient() {
    static psirngclient_manager manager;
    return manager.psirngclient_ptr;
}

psirngclient_manager::~psirngclient_manager() {
    if (psirngclient_ptr) {
        psirngclient_free(psirngclient_ptr);
    }
}

psirngclient_manager::psirngclient_manager() {
    const char* psirng_host      = std::getenv("PSIRNG_HOST");
    const char* psirng_grpc_port = std::getenv("PSIRNG_GRPC_PORT");
    const char* psirng_cert_path = std::getenv("PSIRNG_CERT_PATH");

    if (psirng_host != nullptr && psirng_grpc_port != nullptr && psirng_cert_path != nullptr) {
        int result = psirngclient_init(&psirngclient_ptr, psirng_host, std::atoi(psirng_grpc_port), psirng_cert_path);
        if (result != PSIRNGCLIENT_RESULT_OK) {
            throw std::runtime_error("failed to initialize psirng client: " + std::to_string(result));
        }

        if (!psirngclient_ishealthy(psirngclient_ptr)) {
            throw std::runtime_error("psirng is not healthy");
        }
    } else {
        throw std::runtime_error("psirng is not configured");
    }
}
