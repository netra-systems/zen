#!/usr/bin/env python3
"""
Unified Staging Build Script
Handles Docker image building and local testing for staging environment
"""

import subprocess
import sys
import os
import time
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any

class StagingBuilder:
    """Manages staging environment builds and deployments"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.docker_compose_file = project_root / "docker-compose.staging.yml"
        
    def check_docker(self) -> bool:
        """Check if Docker is installed and running"""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                print("❌ Docker is not running or not installed")
                return False
            print("✅ Docker is running")
            return True
        except FileNotFoundError:
            print("❌ Docker is not installed")
            return False
            
    def build_backend(self, tag: str = "latest") -> bool:
        """Build backend Docker image"""
        print("\n🔨 Building backend Docker image...")
        dockerfile = self.project_root / "Dockerfile.backend"
        
        if not dockerfile.exists():
            print(f"❌ Backend Dockerfile not found at {dockerfile}")
            return False
            
        cmd = [
            "docker", "build",
            "-t", f"netra-backend:{tag}",
            "-f", str(dockerfile),
            "--build-arg", "BUILDKIT_INLINE_CACHE=1",
            "--cache-from", f"netra-backend:{tag}",
            "--progress", "plain",
            "."
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False,
                text=True,
                check=True
            )
            print("✅ Backend image built successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build backend: {e}")
            return False
            
    def build_frontend(self, tag: str = "latest", api_url: str = "http://localhost:8080") -> bool:
        """Build frontend Docker image"""
        print("\n🔨 Building frontend Docker image...")
        
        # Check which Dockerfile to use
        dockerfiles = [
            self.project_root / "Dockerfile.frontend.staging",
            self.project_root / "frontend" / "Dockerfile.frontend"
        ]
        
        dockerfile = None
        for df in dockerfiles:
            if df.exists():
                dockerfile = df
                break
                
        if not dockerfile:
            print("❌ Frontend Dockerfile not found")
            return False
            
        # Determine build context based on Dockerfile location
        if "staging" in str(dockerfile):
            # Build from root for staging Dockerfile
            context = str(self.project_root)
        else:
            # Build from frontend directory
            context = str(self.project_root / "frontend")
            
        cmd = [
            "docker", "build",
            "-t", f"netra-frontend:{tag}",
            "-f", str(dockerfile),
            "--build-arg", f"NEXT_PUBLIC_API_URL={api_url}",
            "--build-arg", "BUILDKIT_INLINE_CACHE=1",
            "--cache-from", f"netra-frontend:{tag}",
            "--progress", "plain",
            context
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=False,
                text=True,
                check=True
            )
            print("✅ Frontend image built successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build frontend: {e}")
            return False
            
    def start_staging_env(self) -> bool:
        """Start the staging environment using docker-compose"""
        print("\n🚀 Starting staging environment...")
        
        if not self.docker_compose_file.exists():
            print(f"❌ Docker Compose file not found at {self.docker_compose_file}")
            return False
            
        cmd = [
            "docker-compose",
            "-f", str(self.docker_compose_file),
            "up", "-d"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print("✅ Staging environment started")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start staging environment: {e}")
            return False
            
    def stop_staging_env(self) -> bool:
        """Stop the staging environment"""
        print("\n🛑 Stopping staging environment...")
        
        cmd = [
            "docker-compose",
            "-f", str(self.docker_compose_file),
            "down", "-v"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print("✅ Staging environment stopped")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to stop staging environment: {e}")
            return False
            
    def health_check(self, max_retries: int = 30, retry_delay: int = 10) -> bool:
        """Check if all services are healthy"""
        print("\n🏥 Running health checks...")
        
        services = {
            "Backend": "http://localhost:8080/health",
            "Frontend": "http://localhost:3000",
            "API Docs": "http://localhost:8080/docs"
        }
        
        import requests
        
        for service_name, url in services.items():
            print(f"\nChecking {service_name}...")
            
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code in [200, 301, 302]:
                        print(f"✅ {service_name} is healthy")
                        break
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"❌ {service_name} failed health check: {e}")
                        return False
                    else:
                        print(f"  Attempt {attempt + 1}/{max_retries}: Not ready yet...")
                        time.sleep(retry_delay)
                        
        print("\n✅ All services are healthy!")
        return True
        
    def run_tests(self) -> bool:
        """Run staging environment tests"""
        print("\n🧪 Running staging tests...")
        
        # Run backend tests
        cmd = [
            "python", "test_runner.py",
            "--level", "smoke",
            "--staging"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False,
                text=True,
                check=True
            )
            print("✅ Staging tests passed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Staging tests failed: {e}")
            return False
            
    def view_logs(self, service: Optional[str] = None):
        """View logs from staging services"""
        cmd = ["docker-compose", "-f", str(self.docker_compose_file), "logs"]
        
        if service:
            cmd.append(service)
        else:
            cmd.append("--tail=50")
            
        subprocess.run(cmd)
        
def main():
    parser = argparse.ArgumentParser(description="Build and manage staging environment")
    parser.add_argument(
        "--action",
        choices=["build", "start", "stop", "test", "health", "logs", "full"],
        default="full",
        help="Action to perform"
    )
    parser.add_argument(
        "--tag",
        default="latest",
        help="Docker image tag"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8080",
        help="API URL for frontend build"
    )
    parser.add_argument(
        "--service",
        help="Service name for logs"
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip building Docker images"
    )
    
    args = parser.parse_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    builder = StagingBuilder(project_root)
    
    # Check Docker
    if not builder.check_docker():
        sys.exit(1)
        
    # Execute action
    if args.action == "build":
        success = builder.build_backend(args.tag) and builder.build_frontend(args.tag, args.api_url)
        sys.exit(0 if success else 1)
        
    elif args.action == "start":
        success = builder.start_staging_env()
        if success:
            builder.health_check()
        sys.exit(0 if success else 1)
        
    elif args.action == "stop":
        success = builder.stop_staging_env()
        sys.exit(0 if success else 1)
        
    elif args.action == "test":
        success = builder.run_tests()
        sys.exit(0 if success else 1)
        
    elif args.action == "health":
        success = builder.health_check()
        sys.exit(0 if success else 1)
        
    elif args.action == "logs":
        builder.view_logs(args.service)
        
    elif args.action == "full":
        # Full workflow: build, start, health check, test
        print("🚀 Running full staging workflow...")
        
        # Build images
        if not args.skip_build:
            if not builder.build_backend(args.tag):
                print("❌ Backend build failed")
                sys.exit(1)
                
            if not builder.build_frontend(args.tag, args.api_url):
                print("❌ Frontend build failed")
                sys.exit(1)
                
        # Stop any existing environment
        builder.stop_staging_env()
        
        # Start new environment
        if not builder.start_staging_env():
            print("❌ Failed to start environment")
            sys.exit(1)
            
        # Health checks
        if not builder.health_check():
            print("❌ Health checks failed")
            builder.view_logs()
            sys.exit(1)
            
        # Run tests
        if not builder.run_tests():
            print("❌ Tests failed")
            builder.view_logs()
            sys.exit(1)
            
        print("\n✅ Staging environment is ready!")
        print(f"   Frontend: http://localhost:3000")
        print(f"   Backend API: http://localhost:8080")
        print(f"   API Docs: http://localhost:8080/docs")
        print(f"\nRun 'python {__file__} --action stop' to shut down")

if __name__ == "__main__":
    main()