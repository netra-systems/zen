#!/bin/bash

# Memory-safe Cypress test runner
# Runs tests in small batches to prevent memory crashes

set -e

echo "🔧 Starting memory-safe Cypress test execution..."

# Check if services are running
echo "🔍 Checking if services are available..."
if ! curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "❌ Frontend not available at localhost:3000"
    echo "Please start your local dev deployment first"
    exit 1
fi

# Get list of test files
echo "📋 Discovering test files..."
TEST_FILES=($(find cypress/e2e -name "*.cy.ts" | sort))
echo "Found ${#TEST_FILES[@]} test files"

# Configuration
BATCH_SIZE=3
TOTAL_TESTS=${#TEST_FILES[@]}
PASSED=0
FAILED=0
RESULTS_FILE="cypress-memory-safe-results.txt"

echo "🚀 Running tests in batches of $BATCH_SIZE to prevent memory issues..."
echo "Results will be logged to $RESULTS_FILE"

# Clear previous results
> $RESULTS_FILE

# Process tests in batches
for ((i=0; i<$TOTAL_TESTS; i+=BATCH_SIZE)); do
    BATCH_START=$i
    BATCH_END=$((i + BATCH_SIZE - 1))
    if [ $BATCH_END -ge $TOTAL_TESTS ]; then
        BATCH_END=$((TOTAL_TESTS - 1))
    fi
    
    echo ""
    echo "📦 Batch $((i/BATCH_SIZE + 1)): Running tests $((BATCH_START + 1)) to $((BATCH_END + 1))"
    
    # Get current batch of files
    BATCH_FILES=()
    for ((j=BATCH_START; j<=BATCH_END; j++)); do
        BATCH_FILES+=("${TEST_FILES[$j]}")
    done
    
    # Create spec pattern for this batch
    SPEC_PATTERN=$(IFS=','; echo "${BATCH_FILES[*]}")
    
    echo "Running: ${BATCH_FILES[*]}"
    echo "----------------------------------------"
    
    # Run the batch with memory-safe config
    if npx cypress run \
        --config-file cypress.config.memory-safe.ts \
        --browser chrome \
        --spec "$SPEC_PATTERN" \
        --config video=false,screenshotOnRunFailure=false; then
        echo "✅ Batch $((i/BATCH_SIZE + 1)) completed successfully" | tee -a $RESULTS_FILE
        PASSED=$((PASSED + ${#BATCH_FILES[@]}))
    else
        echo "❌ Batch $((i/BATCH_SIZE + 1)) had failures" | tee -a $RESULTS_FILE
        FAILED=$((FAILED + ${#BATCH_FILES[@]}))
    fi
    
    # Small delay between batches to let memory settle
    echo "⏸️  Cooling down for 3 seconds..."
    sleep 3
done

# Summary
echo ""
echo "================================================"
echo "🏁 Memory-safe Cypress execution complete!"
echo "📊 Results:"
echo "   ✅ Passed batches: $PASSED tests"
echo "   ❌ Failed batches: $FAILED tests"
echo "   📋 Total tests: $TOTAL_TESTS"
echo ""
echo "📝 Detailed results saved to: $RESULTS_FILE"
echo "================================================"