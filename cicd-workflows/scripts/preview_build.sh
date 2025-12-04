#!/usr/bin/env bash
set -e
echo "Running build for project: virtualfit-enterprise"
npm ci
npm run build
echo "Build complete. Check ./dist"
