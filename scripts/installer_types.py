#!/usr/bin/env python3
"""
Type definitions for the Netra AI Platform installer modules.
Shared types across env_checker.py, dependency_installer.py, and config_setup.py.
"""

import platform
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple


class InstallerConfig(NamedTuple):
    """Configuration for installer modules"""
    os_type: str
    is_windows: bool
    is_mac: bool
    is_linux: bool
    project_root: Path
    venv_path: Path
    frontend_path: Path


class VersionRequirements(NamedTuple):
    """Version requirements for tools and services"""
    min_python_version: Tuple[int, int]
    min_node_version: str
    services: Dict[str, Dict[str, any]]


class InstallerResult(NamedTuple):
    """Result from installer operations"""
    success: bool
    messages: List[str]
    errors: List[str]
    warnings: List[str]


class ServiceConfig(NamedTuple):
    """Configuration for database/service installation"""
    name: str
    default_port: int
    test_port: Optional[int]
    min_version: str
    required: bool


def create_installer_config() -> InstallerConfig:
    """Create installer configuration"""
    os_type = platform.system().lower()
    project_root = Path.cwd()
    return InstallerConfig(
        os_type=os_type,
        is_windows=os_type == 'windows',
        is_mac=os_type == 'darwin', 
        is_linux=os_type == 'linux',
        project_root=project_root,
        venv_path=project_root / "venv",
        frontend_path=project_root / "frontend"
    )


def create_version_requirements() -> VersionRequirements:
    """Create version requirements configuration"""
    services = {
        'postgresql': {
            'default_port': 5432,
            'test_port': 5433,
            'min_version': '13.0'
        },
        'redis': {
            'default_port': 6379,
            'test_port': 6380,
            'min_version': '6.0'
        },
        'clickhouse': {
            'default_port': 9000,
            'http_port': 8123,
            'min_version': '21.0'
        }
    }
    
    return VersionRequirements(
        min_python_version=(3, 9),
        min_node_version="18.0.0",
        services=services
    )