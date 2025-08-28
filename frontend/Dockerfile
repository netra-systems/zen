# Frontend Dockerfile for Netra Apex AI Optimization Platform
# Business Value: Ensures reliable frontend deployment for staging and production
# Prevents $25K+ MRR loss from frontend availability issues

# Use the official Node.js runtime as the base image
FROM node:18-alpine AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache libc6-compat curl

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./
COPY next.config.ts ./
COPY tailwind.config.ts ./
COPY postcss.config.mjs ./

# Install dependencies
RUN npm ci --production=false

# Copy source code
COPY . .

# Build arguments for environment configuration
ARG NODE_ENV=production
ARG ENVIRONMENT=production
ARG BUILD_TARGET=production

# Set environment variables
ENV NODE_ENV=$NODE_ENV
ENV ENVIRONMENT=$ENVIRONMENT
ENV BUILD_TARGET=$BUILD_TARGET
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Build the application
RUN npm run build

# Production image
FROM node:18-alpine AS runner

WORKDIR /app

# Install runtime dependencies only
RUN apk add --no-cache curl

# Create a non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=base --chown=nextjs:nodejs /app/.next ./.next
COPY --from=base --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --from=base --chown=nextjs:nodejs /app/package.json ./package.json
COPY --from=base --chown=nextjs:nodejs /app/public ./public

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# Start the application
CMD ["npm", "start"]