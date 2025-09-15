#!/bin/bash

# NetraOptimizer Quick Start Script
# This script sets up NetraOptimizer for tracking Claude usage with CloudSQL

set -e

echo "=========================================="
echo "NetraOptimizer Quick Start Setup"
echo "=========================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK is not installed."
    echo "   Please install from: https://cloud.google.com/sdk/install"
    exit 1
fi

# Check if cloud-sql-proxy is installed
if ! command -v cloud-sql-proxy &> /dev/null; then
    echo "⚠️  Cloud SQL Proxy is not installed."
    echo "   Installing with brew (macOS)..."
    if command -v brew &> /dev/null; then
        brew install cloud-sql-proxy
    else
        echo "   Please install cloud-sql-proxy manually:"
        echo "   https://cloud.google.com/sql/docs/mysql/sql-proxy"
        exit 1
    fi
fi

echo ""
echo "1. Setting up Python environment..."
echo "-----------------------------------------"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
echo "✅ Virtual environment activated"

# Install dependencies
echo ""
echo "2. Installing dependencies..."
echo "-----------------------------------------"
pip install -q -r netraoptimizer/requirements.txt
echo "✅ Dependencies installed"

echo ""
echo "3. Configuring Google Cloud..."
echo "-----------------------------------------"

# Check if already authenticated
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "✅ Already authenticated with Google Cloud"
else
    echo "📝 Please authenticate with Google Cloud:"
    gcloud auth application-default login
fi

# Set project
echo ""
read -p "Enter your Google Cloud Project ID [netra-staging]: " project_id
project_id=${project_id:-netra-staging}
gcloud config set project "$project_id"
echo "✅ Project set to: $project_id"

echo ""
echo "4. Starting Cloud SQL Proxy..."
echo "-----------------------------------------"
echo "📝 Starting proxy in background on port 5434..."

# Kill any existing proxy
pkill -f "cloud-sql-proxy" 2>/dev/null || true

# Start proxy in background
cloud-sql-proxy --port=5434 "${project_id}:us-central1:staging-shared-postgres" &
PROXY_PID=$!
echo "✅ Cloud SQL Proxy started (PID: $PROXY_PID)"

# Wait for proxy to be ready
sleep 3

echo ""
echo "5. Setting up environment variables..."
echo "-----------------------------------------"

# Create .env file
cat > .env.netraoptimizer << EOF
# NetraOptimizer Configuration
USE_CLOUD_SQL=true
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_USER=postgres
GCP_PROJECT_ID=$project_id
ENVIRONMENT=development

# Claude settings
CLAUDE_EXECUTABLE=claude
CLAUDE_TIMEOUT=600

# Analytics
NETRA_ENABLE_ANALYTICS=true
EOF

# Try to get password from Secret Manager
echo "📝 Attempting to load database password from Secret Manager..."
if password=$(gcloud secrets versions access latest --secret=postgres-password-staging 2>/dev/null); then
    echo "POSTGRES_PASSWORD=$password" >> .env.netraoptimizer
    echo "✅ Password loaded from Secret Manager"
else
    echo "⚠️  Could not load password from Secret Manager"
    read -s -p "Enter PostgreSQL password: " db_password
    echo ""
    echo "POSTGRES_PASSWORD=$db_password" >> .env.netraoptimizer
fi

# Load environment
set -a
source .env.netraoptimizer
set +a
echo "✅ Environment configured"

echo ""
echo "6. Setting up database..."
echo "-----------------------------------------"

# Run database setup
python netraoptimizer/database/setup.py

echo ""
echo "7. Verifying setup..."
echo "-----------------------------------------"

# Test connection
python netraoptimizer/test_cloud_connection.py

echo ""
echo "=========================================="
echo "✅ NetraOptimizer Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Keep the Cloud SQL Proxy running (PID: $PROXY_PID)"
echo "2. Use 'source .env.netraoptimizer' to load environment"
echo "3. Run 'python netraoptimizer/example_usage.py' to see it in action"
echo "4. Integrate with your application using the examples in docs/"
echo ""
echo "To stop the Cloud SQL Proxy later:"
echo "  kill $PROXY_PID"
echo ""
echo "Happy tracking! 🚀"