# Alpine-based Production Dockerfile for Frontend Service
# Optimized for test isolation and minimal size
FROM node:20-alpine3.19 as builder

# Build arguments
ARG BUILD_ENV=test
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AUTH_URL
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_ENVIRONMENT

# Install build dependencies
RUN apk add --no-cache python3 make g++

WORKDIR /build

# Copy package files
COPY frontend/package*.json ./

# Install dependencies with production flag
RUN npm ci --only=production && \
    npm cache clean --force

# Copy source code
COPY frontend ./

# Build Next.js application with production optimizations
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Production stage - minimal Alpine image
FROM node:20-alpine3.19

# Install runtime dependencies only
RUN apk add --no-cache \
    curl \
    tini \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1000 netra && \
    adduser -D -u 1000 -G netra netra && \
    mkdir -p /app/.next/cache && \
    chown -R netra:netra /app

WORKDIR /app

# Copy built application from builder
COPY --from=builder --chown=netra:netra /build/.next /app/.next
COPY --from=builder --chown=netra:netra /build/public /app/public
COPY --from=builder --chown=netra:netra /build/package*.json /app/
COPY --from=builder --chown=netra:netra /build/node_modules /app/node_modules

# Set environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV BUILD_ENV=${BUILD_ENV}

# Security: Drop all capabilities
USER netra

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

EXPOSE 3000

# Production command
CMD ["npm", "start"]