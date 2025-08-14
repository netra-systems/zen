# Netra Development Launcher

A modular development environment launcher with intelligent service configuration management.

## Overview

The dev launcher provides a streamlined way to start your development environment with proper service configuration. It handles:

- **Service Configuration**: Choose between local, shared, or mock services
- **Automatic Port Management**: Dynamic port allocation to avoid conflicts
- **Process Management**: Auto-restart on crashes, real-time log streaming
- **Secret Management**: Automatic loading from Google Cloud Secret Manager

## Quick Start

```bash
# Recommended: Use shared resources with dynamic ports
python dev_launcher.py --dynamic --no-backend-reload --load-secrets

# First-time setup will prompt for configuration
python dev_launcher.py
```

## Service Configuration

### Service Modes

Each service (Redis, ClickHouse, PostgreSQL, LLM) can operate in one of four modes:

1. **SHARED** (Recommended for most developers)
   - Uses cloud-hosted development resources
   - No local installation required
   - Consistent environment across team
   - Pre-configured with credentials

2. **LOCAL**
   - Uses locally installed services
   - Requires service installation
   - Full control over configuration
   - Good for offline development

3. **MOCK**
   - Uses mock implementations
   - No external dependencies
   - Limited functionality
   - Good for UI development

4. **DISABLED** (Not recommended)
   - Service is completely disabled
   - Some features will not work
   - Use only for specific testing scenarios

### Configuration Wizard

On first run, the launcher will present an interactive configuration wizard:

```
🚀 Netra Development Environment Configuration Wizard
========================================================

This wizard will help you configure services for development.
You can choose between:
  • SHARED: Use cloud-hosted development resources (recommended)
  • LOCAL:  Use locally installed services
  • MOCK:   Use mock implementations (limited functionality)

Use recommended configuration? (Shared Redis & ClickHouse, Local PostgreSQL) [Y/n]:
```

### Shared Resources

The default shared resources are configured as follows:

#### Redis (Shared)
- **Host**: redis-17593.c305.ap-south-1-1.ec2.redns.redis-cloud.com
- **Port**: 17593
- **Password**: Automatically loaded from secrets
- **Purpose**: Caching, real-time features, WebSocket coordination

#### ClickHouse (Shared)
- **Host**: xedvrr4c3r.us-central1.gcp.clickhouse.cloud
- **Port**: 8443
- **User**: default
- **Password**: Automatically loaded from secrets
- **Database**: default
- **Purpose**: Analytics, metrics, log aggregation

#### PostgreSQL (Local by default)
- **Host**: localhost
- **Port**: 5432
- **User**: postgres
- **Password**: postgres
- **Database**: netra_dev
- **Purpose**: Main application database

#### LLM Services (Shared)
- **Providers**: Anthropic, OpenAI, Google Gemini
- **Default**: Gemini
- **API Keys**: Automatically loaded from secrets
- **Purpose**: AI features, agent intelligence

### Configuration File

Your service configuration is saved to `.dev_services.json`:

```json
{
  "redis": {
    "mode": "shared",
    "config": {
      "host": "redis-17593.c305.ap-south-1-1.ec2.redns.redis-cloud.com",
      "port": 17593,
      "password": "***",
      "db": 0
    }
  },
  "clickhouse": {
    "mode": "shared",
    "config": {
      "host": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
      "port": 8443,
      "user": "default",
      "password": "***",
      "database": "default",
      "secure": true
    }
  },
  "postgres": {
    "mode": "local",
    "config": {
      "host": "localhost",
      "port": 5432,
      "user": "postgres",
      "password": "postgres",
      "database": "netra_dev"
    }
  },
  "llm": {
    "mode": "shared",
    "config": {
      "providers": ["anthropic", "openai", "gemini"],
      "default_provider": "gemini"
    }
  }
}
```

## Command Line Options

### Port Configuration
- `--backend-port PORT`: Specify backend port (default: 8000)
- `--frontend-port PORT`: Specify frontend port (default: 3000)
- `-d, --dynamic`: Use dynamic port allocation (recommended)

### Hot Reload
- `--no-backend-reload`: Disable backend hot reload (30-50% performance improvement)
- `--no-frontend-reload`: Disable frontend hot reload
- `--no-reload`: Disable all hot reload (maximum performance)

### Secret Management
- `--load-secrets`: Force loading secrets from Google Cloud
- `--no-secrets`: Skip secret loading
- `--project-id ID`: Specify Google Cloud project ID

### Process Management
- `--no-auto-restart`: Disable automatic restart on crash
- `--max-restarts N`: Maximum restart attempts (default: 3)
- `--restart-delay N`: Seconds between restarts (default: 5)

### UI Configuration
- `--no-browser`: Don't open browser automatically
- `-v, --verbose`: Show detailed debug information

### Build Configuration
- `--no-turbopack`: Use webpack instead of turbopack
- `--turbopack`: Use turbopack (experimental, faster)

## Environment Variables

The launcher automatically sets these environment variables based on your service configuration:

```bash
# Service modes (set by launcher)
REDIS_MODE=shared|local|mock|disabled
CLICKHOUSE_MODE=shared|local|mock|disabled
POSTGRES_MODE=shared|local|mock|disabled
LLM_MODE=shared|local|mock|disabled

# Connection URLs (automatically generated)
REDIS_URL=redis://...
CLICKHOUSE_URL=clickhouse+https://...
DATABASE_URL=postgresql://...

# Service-specific configuration
REDIS_HOST=...
REDIS_PORT=...
CLICKHOUSE_HOST=...
CLICKHOUSE_PORT=...
# etc.
```

## Troubleshooting

### Service Connection Issues

If you encounter connection issues with shared resources:

1. **Check network connectivity**: Ensure you can reach the cloud services
2. **Verify credentials**: Run with `--load-secrets` to refresh credentials
3. **Check firewall**: Some corporate networks may block certain ports
4. **Use mock mode**: For UI development, you can use mock mode temporarily

### Local Service Setup

If using LOCAL mode for services:

#### Redis (Local)
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Windows
# Download from https://github.com/microsoftarchive/redis/releases
```

#### ClickHouse (Local)
```bash
# macOS
brew install clickhouse
clickhouse server

# Ubuntu/Debian
sudo apt-get install clickhouse-server clickhouse-client
sudo systemctl start clickhouse-server
```

#### PostgreSQL (Local)
```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get install postgresql
sudo systemctl start postgresql

# Create database
createdb netra_dev
```

### Changing Service Configuration

To reconfigure services after initial setup:

1. **Delete configuration file**: `rm .dev_services.json`
2. **Run launcher**: `python dev_launcher.py`
3. **Follow wizard**: Choose new configuration options

Or manually edit `.dev_services.json` and change the `mode` field for any service.

## Best Practices

1. **Use Shared Resources**: Unless you have specific needs, use shared resources for consistency
2. **Dynamic Ports**: Always use `--dynamic` to avoid port conflicts
3. **Disable Hot Reload**: Use `--no-backend-reload` for better performance during development
4. **Save Configuration**: Let the wizard save your configuration for consistent environments
5. **Check Warnings**: Pay attention to configuration warnings on startup

## Security Notes

- Shared resource credentials are managed securely through Google Cloud Secret Manager
- Local PostgreSQL uses default credentials (change for production)
- Mock mode provides no real functionality but is safe for UI development
- Never commit `.dev_services.json` if you've customized it with sensitive data

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs in `logs/` directory
3. Run with `--verbose` for detailed debug output
4. Contact the platform team for shared resource access issues