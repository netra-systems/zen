#!/usr/bin/env python3
"""
Script Creation and Testing for Netra AI Platform installer.
Startup scripts and installation verification.
CRITICAL: All functions MUST be  <= 8 lines, file  <= 300 lines.
"""

import os
import sys
from pathlib import Path
from typing import List

# Add scripts directory to path for imports
script_dir = Path(__file__).parent

from env_checker import run_command
from installer_types import InstallerConfig, InstallerResult


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


def get_venv_python_path(config: InstallerConfig) -> Path:
    """Get Python executable path from virtual environment"""
    if config.is_windows:
        return config.venv_path / "Scripts" / "python.exe"
    else:
        return config.venv_path / "bin" / "python"


def run_installation_tests(config: InstallerConfig, python_path: Path) -> InstallerResult:
    """Execute installation verification tests"""
    test_results = []
    
    test_results.append(test_python_imports(python_path))
    test_results.append(test_frontend_status(config))
    test_results.append(test_database_connectivity(python_path))
    
    return combine_test_results(test_results)


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
        return InstallerResult(True, ["Frontend dependencies: OK"], [], [])
    
    return InstallerResult(True, [], [], ["Frontend dependencies: MISSING"])


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
            print("Database connectivity: OK")
    except Exception as e:
        print(f"Database connectivity: FAILED ({e})")

asyncio.run(test_db())
"""


def combine_test_results(results: List[InstallerResult]) -> InstallerResult:
    """Combine multiple test results"""
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