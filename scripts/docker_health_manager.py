#!/usr/bin/env python3
"""
Docker Health Manager - DEPRECATED

⚠️  DEPRECATION NOTICE ⚠️ 
This script is DEPRECATED and should NOT be used for new code.

ALL Docker operations must now go through UnifiedDockerManager per CLAUDE.md Section 7.1.

Use instead:
- test_framework.unified_docker_manager.UnifiedDockerManager
- scripts/docker_manual.py (uses UnifiedDockerManager)

This file remains only for legacy compatibility and will be removed in a future version.
"""

import argparse
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

# Issue deprecation warning
warnings.warn(
    "DockerHealthManager is deprecated. Use test_framework.unified_docker_manager.UnifiedDockerManager instead.",
    DeprecationWarning,
    stacklevel=2
)


class ContainerState(Enum):
    RUNNING = "running"
    STOPPED = "stopped" 
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"


@dataclass
class ContainerInfo:
    name: str
    service: str
    state: ContainerState
    health: Optional[str] = None
    uptime: Optional[str] = None


class DockerHealthManager:
    """Smart Docker container lifecycle management."""
    
    def __init__(self, compose_file: str = "docker-compose.test.yml", project_name: str = "netra-test"):
        self.compose_file = Path(compose_file)
        self.project_name = project_name
        
    def get_container_status(self, services: Optional[List[str]] = None) -> Dict[str, ContainerInfo]:
        """Get current status of containers."""
        # Check if Docker is running first
        try:
            subprocess.run(["docker", "version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("[WARNING] Docker is not running or not installed")
            return {}
        
        cmd = [
            "docker", "compose", "-f", str(self.compose_file),
            "-p", self.project_name, "ps", "--format", "json"
        ]
        
        if services:
            cmd.extend(services)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # If command failed, likely no containers exist yet
            if result.returncode != 0:
                if services:
                    # Return stopped status for requested services
                    return {
                        service: ContainerInfo(
                            name=f"{self.project_name}-{service}",
                            service=service,
                            state=ContainerState.STOPPED
                        ) for service in services
                    }
                return {}
            
            containers = {}
            
            if not result.stdout.strip():
                # No containers found
                if services:
                    return {
                        service: ContainerInfo(
                            name=f"{self.project_name}-{service}",
                            service=service,
                            state=ContainerState.STOPPED
                        ) for service in services
                    }
                return {}
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    container_data = json.loads(line)
                    name = container_data.get("Name", "")
                    service = container_data.get("Service", "")
                    state_str = container_data.get("State", "").lower()
                    health = container_data.get("Health", "")
                    
                    # Determine container state
                    if state_str == "running":
                        if health == "healthy":
                            state = ContainerState.HEALTHY
                        elif health == "unhealthy":
                            state = ContainerState.UNHEALTHY
                        elif health == "starting":
                            state = ContainerState.STARTING
                        else:
                            state = ContainerState.RUNNING
                    else:
                        state = ContainerState.STOPPED
                    
                    containers[service] = ContainerInfo(
                        name=name,
                        service=service,
                        state=state,
                        health=health,
                        uptime=container_data.get("RunningFor", "")
                    )
                except json.JSONDecodeError:
                    continue  # Skip malformed lines
                
            return containers
            
        except Exception as e:
            print(f"Error getting container status: {e}")
            return {}
    
    def start_services_smart(self, services: List[str], wait_healthy: bool = True) -> bool:
        """Start services only if they're not already healthy."""
        print(f"[HEALTH] Checking status of services: {', '.join(services)}")
        
        current_status = self.get_container_status(services)
        
        # Determine which services need to be started
        services_to_start = []
        already_healthy = []
        
        for service in services:
            if service in current_status:
                container = current_status[service]
                if container.state == ContainerState.HEALTHY:
                    already_healthy.append(service)
                elif container.state in [ContainerState.RUNNING, ContainerState.STARTING]:
                    # Container is running but may not be healthy yet
                    print(f"[HEALTH] {service} is {container.state.value}, will wait for health check")
                else:
                    services_to_start.append(service)
            else:
                services_to_start.append(service)
        
        if already_healthy:
            print(f"[HEALTH] Services already healthy: {', '.join(already_healthy)}")
        
        if services_to_start:
            print(f"[HEALTH] Starting services: {', '.join(services_to_start)}")
            
            cmd = [
                "docker", "compose", "-f", str(self.compose_file),
                "-p", self.project_name, "up", "-d"
            ] + services_to_start
            
            try:
                result = subprocess.run(cmd, check=True)
                if result.returncode != 0:
                    print(f"[ERROR] Failed to start services")
                    return False
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Failed to start services: {e}")
                return False
        
        # Wait for all services to be healthy if requested
        if wait_healthy:
            all_services = set(services)
            return self.wait_for_healthy(all_services)
        
        return True
    
    def wait_for_healthy(self, services: Set[str], timeout: int = 60) -> bool:
        """Wait for services to become healthy."""
        print(f"[HEALTH] Waiting for services to become healthy: {', '.join(services)}")
        
        start_time = time.time()
        healthy_services = set()
        
        while time.time() - start_time < timeout:
            current_status = self.get_container_status(list(services))
            
            for service in services:
                if service in current_status:
                    container = current_status[service]
                    if container.state == ContainerState.HEALTHY:
                        if service not in healthy_services:
                            print(f"[HEALTH] ✓ {service} is healthy")
                            healthy_services.add(service)
                    elif container.state == ContainerState.UNHEALTHY:
                        print(f"[HEALTH] ✗ {service} is unhealthy")
                        return False
            
            if healthy_services == services:
                print(f"[HEALTH] ✓ All services are healthy")
                return True
            
            time.sleep(2)
        
        missing = services - healthy_services
        print(f"[HEALTH] ✗ Timeout waiting for services: {', '.join(missing)}")
        return False
    
    def stop_services_graceful(self, services: List[str], timeout: int = 30) -> bool:
        """Stop services gracefully with proper cleanup."""
        print(f"[HEALTH] Stopping services gracefully: {', '.join(services)}")
        
        cmd = [
            "docker", "compose", "-f", str(self.compose_file),
            "-p", self.project_name, "stop", "-t", str(timeout)
        ] + services
        
        try:
            result = subprocess.run(cmd, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to stop services: {e}")
            return False
    
    def cleanup_orphans(self) -> bool:
        """Clean up orphaned containers from previous runs."""
        print("[HEALTH] Cleaning up orphaned containers...")
        
        cmd = [
            "docker", "compose", "-f", str(self.compose_file),
            "-p", self.project_name, "down", "--remove-orphans"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("[HEALTH] ✓ Cleanup completed")
            else:
                print(f"[HEALTH] Cleanup had issues: {result.stderr}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to cleanup: {e}")
            return False
    
    def print_status(self, services: Optional[List[str]] = None):
        """Print current status of containers."""
        containers = self.get_container_status(services)
        
        if not containers:
            print("[HEALTH] No containers found")
            return
        
        print("\n" + "=" * 60)
        print("DOCKER CONTAINER STATUS")
        print("=" * 60)
        
        for service, container in containers.items():
            status_icon = {
                ContainerState.HEALTHY: "✓",
                ContainerState.RUNNING: "▶",
                ContainerState.STARTING: "⏳",
                ContainerState.UNHEALTHY: "✗",
                ContainerState.STOPPED: "⏹"
            }.get(container.state, "?")
            
            print(f"{status_icon} {service:20} {container.state.value:12} {container.health or 'N/A':10} {container.uptime or 'N/A'}")


def main():
    parser = argparse.ArgumentParser(description="Smart Docker container health management")
    parser.add_argument("command", choices=["start", "stop", "status", "cleanup", "restart"], 
                       help="Command to run")
    parser.add_argument("services", nargs="*", help="Services to manage")
    parser.add_argument("-f", "--file", default="docker-compose.test.yml", 
                       help="Docker Compose file")
    parser.add_argument("-p", "--project", default="netra-test", 
                       help="Project name")
    parser.add_argument("--no-wait", action="store_true",
                       help="Don't wait for services to be healthy")
    parser.add_argument("-t", "--timeout", type=int, default=60,
                       help="Timeout for operations")
    
    args = parser.parse_args()
    
    manager = DockerHealthManager(args.file, args.project)
    
    if args.command == "status":
        manager.print_status(args.services)
        
    elif args.command == "start":
        if not args.services:
            print("Error: Must specify services to start")
            sys.exit(1)
        success = manager.start_services_smart(args.services, wait_healthy=not args.no_wait)
        sys.exit(0 if success else 1)
        
    elif args.command == "stop":
        if not args.services:
            print("Error: Must specify services to stop")
            sys.exit(1)
        success = manager.stop_services_graceful(args.services, args.timeout)
        sys.exit(0 if success else 1)
        
    elif args.command == "cleanup":
        success = manager.cleanup_orphans()
        sys.exit(0 if success else 1)
        
    elif args.command == "restart":
        if not args.services:
            print("Error: Must specify services to restart")
            sys.exit(1)
        
        # Smart restart: only restart if not healthy
        success = (
            manager.stop_services_graceful(args.services, args.timeout) and
            manager.start_services_smart(args.services, wait_healthy=not args.no_wait)
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()