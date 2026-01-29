#pragma once

#include "psirngclient.h"
#include "psijent.h"

class psirng_wrapper {
public:
    ~psirng_wrapper();
    static double uniform01();

private:
    psirng_wrapper();
    static psirng_wrapper& instance();
    psirngclient* psirngclient_ptr = nullptr;
    psijent* psijent_ptr = nullptr;
    int psijent_mantissa_length = 52;
};