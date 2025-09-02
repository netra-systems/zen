from shared.isolated_environment import get_env
"""
Diagnostic Helpers Module
Support functions for startup diagnostics - separated to maintain 450-line limit
"""

import asyncio
import os
import socket
from pathlib import Path
from typing import List, Optional

import psutil

from netra_backend.app.schemas.diagnostic_types import (
    DiagnosticConfiguration,
    DiagnosticError,
    DiagnosticSeverity,
    FixResult,
    ServiceType,
    StartupPhase,
    SystemState,
)


def is_port_in_use(port: int) -> bool:
    """Check if port is currently in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        return result == 0


def create_port_error(port: int) -> DiagnosticError:
    """Create diagnostic error for port conflict"""
    return DiagnosticError(
        service=ServiceType.SYSTEM,
        phase=StartupPhase.STARTUP,
        severity=DiagnosticSeverity.HIGH,
        message=f"Port {port} is already in use",
        suggested_fix=f"Kill process using port {port} or use alternative port",
        can_auto_fix=True
    )


def create_db_error() -> DiagnosticError:
    """Create database connection error"""
    return DiagnosticError(
        service=ServiceType.DATABASE,
        phase=StartupPhase.STARTUP,
        severity=DiagnosticSeverity.CRITICAL,
        message="Cannot connect to database",
        suggested_fix="Start PostgreSQL or check connection string",
        can_auto_fix=True
    )


def create_dependency_error(dep_type: str) -> DiagnosticError:
    """Create dependency error"""
    fix_cmd = "pip install -r requirements.txt" if dep_type == "Python" else "npm install"
    return DiagnosticError(
        service=ServiceType.SYSTEM,
        phase=StartupPhase.VALIDATION,
        severity=DiagnosticSeverity.HIGH,
        message=f"{dep_type} dependencies missing or invalid",
        suggested_fix=f"Run {fix_cmd}",
        can_auto_fix=True
    )


def create_env_error(var_name: str) -> DiagnosticError:
    """Create environment variable error"""
    return DiagnosticError(
        service=ServiceType.SYSTEM,
        phase=StartupPhase.VALIDATION,
        severity=DiagnosticSeverity.MEDIUM,
        message=f"Required environment variable {var_name} not set",
        suggested_fix=f"Set {var_name} in environment or .env file",
        can_auto_fix=False
    )


def create_migration_error() -> DiagnosticError:
    """Create migration error"""
    return DiagnosticError(
        service=ServiceType.DATABASE,
        phase=StartupPhase.STARTUP,
        severity=DiagnosticSeverity.HIGH,
        message="Database migrations pending",
        suggested_fix="Run alembic upgrade head",
        can_auto_fix=True
    )


def get_system_state() -> SystemState:
    """Capture current system state"""
    processes = []
    for i, p in enumerate(psutil.process_iter()):
        if i >= 10:
            break
        try:
            processes.append({"pid": p.pid, "name": p.name()})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return SystemState(
        processes=processes,
        ports=get_used_ports(),
        memory_usage=psutil.virtual_memory().percent,
        cpu_usage=psutil.cpu_percent(),
        disk_usage=psutil.disk_usage('/').percent if os.name != 'nt' else 0.0
    )


def get_used_ports() -> List[int]:
    """Get list of used ports"""
    used_ports = []
    for conn in psutil.net_connections():
        if conn.laddr and conn.laddr.port:
            used_ports.append(conn.laddr.port)
    return sorted(list(set(used_ports)))[:20]


def get_configuration() -> DiagnosticConfiguration:
    """Capture configuration snapshot"""
    env_vars = {k: v for k, v in os.environ.items() if not k.startswith('_')}
    config_files = {
        ".env": Path(".env").exists(),
        "requirements.txt": Path("requirements.txt").exists(),
        "package.json": Path("frontend/package.json").exists()
    }
    return DiagnosticConfiguration(
        environment_variables=env_vars,
        config_files=config_files,
        dependencies={}
    )


def create_fix_result(error_id: str, attempted: bool, successful: bool, message: str) -> FixResult:
    """Create fix result"""
    return FixResult(
        error_id=error_id,
        attempted=attempted,
        successful=successful,
        message=message
    )


async def run_command_async(cmd: List[str], timeout: int = 30, cwd: Optional[str] = None) -> str:
    """Run command asynchronously with timeout"""
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return stdout.decode() + stderr.decode()
    except asyncio.TimeoutError:
        process.kill()
        raise Exception("Command timed out")
