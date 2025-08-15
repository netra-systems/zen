#!/bin/bash
"""
Architecture Pre-commit Hooks Setup Script (Unix/Linux/macOS)
Sets up git hooks for enforcing CLAUDE.md architectural rules
"""

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GITHOOKS_DIR="${PROJECT_ROOT}/.githooks"

echo "🔧 Setting up architecture enforcement pre-commit hooks..."
echo "📁 Project root: ${PROJECT_ROOT}"

# Verify we're in a git repository
if [ ! -d "${PROJECT_ROOT}/.git" ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Verify .githooks directory exists
if [ ! -d "${GITHOOKS_DIR}" ]; then
    echo "❌ Error: .githooks directory not found"
    echo "   Expected at: ${GITHOOKS_DIR}"
    exit 1
fi

# Verify pre-commit hook exists
if [ ! -f "${GITHOOKS_DIR}/pre-commit" ]; then
    echo "❌ Error: pre-commit hook not found"
    echo "   Expected at: ${GITHOOKS_DIR}/pre-commit"
    exit 1
fi

# Make pre-commit hook executable
chmod +x "${GITHOOKS_DIR}/pre-commit"
echo "✅ Made pre-commit hook executable"

# Configure git to use custom hooks directory
cd "${PROJECT_ROOT}"
git config core.hooksPath .githooks
echo "✅ Configured git to use .githooks directory"

# Verify configuration
HOOKS_PATH=$(git config core.hooksPath)
if [ "${HOOKS_PATH}" != ".githooks" ]; then
    echo "❌ Error: Failed to configure hooks path"
    echo "   Expected: .githooks"
    echo "   Got: ${HOOKS_PATH}"
    exit 1
fi

echo ""
echo "🧪 Testing hook functionality..."

# Create a temporary test file that violates rules
TEST_FILE="test_hook_violation.py"
cat > "${TEST_FILE}" << 'EOF'
def test_function():
    # This function intentionally violates the 8-line rule
    line1 = 1
    line2 = 2
    line3 = 3
    line4 = 4
    line5 = 5
    line6 = 6
    line7 = 7
    line8 = 8
    line9 = 9  # This line makes it 9 lines, violating the rule
    return line9
EOF

# Add the test file to git staging
git add "${TEST_FILE}" 2>/dev/null || true

# Test the pre-commit hook
echo "📋 Running pre-commit hook test..."
if "${GITHOOKS_DIR}/pre-commit"; then
    echo "⚠️  Warning: Hook should have failed but didn't"
    HOOK_TEST_RESULT="unexpected_pass"
else
    echo "✅ Hook correctly detected violations"
    HOOK_TEST_RESULT="expected_fail"
fi

# Clean up test file
git reset HEAD "${TEST_FILE}" 2>/dev/null || true
rm -f "${TEST_FILE}"

echo ""
echo "="*60
echo "🎉 SETUP COMPLETE!"
echo "="*60
echo ""
echo "📋 Architecture rules enforced:"
echo "   • Files must be ≤300 lines"
echo "   • Functions must be ≤8 lines"  
echo "   • No test stubs in production code"
echo ""
echo "🔧 Hook configuration:"
echo "   • Hooks directory: .githooks"
echo "   • Pre-commit hook: ✅ Active"
echo "   • Hook test result: ${HOOK_TEST_RESULT}"
echo ""
echo "💡 Usage:"
echo "   • Hooks run automatically on 'git commit'"
echo "   • Manual check: python scripts/check_architecture_compliance.py"
echo "   • Bypass (emergency): git commit --no-verify"
echo ""
echo "⚡ Performance: Hooks only check staged files for fast commits"

if [ "${HOOK_TEST_RESULT}" = "unexpected_pass" ]; then
    echo ""
    echo "⚠️  Warning: Hook test had unexpected result. Manual verification recommended:"
    echo "   1. Create a file with >300 lines or >8 line functions"
    echo "   2. Stage it with 'git add'"
    echo "   3. Try 'git commit' - it should be blocked"
    exit 1
fi

echo ""
echo "✅ All systems ready! Your commits are now architecture-protected."