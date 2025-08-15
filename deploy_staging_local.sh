#!/bin/bash
# Deploy Staging Locally - Simplified Script

echo "🚀 Starting Local Staging Deployment"
echo "=================================="

# Enable BuildKit for faster Docker builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Configuration
DEPLOY_METHOD=${1:-docker}  # Options: docker, act
REBUILD=${2:-cache}         # Options: cache, no-cache

echo "Deploy Method: $DEPLOY_METHOD"
echo "Build Mode: $REBUILD"

# Function to deploy with Docker Compose
deploy_docker() {
    echo "📦 Deploying with Docker Compose..."
    
    # Build options
    BUILD_OPTS=""
    if [ "$REBUILD" = "no-cache" ]; then
        BUILD_OPTS="--no-cache"
    fi
    
    # Build services
    echo "🔨 Building services..."
    docker-compose -f docker-compose.staging.yml build $BUILD_OPTS
    
    if [ $? -ne 0 ]; then
        echo "❌ Build failed!"
        exit 1
    fi
    
    # Start services
    echo "🚀 Starting services..."
    docker-compose -f docker-compose.staging.yml up -d
    
    # Wait for services to be healthy
    echo "⏳ Waiting for services to be healthy..."
    sleep 10
    
    # Check health
    docker-compose -f docker-compose.staging.yml ps
    
    echo "✅ Services deployed!"
    echo "📍 Frontend: http://localhost:3000"
    echo "📍 Backend: http://localhost:8080"
    echo "📍 Proxy: http://localhost:80"
}

# Function to deploy with ACT
deploy_act() {
    echo "🎬 Deploying with ACT (GitHub Actions locally)..."
    
    # Check if ACT is available
    if ! command -v act &> /dev/null && ! [ -f "./act.exe" ]; then
        echo "❌ ACT not found! Please install ACT first."
        exit 1
    fi
    
    # Create event.json if not exists
    if [ ! -f event.json ]; then
        echo '{"action": "deploy", "inputs": {"action": "deploy"}}' > event.json
    fi
    
    # Set environment variables
    export ACT=true
    export LOCAL_DEPLOY=true
    
    # Run ACT
    if [ -f "./act.exe" ]; then
        ./act.exe -W .github/workflows/staging-environment.yml \
            --container-architecture linux/amd64 \
            -e event.json \
            workflow_dispatch
    else
        act -W .github/workflows/staging-environment.yml \
            --container-architecture linux/amd64 \
            -e event.json \
            workflow_dispatch
    fi
}

# Function to check Docker
check_docker() {
    if ! docker info &> /dev/null; then
        echo "❌ Docker is not running! Please start Docker Desktop."
        exit 1
    fi
    echo "✅ Docker is running"
}

# Function to stop services
stop_services() {
    echo "🛑 Stopping services..."
    docker-compose -f docker-compose.staging.yml down
    echo "✅ Services stopped"
}

# Main execution
case "$DEPLOY_METHOD" in
    docker)
        check_docker
        deploy_docker
        ;;
    act)
        check_docker
        deploy_act
        ;;
    stop)
        stop_services
        ;;
    *)
        echo "Usage: $0 [docker|act|stop] [cache|no-cache]"
        echo "  docker - Deploy using Docker Compose"
        echo "  act    - Deploy using ACT (GitHub Actions locally)"
        echo "  stop   - Stop all services"
        exit 1
        ;;
esac

echo "=================================="
echo "🎉 Deployment Complete!"