#!/usr/bin/env python3
"""
Dependency Installer for Netra AI Platform.
Handles Python virtual environment, packages, and external services installation.
CRITICAL: All functions MUST be ≤8 lines, file ≤300 lines.
"""

import sys
import subprocess
import shutil
from typing import List, Optional
from pathlib import Path

from installer_types import InstallerConfig, InstallerResult
from env_checker import run_command, check_command_exists, get_version_from_output


class DependencyInstaller:
    """Installs Python packages and external services"""
    
    def __init__(self, config: InstallerConfig):
        self.config = config


def create_virtual_environment(config: InstallerConfig) -> InstallerResult:
    """Create Python virtual environment"""
    if config.venv_path.exists():
        message = "Virtual environment already exists"
        return InstallerResult(True, [message], [], [])
    
    return setup_new_virtual_environment(config)


def setup_new_virtual_environment(config: InstallerConfig) -> InstallerResult:
    """Set up new Python virtual environment"""
    result = run_command([sys.executable, "-m", "venv", str(config.venv_path)])
    
    if result is not None or not config.venv_path.exists():
        return InstallerResult(True, ["Virtual environment created"], [], [])
    
    return InstallerResult(False, [], ["Failed to create virtual environment"], [])


def get_venv_paths(config: InstallerConfig) -> tuple[Path, Path]:
    """Get pip and python paths for virtual environment"""
    if config.is_windows:
        pip_path = config.venv_path / "Scripts" / "pip.exe"
        python_path = config.venv_path / "Scripts" / "python.exe"
    else:
        pip_path = config.venv_path / "bin" / "pip"
        python_path = config.venv_path / "bin" / "python"
    
    return pip_path, python_path


def upgrade_pip(config: InstallerConfig) -> InstallerResult:
    """Upgrade pip in virtual environment"""
    _, python_path = get_venv_paths(config)
    
    result = run_command([
        str(python_path), "-m", "pip", "install", "--upgrade", "pip"
    ])
    
    if result is not None:
        return InstallerResult(True, ["pip upgraded"], [], [])
    
    return InstallerResult(True, [], [], ["pip upgrade failed"])


def install_requirements_file(config: InstallerConfig) -> InstallerResult:
    """Install Python dependencies from requirements.txt"""
    pip_path, _ = get_venv_paths(config)
    requirements_file = config.project_root / "requirements.txt"
    
    if not requirements_file.exists():
        return InstallerResult(False, [], ["requirements.txt not found"], [])
    
    return install_from_requirements(pip_path, requirements_file)


def install_from_requirements(pip_path: Path, requirements_file: Path) -> InstallerResult:
    """Install packages from requirements file"""
    result = run_command([
        str(pip_path), "install", "-r", str(requirements_file)
    ])
    
    if result is not None:
        return InstallerResult(True, ["Python dependencies installed"], [], [])
    
    return install_essential_packages_fallback(pip_path)


def install_essential_packages_fallback(pip_path: Path) -> InstallerResult:
    """Install essential packages individually if bulk install fails"""
    essential_packages = [
        "fastapi", "uvicorn", "sqlalchemy", "aiosqlite", "asyncpg",
        "redis", "pydantic", "python-jose", "passlib", "bcrypt",
        "python-multipart", "httpx", "pytest", "pytest-asyncio"
    ]
    
    return install_package_list(pip_path, essential_packages)


def install_package_list(pip_path: Path, packages: List[str]) -> InstallerResult:
    """Install list of packages individually"""
    installed = []
    failed = []
    
    for package in packages:
        result = run_command([str(pip_path), "install", package])
        if result is not None:
            installed.append(package)
        else:
            failed.append(package)
    
    messages = [f"Installed {len(installed)} essential packages"]
    warnings = [f"Failed to install: {', '.join(failed)}"] if failed else []
    return InstallerResult(True, messages, [], warnings)


def setup_python_environment(config: InstallerConfig) -> InstallerResult:
    """Complete Python environment setup"""
    results = [
        create_virtual_environment(config),
        upgrade_pip(config),
        install_requirements_file(config)
    ]
    
    return combine_dependency_results(results)


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
        run_command(["brew", "install", "postgresql@14"])
        run_command(["brew", "services", "start", "postgresql@14"])
        return ["Installing PostgreSQL via Homebrew..."]
    else:
        return [
            "Install Homebrew first:",
            '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
            "Then run: brew install postgresql@14"
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


def install_frontend_dependencies(config: InstallerConfig) -> InstallerResult:
    """Install frontend NPM dependencies"""
    if not config.frontend_path.exists():
        return InstallerResult(False, [], ["Frontend directory not found"], [])
    
    return setup_npm_packages(config)


def setup_npm_packages(config: InstallerConfig) -> InstallerResult:
    """Set up NPM packages and build frontend"""
    package_json = config.frontend_path / "package.json"
    if not package_json.exists():
        return InstallerResult(False, [], ["package.json not found"], [])
    
    clean_node_modules(config)
    return install_and_build_frontend(config)


def clean_node_modules(config: InstallerConfig) -> None:
    """Clean existing node_modules directory"""
    node_modules = config.frontend_path / "node_modules"
    
    if node_modules.exists():
        if config.is_windows:
            run_command(["rmdir", "/s", "/q", str(node_modules)])
        else:
            run_command(["rm", "-rf", str(node_modules)])


def install_and_build_frontend(config: InstallerConfig) -> InstallerResult:
    """Install NPM packages and build frontend"""
    # Install dependencies
    result = run_command(["npm", "install"], cwd=config.frontend_path)
    
    if result is None and not (config.frontend_path / "node_modules").exists():
        return InstallerResult(False, [], ["Failed to install frontend dependencies"], [])
    
    return build_frontend(config)


def build_frontend(config: InstallerConfig) -> InstallerResult:
    """Build frontend application"""
    build_result = run_command(["npm", "run", "build"], cwd=config.frontend_path)
    
    messages = ["Frontend dependencies installed"]
    warnings = []
    
    if build_result is None:
        warnings.append("Frontend build failed (can rebuild later)")
    else:
        messages.append("Frontend built successfully")
    
    return InstallerResult(True, messages, [], warnings)


def install_all_services() -> InstallerResult:
    """Install or check all external services"""
    service_results = [
        check_postgresql_installation(),
        check_redis_installation(),
        check_clickhouse_installation()
    ]
    
    return combine_dependency_results(service_results)


def combine_dependency_results(results: List[InstallerResult]) -> InstallerResult:
    """Combine multiple installer results"""
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


def run_complete_dependency_installation(config: InstallerConfig) -> InstallerResult:
    """Run complete dependency installation process"""
    installation_results = [
        setup_python_environment(config),
        install_all_services(),
        install_frontend_dependencies(config)
    ]
    
    return combine_dependency_results(installation_results)