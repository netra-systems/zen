#!/usr/bin/env python3
"""
Service Installation for Netra AI Platform installer.
PostgreSQL, Redis, and ClickHouse installation guidance.
CRITICAL: All functions MUST be  <= 8 lines, file  <= 300 lines.
"""

import sys
from pathlib import Path
from typing import List

# Add scripts directory to path for imports
script_dir = Path(__file__).parent

from env_checker import check_command_exists, get_version_from_output, run_command
from installer_types import InstallerResult


def check_postgresql_installation() -> InstallerResult:
    """Check or provide PostgreSQL installation guidance"""
    if check_command_exists("psql"):
        version = get_version_from_output(
            run_command(["psql", "--version"]), r'(\d+\.\d+)'
        )
        return InstallerResult(True, [f"PostgreSQL {version} found"], [], [])
    
    return get_postgresql_install_instructions()


def get_postgresql_install_instructions() -> InstallerResult:
    """Provide PostgreSQL installation instructions"""
    import platform
    
    os_type = platform.system().lower()
    instructions = get_os_specific_pg_instructions(os_type)
    
    return InstallerResult(False, [], [], instructions)


def get_os_specific_pg_instructions(os_type: str) -> List[str]:
    """Get PostgreSQL installation instructions for specific OS"""
    if os_type == 'windows':
        return [
            "PostgreSQL not found",
            "Install from: https://www.postgresql.org/download/windows/",
            "Or via Chocolatey: choco install postgresql"
        ]
    elif os_type == 'darwin':
        return get_mac_pg_instructions()
    else:
        return [
            "Install PostgreSQL using your package manager:",
            "Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib",
            "RHEL/CentOS: sudo yum install postgresql-server postgresql-contrib"
        ]


def get_mac_pg_instructions() -> List[str]:
    """Get macOS PostgreSQL installation instructions"""
    if check_command_exists("brew"):
        run_command(["brew", "install", "postgresql@17"])
        run_command(["brew", "services", "start", "postgresql@17"])
        return ["Installing PostgreSQL via Homebrew..."]
    else:
        return [
            "Install Homebrew first:",
            '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
            "Then run: brew install postgresql@17"
        ]


def check_redis_installation() -> InstallerResult:
    """Check or provide Redis installation guidance"""
    if check_command_exists("redis-cli"):
        version = get_version_from_output(
            run_command(["redis-cli", "--version"]), r'(\d+\.\d+\.\d+)'
        )
        return InstallerResult(True, [f"Redis {version} found"], [], [])
    
    return get_redis_install_instructions()


def get_redis_install_instructions() -> InstallerResult:
    """Provide Redis installation instructions"""
    import platform
    
    os_type = platform.system().lower()
    instructions = get_os_specific_redis_instructions(os_type)
    
    return InstallerResult(False, [], [], instructions)


def get_os_specific_redis_instructions(os_type: str) -> List[str]:
    """Get Redis installation instructions for specific OS"""
    if os_type == 'windows':
        return [
            "Redis not found",
            "Enable WSL2: wsl --install",
            "Install in WSL: sudo apt update && sudo apt install redis-server",
            "Or use: https://github.com/microsoftarchive/redis/releases"
        ]
    elif os_type == 'darwin':
        return get_mac_redis_instructions()
    else:
        return [
            "Install Redis using your package manager:",
            "Ubuntu/Debian: sudo apt-get install redis-server",
            "RHEL/CentOS: sudo yum install redis"
        ]


def get_mac_redis_instructions() -> List[str]:
    """Get macOS Redis installation instructions"""
    if check_command_exists("brew"):
        run_command(["brew", "install", "redis"])
        run_command(["brew", "services", "start", "redis"])
        return ["Installing Redis via Homebrew..."]
    else:
        return ["Install Homebrew first, then run: brew install redis"]


def check_clickhouse_installation() -> InstallerResult:
    """Check ClickHouse installation (optional)"""
    if check_command_exists("clickhouse-client"):
        return InstallerResult(True, ["ClickHouse found"], [], [])
    
    messages = [
        "ClickHouse not found (optional for development)",
        "To install: https://clickhouse.com/docs/en/install"
    ]
    return InstallerResult(True, messages, [], [])


def install_all_services() -> InstallerResult:
    """Install or check all external services"""
    service_results = [
        check_postgresql_installation(),
        check_redis_installation(),
        check_clickhouse_installation()
    ]
    
    return combine_service_results(service_results)


def combine_service_results(results: List[InstallerResult]) -> InstallerResult:
    """Combine multiple service installation results"""
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