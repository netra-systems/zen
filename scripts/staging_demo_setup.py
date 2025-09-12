#!/usr/bin/env python3
"""
Staging Demo Setup Script for Netra Apex Platform

This script sets up and launches the staging demo environment with flexible
frontend configuration (localhost or GCP deployment).
"""

import os
import sys
import json
import subprocess
import webbrowser
import time
import argparse
import requests
from typing import Dict, Optional, Tuple
from pathlib import Path


class StagingDemoSetup:
    """Manages staging demo setup and launch."""
    
    def __init__(self, frontend_mode: str = "gcp"):
        """
        Initialize staging demo setup.
        
        Args:
            frontend_mode: Either 'localhost' or 'gcp' for frontend deployment
        """
        self.frontend_mode = frontend_mode
        self.project_id = "netra-staging"
        self.backend_service = "backend-staging"
        self.frontend_service = "frontend-staging"
        self.backend_url = "https://backend-staging-906714043974.us-central1.run.app"
        self.frontend_gcp_url = "https://frontend-staging-906714043974.us-central1.run.app"
        self.frontend_local_url = "http://localhost:3000"
        self.region = "us-central1"
        
        # Determine project root
        self.project_root = Path(__file__).resolve().parent.parent
        
    def check_gcloud_auth(self) -> bool:
        """Check if gcloud is authenticated."""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            accounts = json.loads(result.stdout)
            if accounts:
                print(f"✅ Authenticated as: {accounts[0]['account']}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error checking gcloud auth: {e}")
            return False
    
    def authenticate_gcloud(self):
        """Authenticate with gcloud if needed."""
        if not self.check_gcloud_auth():
            print("🔐 Authenticating with gcloud...")
            subprocess.run(["gcloud", "auth", "login"], check=True)
            subprocess.run(["gcloud", "auth", "application-default", "login"], check=True)
    
    def set_project(self):
        """Set the GCP project."""
        print(f"🎯 Setting project to {self.project_id}...")
        subprocess.run(
            ["gcloud", "config", "set", "project", self.project_id],
            check=True
        )
    
    def setup_environment_variables(self) -> Dict[str, str]:
        """Set up required environment variables."""
        env_vars = {
            "ENVIRONMENT": "staging",
            "GCP_PROJECT": self.project_id,
            "BACKEND_URL": self.backend_url,
            "NEXT_PUBLIC_API_URL": self.backend_url,
            "NEXT_PUBLIC_WS_URL": self.backend_url.replace("https://", "wss://"),
            "NEXT_PUBLIC_ENVIRONMENT": "staging",
            "NEXT_PUBLIC_GCP_PROJECT": self.project_id,
            "NODE_ENV": "production" if self.frontend_mode == "gcp" else "development"
        }
        
        # Export environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
            
        print("✅ Environment variables configured:")
        for key, value in env_vars.items():
            print(f"  {key}={value}")
            
        return env_vars
    
    def check_secret_access(self):
        """Check and setup Secret Manager access."""
        print("\n🔑 Checking Secret Manager access...")
        
        secrets_to_check = [
            "jwt-secret-key",
            "openai-api-key",
            "database-url",
            "redis-url"
        ]
        
        for secret in secrets_to_check:
            try:
                result = subprocess.run(
                    [
                        "gcloud", "secrets", "versions", "access", "latest",
                        f"--secret={secret}",
                        f"--project={self.project_id}"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    print(f"  ✅ {secret}: Accessible")
                else:
                    print(f"  ⚠️  {secret}: Not accessible - may need permissions")
            except subprocess.TimeoutExpired:
                print(f"  ⚠️  {secret}: Check timed out")
            except Exception as e:
                print(f"  ⚠️  {secret}: Error checking - {e}")
    
    def check_service_status(self) -> Tuple[bool, bool]:
        """Check if Cloud Run services are deployed and running."""
        backend_ok = False
        frontend_ok = False
        
        print("\n🔍 Checking Cloud Run services...")
        
        # Check backend service
        try:
            result = subprocess.run(
                [
                    "gcloud", "run", "services", "describe",
                    self.backend_service,
                    f"--region={self.region}",
                    f"--project={self.project_id}",
                    "--format=json"
                ],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                service_info = json.loads(result.stdout)
                status = service_info.get("status", {}).get("conditions", [{}])[0].get("status")
                if status == "True":
                    print(f"  ✅ Backend service ({self.backend_service}): Running")
                    backend_ok = True
                else:
                    print(f"  ⚠️  Backend service ({self.backend_service}): Not ready")
            else:
                print(f"  ❌ Backend service ({self.backend_service}): Not found")
        except Exception as e:
            print(f"  ❌ Error checking backend: {e}")
        
        # Check frontend service if using GCP mode
        if self.frontend_mode == "gcp":
            try:
                result = subprocess.run(
                    [
                        "gcloud", "run", "services", "describe",
                        self.frontend_service,
                        f"--region={self.region}",
                        f"--project={self.project_id}",
                        "--format=json"
                    ],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    service_info = json.loads(result.stdout)
                    status = service_info.get("status", {}).get("conditions", [{}])[0].get("status")
                    if status == "True":
                        print(f"  ✅ Frontend service ({self.frontend_service}): Running")
                        frontend_ok = True
                    else:
                        print(f"  ⚠️  Frontend service ({self.frontend_service}): Not ready")
                else:
                    print(f"  ❌ Frontend service ({self.frontend_service}): Not found")
            except Exception as e:
                print(f"  ❌ Error checking frontend: {e}")
        else:
            frontend_ok = True  # Assume localhost will work
            
        return backend_ok, frontend_ok
    
    def deploy_services(self, backend_ok: bool, frontend_ok: bool):
        """Deploy services if they're not running."""
        if not backend_ok:
            print("\n🚀 Deploying backend service to staging...")
            deploy_script = self.project_root / "scripts" / "deploy_to_gcp.py"
            if deploy_script.exists():
                subprocess.run(
                    [
                        sys.executable, str(deploy_script),
                        "--project", self.project_id,
                        "--service", "backend",
                        "--build-local"
                    ],
                    check=True
                )
            else:
                print("  ⚠️  Deploy script not found, please deploy manually")
        
        if self.frontend_mode == "gcp" and not frontend_ok:
            print("\n🚀 Deploying frontend service to staging...")
            deploy_script = self.project_root / "scripts" / "deploy_to_gcp.py"
            if deploy_script.exists():
                subprocess.run(
                    [
                        sys.executable, str(deploy_script),
                        "--project", self.project_id,
                        "--service", "frontend",
                        "--build-local"
                    ],
                    check=True
                )
            else:
                print("  ⚠️  Deploy script not found, please deploy manually")
    
    def start_local_frontend(self):
        """Start the frontend locally if in localhost mode."""
        if self.frontend_mode != "localhost":
            return
            
        print("\n🏃 Starting frontend locally...")
        frontend_dir = self.project_root / "frontend"
        
        if not frontend_dir.exists():
            print("❌ Frontend directory not found")
            return
        
        # Check if node_modules exists
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print("📦 Installing frontend dependencies...")
            subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                check=True
            )
        
        # Start the development server
        print("🚀 Starting Next.js development server...")
        subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            env={**os.environ, **self.setup_environment_variables()}
        )
        
        # Wait for server to start
        print("⏳ Waiting for frontend to start...")
        time.sleep(5)
    
    def test_connectivity(self) -> bool:
        """Test connectivity to services."""
        print("\n🧪 Testing service connectivity...")
        
        # Test backend
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ Backend health check: OK")
            else:
                print(f"  ⚠️  Backend health check: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Backend health check failed: {e}")
            return False
        
        # Test frontend
        frontend_url = self.frontend_local_url if self.frontend_mode == "localhost" else self.frontend_gcp_url
        try:
            response = requests.get(frontend_url, timeout=5)
            if response.status_code == 200:
                print(f"  ✅ Frontend ({self.frontend_mode}): OK")
            else:
                print(f"  ⚠️  Frontend ({self.frontend_mode}): {response.status_code}")
        except Exception as e:
            if self.frontend_mode == "localhost":
                print(f"  ⚠️  Frontend not ready yet, but will open browser anyway")
            else:
                print(f"  ❌ Frontend check failed: {e}")
                return False
        
        return True
    
    def open_browser(self):
        """Open the frontend in the default browser."""
        frontend_url = self.frontend_local_url if self.frontend_mode == "localhost" else self.frontend_gcp_url
        
        print(f"\n🌐 Opening browser to {frontend_url}...")
        webbrowser.open(frontend_url)
        
        print("\n✨ Demo setup complete!")
        print(f"📍 Frontend URL: {frontend_url}")
        print(f"📍 Backend URL: {self.backend_url}")
        print("\n💡 Tips:")
        print("  - Login with your Google account")
        print("  - Try asking questions to test the AI chat functionality")
        print("  - Check the browser console for any errors")
        
        if self.frontend_mode == "localhost":
            print("\n⚠️  Keep this terminal open - it's running the frontend server")
            print("Press Ctrl+C to stop the local frontend server")
    
    def run(self):
        """Run the complete staging demo setup."""
        print("🚀 Netra Apex Staging Demo Setup")
        print(f"📍 Frontend Mode: {self.frontend_mode}")
        print("=" * 50)
        
        try:
            # Step 1: Authenticate
            self.authenticate_gcloud()
            
            # Step 2: Set project
            self.set_project()
            
            # Step 3: Setup environment
            self.setup_environment_variables()
            
            # Step 4: Check secrets
            self.check_secret_access()
            
            # Step 5: Check services
            backend_ok, frontend_ok = self.check_service_status()
            
            # Step 6: Deploy if needed
            self.deploy_services(backend_ok, frontend_ok)
            
            # Step 7: Start local frontend if needed
            if self.frontend_mode == "localhost":
                self.start_local_frontend()
            
            # Step 8: Test connectivity
            self.test_connectivity()
            
            # Step 9: Open browser
            self.open_browser()
            
            # Keep running if localhost mode
            if self.frontend_mode == "localhost":
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n👋 Stopping local frontend server...")
                    
        except KeyboardInterrupt:
            print("\n⚠️  Setup interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup and launch Netra Apex staging demo"
    )
    parser.add_argument(
        "--frontend",
        choices=["localhost", "gcp"],
        default="gcp",
        help="Frontend deployment mode (default: gcp)"
    )
    
    args = parser.parse_args()
    
    setup = StagingDemoSetup(frontend_mode=args.frontend)
    setup.run()


if __name__ == "__main__":
    main()