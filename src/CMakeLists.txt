llama_add_compile_flags()

#
# libraries
#

# llama

add_library(llama
            ../include/llama.h
            llama.cpp
            llama-adapter.cpp
            llama-arch.cpp
            llama-batch.cpp
            llama-chat.cpp
            llama-context.cpp
            llama-cparams.cpp
            llama-grammar.cpp
            llama-graph.cpp
            llama-hparams.cpp
            llama-impl.cpp
            llama-io.cpp
            llama-kv-cache.cpp
            llama-kv-cache-iswa.cpp
            llama-memory.cpp
            llama-memory-hybrid.cpp
            llama-memory-recurrent.cpp
            llama-mmap.cpp
            llama-model-loader.cpp
            llama-model-saver.cpp
            llama-model.cpp
            llama-quant.cpp
            llama-sampling.cpp
            llama-vocab.cpp
            unicode-data.cpp
            unicode.cpp
            unicode.h
            psirngclient-manager.cpp
            psirngclient-manager.h
            anu-qrng-client.cpp
            anu-qrng-client.h
            )

target_include_directories(llama PRIVATE .)
target_include_directories(llama PUBLIC ../include ../libpsirngclient/src)
target_compile_features   (llama PRIVATE cxx_std_17) # don't bump

if (MSVC)
    target_link_libraries(llama PUBLIC ggml psirngclient_static)
else()
    target_link_libraries(llama PUBLIC ggml psirngclient)
endif()

# ANU QRNG HTTP client dependencies
if (WIN32)
    # Windows uses WinHTTP (linked via pragma comment in anu-qrng-client.cpp)
else()
    # Linux/Mac use libcurl
    find_package(CURL)
    if (CURL_FOUND)
        target_link_libraries(llama PRIVATE CURL::libcurl)
    else()
        message(WARNING "libcurl not found. ANU QRNG client will not be available on this platform. Install libcurl-dev (Debian/Ubuntu) or libcurl-devel (RedHat/Fedora).")
    endif()
endif()

if (BUILD_SHARED_LIBS)
    set_target_properties(llama PROPERTIES POSITION_INDEPENDENT_CODE ON)
    target_compile_definitions(llama PRIVATE LLAMA_BUILD)
    target_compile_definitions(llama PUBLIC  LLAMA_SHARED)
endif()
