#!/bin/bash
# Run this script directly on the GitHub runner VM to diagnose issues

echo "GitHub Runner Local Diagnostics"
echo "================================"

# Check if runner user exists
echo -e "\n1. Checking runner user..."
if id runner &>/dev/null; then
    echo "✓ Runner user exists"
    groups runner
else
    echo "✗ Runner user does not exist"
fi

# Check runner directory
echo -e "\n2. Checking runner directory..."
RUNNER_DIR="/home/runner/actions-runner"
if [ -d "$RUNNER_DIR" ]; then
    echo "✓ Runner directory exists"
    ls -la "$RUNNER_DIR" | head -5
else
    echo "✗ Runner directory does not exist at $RUNNER_DIR"
fi

# Check runner configuration
echo -e "\n3. Checking runner configuration..."
if [ -f "$RUNNER_DIR/.runner" ]; then
    echo "✓ Runner is configured"
    cat "$RUNNER_DIR/.runner" | jq .
else
    echo "✗ Runner is not configured"
fi

# Check runner service
echo -e "\n4. Checking runner service..."
systemctl status actions.runner.* --no-pager

# Check if runner process is running
echo -e "\n5. Checking runner process..."
if pgrep -f "Runner.Listener" > /dev/null; then
    echo "✓ Runner process is running"
    ps aux | grep -i runner | grep -v grep
else
    echo "✗ Runner process is not running"
fi

# Check recent runner logs
echo -e "\n6. Recent runner logs..."
if ls $RUNNER_DIR/_diag/Runner_*.log 2>/dev/null; then
    echo "Latest log file:"
    ls -lt $RUNNER_DIR/_diag/Runner_*.log | head -1
    echo -e "\nLast 20 lines:"
    tail -20 $(ls -t $RUNNER_DIR/_diag/Runner_*.log | head -1)
else
    echo "No runner logs found"
fi

# Check worker logs
echo -e "\n7. Worker logs (if any)..."
if ls $RUNNER_DIR/_diag/Worker_*.log 2>/dev/null; then
    echo "Latest worker log:"
    tail -10 $(ls -t $RUNNER_DIR/_diag/Worker_*.log | head -1)
else
    echo "No worker logs found (normal if no jobs have run)"
fi

# Check network connectivity
echo -e "\n8. Network connectivity..."
echo -n "GitHub API: "
curl -s -o /dev/null -w "%{http_code}\n" https://api.github.com/meta

echo -n "GitHub.com: "
curl -s -o /dev/null -w "%{http_code}\n" https://github.com

# Check GitHub token
echo -e "\n9. GitHub token access..."
if gcloud secrets versions access latest --secret="github-runner-token" &>/dev/null; then
    echo "✓ Can access GitHub token from Secret Manager"
else
    echo "✗ Cannot access GitHub token from Secret Manager"
fi

# Check startup script execution
echo -e "\n10. Startup script logs..."
journalctl -u google-startup-scripts.service --no-pager | tail -30

# Try to manually start the runner if it's not running
echo -e "\n11. Runner service control..."
echo "To manually start the runner:"
echo "  sudo systemctl start actions.runner.*.service"
echo "To see live logs:"
echo "  sudo journalctl -u actions.runner.*.service -f"
echo "To restart the runner:"
echo "  sudo systemctl restart actions.runner.*.service"