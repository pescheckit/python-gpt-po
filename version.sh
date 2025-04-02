#!/bin/bash
# Get version from git
GIT_VERSION=$(git describe --tags --always 2>/dev/null || echo "0.1.0")

# Clean up version for PEP 440 compliance
if [[ "$GIT_VERSION" == *-*-* ]]; then
    # Format: v0.3.5-5-gd9775d7 -> 0.3.5.dev5+gd9775d7
    VERSION=$(echo "$GIT_VERSION" | sed -E 's/^v?([0-9]+\.[0-9]+\.[0-9]+)-([0-9]+)-g([a-f0-9]+)/\1.dev\2+\3/')
else
    # Simple version, just remove v prefix if present
    VERSION="${GIT_VERSION#v}"
fi

# If first argument is "docker", return Docker-friendly version (replace + with -)
if [ "$1" = "docker" ]; then
    echo "${VERSION//+/-}"
else
    echo "$VERSION"
fi
