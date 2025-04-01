ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

# Accept version as build arg
ARG VERSION="0.1.0"

WORKDIR /app

# Install git to properly detect version during build
RUN apt-get update && apt-get install -y git && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything needed for versioning and installation
COPY . .

# Disable setuptools_scm and use the provided version
ENV SETUPTOOLS_SCM_PRETEND_VERSION=$VERSION

# Install the package with proper versioning support
RUN pip install --no-cache-dir .

# Create a wrapper script to allow more flexibility
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
