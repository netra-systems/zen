#!/bin/bash
# Start Redis for integration testing (port 6381)
# For use with no-Docker integration tests

echo "Starting Redis server for integration testing..."
cd "$(dirname "$0")/../redis-local/Redis-8.2.1-Windows-x64-msys2"

if [ ! -f "redis-server.exe" ]; then
    echo "ERROR: Redis not found. Please run the setup first."
    echo "Download from: https://github.com/redis-windows/redis-windows/releases"
    exit 1
fi

echo "Starting Redis on port 6381 for integration tests..."
./redis-server.exe --port 6381 &
REDIS_PID=$!

sleep 3

echo "Testing Redis connection..."
if ./redis-cli.exe -p 6381 ping > /dev/null 2>&1; then
    echo "✓ Redis server started successfully on port 6381 (PID: $REDIS_PID)"
    echo "✓ Ready for integration tests without Docker"
    echo ""
    echo "Redis server is running in the background."
    echo "To stop Redis, run: kill $REDIS_PID"
    echo "Redis PID: $REDIS_PID"
else
    echo "✗ Failed to start Redis server"
    exit 1
fi