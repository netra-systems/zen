FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files first for better caching
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

# Copy all frontend source files
# The .dockerignore file handles exclusions (node_modules, tests, etc.)
COPY frontend/ .
COPY shared/ ../shared/

# Build the application
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Copy built application
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/next.config.js ./

# Install production dependencies only
RUN npm ci --legacy-peer-deps --production

# Set environment variables
ENV NODE_ENV=production

EXPOSE 3000

# Run the application
CMD ["npm", "start"]
