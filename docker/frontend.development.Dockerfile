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
# Skip build in dev mode as we'll use next dev
ARG BUILD_MODE=development
RUN if [ "$BUILD_MODE" = "production" ]; then npm run build; fi

# Production stage
FROM node:20-alpine

# Install runtime dependencies
RUN apk add --no-cache curl

# Create non-root user (check if group/user exists first)
RUN (addgroup -g 1000 netra 2>/dev/null || true) && \
    (adduser -D -u 1000 -G netra netra 2>/dev/null || true) && \
    mkdir -p /app && \
    chown -R 1000:1000 /app

# Set working directory
WORKDIR /app

# Copy node modules and built app from builder
COPY --from=builder --chown=1000:1000 /app/node_modules ./node_modules
COPY --from=builder --chown=1000:1000 /app/package*.json ./
COPY --from=builder --chown=1000:1000 /app/tsconfig.json ./
COPY --from=builder --chown=1000:1000 /app/tailwind.config.ts ./
COPY --from=builder --chown=1000:1000 /app/postcss.config.mjs ./

# Copy Next.js specific directories (these may or may not exist depending on dev/prod mode)
COPY --from=builder --chown=1000:1000 /app/ ./

# Create .next directory with proper permissions
RUN mkdir -p /app/.next && chown -R 1000:1000 /app/.next

# Switch to non-root user
USER 1000

# Environment variables
ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1

# Health check - check the Next.js health endpoint or app root  
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || curl -f http://localhost:3000/ || exit 1

# Expose frontend port
EXPOSE 3000

# Default command for development with turbopack
CMD ["npm", "run", "dev"]