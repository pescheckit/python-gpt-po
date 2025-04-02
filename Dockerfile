ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

# Accept version as build arg (mostly for reference now, or if used elsewhere)
ARG VERSION="0.1.0"
# ENV PACKAGE_VERSION=${VERSION}  # REMOVE THIS - Let setuptools_scm handle it
ENV PYTHONPATH=/app # Keep if needed, might be optional after install

WORKDIR /app

# Install git - NEEDED for setuptools_scm to read .git directory
RUN apt-get update && apt-get install -y --no-install-recommends git && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code INCLUDING .git
# *** IMPORTANT: Ensure .git is NOT listed in your .dockerignore file ***
COPY . .

# Install the package itself. This triggers setuptools_scm inside the container.
# It reads the version from the copied .git directory.
RUN pip install . --no-cache-dir

# The above step should create the /usr/local/bin/gpt-po-translator entry point
# based on your pyproject.toml [project.scripts] section.
# So, this manual creation is likely redundant:
# RUN echo '#!/bin/bash\npython -m python_gpt_po.main "$@"' > /usr/local/bin/gpt-po-translator && \
#     chmod +x /usr/local/bin/gpt-po-translator

# Keep your custom entrypoint script if it adds value
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Use your custom entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# If docker-entrypoint.sh just runs `gpt-po-translator "$@"` you could simplify:
# ENTRYPOINT ["gpt-po-translator"]
# CMD ["--help"]