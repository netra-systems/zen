#!/usr/bin/env python3
"""
Environment Checker for Netra AI Platform installer.
Validates prerequisites: Python, Node.js, Git versions and system requirements.
CRITICAL: All functions MUST be  <= 8 lines, file  <= 300 lines.
"""

import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Add scripts directory to path for imports
script_dir = Path(__file__).parent

from installer_types import InstallerConfig, InstallerResult, VersionRequirements


class EnvironmentChecker:
    """Validates system prerequisites for development environment"""
    
    def __init__(self, config: InstallerConfig, requirements: VersionRequirements):
        self.config = config
        self.requirements = requirements
        self.errors: List[str] = []
        self.warnings: List[str] = []


def check_command_exists(command: str) -> bool:
    """Check if a command exists in the system PATH"""
    return shutil.which(command) is not None


def run_command(command: List[str], cwd: Optional[Path] = None, shell: bool = False) -> Optional[str]:
    """Run a command and return output safely"""
    try:
        cmd = ' '.join(command) if shell else command
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, cwd=cwd, shell=shell
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


def get_version_from_output(output: str, pattern: Optional[str] = None) -> Optional[str]:
    """Extract version from command output"""
    if not output:
        return None
    if pattern:
        match = re.search(pattern, output)
        return match.group(1) if match else None
    return output.split()[0] if output else None


def compare_versions(version1: str, version2: str) -> int:
    """Compare two version strings (-1: v1<v2, 0: equal, 1: v1>v2)"""
    def normalize_version(v: str) -> List[int]:
        return [int(x) for x in re.sub(r'[^0-9.]', '', v).split('.')]
    
    try:
        v1_parts = normalize_version(version1)
        v2_parts = normalize_version(version2)
        max_len = max(len(v1_parts), len(v2_parts))
        
        for i in range(max_len):
            v1_part = v1_parts[i] if i < len(v1_parts) else 0
            v2_part = v2_parts[i] if i < len(v2_parts) else 0
            if v1_part < v2_part:
                return -1
            elif v1_part > v2_part:
                return 1
        return 0
    except Exception:
        return 0


def check_port_available(port: int) -> bool:
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            return True
    except Exception:
        return False


def find_free_port(start_port: int, max_attempts: int = 10) -> Optional[int]:
    """Find a free port starting from start_port"""
    for i in range(max_attempts):
        port = start_port + i
        if check_port_available(port):
            return port
    return None


def check_python_version(requirements: VersionRequirements) -> InstallerResult:
    """Check Python installation and version"""
    version_info = sys.version_info
    min_version = requirements.min_python_version
    
    if version_info >= min_version:
        success_msg = f"Python {version_info.major}.{version_info.minor}.{version_info.micro} found"
        return InstallerResult(True, [success_msg], [], [])
    
    error_msg = f"Python {min_version[0]}.{min_version[1]}+ required, found {version_info.major}.{version_info.minor}"
    return InstallerResult(False, [], [error_msg], [])


def check_node_installation(requirements: VersionRequirements) -> InstallerResult:
    """Check Node.js installation and version"""
    if not check_command_exists("node"):
        error_msg = "Node.js not found. Please install Node.js 18+ from https://nodejs.org/"
        return InstallerResult(False, [], [error_msg], [])
    
    return check_node_version(requirements)


def check_node_version(requirements: VersionRequirements) -> InstallerResult:
    """Validate Node.js version meets requirements"""
    output = run_command(["node", "-v"])
    node_version = get_version_from_output(output, r'v?(\d+\.\d+\.\d+)')
    
    if not node_version:
        warning_msg = "Could not determine Node.js version"
        return InstallerResult(True, [], [], [warning_msg])
    
    if compare_versions(node_version, requirements.min_node_version) >= 0:
        success_msg = f"Node.js {node_version} found"
        return InstallerResult(True, [success_msg], [], [])
    
    error_msg = f"Node.js {requirements.min_node_version}+ required, found {node_version}"
    return InstallerResult(False, [], [error_msg], [])


def check_git_installation() -> InstallerResult:
    """Check Git installation"""
    if not check_command_exists("git"):
        error_msg = "Git not found. Please install Git from https://git-scm.com/"
        return InstallerResult(False, [], [error_msg], [])
    
    return get_git_version()


def get_git_version() -> InstallerResult:
    """Get Git version information"""
    output = run_command(["git", "--version"])
    git_version = get_version_from_output(output, r'(\d+\.\d+\.\d+)')
    
    success_msg = f"Git {git_version or 'unknown version'} found"
    return InstallerResult(True, [success_msg], [], [])


def check_system_prerequisites(config: InstallerConfig, requirements: VersionRequirements) -> InstallerResult:
    """Check all system prerequisites"""
    results = []
    results.append(check_python_version(requirements))
    results.append(check_node_installation(requirements))
    results.append(check_git_installation())
    
    return combine_results(results)


def combine_results(results: List[InstallerResult]) -> InstallerResult:
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


def validate_project_structure(config: InstallerConfig) -> InstallerResult:
    """Validate project structure and required files"""
    required_files = [
        config.project_root / "requirements.txt",
        config.frontend_path / "package.json"
    ]
    
    return check_required_files(required_files)


def check_required_files(file_paths: List[Path]) -> InstallerResult:
    """Check that required files exist"""
    missing_files = []
    found_files = []
    
    for file_path in file_paths:
        if file_path.exists():
            found_files.append(f"Found {file_path.name}")
        else:
            missing_files.append(f"Missing {file_path}")
    
    if missing_files:
        return InstallerResult(False, found_files, missing_files, [])
    return InstallerResult(True, found_files, [], [])


def check_system_resources() -> InstallerResult:
    """Check system has adequate resources"""
    import shutil
    
    try:
        disk_usage = shutil.disk_usage(".")
        free_gb = disk_usage.free / (1024**3)
        
        if free_gb < 1.0:
            warning_msg = f"Low disk space: {free_gb:.1f}GB free"
            return InstallerResult(True, [], [], [warning_msg])
        
        success_msg = f"Disk space adequate: {free_gb:.1f}GB free"
        return InstallerResult(True, [success_msg], [], [])
    except Exception:
        return InstallerResult(True, [], [], ["Could not check disk space"])


def get_service_ports_status(requirements: VersionRequirements) -> InstallerResult:
    """Check availability of service ports"""
    messages = []
    warnings = []
    
    for service_name, service_config in requirements.services.items():
        port = service_config['default_port']
        if check_port_available(port):
            messages.append(f"Port {port} ({service_name}) available")
        else:
            warnings.append(f"Port {port} ({service_name}) in use")
    
    return InstallerResult(True, messages, [], warnings)


def run_full_environment_check(config: InstallerConfig, requirements: VersionRequirements) -> InstallerResult:
    """Run comprehensive environment check"""
    check_results = [
        check_system_prerequisites(config, requirements),
        validate_project_structure(config),
        check_system_resources(),
        get_service_ports_status(requirements)
    ]
    
    return combine_results(check_results)