FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy application code
COPY . .

# Build the application
ENV NEXT_PUBLIC_API_URL=https://netra-backend-701982941522.us-central1.run.app
ENV NEXT_PUBLIC_WS_URL=wss://netra-backend-701982941522.us-central1.run.app
ENV NEXT_PUBLIC_AUTH_URL=https://netra-auth-service-701982941522.us-central1.run.app

RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Copy built application
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules

ENV PORT=3000
ENV NODE_ENV=production

EXPOSE 3000

CMD ["npm", "start"]