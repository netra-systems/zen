#!/usr/bin/env python3
"""
Core Configuration Setup for Netra AI Platform installer.
Database initialization and environment file creation.
CRITICAL: All functions MUST be  <= 8 lines, file  <= 300 lines.
"""

import os
import shutil
import sys
from pathlib import Path

# Add scripts directory to path for imports
script_dir = Path(__file__).parent

from env_checker import check_command_exists, run_command
from installer_types import InstallerConfig, InstallerResult


def setup_databases(config: InstallerConfig) -> InstallerResult:
    """Initialize databases and run migrations"""
    python_path = get_venv_python_path(config)
    
    if not python_path.exists():
        return InstallerResult(False, [], ["Virtual environment not found"], [])
    
    return run_database_setup(config, python_path)


def get_venv_python_path(config: InstallerConfig) -> Path:
    """Get Python executable path from virtual environment"""
    if config.is_windows:
        return config.venv_path / "Scripts" / "python.exe"
    else:
        return config.venv_path / "bin" / "python"


def run_database_setup(config: InstallerConfig, python_path: Path) -> InstallerResult:
    """Run database creation and migration scripts"""
    results = []
    
    results.append(check_postgresql_status())
    results.append(run_database_creation(config, python_path))
    results.append(run_database_migrations(config, python_path))
    
    return combine_config_results(results)


def check_postgresql_status() -> InstallerResult:
    """Check if PostgreSQL is running"""
    if not check_command_exists("pg_isready"):
        warning = "PostgreSQL status unknown - pg_isready not available"
        return InstallerResult(True, [], [], [warning])
    
    return verify_postgresql_connection()


def verify_postgresql_connection() -> InstallerResult:
    """Verify PostgreSQL connection status"""
    pg_status = run_command(["pg_isready"])
    
    if pg_status and "accepting connections" in pg_status:
        return InstallerResult(True, ["PostgreSQL is running"], [], [])
    
    warning = "PostgreSQL not running - will use SQLite fallback"
    return InstallerResult(True, [], [], [warning])


def run_database_creation(config: InstallerConfig, python_path: Path) -> InstallerResult:
    """Run database creation script"""
    create_db_script = config.project_root / "create_db.py"
    
    if not create_db_script.exists():
        return InstallerResult(True, ["No database creation script found"], [], [])
    
    return execute_database_script(python_path, create_db_script, "Database created")


def run_database_migrations(config: InstallerConfig, python_path: Path) -> InstallerResult:
    """Run database migration script"""
    migrations_script = config.project_root / "run_migrations.py"
    
    if not migrations_script.exists():
        return InstallerResult(True, ["No migration script found"], [], [])
    
    return execute_database_script(python_path, migrations_script, "Migrations completed")


def execute_database_script(python_path: Path, script_path: Path, success_msg: str) -> InstallerResult:
    """Execute a database-related Python script"""
    result = run_command([str(python_path), str(script_path)])
    
    if result is not None:
        return InstallerResult(True, [success_msg], [], [])
    
    warning_msg = f"{script_path.name} failed (will retry on first run)"
    return InstallerResult(True, [], [], [warning_msg])


def create_environment_file(config: InstallerConfig) -> InstallerResult:
    """Create .env file with default configuration"""
    env_file = config.project_root / ".env"
    
    if env_file.exists():
        return InstallerResult(True, [".env file already exists"], [], [])
    
    return generate_new_env_file(config, env_file)


def generate_new_env_file(config: InstallerConfig, env_file: Path) -> InstallerResult:
    """Generate new .env file from example or default template"""
    env_example = config.project_root / ".env.example"
    
    if env_example.exists():
        return copy_env_from_example(env_example, env_file)
    else:
        return create_default_env_file(env_file)


def copy_env_from_example(env_example: Path, env_file: Path) -> InstallerResult:
    """Copy environment file from example"""
    try:
        shutil.copy(env_example, env_file)
        return InstallerResult(True, [".env file created from example"], [], [])
    except Exception:
        return InstallerResult(False, [], ["Failed to copy .env.example"], [])


def create_default_env_file(env_file: Path) -> InstallerResult:
    """Create default .env file with standard configuration"""
    env_content = get_default_env_content()
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        return InstallerResult(True, [".env file created with defaults"], [], [])
    except Exception:
        return InstallerResult(False, [], ["Failed to create .env file"], [])


def get_default_env_content() -> str:
    """Get default environment file content"""
    random_key = os.urandom(24).hex()
    sections = [
        get_env_header(), get_env_environment_config(), get_env_database_config(),
        get_env_security_config(random_key), get_env_api_keys_config(), get_env_oauth_config(),
        get_env_frontend_config(), get_env_server_config(), get_env_cors_config(),
        get_env_service_limits_config(), get_env_feature_flags_config(), get_env_cache_config()
    ]
    return '\n\n'.join(sections)


def get_env_header() -> str:
    """Get environment file header section"""
    return """# Netra AI Platform - Development Environment Configuration
# Generated by install_dev_env.py"""


def get_env_environment_config() -> str:
    """Get environment configuration section"""
    return """# Environment
ENVIRONMENT=development
DEBUG=true"""


def get_env_database_config() -> str:
    """Get database configuration section"""
    return """# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/netra
CLICKHOUSE_URL=clickhouse://default:@localhost:9000/default
REDIS_URL=redis://localhost:6379/0"""


def get_env_security_config(random_key: str) -> str:
    """Get security configuration section"""
    return f"""# Security
SECRET_KEY=dev-secret-key-change-in-production-{random_key}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24"""


def get_env_api_keys_config() -> str:
    """Get API keys configuration section"""
    return """# API Keys (add your own)
ANTHROPIC_API_KEY=
OPENAI_API_KEY="""


def get_env_oauth_config() -> str:
    """Get OAuth configuration section"""
    return """# OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET="""


def get_env_frontend_config() -> str:
    """Get frontend configuration section"""
    return """# Frontend Configuration
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000"""


def get_env_server_config() -> str:
    """Get server configuration section"""
    return """# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=true
WORKERS=1
LOG_LEVEL=INFO"""


def get_env_cors_config() -> str:
    """Get CORS configuration section"""
    return """# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000"""


def get_env_service_limits_config() -> str:
    """Get service limits configuration section"""
    return """# Service Limits
MAX_CONNECTIONS=100
REQUEST_TIMEOUT=30
WS_HEARTBEAT_INTERVAL=30
WS_CONNECTION_TIMEOUT=60"""


def get_env_feature_flags_config() -> str:
    """Get feature flags configuration section"""
    return """# Feature Flags
ENABLE_METRICS=true
ENABLE_CACHE=true
ENABLE_WEBSOCKET=true
ENABLE_OAUTH=false"""


def get_env_cache_config() -> str:
    """Get cache configuration section"""
    return """# Cache Configuration
CACHE_TTL=3600
CACHE_MAX_SIZE=1000"""


def combine_config_results(results) -> InstallerResult:
    """Combine multiple configuration results"""
    all_messages = []
    all_errors = []
    all_warnings = []
    overall_success = True
    
    for result in results:
        all_messages.extend(result.messages)
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        if not result.success:
            overall_success = False
    
    return InstallerResult(overall_success, all_messages, all_errors, all_warnings)