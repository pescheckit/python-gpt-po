ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

ARG VERSION="0.1.0"
# ENV PACKAGE_VERSION=${VERSION}  # Correctly removed

# Keep PYTHONPATH env var if needed, might be optional after install
ENV PYTHONPATH=/app

WORKDIR /app

# Install git - NEEDED for setuptools_scm to read .git directory
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code INCLUDING .git
COPY . .

# Install the package itself. This triggers setuptools_scm inside the container.
RUN pip install . --no-cache-dir

# Keep your custom entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Use your custom entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
