#!/usr/bin/env python3
"""
Docker Services Manager for Netra Platform

This script provides fine-grained control over individual Docker services,
allowing selective startup, shutdown, and management of specific components.

Available Profiles:
  - netra: Just the main Netra backend application (with required dependencies)
  - backend: All backend services (Netra + Auth + databases)
  - frontend: Frontend application only
  - full: Everything (all services)
  - db: Just database services (PostgreSQL)
  - cache: Just cache services (Redis)
  - analytics: Analytics services (ClickHouse)
  - auth: Auth service only
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict
import json

# Fix Unicode output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class DockerServicesManager:
    """Manages Docker Compose services with profile support."""
    
    # Service profiles define logical groupings
    PROFILES = {
        'netra': {
            'description': 'Main Netra backend application with dependencies',
            'services': ['postgres', 'redis', 'backend'],
            'profiles': ['netra']
        },
        'backend': {
            'description': 'All backend services (Netra, Auth, databases)',
            'services': ['postgres', 'redis', 'backend', 'auth'],
            'profiles': ['backend']
        },
        'frontend': {
            'description': 'Frontend application only',
            'services': ['frontend'],
            'profiles': ['frontend']
        },
        'full': {
            'description': 'All services',
            'services': ['postgres', 'redis', 'backend', 'auth', 'frontend'],
            'profiles': ['full']
        },
        'db': {
            'description': 'Database services only',
            'services': ['postgres'],
            'profiles': ['db']
        },
        'cache': {
            'description': 'Cache services only',
            'services': ['redis'],
            'profiles': ['cache']
        },
        'analytics': {
            'description': 'Analytics services (ClickHouse)',
            'services': ['clickhouse'],
            'profiles': ['analytics']
        },
        'auth': {
            'description': 'Auth service with dependencies',
            'services': ['postgres', 'redis', 'auth'],
            'profiles': ['auth']
        }
    }
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.compose_file = "docker-compose.dev.yml"
        
    def run_docker_compose(self, args: List[str], capture_output: bool = False):
        """Run a docker-compose command."""
        cmd = ["docker", "compose", "-f", self.compose_file] + args
        
        if capture_output:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            return result
        else:
            result = subprocess.run(cmd, cwd=self.project_root)
            return result
            
    def start(self, profile: str, build: bool = False, detach: bool = True):
        """Start services for a specific profile."""
        print(f"\n[START] Starting {profile} services...")
        print(f"        {self.PROFILES[profile]['description']}")
        
        args = ["up"]
        
        if detach:
            args.append("-d")
            
        if build:
            args.append("--build")
            
        # Add profile argument
        for p in self.PROFILES[profile]['profiles']:
            args.extend(["--profile", p])
            
        result = self.run_docker_compose(args)
        
        if result.returncode == 0:
            print(f"[OK] {profile} services started successfully")
            self.show_status(profile)
        else:
            print(f"[ERROR] Failed to start {profile} services")
            return False
            
        return True
        
    def stop(self, profile: Optional[str] = None, remove_volumes: bool = False):
        """Stop services."""
        if profile:
            print(f"\n[STOP] Stopping {profile} services...")
            services = self.PROFILES[profile]['services']
            args = ["stop"] + services
        else:
            print("\n[STOP] Stopping all services...")
            args = ["down"]
            if remove_volumes:
                args.append("-v")
                
        result = self.run_docker_compose(args)
        
        if result.returncode == 0:
            print("[OK] Services stopped successfully")
        else:
            print("[ERROR] Failed to stop services")
            return False
            
        return True
        
    def restart(self, profile: str):
        """Restart services for a specific profile."""
        print(f"\n[RESTART] Restarting {profile} services...")
        
        services = self.PROFILES[profile]['services']
        args = ["restart"] + services
        
        result = self.run_docker_compose(args)
        
        if result.returncode == 0:
            print(f"[OK] {profile} services restarted successfully")
        else:
            print(f"[ERROR] Failed to restart {profile} services")
            return False
            
        return True
        
    def logs(self, profile: Optional[str] = None, follow: bool = True, tail: Optional[int] = None):
        """Show logs for services."""
        args = ["logs"]
        
        if follow:
            args.append("-f")
            
        if tail:
            args.extend(["--tail", str(tail)])
            
        if profile and profile in self.PROFILES:
            services = self.PROFILES[profile]['services']
            args.extend(services)
            
        print(f"\n[LOGS] Showing logs{' for ' + profile if profile else ''}...")
        print("       Press Ctrl+C to stop following logs\n")
        
        try:
            self.run_docker_compose(args)
        except KeyboardInterrupt:
            print("\n[OK] Stopped following logs")
            
    def status(self, profile: Optional[str] = None):
        """Show status of services."""
        print("\n[STATUS] Checking service status...")
        
        args = ["ps"]
        
        if profile and profile in self.PROFILES:
            services = self.PROFILES[profile]['services']
            args.extend(services)
            
        result = self.run_docker_compose(args, capture_output=True)
        
        if result.stdout:
            print(result.stdout)
        else:
            print("No services are running")
            
    def show_status(self, profile: str):
        """Show detailed status and URLs for a profile."""
        print(f"\n{'='*60}")
        print(f"{profile.upper()} Services Status")
        print('='*60)
        
        # Show service URLs based on profile
        if profile in ['netra', 'backend', 'full']:
            print(f"   Backend API: http://localhost:8000")
            print(f"   Backend Health: http://localhost:8000/health")
            print(f"   Backend Docs: http://localhost:8000/docs")
            
        if profile in ['auth', 'backend', 'full']:
            print(f"   Auth API: http://localhost:8081")
            print(f"   Auth Health: http://localhost:8081/health")
            
        if profile in ['frontend', 'full']:
            print(f"   Frontend: http://localhost:3000")
            
        if profile in ['db', 'netra', 'backend', 'auth', 'full']:
            print(f"   PostgreSQL: localhost:5432")
            
        if profile in ['cache', 'netra', 'backend', 'auth', 'full']:
            print(f"   Redis: localhost:6379")
            
        if profile in ['analytics', 'full']:
            print(f"   ClickHouse: http://localhost:8123")
            
        print('='*60)
        
    def exec_command(self, service: str, command: List[str]):
        """Execute a command in a running service container."""
        args = ["exec", service] + command
        
        print(f"\n[EXEC] Running command in {service}...")
        result = self.run_docker_compose(args)
        
        return result.returncode == 0
        
    def list_profiles(self):
        """List all available profiles."""
        print("\n[PROFILES] Available service profiles:")
        print('='*60)
        
        for name, config in self.PROFILES.items():
            print(f"  {name:12} - {config['description']}")
            print(f"  {'':12}   Services: {', '.join(config['services'])}")
            print()
            
        print('='*60)
        print("\nUsage examples:")
        print("  python scripts/docker_services.py start netra     # Start just Netra backend")
        print("  python scripts/docker_services.py start frontend  # Start just frontend")
        print("  python scripts/docker_services.py start full      # Start everything")
        print("  python scripts/docker_services.py logs netra      # View Netra logs")
        print("  python scripts/docker_services.py stop            # Stop all services")


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Docker Services Manager for Netra Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
PROFILES:
  netra     - Main Netra backend with dependencies
  backend   - All backend services (Netra + Auth + DBs)
  frontend  - Frontend application only
  full      - All services
  db        - Database services only
  cache     - Cache services only
  analytics - Analytics services (ClickHouse)
  auth      - Auth service with dependencies

EXAMPLES:
  python scripts/docker_services.py start netra          # Start Netra backend only
  python scripts/docker_services.py start frontend       # Start frontend only
  python scripts/docker_services.py start full           # Start everything
  python scripts/docker_services.py logs netra --tail 50 # View last 50 lines of Netra logs
  python scripts/docker_services.py restart backend      # Restart backend services
  python scripts/docker_services.py stop                 # Stop all services
  python scripts/docker_services.py exec backend bash    # Shell into backend container
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start services')
    start_parser.add_argument('profile', choices=list(DockerServicesManager.PROFILES.keys()),
                            help='Service profile to start')
    start_parser.add_argument('--build', action='store_true',
                            help='Build images before starting')
    start_parser.add_argument('--attach', action='store_true',
                            help='Attach to service logs')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop services')
    stop_parser.add_argument('profile', nargs='?', choices=list(DockerServicesManager.PROFILES.keys()),
                            help='Service profile to stop (all if not specified)')
    stop_parser.add_argument('--volumes', '-v', action='store_true',
                            help='Remove volumes')
    
    # Restart command
    restart_parser = subparsers.add_parser('restart', help='Restart services')
    restart_parser.add_argument('profile', choices=list(DockerServicesManager.PROFILES.keys()),
                              help='Service profile to restart')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='View service logs')
    logs_parser.add_argument('profile', nargs='?', choices=list(DockerServicesManager.PROFILES.keys()),
                           help='Service profile to view logs for')
    logs_parser.add_argument('--no-follow', '-n', action='store_true',
                           help="Don't follow logs")
    logs_parser.add_argument('--tail', '-t', type=int, metavar='N',
                           help='Number of lines to show from the end')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show service status')
    status_parser.add_argument('profile', nargs='?', choices=list(DockerServicesManager.PROFILES.keys()),
                             help='Service profile to check')
    
    # Exec command
    exec_parser = subparsers.add_parser('exec', help='Execute command in service')
    exec_parser.add_argument('service', help='Service name')
    exec_parser.add_argument('command', nargs='+', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available profiles')
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    manager = DockerServicesManager()
    
    # Default to list if no command
    if not args.command:
        manager.list_profiles()
        return 0
        
    # Execute command
    success = True
    
    if args.command == 'start':
        success = manager.start(args.profile, args.build, not args.attach)
        if args.attach:
            manager.logs(args.profile)
            
    elif args.command == 'stop':
        success = manager.stop(args.profile, args.volumes)
        
    elif args.command == 'restart':
        success = manager.restart(args.profile)
        
    elif args.command == 'logs':
        manager.logs(args.profile, not args.no_follow, args.tail)
        
    elif args.command == 'status':
        manager.status(args.profile)
        
    elif args.command == 'exec':
        success = manager.exec_command(args.service, args.command)
        
    elif args.command == 'list':
        manager.list_profiles()
        
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())