#!/bin/bash
set -e

# Get version from git
VERSION=$(./version.sh)
echo "Building with version: $VERSION"

# Build Docker image with version from git
docker build --build-arg VERSION="$VERSION" -t gpt-po-translator:$VERSION .