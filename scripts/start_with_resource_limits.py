#!/usr/bin/env python3
"""
Start containers with resource limits using Docker or Podman
Automatically detects and uses the available runtime
"""

import subprocess
import sys
import time
import platform
from pathlib import Path
import json

class ResourceLimitedContainerStarter:
    def __init__(self):
        self.runtime = self._detect_runtime()
        self.compose_tool = self._get_compose_tool()
        self.project_root = Path(__file__).parent.parent
        self.compose_file = self.project_root / "docker-compose.resource-optimized.yml"
        
    def _detect_runtime(self) -> str:
        """Detect available container runtime"""
        # Try Podman first on Windows (generally better performance)
        if platform.system() == "Windows":
            runtimes = ['podman', 'docker']
        else:
            runtimes = ['docker', 'podman']
            
        for cmd in runtimes:
            try:
                result = subprocess.run(
                    [cmd, 'version'], 
                    capture_output=True, 
                    timeout=2
                )
                if result.returncode == 0:
                    print(f"✅ Found container runtime: {cmd}")
                    return cmd
            except:
                continue
        
        print("❌ No container runtime (Docker/Podman) found!")
        print("\nPlease install one of:")
        print("  - Docker Desktop: https://docs.docker.com/desktop/")
        print("  - Podman: https://podman.io/getting-started/installation")
        sys.exit(1)
    
    def _get_compose_tool(self) -> list:
        """Get the appropriate compose command"""
        if self.runtime == 'podman':
            # Check for podman-compose
            try:
                subprocess.run(['podman-compose', '--version'], capture_output=True, timeout=2)
                return ['podman-compose']
            except:
                # Fall back to podman compose (newer versions)
                return ['podman', 'compose']
        else:
            # Docker - try docker compose (v2) first
            try:
                subprocess.run(['docker', 'compose', 'version'], capture_output=True, timeout=2)
                return ['docker', 'compose']
            except:
                # Fall back to docker-compose (v1)
                return ['docker-compose']
    
    def cleanup_old_containers(self):
        """Clean up any existing containers to free resources"""
        print("\n🧹 Cleaning up old containers...")
        
        # Stop existing containers
        cmd = self.compose_tool + ['-f', str(self.compose_file), 'down', '--volumes']
        subprocess.run(cmd, capture_output=True)
        
        # Prune system to free resources
        if self.runtime == 'podman':
            # Podman-specific cleanup
            subprocess.run(['podman', 'system', 'prune', '-f'], capture_output=True)
            subprocess.run(['podman', 'volume', 'prune', '-f'], capture_output=True)
        else:
            # Docker-specific cleanup
            subprocess.run(['docker', 'system', 'prune', '-f'], capture_output=True)
            subprocess.run(['docker', 'volume', 'prune', '-f'], capture_output=True)
        
        print("✅ Cleanup complete")
    
    def check_wsl_memory(self):
        """Check WSL2 memory configuration on Windows"""
        if platform.system() != "Windows":
            return
        
        print("\n🖥️ Checking WSL2 configuration...")
        
        # Check if .wslconfig exists
        wslconfig_path = Path.home() / '.wslconfig'
        if not wslconfig_path.exists():
            print("⚠️  WARNING: .wslconfig not found!")
            print(f"   Copy .wslconfig from project to: {wslconfig_path}")
            print("   Then run: wsl --shutdown")
            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)
        else:
            print("✅ .wslconfig found")
    
    def start_containers_staged(self):
        """Start containers in stages to prevent resource spikes"""
        print("\n🚀 Starting containers with resource limits...")
        print(f"   Using: {self.runtime}")
        print(f"   Compose file: {self.compose_file}")
        
        # Stage 1: Infrastructure (PostgreSQL, Redis)
        print("\n📦 Stage 1: Starting infrastructure services...")
        services_stage1 = ['postgres', 'redis']
        cmd = self.compose_tool + ['-f', str(self.compose_file), 'up', '-d'] + services_stage1
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to start infrastructure: {result.stderr}")
            return False
        
        print("   Waiting for infrastructure to be ready...")
        time.sleep(10)
        
        # Stage 2: Auth service
        print("\n📦 Stage 2: Starting auth service...")
        cmd = self.compose_tool + ['-f', str(self.compose_file), 'up', '-d', 'auth']
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to start auth: {result.stderr}")
            return False
        
        print("   Waiting for auth to be ready...")
        time.sleep(10)
        
        # Stage 3: Backend service
        print("\n📦 Stage 3: Starting backend service...")
        cmd = self.compose_tool + ['-f', str(self.compose_file), 'up', '-d', 'backend']
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to start backend: {result.stderr}")
            return False
        
        print("\n✅ All core services started successfully!")
        return True
    
    def check_container_health(self):
        """Check health status of running containers"""
        print("\n🔍 Checking container health...")
        
        if self.runtime == 'podman':
            cmd = ['podman', 'ps', '--format', 'json']
        else:
            cmd = ['docker', 'ps', '--format', 'json']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout:
                # Parse JSON output
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        containers.append(json.loads(line))
                
                print(f"\n📊 Running containers: {len(containers)}")
                for container in containers:
                    name = container.get('Names', 'unknown')
                    status = container.get('Status', 'unknown')
                    print(f"   • {name}: {status}")
                
                return len(containers) > 0
        except Exception as e:
            print(f"⚠️  Could not check health: {e}")
        
        return False
    
    def show_resource_usage(self):
        """Display current resource usage"""
        print("\n📈 Current resource usage:")
        
        if self.runtime == 'podman':
            cmd = ['podman', 'stats', '--no-stream']
        else:
            cmd = ['docker', 'stats', '--no-stream']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("⚠️  Could not get resource stats")
        except:
            print("⚠️  Stats command timed out")
    
    def run(self):
        """Main execution flow"""
        print("="*60)
        print("RESOURCE-LIMITED CONTAINER STARTUP")
        print("="*60)
        
        # Pre-flight checks
        self.check_wsl_memory()
        
        # Cleanup old containers
        self.cleanup_old_containers()
        
        # Start containers with staging
        if not self.start_containers_staged():
            print("\n❌ Failed to start containers")
            sys.exit(1)
        
        # Wait a bit for stabilization
        print("\n⏳ Waiting for services to stabilize...")
        time.sleep(5)
        
        # Check health
        if self.check_container_health():
            # Show resource usage
            self.show_resource_usage()
            
            print("\n" + "="*60)
            print("✅ CONTAINERS STARTED SUCCESSFULLY")
            print("="*60)
            print("\nNext steps:")
            print("  1. Monitor resources: python scripts/monitor_docker_resources.py")
            print("  2. Check logs: podman logs <container-name>")
            print("  3. Access services:")
            print("     - Backend: http://localhost:8000")
            print("     - Auth: http://localhost:8081")
            print("     - Frontend: http://localhost:3000 (if started)")
        else:
            print("\n⚠️  Some containers may not be healthy")
            print("Check logs for details")


def main():
    try:
        starter = ResourceLimitedContainerStarter()
        starter.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Startup cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()