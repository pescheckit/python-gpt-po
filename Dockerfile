ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Copy requirements and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy essential files needed for setup.py
COPY README.md .
COPY MANIFEST.in .
COPY pyproject.toml .
COPY setup.py .

# Copy the rest of the source code
COPY python_gpt_po/ python_gpt_po/
COPY man/ man/
COPY docker-entrypoint.sh .

# Install the package
RUN pip install .

# Create a wrapper script to allow more flexibility
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
