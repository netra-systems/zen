#!/bin/bash

# test-support-scripts.sh
# Test script to demonstrate the determine-strategy.sh and parse-config.py scripts
# ACT compatible

set -e

echo "🧪 Testing GitHub Actions Support Scripts"
echo "========================================"

# Set up ACT environment for testing
export ACT=true
export ACT_DETECTION=true

SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"

echo ""
echo "1️⃣ Testing determine-strategy.sh"
echo "--------------------------------"

# Test the strategy determination script
"$SCRIPT_DIR/determine-strategy.sh"

echo ""
echo "2️⃣ Testing parse-config.py" 
echo "---------------------------"

# Test config parsing with existing settings
echo "📋 Parsing test_runner.default_level from settings.json:"
python "$SCRIPT_DIR/parse-config.py" settings.json test_runner.default_level

echo ""
echo "📋 Parsing enable_staging_deploy from features.json:"
python "$SCRIPT_DIR/parse-config.py" features.json enable_staging_deploy

echo ""
echo "📋 Testing with default value:"
python "$SCRIPT_DIR/parse-config.py" settings.json nonexistent.key --default "fallback_value"

echo ""
echo "📋 Testing nested boolean value:"
python "$SCRIPT_DIR/parse-config.py" features.json enable_notifications.slack

echo ""
echo "📋 Listing available keys in settings.json:"
python "$SCRIPT_DIR/parse-config.py" settings.json dummy --list-keys

echo ""
echo "3️⃣ Integration Test"
echo "-------------------"

echo "📊 Simulating workflow decision making..."

# Get test strategy
STRATEGY_OUTPUT=$(mktemp)
"$SCRIPT_DIR/determine-strategy.sh" | grep "skip_tests\|skip_deploy\|test_scope" > "$STRATEGY_OUTPUT" || true

if [[ -s "$STRATEGY_OUTPUT" ]]; then
    source "$STRATEGY_OUTPUT"
    echo "✅ Strategy determined:"
    echo "   Skip Tests: ${skip_tests:-false}"
    echo "   Skip Deploy: ${skip_deploy:-false}" 
    echo "   Test Scope: ${test_scope:-unit}"
    
    # Get config values based on strategy
    if [[ "${skip_tests:-false}" == "false" ]]; then
        TEST_TIMEOUT=$(python "$SCRIPT_DIR/parse-config.py" settings.json test_runner.timeout_minutes 2>/dev/null | grep -o '[0-9]*' | head -1)
        echo "   Test Timeout: ${TEST_TIMEOUT:-30} minutes"
    fi
    
    if [[ "${skip_deploy:-false}" == "false" ]]; then
        STAGING_ENABLED=$(python "$SCRIPT_DIR/parse-config.py" features.json enable_staging_deploy 2>/dev/null | grep -o 'true\|false')
        echo "   Staging Deploy: ${STAGING_ENABLED:-true}"
    fi
else
    echo "⚠️  Could not parse strategy output"
fi

rm -f "$STRATEGY_OUTPUT"

echo ""
echo "✅ All tests completed successfully!"
echo ""
echo "📚 Usage Examples:"
echo "   # In workflow: Determine execution strategy"
echo "   ./.github/scripts/determine-strategy.sh"
echo ""
echo "   # In workflow: Get config values"
echo "   python3 ./.github/scripts/parse-config.py settings.json test_runner.timeout_minutes"
echo "   python3 ./.github/scripts/parse-config.py features.json enable_staging_deploy"
echo ""
echo "   # ACT Testing:"
echo "   export ACT=true && ./.github/scripts/test-support-scripts.sh"