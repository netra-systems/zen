#!/usr/bin/env python3
"""
Docker SSOT (Single Source of Truth) Manager
Centralized Docker management with automatic conflict resolution

This is the canonical way to manage Docker containers for the Netra platform.
It automatically handles conflicts, ensures Docker is running, and provides
a unified interface for all Docker operations.

Usage:
    python scripts/docker_ssot.py start       # Start test environment
    python scripts/docker_ssot.py stop        # Stop all containers
    python scripts/docker_ssot.py restart     # Restart services
    python scripts/docker_ssot.py clean       # Clean up everything
    python scripts/docker_ssot.py test        # Run tests with Docker
"""

import sys
import os
import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import UnifiedDockerManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DockerSSOT:
    """Single Source of Truth for Docker operations"""
    
    def __init__(self):
        self.manager = UnifiedDockerManager()
        self.project_root = project_root
        
    def ensure_docker_running(self) -> bool:
        """Ensure Docker Desktop is running (Windows/Mac) or Docker daemon (Linux)"""
        # Check if Docker is already running
        result = subprocess.run(
            ["docker", "ps"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Docker is already running")
            return True
        
        logger.info("🚀 Starting Docker...")
        
        # Platform-specific Docker startup
        if sys.platform == "win32":
            # Windows: Start Docker Desktop
            docker_desktop = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
            if Path(docker_desktop).exists():
                subprocess.Popen([docker_desktop], shell=True)
                logger.info("Starting Docker Desktop on Windows...")
            else:
                logger.error("Docker Desktop not found at expected location")
                return False
                
        elif sys.platform == "darwin":
            # macOS: Start Docker Desktop
            subprocess.run(["open", "-a", "Docker"], capture_output=True)
            logger.info("Starting Docker Desktop on macOS...")
            
        else:
            # Linux: Start Docker daemon
            subprocess.run(["sudo", "systemctl", "start", "docker"], capture_output=True)
            logger.info("Starting Docker daemon on Linux...")
        
        # Wait for Docker to be ready
        max_wait = 60
        for i in range(max_wait):
            result = subprocess.run(
                ["docker", "ps"], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                logger.info(f"✅ Docker is ready after {i+1} seconds")
                return True
            time.sleep(1)
            if i % 5 == 0:
                logger.info(f"Waiting for Docker... ({i}/{max_wait}s)")
        
        logger.error(f"❌ Docker failed to start after {max_wait} seconds")
        return False
    
    def clean_conflicts(self):
        """Clean up any conflicting containers"""
        logger.info("🧹 Cleaning up conflicting containers...")
        
        # Remove all netra-test containers
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=netra-test", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            containers = result.stdout.strip().split('\n')
            for container in containers:
                logger.info(f"  Removing {container}")
                subprocess.run(["docker", "rm", "-f", container], capture_output=True)
            logger.info(f"✅ Removed {len(containers)} conflicting containers")
        else:
            logger.info("✅ No conflicting containers found")
    
    def start(self, environment: str = "test") -> bool:
        """Start Docker services with automatic conflict resolution"""
        logger.info(f"🚀 Starting {environment} environment...")
        
        # Ensure Docker is running
        if not self.ensure_docker_running():
            return False
        
        # Clean up conflicts first
        self.clean_conflicts()
        
        # Use the appropriate compose file
        compose_file = "docker-compose.test.yml" if environment == "test" else "docker-compose.yml"
        compose_path = self.project_root / compose_file
        
        if not compose_path.exists():
            logger.error(f"❌ Compose file not found: {compose_path}")
            return False
        
        # Start services
        cmd = [
            "docker-compose",
            "-f", str(compose_path),
            "up", "-d"
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"❌ Failed to start services: {result.stderr}")
            return False
        
        logger.info("✅ Services started successfully")
        
        # Wait for health checks
        logger.info("⏳ Waiting for services to be healthy...")
        time.sleep(5)  # Give services time to start
        
        # Check health
        health_cmd = ["docker-compose", "-f", str(compose_path), "ps"]
        result = subprocess.run(health_cmd, capture_output=True, text=True)
        logger.info(result.stdout)
        
        return True
    
    def stop(self) -> bool:
        """Stop all Docker services"""
        logger.info("🛑 Stopping all services...")
        
        for compose_file in ["docker-compose.test.yml", "docker-compose.yml"]:
            compose_path = self.project_root / compose_file
            if compose_path.exists():
                cmd = ["docker-compose", "-f", str(compose_path), "down"]
                subprocess.run(cmd, capture_output=True)
        
        logger.info("✅ All services stopped")
        return True
    
    def restart(self, services: Optional[List[str]] = None) -> bool:
        """Restart Docker services"""
        if services:
            logger.info(f"🔄 Restarting services: {', '.join(services)}")
            for service in services:
                self.manager.restart_service(service)
        else:
            logger.info("🔄 Restarting all services...")
            self.stop()
            time.sleep(2)
            self.start()
        
        logger.info("✅ Services restarted")
        return True
    
    def clean(self) -> bool:
        """Clean up everything - containers, volumes, networks"""
        logger.info("🧹 Cleaning up everything...")
        
        # Stop all services
        self.stop()
        
        # Remove all test containers
        subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=netra", "--format", "{{.ID}}"],
            capture_output=True,
            text=True
        ).stdout.strip().split('\n')
        
        # Prune system
        logger.info("Pruning Docker system...")
        subprocess.run(["docker", "system", "prune", "-f"], capture_output=True)
        
        logger.info("✅ Cleanup complete")
        return True
    
    def test(self, test_args: List[str] = None) -> bool:
        """Run tests with Docker services"""
        logger.info("🧪 Running tests with Docker...")
        
        # Ensure services are running
        if not self.start("test"):
            return False
        
        # Run tests
        test_cmd = [
            sys.executable,
            str(self.project_root / "tests" / "unified_test_runner.py"),
            "--real-services"
        ]
        
        if test_args:
            test_cmd.extend(test_args)
        else:
            test_cmd.extend(["--categories", "unit", "integration", "--fast-fail"])
        
        logger.info(f"Running: {' '.join(test_cmd)}")
        result = subprocess.run(test_cmd)
        
        return result.returncode == 0
    
    def status(self) -> bool:
        """Check status of all services"""
        logger.info("📊 Checking service status...")
        
        # Check if Docker is running
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("❌ Docker is not running")
            return False
        
        # List all containers
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=netra", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            logger.info("\nRunning containers:")
            print(result.stdout)
        else:
            logger.info("No Netra containers are running")
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Docker SSOT Manager")
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "clean", "test", "status"],
        help="Command to execute"
    )
    parser.add_argument(
        "--services",
        nargs="+",
        help="Specific services to operate on (for restart)"
    )
    parser.add_argument(
        "--env",
        default="test",
        choices=["test", "dev", "prod"],
        help="Environment to use"
    )
    parser.add_argument(
        "test_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments for test command"
    )
    
    args = parser.parse_args()
    
    docker = DockerSSOT()
    
    try:
        if args.command == "start":
            success = docker.start(args.env)
        elif args.command == "stop":
            success = docker.stop()
        elif args.command == "restart":
            success = docker.restart(args.services)
        elif args.command == "clean":
            success = docker.clean()
        elif args.command == "test":
            success = docker.test(args.test_args)
        elif args.command == "status":
            success = docker.status()
        else:
            logger.error(f"Unknown command: {args.command}")
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()