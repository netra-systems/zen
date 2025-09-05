# Multi-stage build for optimized image size
FROM node:20-slim AS builder

# Set working directory
WORKDIR /app

# Copy package files first for better layer caching
COPY frontend/package*.json ./frontend/

# Install dependencies
WORKDIR /app/frontend
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY frontend/ ./

# Build the application
RUN npm run build

# Production stage
FROM node:20-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (check if user exists first)
RUN (useradd -m -u 1000 netra 2>/dev/null || true) && \
    mkdir -p /app && \
    chown -R 1000:1000 /app

# Set working directory
WORKDIR /app/frontend

# Copy built application and dependencies from builder
COPY --from=builder --chown=netra:netra /app/frontend/node_modules ./node_modules
COPY --from=builder --chown=netra:netra /app/frontend/.next ./.next
COPY --from=builder --chown=netra:netra /app/frontend/public ./public
COPY --from=builder --chown=netra:netra /app/frontend/package*.json ./

# Switch to non-root user
USER netra

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]