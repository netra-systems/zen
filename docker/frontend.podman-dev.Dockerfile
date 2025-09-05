# Development-focused Dockerfile for faster iteration
FROM node:20-slim

# Install runtime dependencies and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    python3 \
    make \
    g++ \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/* && \
    (useradd -m -u 1001 netra || useradd -m netra) && \
    mkdir -p /app && \
    chown -R netra:netra /app

# Set working directory
WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm ci && npm cache clean --force

# Copy source code
COPY frontend/ ./

# Switch to non-root user
USER netra

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# Expose port
EXPOSE 3000

# Start in development mode (faster startup)
CMD ["npm", "run", "dev"]