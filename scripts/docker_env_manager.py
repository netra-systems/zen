#!/usr/bin/env python3
"""
Docker Environment Manager

Unified management script for TEST and DEV Docker environments.
Allows running both environments simultaneously for different purposes.
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class DockerEnvironmentManager:
    """Manage Docker TEST and DEV environments."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.environments = {
            "test": {
                "compose_files": ["docker-compose.test.yml"],
                "env_file": ".env.test",
                "ports": {
                    "PostgreSQL": 5433,
                    "Redis": 6380,
                    "ClickHouse HTTP": 8124,
                    "ClickHouse TCP": 9001,
                    "Backend": 8001,
                    "Auth": 8082,
                    "Frontend": 3001
                },
                "description": "Automated testing with real services"
            },
            "dev": {
                "compose_files": ["docker-compose.dev.yml", "docker-compose.override.yml"],
                "env_file": ".env.dev",
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
        """Check if Docker is installed and running."""
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            subprocess.run(["docker-compose", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: Docker or docker-compose is not installed or not running.")
            return False
    
    def check_port(self, port: int) -> bool:
        """Check if a port is available."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result != 0
    
    def get_running_containers(self) -> Dict[str, List[str]]:
        """Get list of running containers by environment."""
        result = {"test": [], "dev": [], "other": []}
        
        try:
            output = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
            
            if output:
                containers = output.split('\n')
                for container in containers:
                    if "test" in container:
                        result["test"].append(container)
                    elif "dev" in container:
                        result["dev"].append(container)
                    else:
                        result["other"].append(container)
        except subprocess.CalledProcessError:
            pass
        
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
    
    def start_environment(self, env_name: str, detached: bool = True, services: List[str] = None):
        """Start a specific environment."""
        if env_name not in self.environments:
            print(f"Error: Unknown environment '{env_name}'")
            return False
        
        env_config = self.environments[env_name]
        
        # Build docker-compose command
        cmd = ["docker-compose"]
        for compose_file in env_config["compose_files"]:
            if os.path.exists(self.root_dir / compose_file):
                cmd.extend(["-f", compose_file])
        
        cmd.extend(["--env-file", env_config["env_file"], "up"])
        
        if detached:
            cmd.append("-d")
        
        if services:
            cmd.extend(services)
        elif env_name == "dev":
            cmd.extend(["--profile", "full"])
        
        print(f"Starting {env_name.upper()} environment...")
        result = subprocess.run(cmd, cwd=self.root_dir)
        
        if result.returncode == 0:
            print(f"\n{env_name.upper()} environment started successfully!")
            self._print_environment_info(env_name)
            return True
        else:
            print(f"Error: Failed to start {env_name.upper()} environment")
            return False
    
    def stop_environment(self, env_name: str, remove_volumes: bool = False):
        """Stop a specific environment."""
        if env_name not in self.environments:
            print(f"Error: Unknown environment '{env_name}'")
            return False
        
        env_config = self.environments[env_name]
        
        # Build docker-compose command
        cmd = ["docker-compose"]
        for compose_file in env_config["compose_files"]:
            if os.path.exists(self.root_dir / compose_file):
                cmd.extend(["-f", compose_file])
        
        cmd.extend(["--env-file", env_config["env_file"], "down"])
        
        if remove_volumes:
            cmd.append("-v")
        
        print(f"Stopping {env_name.upper()} environment...")
        result = subprocess.run(cmd, cwd=self.root_dir)
        
        if result.returncode == 0:
            print(f"{env_name.upper()} environment stopped.")
            return True
        else:
            print(f"Error: Failed to stop {env_name.upper()} environment")
            return False
    
    def restart_environment(self, env_name: str):
        """Restart a specific environment."""
        self.stop_environment(env_name)
        return self.start_environment(env_name)
    
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
    
    def start_both(self):
        """Start both TEST and DEV environments."""
        print("Starting both TEST and DEV environments...\n")
        
        # Start TEST environment first (usually for background testing)
        test_success = self.start_environment("test", detached=True)
        
        # Start DEV environment
        dev_success = self.start_environment("dev", detached=True)
        
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
    
    def stop_all(self):
        """Stop all environments."""
        print("Stopping all environments...\n")
        self.stop_environment("test")
        self.stop_environment("dev")
        print("\nAll environments stopped.")
    
    def clean_all(self):
        """Stop all environments and remove volumes."""
        print("Cleaning all environments (including volumes)...\n")
        self.stop_environment("test", remove_volumes=True)
        self.stop_environment("dev", remove_volumes=True)
        
        # Also prune unused Docker resources
        print("\nPruning unused Docker resources...")
        subprocess.run(["docker", "system", "prune", "-f"])
        print("\nCleanup complete.")


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
    
    if args.command == "status":
        manager.status()
    
    elif args.command == "start":
        if args.environment == "both":
            manager.start_both()
        else:
            manager.start_environment(
                args.environment,
                detached=args.detach,
                services=args.services
            )
    
    elif args.command == "stop":
        if args.environment == "all":
            manager.stop_all()
        else:
            manager.stop_environment(args.environment, remove_volumes=args.volumes)
    
    elif args.command == "restart":
        manager.restart_environment(args.environment)
    
    elif args.command == "clean":
        manager.clean_all()
    
    elif args.command == "logs":
        env_config = manager.environments[args.environment]
        cmd = ["docker-compose"]
        for compose_file in env_config["compose_files"]:
            cmd.extend(["-f", compose_file])
        cmd.extend(["logs", "-f"])
        if args.service:
            cmd.append(args.service)
        subprocess.run(cmd, cwd=manager.root_dir)


if __name__ == "__main__":
    main()