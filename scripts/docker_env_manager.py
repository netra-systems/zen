#!/usr/bin/env python3
"""
Docker Environment Manager - UPDATED to use UnifiedDockerManager

Unified management script for TEST and DEV Docker environments.
Now uses UnifiedDockerManager as the SSOT for all Docker operations.

CRITICAL: This script now delegates all Docker operations to UnifiedDockerManager
per CLAUDE.md Section 7.1 requirements.
"""

import os
import sys
import asyncio
import argparse
import json
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# SSOT import - all Docker operations go through UnifiedDockerManager
from test_framework.unified_docker_manager import UnifiedDockerManager, get_default_manager


class DockerEnvironmentManager:
    """Manage Docker TEST and DEV environments using UnifiedDockerManager."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        # Get SSOT Docker manager instance
        self.docker_manager = get_default_manager()
        
        self.environments = {
            "test": {
                "environment_type": "test",
                "ports": {
                    "PostgreSQL": 5434,
                    "Redis": 6381,
                    "ClickHouse HTTP": 8124,
                    "ClickHouse TCP": 9001,
                    "Backend": 8001,
                    "Auth": 8082,
                    "Frontend": 3001
                },
                "description": "Automated testing with real services"
            },
            "dev": {
                "environment_type": "dev", 
                "ports": {
                    "PostgreSQL": 5432,
                    "Redis": 6379,
                    "ClickHouse HTTP": 8123,
                    "ClickHouse TCP": 9000,
                    "Backend": 8000,
                    "Auth": 8081,
                    "Frontend": 3000
                },
                "description": "Local development with hot reload"
            }
        }
    
    def check_docker(self) -> bool:
        """Check if Docker is installed and running via UnifiedDockerManager."""
        try:
            return asyncio.run(self.docker_manager.is_docker_available())
        except Exception as e:
            print(f"Error: Docker check failed: {e}")
            return False
    
    def check_port(self, port: int) -> bool:
        """Check if a port is available."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result != 0
    
    def get_running_containers(self) -> Dict[str, List[str]]:
        """Get list of running containers by environment via UnifiedDockerManager."""
        result = {"test": [], "dev": [], "other": []}
        
        try:
            # Use UnifiedDockerManager to get container status
            status = self.docker_manager.get_enhanced_container_status()
            
            for service, container_info in status.items():
                container_name = container_info.get("name", service)
                if "test" in container_name:
                    result["test"].append(container_name)
                elif "dev" in container_name:
                    result["dev"].append(container_name)
                else:
                    result["other"].append(container_name)
        except Exception as e:
            print(f"Warning: Could not get container status: {e}")
        
        return result
    
    def status(self):
        """Show status of both environments."""
        print("=" * 60)
        print("Docker Environment Status")
        print("=" * 60)
        
        running = self.get_running_containers()
        
        for env_name, env_config in self.environments.items():
            print(f"\n{env_name.upper()} Environment:")
            print(f"  Purpose: {env_config['description']}")
            
            # Check containers
            containers = running.get(env_name, [])
            if containers:
                print(f"  Status: RUNNING ({len(containers)} containers)")
                for container in containers:
                    print(f"    - {container}")
            else:
                print("  Status: STOPPED")
            
            # Check ports
            print("  Port Status:")
            for service, port in env_config["ports"].items():
                available = self.check_port(port)
                status = "Available" if available else "In Use"
                symbol = "[OK]" if available else "[X]"
                print(f"    {symbol} {service}: {port} ({status})")
        
        if running.get("other"):
            print("\nOther Containers Running:")
            for container in running["other"]:
                print(f"  - {container}")
        
        print("\n" + "=" * 60)
    
    async def start_environment(self, env_name: str, detached: bool = True, services: List[str] = None):
        """Start a specific environment using UnifiedDockerManager."""
        if env_name not in self.environments:
            print(f"Error: Unknown environment '{env_name}'")
            return False
        
        env_config = self.environments[env_name]
        
        print(f"Starting {env_name.upper()} environment via UnifiedDockerManager...")
        
        try:
            # Default services if none specified
            if services is None:
                services = ["postgres", "redis", "backend", "auth"]
            
            # Start services using UnifiedDockerManager
            success = await self.docker_manager.start_services_smart(
                services=services,
                wait_healthy=True,
                environment_name=env_config["environment_type"]
            )
            
            if success:
                print(f"\n{env_name.upper()} environment started successfully!")
                self._print_environment_info(env_name)
                return True
            else:
                print(f"Error: Failed to start {env_name.upper()} environment")
                return False
                
        except Exception as e:
            print(f"Error starting {env_name.upper()} environment: {e}")
            return False
    
    async def stop_environment(self, env_name: str, remove_volumes: bool = False):
        """Stop a specific environment using UnifiedDockerManager."""
        if env_name not in self.environments:
            print(f"Error: Unknown environment '{env_name}'")
            return False
        
        env_config = self.environments[env_name]
        
        print(f"Stopping {env_name.upper()} environment via UnifiedDockerManager...")
        
        try:
            # Stop environment using UnifiedDockerManager
            success = await self.docker_manager.graceful_shutdown(
                timeout=30,
                cleanup_volumes=remove_volumes
            )
            
            if success:
                print(f"{env_name.upper()} environment stopped.")
                return True
            else:
                print(f"Error: Failed to stop {env_name.upper()} environment")
                return False
                
        except Exception as e:
            print(f"Error stopping {env_name.upper()} environment: {e}")
            return False
    
    async def restart_environment(self, env_name: str):
        """Restart a specific environment."""
        await self.stop_environment(env_name)
        return await self.start_environment(env_name)
    
    def _print_environment_info(self, env_name: str):
        """Print environment access information."""
        env_config = self.environments[env_name]
        
        print(f"\n{env_name.upper()} Services:")
        print(f"  PostgreSQL: localhost:{env_config['ports']['PostgreSQL']}")
        print(f"  Redis: localhost:{env_config['ports']['Redis']}")
        print(f"  ClickHouse: localhost:{env_config['ports']['ClickHouse HTTP']}")
        print(f"  Backend API: http://localhost:{env_config['ports']['Backend']}")
        print(f"  Auth Service: http://localhost:{env_config['ports']['Auth']}")
        print(f"  Frontend: http://localhost:{env_config['ports']['Frontend']}")
    
    async def start_both(self):
        """Start both TEST and DEV environments."""
        print("Starting both TEST and DEV environments...\n")
        
        # Start TEST environment first (usually for background testing)
        test_success = await self.start_environment("test", detached=True)
        
        # Start DEV environment
        dev_success = await self.start_environment("dev", detached=True)
        
        if test_success and dev_success:
            print("\n" + "=" * 60)
            print("Both environments are running!")
            print("=" * 60)
            print("\nYou can now:")
            print("  - Run automated tests on TEST environment (port 8001)")
            print("  - Develop and test manually on DEV environment (port 8000)")
            print("  - Run: python unified_test_runner.py")
            print("  - Browse: http://localhost:3000 (DEV frontend)")
            return True
        
        return False
    
    async def stop_all(self):
        """Stop all environments."""
        print("Stopping all environments...\n")
        await self.stop_environment("test")
        await self.stop_environment("dev")
        print("\nAll environments stopped.")
    
    async def clean_all(self):
        """Stop all environments and remove volumes."""
        print("Cleaning all environments (including volumes)...\n")
        await self.stop_environment("test", remove_volumes=True)
        await self.stop_environment("dev", remove_volumes=True)
        
        # Use UnifiedDockerManager for system cleanup
        print("\nPruning unused Docker resources via UnifiedDockerManager...")
        try:
            await self.docker_manager.cleanup_orphaned_containers()
            print("Cleanup complete.")
        except Exception as e:
            print(f"Warning: Cleanup had issues: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage Docker TEST and DEV environments"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status command
    subparsers.add_parser("status", help="Show status of all environments")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start an environment")
    start_parser.add_argument(
        "environment",
        choices=["test", "dev", "both"],
        help="Environment to start"
    )
    start_parser.add_argument(
        "-d", "--detach",
        action="store_true",
        help="Run in detached mode"
    )
    start_parser.add_argument(
        "-s", "--services",
        nargs="+",
        help="Specific services to start"
    )
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop an environment")
    stop_parser.add_argument(
        "environment",
        choices=["test", "dev", "all"],
        help="Environment to stop"
    )
    stop_parser.add_argument(
        "-v", "--volumes",
        action="store_true",
        help="Remove volumes"
    )
    
    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart an environment")
    restart_parser.add_argument(
        "environment",
        choices=["test", "dev"],
        help="Environment to restart"
    )
    
    # Clean command
    subparsers.add_parser("clean", help="Stop all and clean volumes")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View logs")
    logs_parser.add_argument(
        "environment",
        choices=["test", "dev"],
        help="Environment logs to view"
    )
    logs_parser.add_argument(
        "service",
        nargs="?",
        help="Specific service logs"
    )
    
    args = parser.parse_args()
    
    manager = DockerEnvironmentManager()
    
    if not manager.check_docker():
        sys.exit(1)
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    async def run_command():
        """Run the appropriate command with async support."""
        if args.command == "status":
            manager.status()
        
        elif args.command == "start":
            if args.environment == "both":
                await manager.start_both()
            else:
                await manager.start_environment(
                    args.environment,
                    detached=args.detach,
                    services=args.services
                )
        
        elif args.command == "stop":
            if args.environment == "all":
                await manager.stop_all()
            else:
                await manager.stop_environment(args.environment, remove_volumes=args.volumes)
        
        elif args.command == "restart":
            await manager.restart_environment(args.environment)
        
        elif args.command == "clean":
            await manager.clean_all()
            
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
            
    # Run the async command
    asyncio.run(run_command())


if __name__ == "__main__":
    main()