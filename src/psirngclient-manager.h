#pragma once

#include "psirngclient.h"

class psirngclient_manager {
public:
    static psirngclient* get_psirngclient();
    ~psirngclient_manager();

private:
    psirngclient_manager();
    psirngclient* psirngclient_ptr = nullptr;
};