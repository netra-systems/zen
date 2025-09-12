#!/usr/bin/env python3
"""
Container Build Script - Supports both Docker and Podman
========================================================
This script provides a unified interface for building containers with either Docker or Podman.
Automatically detects which container runtime is available and uses it appropriately.

Business Value: Enables flexibility in container runtime choice, avoiding vendor lock-in
and supporting environments where Docker may not be available (e.g., RHEL/Fedora systems).
"""

import subprocess
import sys
import logging
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


class ContainerRuntime(Enum):
    """Supported container runtimes."""
    DOCKER = "docker"
    PODMAN = "podman"
    DOCKER_COMPOSE = "docker-compose"
    PODMAN_COMPOSE = "podman-compose"


class ContainerBuilder:
    """
    Unified container builder supporting both Docker and Podman.
    
    Automatically detects available runtime and provides consistent interface.
    """
    
    def __init__(self, runtime: Optional[ContainerRuntime] = None):
        """
        Initialize container builder.
        
        Args:
            runtime: Force specific runtime, or None for auto-detect
        """
        self.runtime, self.compose_runtime = self._detect_runtime(runtime)
        self.project_root = PROJECT_ROOT
        logger.info(f"Using container runtime: {self.runtime.value}")
        logger.info(f"Using compose tool: {self.compose_runtime.value}")
    
    def _detect_runtime(self, preferred: Optional[ContainerRuntime] = None) -> Tuple[ContainerRuntime, ContainerRuntime]:
        """
        Detect available container runtime.
        
        Returns:
            Tuple of (container_runtime, compose_runtime)
        """
        # Check if user specified a runtime
        if preferred:
            if preferred in [ContainerRuntime.DOCKER, ContainerRuntime.PODMAN]:
                runtime = preferred
                compose = ContainerRuntime.DOCKER_COMPOSE if runtime == ContainerRuntime.DOCKER else ContainerRuntime.PODMAN_COMPOSE
                
                # Verify it's actually available
                if self._is_command_available(runtime.value):
                    if self._is_command_available(compose.value):
                        return runtime, compose
                    else:
                        logger.warning(f"{compose.value} not found, trying alternatives...")
            
        # Auto-detect: Try Docker first (most common)
        if self._is_command_available("docker"):
            # Check for docker-compose or docker compose
            if self._is_command_available("docker-compose"):
                return ContainerRuntime.DOCKER, ContainerRuntime.DOCKER_COMPOSE
            elif self._check_docker_compose_plugin():
                # Docker Compose v2 as plugin
                return ContainerRuntime.DOCKER, ContainerRuntime.DOCKER_COMPOSE
        
        # Try Podman
        if self._is_command_available("podman"):
            # Check for podman-compose
            if self._is_command_available("podman-compose"):
                return ContainerRuntime.PODMAN, ContainerRuntime.PODMAN_COMPOSE
            else:
                logger.warning("podman-compose not found. Install with: pip install podman-compose")
                # Podman can use docker-compose with some limitations
                if self._is_command_available("docker-compose"):
                    logger.info("Using docker-compose with Podman backend")
                    return ContainerRuntime.PODMAN, ContainerRuntime.DOCKER_COMPOSE
        
        raise RuntimeError(
            "No container runtime found! Please install Docker or Podman.\n"
            "Docker: https://docs.docker.com/get-docker/\n"
            "Podman: https://podman.io/getting-started/installation"
        )
    
    def _is_command_available(self, command: str) -> bool:
        """Check if a command is available in PATH."""
        return shutil.which(command) is not None
    
    def _check_docker_compose_plugin(self) -> bool:
        """Check if Docker Compose v2 is available as a plugin."""
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            return False
    
    def _get_compose_command(self) -> List[str]:
        """Get the appropriate compose command based on runtime."""
        if self.compose_runtime == ContainerRuntime.DOCKER_COMPOSE:
            # Check if it's docker-compose standalone or docker compose plugin
            if self._is_command_available("docker-compose"):
                return ["docker-compose"]
            else:
                return ["docker", "compose"]
        elif self.compose_runtime == ContainerRuntime.PODMAN_COMPOSE:
            return ["podman-compose"]
        else:
            raise RuntimeError(f"Unknown compose runtime: {self.compose_runtime}")
    
    def build_with_compose(
        self,
        service_name: str,
        compose_file: str = "docker-compose.test.yml",
        no_cache: bool = False,
        pull: Optional[str] = None,
        build_args: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Build container using compose file.
        
        Args:
            service_name: Name of service to build
            compose_file: Path to compose file
            no_cache: Build without cache
            pull: Pull policy ('always', 'never', 'missing')
            build_args: Build arguments to pass
            
        Returns:
            True if build succeeded
        """
        compose_path = self.project_root / compose_file
        if not compose_path.exists():
            logger.error(f"Compose file not found: {compose_path}")
            return False
        
        # Build command
        cmd = self._get_compose_command()
        cmd.extend(["-f", str(compose_path), "build"])
        
        # Add options
        if no_cache:
            cmd.append("--no-cache")
        
        # Handle pull policy
        if pull:
            if self.compose_runtime == ContainerRuntime.PODMAN_COMPOSE:
                # podman-compose has different flags
                if pull == "always":
                    cmd.extend(["--pull-always"])
                elif pull == "missing":
                    cmd.extend(["--pull"])
                # Note: podman-compose doesn't have --pull=never equivalent
                # It defaults to not pulling if image exists locally
            else:
                # Docker Compose uses --pull flag
                if pull == "never":
                    cmd.extend(["--pull=never"])
                elif pull == "always":
                    cmd.extend(["--pull"])
                # 'missing' is default for Docker Compose
        
        # Add build args
        if build_args:
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])
        
        # Add service name
        cmd.append(service_name)
        
        logger.info(f"Building {service_name} with command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                logger.error(f"Build failed: {result.stderr}")
                self._handle_build_error(result.stderr)
                return False
            
            logger.info(f" PASS:  Successfully built {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Build error: {e}")
            return False
    
    def build_standalone(
        self,
        dockerfile: str,
        image_name: str,
        context: Optional[str] = None,
        no_cache: bool = False,
        build_args: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Build container directly without compose.
        
        Args:
            dockerfile: Path to Dockerfile
            image_name: Name for built image
            context: Build context directory
            no_cache: Build without cache
            build_args: Build arguments
            
        Returns:
            True if build succeeded
        """
        dockerfile_path = Path(dockerfile)
        if not dockerfile_path.is_absolute():
            dockerfile_path = self.project_root / dockerfile_path
        
        if not dockerfile_path.exists():
            logger.error(f"Dockerfile not found: {dockerfile_path}")
            return False
        
        context_path = context or str(self.project_root)
        
        # Build command
        cmd = [self.runtime.value, "build"]
        cmd.extend(["-f", str(dockerfile_path)])
        cmd.extend(["-t", image_name])
        
        if no_cache:
            cmd.append("--no-cache")
        
        # Add build args
        if build_args:
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])
        
        # Add context
        cmd.append(context_path)
        
        logger.info(f"Building {image_name} with command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode != 0:
                logger.error(f"Build failed: {result.stderr}")
                return False
            
            logger.info(f" PASS:  Successfully built {image_name}")
            return True
            
        except Exception as e:
            logger.error(f"Build error: {e}")
            return False
    
    def _handle_build_error(self, error_output: str):
        """Handle common build errors with helpful messages."""
        if "pull access denied" in error_output or "not found" in error_output:
            logger.error("\n" + "="*60)
            logger.error("BASE IMAGE ISSUE DETECTED!")
            
            if self.runtime == ContainerRuntime.PODMAN:
                logger.error("Podman may need registry configuration.")
                logger.error("Solutions:")
                logger.error("1. Check registry access: podman login docker.io")
                logger.error("2. Use fully qualified image names (e.g., docker.io/python:3.11)")
                logger.error("3. Configure unqualified-search registries in /etc/containers/registries.conf")
            else:
                logger.error("Docker Hub rate limit or missing image.")
                logger.error("Solutions:")
                logger.error("1. Wait for rate limit reset")
                logger.error("2. Use Docker Hub login: docker login")
                logger.error("3. Use alternative registry or local images")
            
            logger.error("="*60 + "\n")
    
    def check_base_images(self) -> Dict[str, bool]:
        """
        Check availability of common base images.
        
        Returns:
            Dict mapping image name to availability
        """
        logger.info("Checking base images...")
        
        required_images = [
            "python:3.11-alpine",
            "python:3.11-alpine3.19",
            "node:18-alpine",
            "postgres:15-alpine",
            "redis:7-alpine"
        ]
        
        available = {}
        cmd_base = [self.runtime.value, "images", "-q"]
        
        for image in required_images:
            cmd = cmd_base + [image]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                available[image] = bool(result.stdout.strip())
            except:
                available[image] = False
        
        # Report results
        logger.info("\nBase image status:")
        for image, is_available in available.items():
            status = " PASS: " if is_available else " FAIL: "
            logger.info(f"  {status} {image}")
        
        missing = [img for img, avail in available.items() if not avail]
        if missing:
            logger.warning(f"\nMissing {len(missing)} base images")
            logger.info("To pull missing images:")
            for img in missing:
                logger.info(f"  {self.runtime.value} pull {img}")
        
        return available
    
    def build_all_services(self, compose_file: str = "docker-compose.test.yml") -> bool:
        """
        Build all services defined in compose file.
        
        Args:
            compose_file: Compose file to use
            
        Returns:
            True if all builds succeeded
        """
        services = ["test-backend", "test-auth", "test-frontend"]
        
        logger.info(f"Building all services from {compose_file}")
        
        # Check base images first
        self.check_base_images()
        
        success = True
        for service in services:
            if not self.build_with_compose(service, compose_file, pull="never"):
                logger.error(f"Failed to build {service}")
                success = False
        
        return success


def main():
    """Main entry point for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Build containers with Docker or Podman"
    )
    parser.add_argument(
        "--runtime",
        choices=["docker", "podman"],
        help="Force specific runtime (auto-detect by default)"
    )
    parser.add_argument(
        "--service",
        help="Build specific service"
    )
    parser.add_argument(
        "--compose-file",
        default="docker-compose.test.yml",
        help="Compose file to use"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Build without cache"
    )
    parser.add_argument(
        "--pull",
        choices=["always", "never", "missing"],
        default="never",
        help="Image pull policy"
    )
    parser.add_argument(
        "--check-images",
        action="store_true",
        help="Just check base images"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build all services"
    )
    
    args = parser.parse_args()
    
    # Initialize builder
    runtime = None
    if args.runtime:
        runtime = ContainerRuntime.DOCKER if args.runtime == "docker" else ContainerRuntime.PODMAN
    
    try:
        builder = ContainerBuilder(runtime)
    except RuntimeError as e:
        logger.error(str(e))
        sys.exit(1)
    
    # Execute requested action
    if args.check_images:
        builder.check_base_images()
        sys.exit(0)
    elif args.all:
        success = builder.build_all_services(args.compose_file)
        sys.exit(0 if success else 1)
    elif args.service:
        success = builder.build_with_compose(
            args.service,
            args.compose_file,
            no_cache=args.no_cache,
            pull=args.pull
        )
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()