#!/bin/bash
# Get version from git
GIT_VERSION=$(git describe --tags --always 2>/dev/null || echo "0.1.0")
# Strip any leading 'v' if present
VERSION="${GIT_VERSION#v}"
echo $VERSION
