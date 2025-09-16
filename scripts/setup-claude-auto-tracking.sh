#!/bin/bash

# Setup automatic Claude metrics tracking
# This creates an alias that automatically tracks ALL Claude usage

echo "🚀 Setting up automatic Claude metrics tracking..."

# Add the monitoring wrapper function to shell config
cat << 'SHELL_FUNCTION' >> ~/.zshrc

# Claude Auto-Tracking Function
claude() {
    # Ensure Cloud SQL proxy is running
    if ! lsof -i:5434 > /dev/null 2>&1; then
        echo "📊 Starting metrics tracking..."
        cloud-sql-proxy --port=5434 netra-staging:us-central1:staging-shared-postgres > /dev/null 2>&1 &
        sleep 2
    fi

    # Set CloudSQL environment
    export POSTGRES_PORT=5434
    export POSTGRES_HOST=localhost
    export POSTGRES_DB=netra_optimizer
    export POSTGRES_USER=postgres
    export POSTGRES_PASSWORD=DTprdt5KoQXlEG4Gh9lF
    export ENVIRONMENT=staging

    # Create temporary config for tracking
    TEMP_CONFIG=$(mktemp)
    cat > "$TEMP_CONFIG" << EOF
{
  "instances": [
    {
      "command": "$*",
      "name": "claude_session_$(date +%s)",
      "description": "Interactive Claude session"
    }
  ]
}
EOF

    # Run with metrics tracking in background
    (python3 /Users/rindhujajohnson/Netra/GitHub/netra-apex/scripts/claude-instance-orchestrator-netra.py \
        --use-cloud-sql \
        --config "$TEMP_CONFIG" \
        > /tmp/claude-metrics.log 2>&1 &)

    # Run actual Claude command
    /opt/homebrew/bin/claude "$@"

    # Clean up
    rm -f "$TEMP_CONFIG"
}

# Quick command to view today's metrics
claude-metrics-today() {
    export PGPASSWORD=DTprdt5KoQXlEG4Gh9lF
    echo "📊 Today's Claude Usage Metrics:"
    echo "================================"
    psql -h localhost -p 5434 -U postgres -d netra_optimizer -t -c "
        SELECT
            COUNT(*) as commands,
            SUM(total_tokens) as total_tokens,
            SUM(cost_usd) as total_cost,
            SUM(cache_savings_usd) as total_savings
        FROM command_executions
        WHERE DATE(timestamp) = CURRENT_DATE;
    " | while read commands tokens cost savings; do
        echo "Commands Run: $commands"
        echo "Total Tokens: $tokens"
        echo "Total Cost: \$$cost"
        echo "Cache Savings: \$$savings"
    done
}

# View recent commands
claude-metrics-recent() {
    export PGPASSWORD=DTprdt5KoQXlEG4Gh9lF
    echo "📊 Recent Claude Commands:"
    echo "========================="
    psql -h localhost -p 5434 -U postgres -d netra_optimizer -t -c "
        SELECT
            timestamp::time,
            LEFT(command_raw, 50) as command,
            total_tokens,
            cost_usd
        FROM command_executions
        WHERE DATE(timestamp) = CURRENT_DATE
        ORDER BY timestamp DESC
        LIMIT 10;
    " | while IFS='|' read time cmd tokens cost; do
        printf "%s | %-50s | %6s tokens | \$%.4f\n" "$time" "$cmd" "$tokens" "$cost"
    done
}

SHELL_FUNCTION

echo "✅ Setup complete!"
echo ""
echo "🎯 What's been set up:"
echo "  • 'claude' command now automatically tracks metrics"
echo "  • All usage is saved to CloudSQL staging database"
echo "  • Metrics tracked in background (won't slow you down)"
echo ""
echo "📊 New commands available:"
echo "  • claude-metrics-today   - View today's total usage"
echo "  • claude-metrics-recent  - View recent commands"
echo ""
echo "⚠️  Please run: source ~/.zshrc"
echo "  Or open a new terminal for changes to take effect"