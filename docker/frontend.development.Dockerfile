# Multi-stage build for frontend
FROM node:20-alpine AS builder

# Install dependencies for native modules
RUN apk add --no-cache python3 make g++

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# Copy frontend code
COPY frontend/ ./

# Build the application (for production mode)
ARG BUILD_MODE=development
RUN if [ "$BUILD_MODE" = "production" ]; then npm run build; fi

# Production stage
FROM node:20-alpine

# Install runtime dependencies
RUN apk add --no-cache curl

# Create non-root user
RUN (addgroup -g 1000 netra 2>/dev/null || true) && \
    (adduser -D -u 1000 -G netra netra 2>/dev/null || true) && \
    mkdir -p /app && \
    chown -R 1000:1000 /app

# Set working directory
WORKDIR /app

# Copy package files first
COPY --from=builder --chown=1000:1000 /app/package*.json ./

# Copy node modules
COPY --from=builder --chown=1000:1000 /app/node_modules ./node_modules

# Copy only necessary config files
COPY --from=builder --chown=1000:1000 /app/tsconfig.json ./
COPY --from=builder --chown=1000:1000 /app/tailwind.config.ts ./
COPY --from=builder --chown=1000:1000 /app/postcss.config.mjs ./
COPY --from=builder --chown=1000:1000 /app/next.config.ts ./
COPY --from=builder --chown=1000:1000 /app/next.config.turbopack.ts ./

# Copy only source code directories (no test files, no cypress)
COPY --from=builder --chown=1000:1000 /app/app ./app
COPY --from=builder --chown=1000:1000 /app/components ./components
COPY --from=builder --chown=1000:1000 /app/hooks ./hooks
COPY --from=builder --chown=1000:1000 /app/services ./services
COPY --from=builder --chown=1000:1000 /app/store ./store
COPY --from=builder --chown=1000:1000 /app/types ./types
COPY --from=builder --chown=1000:1000 /app/utils ./utils
COPY --from=builder --chown=1000:1000 /app/lib ./lib
COPY --from=builder --chown=1000:1000 /app/providers ./providers
COPY --from=builder --chown=1000:1000 /app/auth ./auth
COPY --from=builder --chown=1000:1000 /app/public ./public

# Create .next directory with proper permissions for dev mode
RUN mkdir -p /app/.next && chown -R 1000:1000 /app/.next

# Switch to non-root user
USER 1000

# Environment variables
ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || curl -f http://localhost:3000/ || exit 1

# Expose frontend port
EXPOSE 3000

# Default command for development with turbopack
CMD ["npm", "run", "dev"]