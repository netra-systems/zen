#!/usr/bin/env python3
"""
Docker Windows Helper Script
Helps manage Docker containers on Windows to prevent crashes
"""

import subprocess
import sys
import time
import json
import psutil
import argparse
from pathlib import Path
from typing import List, Dict, Any


class DockerWindowsHelper:
    """Helper class for managing Docker on Windows"""
    
    def __init__(self):
        self.docker_compose_files = [
            "docker-compose.yml",
            "docker-compose.windows.yml"
        ]
        
    def check_docker_desktop_memory(self) -> Dict[str, Any]:
        """Check Docker Desktop memory allocation"""
        try:
            # Get Docker Desktop settings
            settings_path = Path.home() / ".docker" / "settings.json"
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    memory_mb = settings.get('memoryMiB', 2048)
                    cpus = settings.get('cpus', 2)
                    return {
                        'memory_mb': memory_mb,
                        'cpus': cpus,
                        'recommended_memory': 4096,
                        'recommended_cpus': 4
                    }
        except Exception as e:
            print(f"Warning: Could not read Docker Desktop settings: {e}")
        
        return {
            'memory_mb': 'unknown',
            'cpus': 'unknown',
            'recommended_memory': 4096,
            'recommended_cpus': 4
        }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check available system resources"""
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        
        return {
            'total_memory_gb': round(memory.total / (1024**3), 2),
            'available_memory_gb': round(memory.available / (1024**3), 2),
            'memory_percent_used': memory.percent,
            'cpu_count': cpu_count,
            'cpu_percent': psutil.cpu_percent(interval=1)
        }
    
    def stop_all_containers(self):
        """Stop all Docker containers"""
        print("Stopping all Docker containers...")
        subprocess.run(["docker", "stop", "$(docker ps -aq)"], shell=True, capture_output=True)
        print("All containers stopped.")
    
    def clean_docker_resources(self):
        """Clean up Docker resources to free memory"""
        print("\nCleaning Docker resources...")
        
        # Stop all containers
        print("1. Stopping all containers...")
        subprocess.run(["docker", "compose", "down"], capture_output=True)
        
        # Remove stopped containers
        print("2. Removing stopped containers...")
        subprocess.run(["docker", "container", "prune", "-f"], capture_output=True)
        
        # Remove unused images
        print("3. Removing unused images...")
        subprocess.run(["docker", "image", "prune", "-f"], capture_output=True)
        
        # Remove unused volumes (careful with this!)
        print("4. Removing unused volumes...")
        subprocess.run(["docker", "volume", "prune", "-f"], capture_output=True)
        
        # Remove unused networks
        print("5. Removing unused networks...")
        subprocess.run(["docker", "network", "prune", "-f"], capture_output=True)
        
        print("Docker cleanup complete!")
    
    def start_dev_environment(self, use_windows_config: bool = True):
        """Start development environment with Windows optimizations"""
        print("\n Starting development environment...")
        
        # Check resources first
        resources = self.check_system_resources()
        if resources['available_memory_gb'] < 2:
            print(f" WARNING: [U+FE0F]  Warning: Low available memory ({resources['available_memory_gb']}GB)")
            print("Consider closing other applications.")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return
        
        # Build command
        cmd = ["docker", "compose"]
        if use_windows_config:
            cmd.extend(["-f", "docker-compose.yml", "-f", "docker-compose.windows.yml"])
        cmd.extend(["--profile", "dev", "up", "-d"])
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(" PASS:  Development environment started successfully!")
            self.show_container_status()
        else:
            print(f" FAIL:  Failed to start environment: {result.stderr}")
    
    def show_container_status(self):
        """Show status of all containers"""
        print("\nContainer Status:")
        result = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
    
    def monitor_resources(self, interval: int = 5):
        """Monitor Docker and system resources"""
        print(f"\nMonitoring resources (updates every {interval} seconds, Ctrl+C to stop)...")
        
        try:
            while True:
                # Clear screen (Windows)
                subprocess.run("cls", shell=True)
                
                # System resources
                sys_resources = self.check_system_resources()
                print("=== System Resources ===")
                print(f"Memory: {sys_resources['available_memory_gb']}GB available / {sys_resources['total_memory_gb']}GB total ({sys_resources['memory_percent_used']}% used)")
                print(f"CPU: {sys_resources['cpu_percent']}% used ({sys_resources['cpu_count']} cores)")
                
                # Docker stats
                print("\n=== Docker Container Stats ===")
                result = subprocess.run(
                    ["docker", "stats", "--no-stream", "--format", 
                     "table {{.Container}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"],
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
    
    def restart_crashed_containers(self):
        """Restart any crashed containers"""
        print("\nChecking for crashed containers...")
        
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "status=exited", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        crashed = result.stdout.strip().split('\n')
        crashed = [c for c in crashed if c]  # Remove empty strings
        
        if crashed:
            print(f"Found {len(crashed)} crashed container(s): {', '.join(crashed)}")
            for container in crashed:
                print(f"Restarting {container}...")
                subprocess.run(["docker", "start", container], capture_output=True)
            print("All crashed containers restarted.")
        else:
            print("No crashed containers found.")
    
    def run_health_check(self):
        """Run comprehensive health check"""
        print("\n=== Docker Health Check ===\n")
        
        # 1. Check Docker Desktop settings
        docker_settings = self.check_docker_desktop_memory()
        print("1. Docker Desktop Settings:")
        print(f"   Memory: {docker_settings['memory_mb']} MB (Recommended: {docker_settings['recommended_memory']} MB)")
        print(f"   CPUs: {docker_settings['cpus']} (Recommended: {docker_settings['recommended_cpus']})")
        
        # 2. Check system resources
        sys_resources = self.check_system_resources()
        print("\n2. System Resources:")
        print(f"   Available Memory: {sys_resources['available_memory_gb']} GB")
        print(f"   Memory Usage: {sys_resources['memory_percent_used']}%")
        print(f"   CPU Usage: {sys_resources['cpu_percent']}%")
        
        # 3. Check container health
        print("\n3. Container Health:")
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}: {{.Status}}"],
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if "unhealthy" in line.lower():
                    print(f"    FAIL:  {line}")
                elif "healthy" in line.lower():
                    print(f"    PASS:  {line}")
                else:
                    print(f"    WARNING: [U+FE0F]  {line}")
        else:
            print("   No containers running")
        
        # 4. Recommendations
        print("\n4. Recommendations:")
        if docker_settings['memory_mb'] != 'unknown' and docker_settings['memory_mb'] < docker_settings['recommended_memory']:
            print(f"    WARNING: [U+FE0F]  Increase Docker Desktop memory to {docker_settings['recommended_memory']} MB")
        if sys_resources['memory_percent_used'] > 80:
            print("    WARNING: [U+FE0F]  System memory usage is high. Consider closing other applications.")
        if sys_resources['available_memory_gb'] < 3:
            print("    WARNING: [U+FE0F]  Low available memory. Docker may become unstable.")
        
        print("\n PASS:  Health check complete!")


def main():
    parser = argparse.ArgumentParser(description='Docker Windows Helper')
    parser.add_argument('command', choices=[
        'start', 'stop', 'clean', 'status', 'monitor', 'restart-crashed', 'health-check'
    ], help='Command to execute')
    parser.add_argument('--no-windows-config', action='store_true',
                      help='Do not use Windows-specific configuration')
    
    args = parser.parse_args()
    
    helper = DockerWindowsHelper()
    
    if args.command == 'start':
        helper.start_dev_environment(use_windows_config=not args.no_windows_config)
    elif args.command == 'stop':
        helper.stop_all_containers()
    elif args.command == 'clean':
        helper.clean_docker_resources()
    elif args.command == 'status':
        helper.show_container_status()
    elif args.command == 'monitor':
        helper.monitor_resources()
    elif args.command == 'restart-crashed':
        helper.restart_crashed_containers()
    elif args.command == 'health-check':
        helper.run_health_check()


if __name__ == "__main__":
    main()