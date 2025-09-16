# NetraOptimizer Setup Guide for Fresh Users

This guide will walk you through setting up NetraOptimizer to track Claude usage metrics using Google CloudSQL.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Database Setup](#database-setup)
4. [Configuration](#configuration)
5. [Testing Your Setup](#testing-your-setup)
6. [Integration with Your Application](#integration-with-your-application)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### 1. Python Environment
- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Google Cloud Setup

#### Install Google Cloud SDK
```bash
# macOS
brew install google-cloud-sdk

# Ubuntu/Debian
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -
sudo apt-get update && sudo apt-get install google-cloud-sdk

# Or download directly
curl https://sdk.cloud.google.com | bash
```

#### Authenticate with Google Cloud
```bash
# Login to Google Cloud
gcloud auth application-default login

# Set your project
gcloud config set project netra-staging  # or your project ID
```

### 3. Cloud SQL Proxy Installation

The Cloud SQL Proxy allows secure local connections to CloudSQL.

```bash
# macOS
brew install cloud-sql-proxy

# Linux
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud-sql-proxy
chmod +x cloud-sql-proxy

# Windows
# Download from: https://dl.google.com/cloudsql/cloud_sql_proxy.windows.386.exe
```

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/netra-apex.git
cd netra-apex
```

### 2. Install Dependencies
```bash
# Install NetraOptimizer dependencies
pip install -r netraoptimizer/requirements.txt

# Or install from main requirements
pip install -r requirements.txt
```

## Database Setup

### Option 1: CloudSQL Setup (Recommended for Production/Staging)

#### Step 1: Start Cloud SQL Proxy
```bash
# In a separate terminal, start the proxy
cloud-sql-proxy --port=5434 netra-staging:us-central1:staging-shared-postgres

# Keep this terminal running
```

#### Step 2: Set Environment Variables
```bash
# Create a .env file or export directly
cat > .env.netraoptimizer << EOF
USE_CLOUD_SQL=true
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_USER=postgres
POSTGRES_PASSWORD=DTprdt5KoQXlEG4Gh9lF
GCP_PROJECT_ID=netra-staging
EOF

# Load the environment
source .env.netraoptimizer  # Or use python-dotenv
```

#### Step 3: Create Database and Tables
```bash
# Run the setup script
python netraoptimizer/database/setup.py

# You should see:
# ✅ Database setup complete!
# The NetraOptimizer system is ready to collect data.
```

#### Step 4: Verify Connection
```bash
python netraoptimizer/test_cloud_connection.py

# Expected output:
# ✅ All tests passed!
```

### Option 2: Local PostgreSQL Setup (Development Only)

#### Step 1: Install PostgreSQL
```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

#### Step 2: Create Local Database
```bash
createdb netra_optimizer
```

#### Step 3: Set Environment Variables
```bash
export NETRA_DB_HOST=localhost
export NETRA_DB_PORT=5432
export NETRA_DB_NAME=netra_optimizer
export NETRA_DB_USER=$(whoami)
export NETRA_DB_PASSWORD=""
```

#### Step 4: Run Setup
```bash
python netraoptimizer/database/setup.py
```

## Configuration

### Environment Variables Reference

NetraOptimizer uses environment variables for configuration. Create a `.env` file in your project root:

```bash
# For CloudSQL (Production/Staging)
ENVIRONMENT=staging                    # or 'production'
GCP_PROJECT_ID=netra-staging
USE_CLOUD_SQL=true
POSTGRES_HOST=localhost               # When using Cloud SQL Proxy
POSTGRES_PORT=5434                    # Cloud SQL Proxy port
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password       # From Secret Manager

# For Local PostgreSQL
NETRA_DB_HOST=localhost
NETRA_DB_PORT=5432
NETRA_DB_NAME=netra_optimizer
NETRA_DB_USER=your_user
NETRA_DB_PASSWORD=your_password

# Claude Configuration
CLAUDE_EXECUTABLE=claude               # Path to Claude executable
CLAUDE_TIMEOUT=600                    # Timeout in seconds

# Analytics Settings
NETRA_ENABLE_ANALYTICS=true
NETRA_BATCH_PREDICTION=false
```

### Google Secret Manager (Automatic in Staging/Production)

When `ENVIRONMENT` is set to `staging` or `production`, NetraOptimizer automatically loads credentials from Google Secret Manager:

- `postgres-host-staging`
- `postgres-user-staging`
- `postgres-password-staging`
- `postgres-db-staging`

No manual configuration needed if you have proper GCP permissions.

## Testing Your Setup

### 1. Run Connection Test
```bash
python netraoptimizer/test_cloud_connection.py
```

### 2. Run Example Usage
```bash
python netraoptimizer/example_usage.py
```

### 3. Run Unit Tests
```bash
pytest tests/netraoptimizer/ -v
```

## Integration with Your Application

### Basic Integration

```python
import asyncio
from netraoptimizer import NetraOptimizerClient
from netraoptimizer.database import DatabaseClient

async def track_claude_usage():
    # Initialize with CloudSQL
    db_client = DatabaseClient(use_cloud_sql=True)
    await db_client.initialize()

    # Create optimizer client
    optimizer = NetraOptimizerClient(database_client=db_client)

    # Track a Claude command execution
    result = await optimizer.run(
        command_raw="/gitissueprogressorv3 p0 agents",
        workspace_context={"project": "my-project"},
        session_context={"user": "developer"}
    )

    print(f"Execution tracked: {result['execution_id']}")
    print(f"Tokens used: {result['tokens']['total']}")
    print(f"Cost: ${result['cost_usd']:.4f}")

    await db_client.close()

# Run the tracking
asyncio.run(track_claude_usage())
```

### Advanced Integration with Your Orchestrator

```python
from netraoptimizer import NetraOptimizerClient

class YourOrchestrator:
    def __init__(self):
        # Initialize NetraOptimizer as singleton
        self.optimizer = NetraOptimizerClient(use_cloud_sql=True)

    async def execute_claude_command(self, command: str, **kwargs):
        # All Claude executions go through NetraOptimizer
        result = await self.optimizer.run(
            command_raw=command,
            batch_id=kwargs.get('batch_id'),
            workspace_context=kwargs.get('context')
        )

        # Use the metrics for decision making
        if result['tokens']['cache_hit_rate'] < 50:
            print("Warning: Low cache utilization")

        if result['cost_usd'] > 1.0:
            print(f"Expensive operation: ${result['cost_usd']}")

        return result
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "database netra_optimizer does not exist"
```bash
# Solution: Create the database
python netraoptimizer/database/setup.py
```

#### 2. "Reauthentication is needed"
```bash
# Solution: Re-authenticate with Google Cloud
gcloud auth application-default login
```

#### 3. "Connection refused" on port 5434
```bash
# Solution: Ensure Cloud SQL Proxy is running
cloud-sql-proxy --port=5434 netra-staging:us-central1:staging-shared-postgres
```

#### 4. "POSTGRES_USER not configured"
```bash
# Solution: Set environment variables
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD="your_password"
```

#### 5. Permission denied for Secret Manager
```bash
# Solution: Grant necessary permissions
gcloud projects add-iam-policy-binding netra-staging \
    --member="user:your-email@example.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Verification Commands

```bash
# Check Cloud SQL Proxy is running
ps aux | grep cloud-sql-proxy

# Test database connection
PGPASSWORD=$POSTGRES_PASSWORD psql -h localhost -p 5434 -U postgres -d netra_optimizer -c "SELECT 1;"

# Check tables exist
PGPASSWORD=$POSTGRES_PASSWORD psql -h localhost -p 5434 -U postgres -d netra_optimizer -c "\dt"

# View recent executions
python -c "
import asyncio
from netraoptimizer.database import DatabaseClient

async def check():
    client = DatabaseClient(use_cloud_sql=True)
    await client.initialize()
    records = await client.get_recent_executions(10)
    print(f'Found {len(records)} executions')
    await client.close()

asyncio.run(check())
"
```

## Next Steps

1. **Set up monitoring**: Configure alerts for high-cost operations
2. **Implement batch processing**: Group related commands for better caching
3. **Create dashboards**: Visualize usage patterns and costs
4. **Optimize caching**: Analyze cache hit rates and adjust strategies
5. **Set budgets**: Implement cost controls based on historical data

## Support

For issues or questions:
- Check the [main README](README.md)
- Review test files for usage examples
- Create an issue in the repository
- Consult the CloudSQL documentation

## Security Notes

- Never commit passwords or secrets to version control
- Use Google Secret Manager for production credentials
- Rotate database passwords regularly
- Limit database user permissions appropriately
- Use SSL/TLS for all database connections in production

---

**Remember**: Every Claude execution through NetraOptimizer is automatically tracked, providing valuable insights for optimization and cost management.