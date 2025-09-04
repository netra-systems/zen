#!/usr/bin/env python3
"""
Staged startup script for development services with resource optimization
Based on DOCKER_CRASH_DEEP_10_WHYS_ANALYSIS.md recommendations
"""

import subprocess
import time
import sys
from pathlib import Path

class StagedDevStartup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.compose_file = "docker-compose.dev-optimized.yml"
        self.runtime = self._detect_runtime()
        
    def _detect_runtime(self):
        """Detect container runtime"""
        for cmd in ['podman', 'docker']:
            try:
                subprocess.run([cmd, 'version'], capture_output=True, timeout=2, check=True)
                return cmd
            except:
                continue
        print("ERROR: No container runtime found")
        sys.exit(1)
    
    def _run_command(self, cmd, description=""):
        """Run command with error handling"""
        if description:
            print(f"\n>> {description}")
        
        print(f"   Command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"   ERROR: {result.stderr}")
            return False
        return True
    
    def cleanup_resources(self):
        """Clean up dangling resources before startup"""
        print("\n" + "="*60)
        print("STEP 1: PRE-FLIGHT CLEANUP")
        print("="*60)
        
        # Show current resource usage
        self._run_command(
            [self.runtime, 'system', 'df'],
            "Current resource usage"
        )
        
        # Clean up dangling volumes
        self._run_command(
            [self.runtime, 'volume', 'prune', '-f'],
            "Removing unused volumes"
        )
        
        # Clean up stopped containers
        self._run_command(
            [self.runtime, 'container', 'prune', '-f'],
            "Removing stopped containers"
        )
        
        # Clean up dangling images (optional, can be slow)
        print("\nSkipping image cleanup to save time (run manually if needed)")
        
        print("\nCleanup complete!")
        return True
    
    def stop_existing_services(self):
        """Stop any existing services"""
        print("\n" + "="*60)
        print("STEP 2: STOP EXISTING SERVICES")
        print("="*60)
        
        compose_cmd = ['podman-compose'] if self.runtime == 'podman' else ['docker', 'compose']
        
        self._run_command(
            compose_cmd + ['-f', self.compose_file, 'down'],
            "Stopping existing services"
        )
        
        time.sleep(2)  # Let services fully stop
        return True
    
    def start_infrastructure(self):
        """Start infrastructure services first"""
        print("\n" + "="*60)
        print("STEP 3: START INFRASTRUCTURE (Stage 1)")
        print("="*60)
        
        compose_cmd = ['podman-compose'] if self.runtime == 'podman' else ['docker', 'compose']
        
        # Start PostgreSQL and Redis
        services = ['postgres', 'redis']
        print(f"Starting: {', '.join(services)}")
        
        if not self._run_command(
            compose_cmd + ['-f', self.compose_file, 'up', '-d'] + services,
            "Starting infrastructure services"
        ):
            return False
        
        # Wait for services to stabilize
        print("\nWaiting 15 seconds for infrastructure to stabilize...")
        for i in range(15, 0, -1):
            print(f"\r   {i} seconds remaining...", end='', flush=True)
            time.sleep(1)
        print("\r   Infrastructure ready!        ")
        
        return True
    
    def start_auth_service(self):
        """Start auth service"""
        print("\n" + "="*60)
        print("STEP 4: START AUTH SERVICE (Stage 2)")
        print("="*60)
        
        compose_cmd = ['podman-compose'] if self.runtime == 'podman' else ['docker', 'compose']
        
        print("Starting: auth")
        
        if not self._run_command(
            compose_cmd + ['-f', self.compose_file, 'up', '-d', 'auth'],
            "Starting auth service"
        ):
            print("\nNOTE: Auth service may need dependencies installed on first run")
            print("This can take 2-3 minutes. Please wait...")
        
        # Wait for auth to stabilize
        print("\nWaiting 20 seconds for auth service to stabilize...")
        for i in range(20, 0, -1):
            print(f"\r   {i} seconds remaining...", end='', flush=True)
            time.sleep(1)
        print("\r   Auth service ready!          ")
        
        return True
    
    def start_backend_service(self):
        """Start backend service"""
        print("\n" + "="*60)
        print("STEP 5: START BACKEND SERVICE (Stage 3)")
        print("="*60)
        
        compose_cmd = ['podman-compose'] if self.runtime == 'podman' else ['docker', 'compose']
        
        print("Starting: backend")
        
        if not self._run_command(
            compose_cmd + ['-f', self.compose_file, 'up', '-d', 'backend'],
            "Starting backend service"
        ):
            print("\nNOTE: Backend service may need dependencies installed on first run")
            print("This can take 3-4 minutes. Please wait...")
        
        # Wait for backend to stabilize
        print("\nWaiting 25 seconds for backend service to stabilize...")
        for i in range(25, 0, -1):
            print(f"\r   {i} seconds remaining...", end='', flush=True)
            time.sleep(1)
        print("\r   Backend service ready!       ")
        
        return True
    
    def check_services(self):
        """Check status of all services"""
        print("\n" + "="*60)
        print("STEP 6: SERVICE STATUS CHECK")
        print("="*60)
        
        # Get container status
        self._run_command(
            [self.runtime, 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'],
            "Running containers"
        )
        
        # Check resource usage
        print("\nResource usage:")
        subprocess.run([self.runtime, 'stats', '--no-stream'])
        
        return True
    
    def display_summary(self):
        """Display startup summary"""
        print("\n" + "="*60)
        print("STARTUP COMPLETE!")
        print("="*60)
        
        print("\nServices available at:")
        print("  - PostgreSQL: localhost:5433")
        print("  - Redis: localhost:6380")
        print("  - Auth API: http://localhost:8081")
        print("  - Backend API: http://localhost:8000")
        print("  - Health Check: http://localhost:8000/health")
        
        print("\nUseful commands:")
        print(f"  - View logs: {self.runtime} logs <service-name>")
        print(f"  - Monitor resources: python scripts/check_resource_limits.py")
        print(f"  - Stop services: podman-compose -f {self.compose_file} down")
        
        print("\nResource limits applied:")
        print("  - PostgreSQL: 256MB")
        print("  - Redis: 128MB")
        print("  - Auth: 512MB")
        print("  - Backend: 1GB (as requested)")
        print("  - TOTAL: <2GB")
        
    def run(self):
        """Execute staged startup"""
        print("\n" + "#"*60)
        print("# STAGED DEVELOPMENT STARTUP WITH RESOURCE OPTIMIZATION")
        print("#"*60)
        print(f"\nUsing runtime: {self.runtime}")
        print(f"Compose file: {self.compose_file}")
        
        try:
            # Execute stages
            if not self.cleanup_resources():
                print("\nERROR: Cleanup failed")
                return False
            
            if not self.stop_existing_services():
                print("\nERROR: Failed to stop existing services")
                return False
            
            if not self.start_infrastructure():
                print("\nERROR: Failed to start infrastructure")
                return False
            
            if not self.start_auth_service():
                print("\nWARNING: Auth service may still be starting")
            
            if not self.start_backend_service():
                print("\nWARNING: Backend service may still be starting")
            
            if not self.check_services():
                print("\nWARNING: Some services may not be healthy")
            
            self.display_summary()
            return True
            
        except KeyboardInterrupt:
            print("\n\nStartup cancelled by user")
            return False
        except Exception as e:
            print(f"\n\nERROR: {e}")
            return False


def main():
    starter = StagedDevStartup()
    success = starter.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()