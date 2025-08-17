#!/bin/bash
# Local staging deployment with proper caching

echo "🚀 Starting local staging deployment..."

# Set environment for local build
export LOCAL_BUILD=true
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Create cache directory if needed
mkdir -p /tmp/.buildx-cache

# Build images with caching
echo "📦 Building images with Docker Compose..."
docker-compose -f docker-compose.staging.yml build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --parallel

# Start services
echo "🏃 Starting services..."
docker-compose -f docker-compose.staging.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health status
docker-compose -f docker-compose.staging.yml ps

echo "✅ Local staging environment ready!"
echo "   Frontend: http://localhost:3000"
echo "   Backend: http://localhost:8080"
echo ""
echo "📋 Useful commands:"
echo "   View logs: docker-compose -f docker-compose.staging.yml logs -f"
echo "   Stop: docker-compose -f docker-compose.staging.yml down"
echo "   Restart: docker-compose -f docker-compose.staging.yml restart"