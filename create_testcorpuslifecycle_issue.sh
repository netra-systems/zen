#!/bin/bash

# Script to create GitHub issue for TestCorpusLifecycle import error
# Usage: ./create_testcorpuslifecycle_issue.sh

echo "Creating GitHub issue for TestCorpusLifecycle import error..."

# Create the issue using GitHub CLI
gh issue create \
  --title "ImportError: TestCorpusLifecycle class not found after rename to CorpusLifecycleTests" \
  --body-file "./github_issue_testcorpuslifecycle_import_error.md" \
  --label "bug,test-infrastructure,ssot-compliance,medium-priority" \
  --assignee "@me"

if [ $? -eq 0 ]; then
    echo "✅ GitHub issue created successfully!"
    echo "📋 Issue details saved in: github_issue_testcorpuslifecycle_import_error.md"
else
    echo "❌ Failed to create GitHub issue via CLI"
    echo "📄 Issue content is available in: github_issue_testcorpuslifecycle_import_error.md"
    echo "💻 You can manually create the issue by copying the content to GitHub"
fi

echo ""
echo "🔍 Quick fix for the import error:"
echo "Edit netra_backend/tests/clickhouse/test_corpus_generation_coverage_index.py"
echo "Change lines 20-22 from:"
echo "    TestCorpusLifecycle,"
echo "    TestWorkloadTypesCoverage,"
echo "To:"
echo "    CorpusLifecycleTests as TestCorpusLifecycle,"
echo "    WorkloadTypesCoverageTests as TestWorkloadTypesCoverage,"