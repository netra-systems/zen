FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for better caching
COPY frontend/package*.json ./
# Use npm install to handle potential lock file inconsistencies
RUN npm install --no-audit

# Copy all frontend source files
# The .dockerignore file handles exclusions (node_modules, tests, etc.)
COPY frontend/ .
COPY shared/ ../shared/

# Set memory limit for build process
ENV NODE_OPTIONS="--max-old-space-size=4096"

# Build the application (creates standalone build)
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy standalone build output
# The standalone build includes all necessary dependencies
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Set environment variables
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
# Set memory limit for runtime
ENV NODE_OPTIONS="--max-old-space-size=2048"

EXPOSE 3000

# Run the standalone server directly
CMD ["node", "server.js"]