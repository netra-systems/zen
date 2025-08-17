#!/bin/bash

echo "Starting Netra AI Development Environment..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Start services
echo "Starting Backend and Frontend..."
python scripts/dev_launcher.py --dynamic --no-backend-reload &
LAUNCHER_PID=$!

echo ""
echo "Development environment is starting..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for interrupt
trap "kill $LAUNCHER_PID; echo 'Services stopped.'; exit" INT
wait $LAUNCHER_PID
