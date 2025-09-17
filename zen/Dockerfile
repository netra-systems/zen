FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy package files
COPY setup.py pyproject.toml MANIFEST.in README.md LICENSE CHANGELOG.md ./
COPY zen_orchestrator.py ./
COPY __init__.py ./
COPY agent_interface ./agent_interface/
COPY token_budget ./token_budget/
COPY token_transparency ./token_transparency/

# Install the package
RUN pip install --no-cache-dir .

# Create a non-root user
RUN useradd -m -u 1000 zen && \
    chown -R zen:zen /app

USER zen

# Set the entrypoint
ENTRYPOINT ["zen"]

# Default command (can be overridden)
CMD ["--help"]