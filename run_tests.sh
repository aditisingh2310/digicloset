#!/bin/bash

# Run Tests locally using Docker to avoid local env usage (WSL Version)
echo "Running End-to-End Tests via Docker..."

# Create a dedicated network
docker network create digicloset-test-net

# Function to cleanup
cleanup() {
    echo "Cleaning up..."
    echo "--- BACKEND LOGS ---"
    docker logs backend
    echo "--- MODEL SERVICE LOGS ---"
    docker logs model-service
    echo "--------------------------"
    docker stop backend 2>/dev/null
    docker rm backend 2>/dev/null
    docker stop model-service 2>/dev/null
    docker rm model-service 2>/dev/null
    docker network rm digicloset-test-net 2>/dev/null
}

# Trap exit to ensure cleanup runs
trap cleanup EXIT

# 1. Start Model Service in background
echo "Starting Model Service..."
mkdir -p "$(pwd)/.model_cache/huggingface"
mkdir -p "$(pwd)/.model_cache/u2net"
docker run -d --name model-service \
  --network digicloset-test-net \
  -v "$(pwd)/.model_cache/huggingface:/root/.cache/huggingface" \
  -v "$(pwd)/.model_cache/u2net:/root/.u2net" \
  model-service:test

# 2. Start Backend in background
echo "Starting Backend..."
IMAGE_NAME=${1:-backend:test}
echo "Using image: $IMAGE_NAME"
# Run with name 'backend' on the network and link to model-service
docker run -d --name backend --network digicloset-test-net -e MODEL_SERVICE_URL="http://model-service:8001/predict" -e EMBEDDING_TEXT_SEARCH_URL="http://model-service:8001/embeddings/search-text" -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" "$IMAGE_NAME"

# Wait for startup (simple sleep)
sleep 10

# 2. Run Tests in a temporary container
echo "Running Tests..."
# Mount tests dir, install deps, and run. 
# Set API_BASE_URL to http://backend:8000 because they are on the same network.
# Using $(pwd)/tests for current directory
docker run --rm --network digicloset-test-net -v "$(pwd)/tests:/tests" -e API_BASE_URL=http://backend:8000 python:3.11-slim sh -c "pip install requests python-dotenv pytest pillow && echo 'Starting Python Test Script...' && pytest -v /tests/unit/test_colors.py /tests/unit/test_embeddings.py /tests/unit/test_ranking.py /tests/unit/test_bg_removal.py /tests/unit/test_cross_sell.py > /tests/pytest.log 2>&1"
