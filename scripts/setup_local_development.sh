#!/bin/bash

# Local Development Setup Script - Docker Alternative
# Use this when Docker Desktop is failing or unstable
# 
# Prerequisites: 
# - Homebrew installed
# - Node.js 18+ installed
# - Python 3.11+ installed

set -e

echo "🚀 Setting up Netra local development environment (without Docker)..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This script is designed for macOS. Please install services manually on other platforms."
    exit 1
fi

# Install services using Homebrew
print_status "Installing PostgreSQL, Redis, and other dependencies..."

# PostgreSQL
if brew list postgresql@15 &>/dev/null; then
    print_status "PostgreSQL 15 already installed"
else
    print_status "Installing PostgreSQL 15..."
    brew install postgresql@15
fi

# Redis
if brew list redis &>/dev/null; then
    print_status "Redis already installed"
else
    print_status "Installing Redis..."
    brew install redis
fi

# Start services
print_status "Starting PostgreSQL and Redis services..."
brew services start postgresql@15
brew services start redis

# Wait for services to start
print_status "Waiting for services to initialize..."
sleep 3

# Create development database
print_status "Creating development database..."
createdb netra_dev 2>/dev/null || print_warning "Database 'netra_dev' may already exist"

# Test database connection
if psql -d netra_dev -c "SELECT 1;" &>/dev/null; then
    print_status "✅ PostgreSQL connection successful"
else
    print_error "❌ PostgreSQL connection failed"
    exit 1
fi

# Test Redis connection
if redis-cli ping &>/dev/null; then
    print_status "✅ Redis connection successful"
else
    print_error "❌ Redis connection failed"
    exit 1
fi

# Create local environment file
print_status "Creating local environment configuration..."
cat > .env.local << EOF
# Local Development Environment (No Docker)
# Created: $(date)

# Environment
ENVIRONMENT=development

# Database (Local PostgreSQL)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=$(whoami)
POSTGRES_PASSWORD=
POSTGRES_DB=netra_dev
DATABASE_URL=postgresql+asyncpg://$(whoami)@localhost:5432/netra_dev

# Redis (Local Redis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379/0

# Disable external services for local development
DEV_MODE_CLICKHOUSE_ENABLED=false
DEV_MODE_LLM_ENABLED=false
DISABLE_GCP_SECRET_MANAGER=true

# Security keys (development only)
SECRET_KEY=local-dev-secret-key-change-in-production-must-be-at-least-32-chars
JWT_SECRET_KEY=local-dev-jwt-secret-key-for-development-only-32-chars-minimum
FERNET_KEY=zzqI4eHx8eH_vApZBb8RPbfi4CtoUl2bA_aMaPVX8-g=

# OAUTH SIMULATIONes for local development
ALLOW_DEV_AUTH_BYPASS=true
WEBSOCKET_AUTH_BYPASS=true
ALLOW_DEV_LOGIN=true

# Logging
DEBUG=true
LOG_LEVEL=INFO

# Frontend URLs
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_AUTH_URL=http://localhost:8001
EOF

# Install Python dependencies (if virtual environment exists)
if [ -d "venv" ] || [ -d ".venv" ]; then
    print_status "Installing Python dependencies..."
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        source .venv/bin/activate
    fi
    
    pip install -r requirements.txt 2>/dev/null || print_warning "Could not install Python requirements"
fi

# Install Node.js dependencies
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    print_status "Installing Node.js dependencies..."
    cd frontend
    npm install
    cd ..
fi

print_status "✅ Local development environment setup complete!"
print_status ""
print_status "🚀 To start development servers:"
print_status "1. Backend:  uvicorn netra_backend.app.main:app --reload --port 8000 --env-file .env.local"
print_status "2. Frontend: cd frontend && npm run dev"
print_status ""
print_status "📊 Service URLs:"
print_status "   • Backend:    http://localhost:8000"
print_status "   • Frontend:   http://localhost:3000" 
print_status "   • PostgreSQL: localhost:5432 (database: netra_dev)"
print_status "   • Redis:      localhost:6379"
print_status ""
print_status "🔧 To stop services later:"
print_status "   brew services stop postgresql@15"
print_status "   brew services stop redis"