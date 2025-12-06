#!/bin/bash
set -e

echo "Building Docker images..."

docker build -t ghcr.io/${GITHUB_REPOSITORY_OWNER}/digicloset-backend:latest -f backend/Dockerfile .
docker build -t ghcr.io/${GITHUB_REPOSITORY_OWNER}/digicloset-frontend:latest -f frontend/Dockerfile .

echo "Images built successfully."