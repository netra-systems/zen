# Netra Frontend - Staging Deployment
# Optimized for production-like staging validation
# CRITICAL: Must match production build exactly

FROM node:18-alpine as builder

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache libc6-compat curl

# Copy package files first for better caching
COPY frontend/package*.json ./
RUN npm ci --only=production

# Copy frontend source
COPY frontend/ .

# Build arguments for staging environment
ARG NODE_ENV=production
ARG NEXT_PUBLIC_ENVIRONMENT=staging
ARG NEXT_PUBLIC_API_URL=http://backend:8000
ARG NEXT_PUBLIC_AUTH_URL=http://auth:8081
ARG NEXT_PUBLIC_WS_URL=ws://backend:8000

# Set build environment variables
ENV NODE_ENV=$NODE_ENV
ENV NEXT_PUBLIC_ENVIRONMENT=$NEXT_PUBLIC_ENVIRONMENT
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_AUTH_URL=$NEXT_PUBLIC_AUTH_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_WEBSOCKET_URL=$NEXT_PUBLIC_WS_URL
ENV NEXT_TELEMETRY_DISABLED=1

# Build the application
RUN npm run build

# Production stage
FROM node:18-alpine as runner

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Set production environment variables
ENV NODE_ENV=production
ENV NEXT_PUBLIC_ENVIRONMENT=staging
ENV PORT=3000

# Health check for staging validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Start the application
CMD ["node", "server.js"]