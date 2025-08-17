#!/usr/bin/env python3
"""
Start Auth Service for local development
Manages Docker containers and service startup
"""
import os
import sys
import subprocess
import time
import requests
from pathlib import Path

class AuthServiceManager:
    """Manage auth service startup and dependencies"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.docker_compose_file = self.project_root / "docker-compose.auth.yml"
        
    def start_dependencies(self):
        """Start Redis and PostgreSQL containers"""
        print("Starting auth service dependencies...")
        
        cmd = [
            "docker-compose",
            "-f", str(self.docker_compose_file),
            "up", "-d",
            "redis", "postgres"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Failed to start dependencies: {result.stderr}")
            return False
        
        print("Dependencies started successfully")
        
        # Wait for services to be ready
        print("Waiting for services to be ready...")
        time.sleep(5)
        
        return True
    
    def start_auth_service(self):
        """Start the auth service"""
        print("Starting auth service...")
        
        # Change to auth_service directory
        os.chdir(self.project_root / "auth_service")
        
        # Start with uvicorn
        cmd = [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8081",
            "--reload"
        ]
        
        # Start in subprocess
        process = subprocess.Popen(cmd)
        
        # Wait for service to be ready
        print("Waiting for auth service to start...")
        for i in range(30):
            try:
                response = requests.get("http://localhost:8081/health")
                if response.status_code == 200:
                    print("Auth service is ready!")
                    return process
            except:
                pass
            time.sleep(1)
        
        print("Auth service failed to start")
        process.terminate()
        return None
    
    def stop_all(self):
        """Stop all services"""
        print("Stopping all services...")
        
        cmd = [
            "docker-compose",
            "-f", str(self.docker_compose_file),
            "down"
        ]
        
        subprocess.run(cmd)
        print("All services stopped")
    
    def run(self):
        """Run the auth service with dependencies"""
        try:
            # Start dependencies
            if not self.start_dependencies():
                print("Failed to start dependencies")
                return 1
            
            # Start auth service
            process = self.start_auth_service()
            if not process:
                print("Failed to start auth service")
                self.stop_all()
                return 1
            
            print("\n" + "="*50)
            print("Auth Service is running!")
            print("URL: http://localhost:8081")
            print("Health: http://localhost:8081/health")
            print("Docs: http://localhost:8081/docs")
            print("="*50 + "\n")
            print("Press Ctrl+C to stop")
            
            # Wait for interrupt
            process.wait()
            
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.stop_all()
            return 0
        except Exception as e:
            print(f"Error: {e}")
            self.stop_all()
            return 1

def main():
    """Main entry point"""
    manager = AuthServiceManager()
    return manager.run()

if __name__ == "__main__":
    sys.exit(main())