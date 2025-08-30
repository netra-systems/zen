# Environment Loader Documentation

## Overview

The Netra Apex environment loader has been simplified to provide a clear, single-source approach for managing environment variables with an optional remote fallback for missing secrets.

## Core Principles

### 1. Single Source of Truth
- **Primary Source**: `.env` file (user-controlled)
- **Never Auto-Generated**: The `.env` file is strictly user-defined
- **Never Overwritten**: System never modifies the `.env` file

### 2. Clear Priority Order
```
1. OS Environment Variables (highest priority)
2. .env file (primary configuration source)
3. Google Secret Manager (fallback for missing secrets only)
4. Default values (lowest priority, non-sensitive only)
```

### 3. User Control
- Users maintain full control over their `.env` file
- Optional remote fallback can be disabled
- Clear visibility into what's loaded from where

## Architecture

### Components

#### EnvFileLoader (`dev_launcher/env_file_loader.py`)
- Simplified to load from single `.env` file only
- Validates that `.env` is user-controlled (not auto-generated)
- Provides clear help messages for creating `.env` files
- Tracks missing required variables

#### SecretLoader (`dev_launcher/secret_loader.py`)
- Orchestrates the loading process
- Manages fallback to Google Secret Manager
- Provides comprehensive observability and logging
- Tracks loaded secrets by source

## Usage

### Basic Usage

```python
from dev_launcher.secret_loader import SecretLoader

# Initialize loader
loader = SecretLoader(
    project_root=Path.cwd(),
    verbose=True,  # Enable detailed logging
    use_remote_fallback=True  # Enable Google Secret Manager fallback
)

# Load all secrets
loader.load_all_secrets()
```

### Disable Remote Fallback

```python
# For fully local development
loader = SecretLoader(
    project_root=Path.cwd(),
    use_remote_fallback=False  # Rely only on .env and OS environment
)
```

## Creating Your .env File

### Option 1: Copy from Example
```bash
cp .env.example .env
# Edit .env with your values
```

### Option 2: Copy from Local Template
```bash
cp .env.local .env
# Edit .env with your values
```

### Option 3: Create Manually
Create a `.env` file in the project root with required variables:

```env
# API Keys
GEMINI_API_KEY=your-api-key-here
ANTHROPIC_API_KEY=your-api-key-here
OPENAI_API_KEY=your-api-key-here

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Database
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your-password
CLICKHOUSE_DB=default

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Security
JWT_SECRET_KEY=your-jwt-secret-key
FERNET_KEY=your-fernet-key

# Monitoring
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key

# Environment
ENVIRONMENT=development
```

## Loading Process

### Step-by-Step Flow

1. **Check OS Environment**
   - Captures existing environment variables
   - These have highest priority

2. **Load .env File**
   - Reads user-defined `.env` file
   - Primary configuration source

3. **Identify Missing Secrets**
   - Compares loaded variables against required set
   - Lists any missing secrets

4. **Fallback to Remote (Optional)**
   - Only loads missing secrets from Google Secret Manager
   - Skipped if `use_remote_fallback=False`

5. **Apply Defaults**
   - Non-sensitive defaults for configs like ports
   - Lowest priority

6. **Set Environment Variables**
   - Merges all sources with proper precedence
   - Sets OS environment variables

## Observability Features

### Detailed Logging

The loader provides comprehensive logging at each step:

```
======================================================================
[SECRET LOADER] Simplified Environment Loading
======================================================================

[ENV CHECK] Checking OS environment variables...
  [OK] Found 5 relevant variables in OS

[ENV LOADER] Loading from .env file...
  [FILE] Path: /project/.env
  [OK] Loaded 15 variables from .env

[MISSING] 2 required secrets not in .env or OS:
  - ANTHROPIC_API_KEY
  - OPENAI_API_KEY

[FALLBACK] Loading 2 missing secrets from Google...
  Project ID: 304612253870
  [OK] Connected to Secret Manager
  [OK] Loaded 2 secrets from Google

[MERGE] Setting environment variables...
Priority: OS Environment > .env file > Google Secrets > Defaults
```

### Summary Statistics

After loading, displays source breakdown:

```
======================================================================
[SUMMARY] Environment Loading Complete
======================================================================

Total variables set: 20

By source:
  .env file                  15 (75.0%)
  OS Environment              3 (15.0%)
  Google Secret Manager       2 (10.0%)
```

### Variable Categories

Variables are organized by category for clarity:

- **Google OAuth**: Authentication credentials
- **API Keys**: LLM and service API keys
- **ClickHouse**: Database configuration
- **Redis**: Cache configuration
- **Langfuse**: Monitoring configuration
- **Security**: JWT and encryption keys
- **Environment**: Runtime environment settings

## Migration Guide

### From Old Multi-File System

If you were using the old system with multiple env files:

1. **Consolidate your configuration**:
   ```bash
   # Merge your preferred settings into single .env
   cat .env.development >> .env
   cat .env.development.local >> .env
   ```

2. **Remove duplicates** and keep only the values you want

3. **Delete old files** (optional):
   ```bash
   rm .env.development .env.development.local
   ```

### Important Notes

- The `.env` file is **never** auto-generated or modified by the system
- Users have full control over their `.env` file
- Remote secrets are only fetched for missing variables
- OS environment variables always take precedence

## Troubleshooting

### No .env File Found

If you see:
```
[INFO] No .env file found (user can create one)
```

Follow the help instructions to create your `.env` file.

### Missing Secrets

If secrets are missing and remote fallback is disabled:
```
[MISSING] 2 required secrets not in .env or OS:
  - ANTHROPIC_API_KEY
  - OPENAI_API_KEY
```

Either:
1. Add them to your `.env` file
2. Set them as OS environment variables
3. Enable remote fallback with `use_remote_fallback=True`

### Auto-Generated Warning

If you see:
```
[WARN] .env appears to be auto-generated
[WARN] User should create their own .env file
```

This means your `.env` file contains auto-generation markers. Create a fresh `.env` file with your own values.

## Best Practices

1. **Keep .env in .gitignore**: Never commit secrets to version control
2. **Use .env.example**: Maintain an example file with dummy values
3. **Set critical secrets in OS**: For production, use OS environment variables
4. **Enable verbose mode**: During development for better visibility
5. **Disable remote fallback**: For fully offline development

## Required Environment Variables

### Essential Secrets
- `JWT_SECRET_KEY`: For authentication
- `FERNET_KEY`: For encryption
- `GEMINI_API_KEY`: For Gemini LLM access

### Database Configuration
- `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`, `CLICKHOUSE_USER`
- `CLICKHOUSE_PASSWORD`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`

### Optional Services
- `ANTHROPIC_API_KEY`: For Claude API
- `OPENAI_API_KEY`: For OpenAI API
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`: For monitoring
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`: For OAuth

## Security Considerations

1. **Sensitive Value Masking**: All logged values are masked (e.g., `abc***xyz`)
2. **No Secret Logging**: Full secret values are never logged
3. **User Control**: Users maintain full control over their secrets
4. **Fallback Optional**: Remote secret fetching can be completely disabled
5. **Priority System**: OS environment always overrides file-based configs