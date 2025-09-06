"""
Container Runtime Detection and Abstraction Layer

Provides automatic detection of available container runtimes (Docker/Podman)
and abstracts their differences for unified usage.

Business Value: Enables testing without Docker Desktop licensing requirements
while maintaining full compatibility with existing infrastructure.
"""

import subprocess
import os
import json
import logging
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import shutil
import platform

logger = logging.getLogger(__name__)


class ContainerRuntime(Enum):
    """Available container runtime engines."""
    DOCKER = "docker"
    PODMAN = "podman"
    NONE = "none"


@dataclass
class RuntimeInfo:
    """Information about a detected container runtime."""
    runtime: ContainerRuntime
    version: str
    compose_command: str
    socket_path: Optional[str] = None
    is_rootless: bool = False
    supports_compose: bool = False
    binary_path: Optional[str] = None
    

class ContainerRuntimeDetector:
    """Detects and provides information about available container runtimes."""
    
    def __init__(self):
        self._runtime_info: Optional[RuntimeInfo] = None
        self._cached = False
    
    def detect_runtime(self) -> RuntimeInfo:
        """
        Detect available container runtime.
        On Windows: Always use Docker (default).
        On other platforms: Docker only.
        """
        if self._cached and self._runtime_info:
            return self._runtime_info
        
        # Always use Docker - no Podman support
        docker_info = self._check_docker()
        if docker_info:
            self._runtime_info = docker_info
            self._cached = True
            if platform.system() == 'Windows':
                logger.info("Using Docker runtime on Windows (default)")
            else:
                logger.info("Using Docker runtime")
            return docker_info
        
        # No runtime available
        self._runtime_info = RuntimeInfo(
            runtime=ContainerRuntime.NONE,
            version="0.0.0",
            compose_command=""
        )
        self._cached = True
        logger.error("Docker is not available. Please install Docker Desktop.")
        return self._runtime_info
    
    def _check_docker(self) -> Optional[RuntimeInfo]:
        """Check if Docker is available and get its info."""
        docker_binary = shutil.which("docker")
        if not docker_binary:
            logger.debug("Docker binary not found in PATH")
            return None
        
        try:
            # Check Docker version
            version_result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if version_result.returncode != 0:
                logger.debug("Docker version check failed")
                return None
            
            version = self._parse_version(version_result.stdout, "Docker")
            
            # Check if Docker daemon is running
            info_result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if info_result.returncode != 0:
                logger.warning("Docker daemon is not running or not accessible")
                return None
            
            # Check for docker-compose or docker compose
            compose_command = self._detect_compose_command("docker")
            
            # Get Docker socket path
            socket_path = self._get_docker_socket()
            
            return RuntimeInfo(
                runtime=ContainerRuntime.DOCKER,
                version=version,
                compose_command=compose_command,
                socket_path=socket_path,
                is_rootless=self._is_docker_rootless(info_result.stdout),
                supports_compose=bool(compose_command),
                binary_path=docker_binary
            )
            
        except subprocess.TimeoutExpired:
            logger.warning("Docker check timed out")
            return None
        except Exception as e:
            logger.debug(f"Error checking Docker: {e}")
            return None
    
    def _check_podman(self) -> Optional[RuntimeInfo]:
        """Check if Podman is available and get its info."""
        podman_binary = shutil.which("podman")
        if not podman_binary:
            logger.debug("Podman binary not found in PATH")
            return None
        
        try:
            # Check Podman version
            version_result = subprocess.run(
                ["podman", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if version_result.returncode != 0:
                logger.debug("Podman version check failed")
                return None
            
            version = self._parse_version(version_result.stdout, "podman")
            
            # Check if Podman is functional
            info_result = subprocess.run(
                ["podman", "info", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if info_result.returncode != 0:
                logger.warning("Podman is not functional or not configured")
                return None
            
            info_data = json.loads(info_result.stdout)
            
            # Check for podman-compose
            compose_command = self._detect_compose_command("podman")
            
            # Get Podman socket path
            socket_path = self._get_podman_socket(info_data)
            
            return RuntimeInfo(
                runtime=ContainerRuntime.PODMAN,
                version=version,
                compose_command=compose_command,
                socket_path=socket_path,
                is_rootless=info_data.get("host", {}).get("rootless", False),
                supports_compose=bool(compose_command),
                binary_path=podman_binary
            )
            
        except subprocess.TimeoutExpired:
            logger.warning("Podman check timed out")
            return None
        except json.JSONDecodeError:
            logger.warning("Failed to parse Podman info output")
            return None
        except Exception as e:
            logger.debug(f"Error checking Podman: {e}")
            return None
    
    def _detect_compose_command(self, runtime: str) -> str:
        """Detect the appropriate compose command for the runtime."""
        if runtime == "docker":
            # Try docker compose (v2) first
            try:
                result = subprocess.run(
                    ["docker", "compose", "version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return "docker compose"
            except:
                pass
            
            # Try docker-compose (v1)
            if shutil.which("docker-compose"):
                return "docker-compose"
        
        elif runtime == "podman":
            # Try podman-compose
            if shutil.which("podman-compose"):
                return "podman-compose"
            
            # Try podman compose (if available in newer versions)
            try:
                result = subprocess.run(
                    ["podman", "compose", "version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return "podman compose"
            except:
                pass
        
        return ""
    
    def _parse_version(self, version_output: str, tool: str) -> str:
        """Parse version from command output."""
        # Common patterns for version extraction
        import re
        
        # Docker: "Docker version 24.0.5, build 1234567"
        # Podman: "podman version 4.5.0"
        pattern = rf"{tool}.*?(\d+\.\d+\.\d+)"
        match = re.search(pattern, version_output, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback to full output
        return version_output.strip()
    
    def _get_docker_socket(self) -> Optional[str]:
        """Get Docker daemon socket path."""
        if platform.system() == "Windows":
            # Windows named pipe
            return r"\\.\pipe\docker_engine"
        else:
            # Unix socket
            socket_paths = [
                "/var/run/docker.sock",
                os.path.expanduser("~/.docker/run/docker.sock"),  # Rootless
                "/run/user/{}/docker.sock".format(os.getuid()) if os.name != 'nt' else None
            ]
            for path in filter(None, socket_paths):
                if os.path.exists(path):
                    return path
        return None
    
    def _get_podman_socket(self, info_data: Dict) -> Optional[str]:
        """Get Podman socket path from info."""
        # Try to get from info data
        remote_socket = info_data.get("host", {}).get("remoteSocket", {})
        if remote_socket and remote_socket.get("path"):
            return remote_socket["path"]
        
        if platform.system() == "Windows":
            # Windows Podman socket locations
            socket_paths = [
                r"\\.\pipe\podman-machine-default",
                os.path.expanduser(r"~\.local\share\containers\podman\machine\podman.sock")
            ]
        else:
            # Unix socket paths
            socket_paths = [
                "/run/podman/podman.sock",
                "/var/run/podman/podman.sock",
                os.path.expanduser("~/.local/share/containers/podman/machine/podman.sock"),
                f"/run/user/{os.getuid()}/podman/podman.sock" if os.name != 'nt' else None
            ]
        
        for path in filter(None, socket_paths):
            if path and os.path.exists(path):
                return path
        
        return None
    
    def _is_docker_rootless(self, info_output: str) -> bool:
        """Check if Docker is running in rootless mode."""
        return "rootless" in info_output.lower()
    
    def get_runtime(self) -> ContainerRuntime:
        """Get the detected runtime type."""
        info = self.detect_runtime()
        return info.runtime
    
    def get_compose_command(self) -> List[str]:
        """Get the compose command as a list for subprocess."""
        info = self.detect_runtime()
        if not info.compose_command:
            raise RuntimeError(f"No compose tool available for {info.runtime.value}")
        return info.compose_command.split()
    
    def is_available(self) -> bool:
        """Check if any container runtime is available."""
        info = self.detect_runtime()
        return info.runtime != ContainerRuntime.NONE
    
    def get_runtime_command(self) -> List[str]:
        """Get the base runtime command."""
        info = self.detect_runtime()
        if info.runtime == ContainerRuntime.DOCKER:
            return ["docker"]
        elif info.runtime == ContainerRuntime.PODMAN:
            return ["podman"]
        else:
            raise RuntimeError("No container runtime available")


# Global singleton instance
_detector = ContainerRuntimeDetector()


def detect_container_runtime() -> RuntimeInfo:
    """Detect and return information about available container runtime."""
    return _detector.detect_runtime()


def get_compose_command() -> List[str]:
    """Get the appropriate compose command for the detected runtime."""
    return _detector.get_compose_command()


def get_runtime_type() -> ContainerRuntime:
    """Get the type of detected container runtime."""
    return _detector.get_runtime()


def is_podman() -> bool:
    """Check if Podman is the active runtime."""
    return _detector.get_runtime() == ContainerRuntime.PODMAN


def is_docker() -> bool:
    """Check if Docker is the active runtime."""
    return _detector.get_runtime() == ContainerRuntime.DOCKER


def get_runtime_command() -> List[str]:
    """Get the base container runtime command."""
    return _detector.get_runtime_command()