#!/bin/bash
# ClickHouse startup script for GCP Compute Engine

set -e

# Colors for output (escaped for Terraform templatefile)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Starting ClickHouse setup..."

# Update system
apt-get update
apt-get install -y apt-transport-https ca-certificates dirmngr gnupg

# Add ClickHouse repository
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 8919F6BD2B48D754
echo "deb https://packages.clickhouse.com/deb stable main" | tee /etc/apt/sources.list.d/clickhouse.list

# Install ClickHouse
apt-get update
apt-get install -y clickhouse-server clickhouse-client

# Configure ClickHouse for external access
cat > /etc/clickhouse-server/config.d/listen.xml << 'EOF'
<clickhouse>
    <listen_host>::</listen_host>
    <listen_host>0.0.0.0</listen_host>
</clickhouse>
EOF

# Configure users and security
cat > /etc/clickhouse-server/users.d/users.xml << 'EOF'
<clickhouse>
    <users>
        <default>
            <password>changeme</password>
            <networks>
                <ip>::/0</ip>
            </networks>
            <profile>default</profile>
            <quota>default</quota>
        </default>
    </users>
</clickhouse>
EOF

# Create database for Netra
clickhouse-client --query "CREATE DATABASE IF NOT EXISTS netra"

# Create tables for metrics
clickhouse-client --query "
CREATE TABLE IF NOT EXISTS netra.metrics (
    timestamp DateTime,
    metric_name String,
    metric_value Float64,
    labels Nested(
        key String,
        value String
    ),
    environment String
) ENGINE = MergeTree()
ORDER BY (timestamp, metric_name)
PARTITION BY toYYYYMM(timestamp)
"

clickhouse-client --query "
CREATE TABLE IF NOT EXISTS netra.agent_logs (
    timestamp DateTime,
    agent_id String,
    agent_type String,
    log_level String,
    message String,
    metadata String,
    environment String
) ENGINE = MergeTree()
ORDER BY (timestamp, agent_id)
PARTITION BY toYYYYMM(timestamp)
"

# Start ClickHouse service
systemctl enable clickhouse-server
systemctl restart clickhouse-server

# Check if service is running
if systemctl is-active --quiet clickhouse-server; then
    echo -e "$${GREEN}ClickHouse started successfully$${NC}"
else
    echo -e "$${RED}Failed to start ClickHouse$${NC}"
    exit 1
fi

echo "ClickHouse setup completed!"
echo "Access ClickHouse at: http://$(curl -s ifconfig.me):8123"