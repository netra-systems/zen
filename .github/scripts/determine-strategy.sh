#!/bin/bash

# determine-strategy.sh
# Analyzes changed files and commit messages to determine skip conditions and test scope
# ACT compatible - follows patterns from MASTER_GITHUB_WORKFLOW.xml

set -e

# Source ACT utilities if available
SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")"
if [[ -f "$SCRIPT_DIR/act_utils.sh" ]]; then
    source "$SCRIPT_DIR/act_utils.sh"
    print_act_debug
fi

echo "🔍 Determining workflow execution strategy..."

# Initialize default values
SKIP_TESTS="false"
SKIP_DEPLOY="false" 
TEST_SCOPE="full"
CHANGED_FILES=""
COMMIT_MESSAGE=""

# Function to get changed files (ACT compatible)
get_changed_files() {
    if [[ "$(is_act_environment)" == "true" ]]; then
        echo "🧪 ACT: Using mock changed files"
        echo "frontend/components/chat.tsx app/routes/api.py docs/README.md"
    else
        # Get changed files from git or GitHub context
        if [[ -n "${GITHUB_EVENT_PATH}" && -f "${GITHUB_EVENT_PATH}" ]]; then
            # Extract from GitHub event (PR context)
            python3 -c "
import json, sys
try:
    with open('${GITHUB_EVENT_PATH}', 'r') as f:
        event = json.load(f)
    if 'pull_request' in event:
        print(' '.join([f['filename'] for f in event.get('pull_request', {}).get('changed_files', [])]))
    else:
        print('')
except:
    print('')
"
        else
            # Fallback to git diff
            git diff --name-only HEAD~1 HEAD 2>/dev/null || echo ""
        fi
    fi
}

# Function to get commit message (ACT compatible)
get_commit_message() {
    if [[ "$(is_act_environment)" == "true" ]]; then
        echo "🧪 ACT: Using mock commit message"
        echo "feat: add new chat component"
    else
        if [[ -n "${GITHUB_EVENT_PATH}" && -f "${GITHUB_EVENT_PATH}" ]]; then
            # Extract from GitHub event
            python3 -c "
import json
try:
    with open('${GITHUB_EVENT_PATH}', 'r') as f:
        event = json.load(f)
    if 'head_commit' in event:
        print(event['head_commit']['message'])
    elif 'pull_request' in event:
        print(event['pull_request']['title'])
    else:
        print('')
except:
    print('')
"
        else
            # Fallback to git log
            git log -1 --pretty=format:"%s" 2>/dev/null || echo ""
        fi
    fi
}

# Function to check if changes are docs-only
is_docs_only() {
    local files="$1"
    local docs_pattern="^(.*\.md|docs/.*|SPEC/.*|\.github/.*\.md)$"
    
    if [[ -z "$files" ]]; then
        return 1
    fi
    
    local all_docs=true
    for file in $files; do
        if ! [[ "$file" =~ $docs_pattern ]]; then
            all_docs=false
            break
        fi
    done
    
    if [[ "$all_docs" == "true" ]]; then
        echo "📚 Detected docs-only changes"
        return 0
    fi
    return 1
}

# Function to check for CI skip markers
has_ci_skip() {
    local message="$1"
    if [[ "$message" =~ \[(skip ci|ci skip)\] ]]; then
        echo "⏭️  Detected CI skip marker in commit message"
        return 0
    fi
    return 1
}

# Function to check if changes are frontend-only
is_frontend_only() {
    local files="$1"
    local frontend_pattern="^frontend/.*$"
    
    if [[ -z "$files" ]]; then
        return 1
    fi
    
    local all_frontend=true
    for file in $files; do
        if ! [[ "$file" =~ $frontend_pattern ]]; then
            all_frontend=false
            break
        fi
    done
    
    if [[ "$all_frontend" == "true" ]]; then
        echo "🎨 Detected frontend-only changes"
        return 0
    fi
    return 1
}

# Function to check if changes are backend-only
is_backend_only() {
    local files="$1"
    local backend_pattern="^app/.*$"
    
    if [[ -z "$files" ]]; then
        return 1
    fi
    
    local all_backend=true
    for file in $files; do
        if ! [[ "$file" =~ $backend_pattern ]]; then
            all_backend=false
            break
        fi
    done
    
    if [[ "$all_backend" == "true" ]]; then
        echo "⚙️  Detected backend-only changes"
        return 0
    fi
    return 1
}

# Function to determine test scope
determine_test_scope() {
    local files="$1"
    
    # Check for critical paths that require full testing
    if echo "$files" | grep -E "(main\.py|config\.py|database|auth|security)" >/dev/null; then
        echo "full"
        return
    fi
    
    # Check for agent changes that require e2e tests
    if echo "$files" | grep -E "app/agents/" >/dev/null; then
        echo "agents"
        return
    fi
    
    # Check for frontend changes
    if is_frontend_only "$files"; then
        echo "frontend"
        return
    fi
    
    # Check for backend changes
    if is_backend_only "$files"; then
        echo "backend"
        return
    fi
    
    # Default to unit tests for small changes
    echo "unit"
}

# Main analysis logic
main() {
    echo "📊 Analyzing repository changes..."
    
    # Get changed files and commit message
    CHANGED_FILES=$(get_changed_files)
    COMMIT_MESSAGE=$(get_commit_message)
    
    echo "📝 Changed files: $CHANGED_FILES"
    echo "💬 Commit message: $COMMIT_MESSAGE"
    
    # Check skip conditions in order of precedence
    if has_ci_skip "$COMMIT_MESSAGE"; then
        SKIP_TESTS="true"
        SKIP_DEPLOY="true"
        TEST_SCOPE="none"
        echo "🛑 Skipping all workflows due to CI skip marker"
    elif is_docs_only "$CHANGED_FILES"; then
        SKIP_TESTS="true"
        SKIP_DEPLOY="true"
        TEST_SCOPE="none"
        echo "📚 Skipping tests and deployment for docs-only changes"
    else
        # Determine test scope based on changes
        TEST_SCOPE=$(determine_test_scope "$CHANGED_FILES")
        echo "🎯 Test scope determined: $TEST_SCOPE"
        
        # Set deployment strategy
        if [[ "$TEST_SCOPE" == "frontend" ]]; then
            echo "🎨 Frontend-only changes detected"
        elif [[ "$TEST_SCOPE" == "backend" ]]; then
            echo "⚙️  Backend-only changes detected"
        fi
    fi
    
    # Output results for GitHub Actions (ACT compatible)
    if [[ -n "${GITHUB_OUTPUT}" && -f "${GITHUB_OUTPUT}" ]]; then
        echo "skip_tests=$SKIP_TESTS" >> "$GITHUB_OUTPUT"
        echo "skip_deploy=$SKIP_DEPLOY" >> "$GITHUB_OUTPUT"  
        echo "test_scope=$TEST_SCOPE" >> "$GITHUB_OUTPUT"
    elif [[ "$(is_act_environment)" == "true" ]]; then
        echo "🧪 ACT: GITHUB_OUTPUT not available, outputting to stdout"
        echo "skip_tests=$SKIP_TESTS"
        echo "skip_deploy=$SKIP_DEPLOY"
        echo "test_scope=$TEST_SCOPE"
    fi
    
    # Also output as environment variables for backward compatibility
    if [[ -n "${GITHUB_ENV}" ]]; then
        echo "SKIP_TESTS=$SKIP_TESTS" >> "$GITHUB_ENV"
        echo "SKIP_DEPLOY=$SKIP_DEPLOY" >> "$GITHUB_ENV"
        echo "TEST_SCOPE=$TEST_SCOPE" >> "$GITHUB_ENV"
    fi
    
    # Summary output
    echo ""
    echo "📋 Strategy Summary:"
    echo "   Skip Tests: $SKIP_TESTS"
    echo "   Skip Deploy: $SKIP_DEPLOY"
    echo "   Test Scope: $TEST_SCOPE"
    echo ""
    
    # ACT-specific logging
    if [[ "$(is_act_environment)" == "true" ]]; then
        echo "🧪 ACT: Strategy determination completed"
        cat > act_strategy_output.json << EOF
{
  "skip_tests": "$SKIP_TESTS",
  "skip_deploy": "$SKIP_DEPLOY", 
  "test_scope": "$TEST_SCOPE",
  "changed_files": "$CHANGED_FILES",
  "commit_message": "$COMMIT_MESSAGE",
  "act_mock": true
}
EOF
        echo "📝 ACT: Strategy saved to act_strategy_output.json"
    fi
}

# Run main function
main "$@"