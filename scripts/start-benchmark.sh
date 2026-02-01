#!/usr/bin/env bash

BENCHMARKS_PATH=$(realpath "$(dirname ${BASH_SOURCE[0]})/../benchmarks")

# Build the image if it doesn't exist:
docker images --format '{{.Repository}}' | grep -q 'gatling'\
    || docker build -t 'gatling' "$BENCHMARKS_PATH"

# Guarantee fresh start:
curl 'http://localhost:9999/health' >/dev/null 2>&1 \
    && docker compose --progress 'quiet' down

# Set up the API and run Gatling against it:
docker compose --progress 'quiet' up -d \
    && docker run --rm \
        --name 'gatling' \
        --network 'host' \
        -v "${BENCHMARKS_PATH}/results:/opt/gatling/results" \
        gatling >/dev/null

docker compose --progress 'quiet' down
