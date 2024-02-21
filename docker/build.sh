#!/bin/bash

set -e
cd ..
echo "Building docker image..."
docker build . -f ./docker/Dockerfile -t evok

