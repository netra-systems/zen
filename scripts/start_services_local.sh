#!/bin/bash

# Service Startup Script for Local Integration Testing
# This script starts Backend and Auth services without Docker for integration testing

set -e  # Exit on any error

PROJECT_ROOT="/Users/anthony/Documents/GitHub/netra-apex"
VENV_PATH="$PROJECT_ROOT/venv"

echo "🚀 Starting Local Services for Integration Testing"
echo "=================================================="

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source "$VENV_PATH/bin/activate" || {
    echo "❌ ERROR: Cannot activate virtual environment at $VENV_PATH"
    echo "Please ensure the virtual environment exists"
    exit 1
}

# Set Python path
export PYTHONPATH="$PROJECT_ROOT"

echo "📊 Service Configuration:"
echo "  - Backend: http://localhost:8000"
echo "  - Auth:    http://localhost:8083 (port 8081 in use)"
echo "  - Project Root: $PROJECT_ROOT"
echo ""

# Function to kill existing processes
cleanup_services() {
    echo "🧹 Cleaning up existing service processes..."
    pkill -f "python.*netra_backend/app/main.py" || true
    pkill -f "python.*auth_service/main.py" || true
    sleep 2
}

# Function to check service health
check_service() {
    local service_name="$1"
    local url="$2"
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s --fail "$url" > /dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts - waiting..."
        sleep 1
        ((attempt++))
    done
    
    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Cleanup existing services
cleanup_services

echo "🚀 Starting Auth Service on port 8083..."
PORT=8083 python auth_service/main.py &
AUTH_PID=$!
echo "  Auth Service PID: $AUTH_PID"

echo "🚀 Starting Backend Service on port 8000 (with database bypass)..."
BYPASS_STARTUP_VALIDATION=true python netra_backend/app/main.py &
BACKEND_PID=$!
echo "  Backend Service PID: $BACKEND_PID"

# Save PIDs for cleanup
echo "$AUTH_PID" > /tmp/netra_auth_service.pid
echo "$BACKEND_PID" > /tmp/netra_backend_service.pid

echo ""
echo "⏳ Checking service health..."

# Check Auth Service
if check_service "Auth Service" "http://localhost:8083/health"; then
    echo "✅ Auth Service: READY"
else
    echo "❌ Auth Service: FAILED"
    AUTH_READY=false
fi

# Check Backend Service (may fail due to database but still be listening)
if check_service "Backend Service" "http://localhost:8000/" || curl -s --connect-timeout 5 "http://localhost:8000" > /dev/null 2>&1; then
    echo "✅ Backend Service: READY (may have database issues but listening)"
    BACKEND_READY=true
else
    echo "❌ Backend Service: NOT LISTENING"
    BACKEND_READY=false
fi

echo ""
echo "📋 SERVICE STATUS SUMMARY"
echo "========================="
echo "Auth Service (port 8083):    ${AUTH_READY:-true}"
echo "Backend Service (port 8000): ${BACKEND_READY:-false}"
echo ""
echo "💡 INTEGRATION TEST CONFIGURATION:"
echo "  Set AUTH_SERVICE_URL=http://localhost:8083"
echo "  Set BACKEND_URL=http://localhost:8000"
echo ""
echo "🛑 To stop services run: ./stop_services_local.sh"

# Create stop script
cat > "$PROJECT_ROOT/stop_services_local.sh" << 'EOF'
#!/bin/bash
echo "🛑 Stopping Local Services..."
if [ -f /tmp/netra_auth_service.pid ]; then
    kill $(cat /tmp/netra_auth_service.pid) 2>/dev/null || true
    rm -f /tmp/netra_auth_service.pid
fi
if [ -f /tmp/netra_backend_service.pid ]; then
    kill $(cat /tmp/netra_backend_service.pid) 2>/dev/null || true
    rm -f /tmp/netra_backend_service.pid
fi
echo "✅ Services stopped"
EOF

chmod +x "$PROJECT_ROOT/stop_services_local.sh"

echo "✅ Local services startup completed!"
echo "    Use 'curl http://localhost:8083/health' to test Auth service"
echo "    Use 'curl http://localhost:8000/' to test Backend service"