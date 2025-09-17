#!/bin/bash

# Create GitHub Issue for WebSocket Connectivity Cluster 4
# Process Cluster 4: P1 HIGH - WebSocket Connectivity Issues (15 incidents)

echo "Creating GitHub issue for WebSocket Connectivity Degradation..."

# Option 1: Using GitHub CLI (Recommended)
gh issue create \
  --title "GCP-active-dev | P1 | WebSocket Connectivity Degradation Affecting Chat - Worker Initialization Failures" \
  --body-file "C:\netra-apex\temp_websocket_connectivity_cluster_4_issue.md" \
  --label "claude-code-generated-issue" \
  --label "P1" \
  --label "websocket" \
  --label "chat" \
  --label "connectivity" \
  --label "business-critical" \
  --label "gunicorn" \
  --label "worker-initialization"

# Check if issue creation was successful
if [ $? -eq 0 ]; then
    echo "✅ WebSocket connectivity issue created successfully!"
    echo "📋 Issue labels: claude-code-generated-issue, P1, websocket, chat, connectivity, business-critical, gunicorn, worker-initialization"
    echo "🔗 Business Impact: 90% of platform value (chat) affected"
    echo "💰 Revenue Impact: $500K+ ARR at risk"

    # Cleanup temporary files
    echo "🧹 Cleaning up temporary files..."
    rm -f "C:\netra-apex\temp_websocket_connectivity_cluster_4_issue.md"
    rm -f "C:\netra-apex\create_websocket_connectivity_cluster_4_issue.sh"

    echo "✅ Issue creation complete!"
else
    echo "❌ Failed to create issue. Please try manual creation:"
    echo "1. Go to GitHub Issues page"
    echo "2. Use title: 'GCP-active-dev | P1 | WebSocket Connectivity Degradation Affecting Chat - Worker Initialization Failures'"
    echo "3. Copy body from: C:\netra-apex\temp_websocket_connectivity_cluster_4_issue.md"
    echo "4. Add labels: claude-code-generated-issue, P1, websocket, chat, connectivity, business-critical, gunicorn, worker-initialization"
fi