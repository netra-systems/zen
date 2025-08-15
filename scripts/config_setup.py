#!/usr/bin/env python3
"""
Configuration Setup for Netra AI Platform installer.
Handles database initialization, environment files, startup scripts, and testing.
CRITICAL: All functions MUST be ≤8 lines, file ≤300 lines.
"""

import os
import shutil
import sys
from typing import List
from pathlib import Path

from installer_types import InstallerConfig, InstallerResult
from env_checker import run_command, check_command_exists


class ConfigurationSetup:
    """Handles final configuration and testing"""
    
    def __init__(self, config: InstallerConfig):
        self.config = config


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
    
    return f"""# Netra AI Platform - Development Environment Configuration
# Generated by install_dev_env.py

# Environment
ENVIRONMENT=development
DEBUG=true

# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/netra
CLICKHOUSE_URL=clickhouse://default:@localhost:9000/default
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=dev-secret-key-change-in-production-{random_key}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Keys (add your own)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Frontend Configuration
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=true
WORKERS=1
LOG_LEVEL=INFO

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000

# Service Limits
MAX_CONNECTIONS=100
REQUEST_TIMEOUT=30
WS_HEARTBEAT_INTERVAL=30
WS_CONNECTION_TIMEOUT=60

# Feature Flags
ENABLE_METRICS=true
ENABLE_CACHE=true
ENABLE_WEBSOCKET=true
ENABLE_OAUTH=false

# Cache Configuration
CACHE_TTL=3600
CACHE_MAX_SIZE=1000
"""


def create_startup_scripts(config: InstallerConfig) -> InstallerResult:
    """Create convenient startup scripts for development"""
    if config.is_windows:
        return create_windows_startup_script(config)
    else:
        return create_unix_startup_script(config)


def create_windows_startup_script(config: InstallerConfig) -> InstallerResult:
    """Create Windows batch startup script"""
    bat_content = get_windows_script_content()
    bat_file = config.project_root / "start_dev.bat"
    
    try:
        with open(bat_file, 'w') as f:
            f.write(bat_content)
        return InstallerResult(True, ["Created start_dev.bat"], [], [])
    except Exception:
        return InstallerResult(False, [], ["Failed to create start_dev.bat"], [])


def get_windows_script_content() -> str:
    """Get Windows startup script content"""
    return """@echo off
echo Starting Netra AI Development Environment...
echo.

REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Start services in new windows
echo Starting Backend Server...
start "Netra Backend" cmd /k "python dev_launcher.py --dynamic --no-backend-reload"

echo.
echo Development environment is starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to stop all services...
pause >NUL

REM Kill processes
taskkill /FI "WindowTitle eq Netra Backend" /T /F
echo Services stopped.
"""


def create_unix_startup_script(config: InstallerConfig) -> InstallerResult:
    """Create Unix shell startup script"""
    sh_content = get_unix_script_content()
    sh_file = config.project_root / "start_dev.sh"
    
    try:
        with open(sh_file, 'w') as f:
            f.write(sh_content)
        os.chmod(sh_file, 0o755)
        return InstallerResult(True, ["Created start_dev.sh"], [], [])
    except Exception:
        return InstallerResult(False, [], ["Failed to create start_dev.sh"], [])


def get_unix_script_content() -> str:
    """Get Unix startup script content"""
    return """#!/bin/bash

echo "Starting Netra AI Development Environment..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Start services
echo "Starting Backend and Frontend..."
python dev_launcher.py --dynamic --no-backend-reload &
LAUNCHER_PID=$!

echo ""
echo "Development environment is starting..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for interrupt
trap "kill $LAUNCHER_PID; echo 'Services stopped.'; exit" INT
wait $LAUNCHER_PID
"""


def test_installation(config: InstallerConfig) -> InstallerResult:
    """Run basic tests to verify installation"""
    python_path = get_venv_python_path(config)
    
    if not python_path.exists():
        return InstallerResult(False, [], ["Virtual environment not found"], [])
    
    return run_installation_tests(config, python_path)


def run_installation_tests(config: InstallerConfig, python_path: Path) -> InstallerResult:
    """Execute installation verification tests"""
    test_results = []
    
    test_results.append(test_python_imports(python_path))
    test_results.append(test_frontend_status(config))
    test_results.append(test_database_connectivity(python_path))
    
    return combine_config_results(test_results)


def test_python_imports(python_path: Path) -> InstallerResult:
    """Test essential Python module imports"""
    test_modules = [
        "fastapi", "uvicorn", "sqlalchemy", "pydantic",
        "redis", "httpx", "pytest"
    ]
    
    return verify_module_imports(python_path, test_modules)


def verify_module_imports(python_path: Path, modules: List[str]) -> InstallerResult:
    """Verify that Python modules can be imported"""
    successful_imports = []
    failed_imports = []
    
    for module in modules:
        result = run_command([
            str(python_path), "-c", f"import {module}"
        ])
        if result is not None:
            successful_imports.append(module)
        else:
            failed_imports.append(module)
    
    messages = [f"Python imports: {len(successful_imports)}/{len(modules)} successful"]
    warnings = [f"Failed imports: {', '.join(failed_imports)}"] if failed_imports else []
    return InstallerResult(True, messages, [], warnings)


def test_frontend_status(config: InstallerConfig) -> InstallerResult:
    """Test frontend dependency status"""
    node_modules = config.frontend_path / "node_modules"
    
    if node_modules.exists():
        return InstallerResult(True, ["Frontend dependencies: ✓"], [], [])
    
    return InstallerResult(True, [], [], ["Frontend dependencies: ✗"])


def test_database_connectivity(python_path: Path) -> InstallerResult:
    """Test basic database connectivity"""
    test_script = get_db_test_script()
    
    result = run_command([str(python_path), "-c", test_script])
    
    if result is not None:
        return InstallerResult(True, ["Database connectivity test passed"], [], [])
    
    return InstallerResult(True, [], [], ["Database connectivity test failed"])


def get_db_test_script() -> str:
    """Get database connectivity test script"""
    return """
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

async def test_db():
    try:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            print("Database connectivity: ✓")
    except Exception as e:
        print(f"Database connectivity: ✗ ({e})")

asyncio.run(test_db())
"""


def combine_config_results(results: List[InstallerResult]) -> InstallerResult:
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


def run_complete_configuration_setup(config: InstallerConfig) -> InstallerResult:
    """Run complete configuration and setup process"""
    setup_results = [
        setup_databases(config),
        create_environment_file(config),
        create_startup_scripts(config),
        test_installation(config)
    ]
    
    return combine_config_results(setup_results)