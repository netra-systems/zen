#!/bin/bash

# Test script for running GitHub Actions workflows locally with ACT
# This script demonstrates how to test the monitoring and health check workflows

set -e

echo "🧪 GitHub Actions Workflow ACT Testing Suite"
echo "============================================="

# Check if ACT is installed
if ! command -v act &> /dev/null; then
    echo "❌ ACT is not installed. Please install it first:"
    echo "   https://github.com/nektos/act"
    exit 1
fi

echo "✅ ACT is installed: $(act --version)"

# Create ACT environment file
cat > .act.env << 'EOF'
ACT=true
ACT_DETECTION=true
CI=true
GITHUB_ACTIONS=true
EOF

echo "📝 Created .act.env file for testing"

# Function to test a workflow
test_workflow() {
    local workflow_file="$1"
    local workflow_name="$2"
    local additional_inputs="$3"
    
    echo ""
    echo "🚀 Testing: $workflow_name"
    echo "   File: $workflow_file"
    echo "   Inputs: $additional_inputs"
    echo "----------------------------------------"
    
    if [[ -f "$workflow_file" ]]; then
        # Check if workflow is commented out (disabled)
        if grep -q "^# on:" "$workflow_file"; then
            echo "⚠️  Workflow is disabled (commented out), creating test version..."
            
            # Create temporary enabled version for testing
            local test_file="${workflow_file}.act-test"
            sed 's/^# on:/on:/' "$workflow_file" > "$test_file"
            sed -i 's/^#   /  /' "$test_file"
            
            echo "🔧 Running ACT on test version..."
            act workflow_dispatch \
                --workflows "$test_file" \
                --env-file .act.env \
                --input act_local_run=true \
                $additional_inputs \
                --dry-run
            
            rm -f "$test_file"
        else
            echo "🔧 Running ACT..."
            act workflow_dispatch \
                --workflows "$workflow_file" \
                --env-file .act.env \
                --input act_local_run=true \
                $additional_inputs \
                --dry-run
        fi
        
        echo "✅ Test completed for $workflow_name"
    else
        echo "❌ Workflow file not found: $workflow_file"
    fi
}

# Test Health Monitoring Workflow
test_workflow \
    ".github/workflows/health-monitoring.yml" \
    "Health Check Monitoring" \
    "--input environment=all --input detailed_check=true"

# Test Workflow Health Monitor
test_workflow \
    ".github/workflows/workflow-health-monitor.yml" \
    "Workflow Health Monitor" \
    "--input report_type=summary --input days_back=7"

# Test Architecture Health Monitor
test_workflow \
    ".github/workflows/architecture-health.yml" \
    "Architecture Health Monitor" \
    "--input fail_on_violations=false --input generate_reports=true"

echo ""
echo "🎉 All workflow tests completed!"
echo ""
echo "📋 Summary:"
echo "- Health Monitoring: Mock health checks and notifications"
echo "- Workflow Health Monitor: Mock workflow data and cost analysis"  
echo "- Architecture Health: Mock compliance scanning and reporting"
echo ""
echo "🔧 To run a specific workflow with ACT:"
echo "   act workflow_dispatch -W .github/workflows/[workflow-file] --env-file .act.env --input act_local_run=true"
echo ""
echo "📚 For more ACT options:"
echo "   act --help"
echo ""

# Clean up
rm -f .act.env

echo "✅ Test suite completed successfully!"