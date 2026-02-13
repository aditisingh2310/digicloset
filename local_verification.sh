#!/bin/bash

# Local Verification Script for Docker Builds (WSL Version)

echo "Verifying Docker builds..."

# Build model-service
echo "Building digicloset-upgrade-pack/model-service..."
docker build -t model-service:test digicloset-upgrade-pack/model-service
if [ $? -eq 0 ]; then
    echo "SUCCESS: model-service built successfully."
else
    echo "FAILURE: model-service failed to build."
    exit 1
fi

# Build model-service-complete
echo "Building digicloset-upgrade-pack-complete/model-service..."
docker build -t model-service-complete:test digicloset-upgrade-pack-complete/model-service
if [ $? -eq 0 ]; then
    echo "SUCCESS: model-service-complete built successfully."
else
    echo "FAILURE: model-service-complete failed to build."
    exit 1
fi

# Build backend
echo "Building digicloset-upgrade-pack/backend..."
docker build -t backend:test digicloset-upgrade-pack/backend
if [ $? -eq 0 ]; then
    echo "SUCCESS: backend built successfully."
else
    echo "FAILURE: backend failed to build."
    exit 1
fi

# Build backend-complete
echo "Building digicloset-upgrade-pack-complete/backend..."
docker build -t backend-complete:test digicloset-upgrade-pack-complete/backend
if [ $? -eq 0 ]; then
    echo "SUCCESS: backend-complete built successfully."
else
    echo "FAILURE: backend-complete failed to build."
    exit 1
fi
