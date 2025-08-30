# Frontend Test Dockerfile
# Optimized for E2E testing with minimal build time

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install dependencies for Playwright/Cypress if needed
RUN apk add --no-cache \
    chromium \
    nss \
    freetype \
    freetype-dev \
    harfbuzz \
    ca-certificates \
    ttf-freefont

# Copy package files
COPY frontend/package*.json ./

# Install dependencies (use npm install for test environment)
RUN npm install && \
    npm install --save-dev \
    @testing-library/react \
    @testing-library/jest-dom \
    @testing-library/user-event \
    jest \
    jest-environment-jsdom

# Copy application code
COPY frontend/app ./app
COPY frontend/components ./components
COPY frontend/config ./config
COPY frontend/hooks ./hooks
COPY frontend/lib ./lib
COPY frontend/providers ./providers
COPY frontend/services ./services
COPY frontend/store ./store
COPY frontend/styles ./styles
COPY frontend/types ./types
COPY frontend/utils ./utils
COPY frontend/auth ./auth
COPY frontend/public ./public
# Test files are optional for now
COPY frontend/__tests__* ./__tests__/
COPY frontend/next.config.ts ./
COPY frontend/tsconfig.json ./
COPY frontend/tailwind.config.ts ./
COPY frontend/postcss.config.mjs ./
COPY frontend/middleware.ts* ./

# Build the application
RUN npm run build

# Set environment for testing
ENV NODE_ENV=test
ENV NEXT_TELEMETRY_DISABLED=1

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3001 || exit 1

# Expose port
EXPOSE 3001

# Run tests or start server based on command
CMD ["npm", "run", "start"]