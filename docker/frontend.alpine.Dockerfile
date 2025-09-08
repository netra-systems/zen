# Alpine-based Production Dockerfile for Frontend Service
# Optimized for test isolation and minimal size
FROM node:20-alpine AS builder

# Build arguments
ARG BUILD_ENV=test
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AUTH_URL
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_WEBSOCKET_URL
ARG NEXT_PUBLIC_ENVIRONMENT
ARG NEXT_PUBLIC_GTM_ID
ARG NEXT_PUBLIC_GA_MEASUREMENT_ID

# Install minimal build dependencies
RUN apk add --no-cache libc6-compat

WORKDIR /build

# Copy package files
COPY frontend/package*.json ./

# Install ALL dependencies for build (including devDependencies for cross-env)
# CRITICAL: Explicitly install all deps including devDependencies in development mode
ENV NODE_ENV=development
RUN npm ci && \
    npm cache clean --force

# Copy source code
COPY frontend/ .

# Build Next.js with standalone output for smaller image
# CRITICAL: Keep NODE_ENV as development during build to preserve devDependencies like cross-env
ENV NEXT_TELEMETRY_DISABLED=1
RUN NODE_ENV=development npm run build && \
    rm -rf .next/cache

# Production stage - minimal Alpine image
FROM node:20-alpine

# Install runtime dependencies only
RUN apk add --no-cache \
    libc6-compat \
    curl \
    tini \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

WORKDIR /app

# Copy only essential files for standalone server
COPY --from=builder --chown=nextjs:nodejs /build/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /build/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /build/public ./public

# Set environment
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV BUILD_ENV=test
ENV RUNNING_IN_DOCKER=true

# Security: Drop all capabilities
USER nextjs

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

EXPOSE 3000

# Production command (using standalone server)
CMD ["node", "server.js"]