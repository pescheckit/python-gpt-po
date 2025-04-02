ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

# Accept version as build arg
ARG VERSION="0.1.0"
# Set as environment variable for setup.py to use
ENV PACKAGE_VERSION=${VERSION}
ENV PYTHONPATH=/app

WORKDIR /app

# Install git for versioning
RUN apt-get update && apt-get install -y git && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create a simple wrapper script
RUN echo '#!/bin/bash\npython -m python_gpt_po.main "$@"' > /usr/local/bin/gpt-po-translator && \
    chmod +x /usr/local/bin/gpt-po-translator

# Create a wrapper script to allow more flexibility
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
