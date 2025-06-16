ARG UBUNTU_VERSION=22.04

FROM ubuntu:$UBUNTU_VERSION AS build

RUN apt-get update && \
    apt-get install -y build-essential git cmake && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

COPY . .

RUN cmake -B build && \
    cmake --build build --config Release --target llama-cli -j$(nproc)

ENV LC_ALL=C.utf8

ENTRYPOINT [ "/app/build/bin/llama-cli" ]
