#!/usr/bin/env python3
"""
GCP Deployment Script for Netra Apex Platform
Deploys all three services (backend, auth, frontend) to Google Cloud Run

IMPORTANT: This is the OFFICIAL deployment script. Do NOT create new deployment scripts.
Use this script with appropriate flags for all GCP staging deployments.

Quick Start:
    python scripts/deploy_to_gcp.py --project netra-staging --build-local

See SPEC/gcp_deployment.xml for comprehensive deployment guidelines.
"""

import os
import sys
import subprocess
import json
import time
import argparse
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Import centralized GCP authentication
sys.path.insert(0, str(Path(__file__).parent))
from gcp_auth_config import GCPAuthConfig

# Fix Unicode encoding issues on Windows
if sys.platform == "win32":
    import io
    try:
        # Only wrap if not already wrapped
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    except:
        # If wrapping fails, continue with default encoding
        pass


@dataclass
class ServiceConfig:
    """Configuration for a single service deployment."""
    name: str
    directory: str
    port: int
    dockerfile: str
    cloud_run_name: str
    environment_vars: Dict[str, str]
    memory: str = "512Mi"
    cpu: str = "1"
    min_instances: int = 0
    max_instances: int = 10
    timeout: int = 300


class GCPDeployer:
    """Manages deployment of services to Google Cloud Platform."""
    
    def __init__(self, project_id: str, region: str = "us-central1", service_account_path: Optional[str] = None):
        self.project_id = project_id
        self.region = region
        self.project_root = Path(__file__).parent.parent
        self.registry = f"gcr.io/{project_id}"
        self.service_account_path = service_account_path
        
        # Use gcloud.cmd on Windows
        self.gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        self.docker_cmd = "docker" 
        self.use_shell = sys.platform == "win32"
        
        # Service configurations
        self.services = [
            ServiceConfig(
                name="backend",
                directory="netra_backend",
                port=8888,
                dockerfile="Dockerfile.backend",
                cloud_run_name="netra-backend-staging",
                memory="1Gi",
                cpu="2",
                min_instances=1,
                max_instances=20,
                environment_vars={
                    "ENVIRONMENT": "staging",
                    "PYTHONUNBUFFERED": "1",
                    "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
                    "FRONTEND_URL": "https://frontend.staging.netrasystems.ai",
                }
            ),
            ServiceConfig(
                name="auth",
                directory="auth_service",
                port=8080,
                dockerfile="Dockerfile.auth",
                cloud_run_name="netra-auth-service",
                memory="512Mi",
                cpu="1",
                min_instances=1,
                max_instances=10,
                environment_vars={
                    "ENVIRONMENT": "staging",
                    "PYTHONUNBUFFERED": "1",
                    "FRONTEND_URL": "https://frontend.staging.netrasystems.ai",
                }
            ),
            ServiceConfig(
                name="frontend",
                directory="frontend",
                port=3000,
                dockerfile="Dockerfile.frontend",
                cloud_run_name="netra-frontend-staging",
                memory="1Gi",
                cpu="1",
                min_instances=0,
                max_instances=10,
                environment_vars={
                    "NODE_ENV": "production",
                }
            )
        ]
    
    def check_gcloud(self) -> bool:
        """Check if gcloud CLI is installed and configured."""
        try:
            result = subprocess.run(
                [self.gcloud_cmd, "--version"],
                capture_output=True,
                text=True,
                check=False,
                shell=self.use_shell
            )
            if result.returncode != 0:
                print("❌ gcloud CLI is not installed")
                return False
            
            # Authenticate with service account if provided
            if self.service_account_path:
                if not self.authenticate_with_service_account():
                    return False
                    
            # Check if project is set
            result = subprocess.run(
                [self.gcloud_cmd, "config", "get-value", "project"],
                capture_output=True,
                text=True,
                check=False,
                shell=self.use_shell
            )
            current_project = result.stdout.strip()
            
            if current_project != self.project_id:
                print(f"⚠️ Current project is '{current_project}', switching to '{self.project_id}'")
                subprocess.run(
                    [self.gcloud_cmd, "config", "set", "project", self.project_id],
                    check=True,
                    shell=self.use_shell
                )
                
            print(f"✅ gcloud CLI configured for project: {self.project_id}")
            return True
            
        except FileNotFoundError:
            print("❌ gcloud CLI is not installed")
            print("Please install: https://cloud.google.com/sdk/docs/install")
            return False
    
    def authenticate_with_service_account(self) -> bool:
        """Authenticate using service account key file."""
        # If explicit path provided, use it
        if self.service_account_path:
            service_account_file = Path(self.service_account_path)
            if not service_account_file.exists():
                print(f"❌ Service account file not found: {service_account_file}")
                return False
            return GCPAuthConfig.setup_authentication(service_account_file)
        
        # Otherwise use centralized auth config to find and set up authentication
        print("🔍 Using centralized authentication configuration...")
        return GCPAuthConfig.ensure_authentication()
    
    def run_pre_deployment_checks(self) -> bool:
        """Run pre-deployment checks to ensure code quality."""
        print("\n🔍 Running pre-deployment checks...")
        
        checks = [
            {
                "name": "Architecture Compliance",
                "command": [sys.executable, "scripts/check_architecture_compliance.py"],
                "required": True
            },
            {
                "name": "String Literals Scan",
                "command": [sys.executable, "scripts/scan_string_literals.py"],
                "required": False
            },
            {
                "name": "Integration Tests",
                "command": [sys.executable, "unified_test_runner.py", "--level", "integration", "--no-coverage", "--fast-fail"],
                "required": True
            }
        ]
        
        all_passed = True
        for check in checks:
            print(f"\n  Running {check['name']}...")
            try:
                result = subprocess.run(
                    check["command"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    print(f"  ✅ {check['name']} passed")
                else:
                    print(f"  ❌ {check['name']} failed")
                    if check["required"]:
                        print(f"     Error: {result.stderr[:500]}")
                        all_passed = False
                    else:
                        print(f"     Warning: Non-critical check failed")
                        
            except FileNotFoundError:
                print(f"  ⚠️ {check['name']} script not found")
                if check["required"]:
                    all_passed = False
                    
        if not all_passed:
            print("\n❌ Required checks failed. Please fix issues before deploying.")
            print("   See SPEC/gcp_deployment.xml for deployment guidelines.")
            return False
            
        print("\n✅ All pre-deployment checks passed")
        return True
    
    def enable_apis(self) -> bool:
        """Enable required GCP APIs."""
        print("\n🔧 Enabling required GCP APIs...")
        
        required_apis = [
            "run.googleapis.com",
            "containerregistry.googleapis.com",
            "cloudbuild.googleapis.com",
            "secretmanager.googleapis.com",
            "compute.googleapis.com"
        ]
        
        for api in required_apis:
            print(f"  Enabling {api}...")
            result = subprocess.run(
                [self.gcloud_cmd, "services", "enable", api],
                capture_output=True,
                text=True,
                check=False,
                shell=self.use_shell
            )
            if result.returncode != 0:
                if "already enabled" in result.stderr.lower():
                    print(f"  ✓ {api} already enabled")
                elif "permission_denied" in result.stderr.lower() or "auth_permission_denied" in result.stderr.lower():
                    print(f"  ⚠️ {api} - checking if already enabled...")
                    # Check if the API is already enabled
                    check_result = subprocess.run(
                        [self.gcloud_cmd, "services", "list", "--enabled", "--filter", f"name:{api}"],
                        capture_output=True,
                        text=True,
                        check=False,
                        shell=self.use_shell
                    )
                    if api in check_result.stdout:
                        print(f"  ✓ {api} is already enabled")
                    else:
                        print(f"  ❌ Failed to enable {api}: Permission denied")
                        print(f"     The service account may lack permissions to enable APIs.")
                        print(f"     Please ensure {api} is enabled in the GCP Console.")
                        return False
                else:
                    print(f"  ❌ Failed to enable {api}: {result.stderr}")
                    return False
                
        print("✅ All required APIs enabled")
        return True
    
    def create_dockerfile(self, service: ServiceConfig) -> bool:
        """Create Dockerfile for the service if it doesn't exist."""
        dockerfile_path = self.project_root / service.dockerfile
        
        if dockerfile_path.exists():
            print(f"  Using existing {service.dockerfile}")
            return True
            
        print(f"  Creating {service.dockerfile}...")
        
        if service.name == "backend":
            content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY netra_backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY netra_backend/ ./netra_backend/
COPY shared/ ./shared/

# Set environment variables
ENV PYTHONPATH=/app

# Run the application - use sh to evaluate PORT env var
CMD ["sh", "-c", "uvicorn netra_backend.app.main:app --host 0.0.0.0 --port ${PORT:-8888}"]
"""
        elif service.name == "auth":
            content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY auth_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY auth_service/ ./auth_service/
COPY shared/ ./shared/

# Set environment variables
ENV PYTHONPATH=/app

# Run the application - use sh to evaluate PORT env var
CMD ["sh", "-c", "uvicorn auth_service.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
"""
        elif service.name == "frontend":
            content = """FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files first for better caching
COPY frontend/package*.json ./
RUN npm ci

# Copy all frontend source files
# The .dockerignore file handles exclusions (node_modules, tests, etc.)
COPY frontend/ .
COPY shared/ ../shared/

# Build the application
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Copy built application
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/next.config.ts ./

# Install production dependencies only
RUN npm ci --production

# Set environment variables
ENV NODE_ENV=production

EXPOSE 3000

# Run the application
CMD ["npm", "start"]
"""
        
        with open(dockerfile_path, 'w') as f:
            f.write(content)
            
        print(f"  ✅ Created {service.dockerfile}")
        return True
    
    def build_image_local(self, service: ServiceConfig) -> bool:
        """Build Docker image locally (faster than Cloud Build)."""
        print(f"\n🔨 Building {service.name} Docker image locally...")
        
        # Create Dockerfile if needed
        if not self.create_dockerfile(service):
            return False
        
        image_tag = f"{self.registry}/{service.cloud_run_name}:latest"
        
        # Build locally with Docker
        cmd = [
            self.docker_cmd, "build",
            "-t", image_tag,
            "-f", service.dockerfile,
            "--platform", "linux/amd64",  # Ensure compatibility with Cloud Run
            "."
        ]
        
        print(f"  Building image locally: {image_tag}")
        print(f"  This is 5-10x faster than Cloud Build...")
        
        try:
            # Build the image
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False,
                text=True,
                check=True
            )
            
            print(f"  ✅ Built successfully, now pushing to registry...")
            
            # Configure docker for GCR
            auth_cmd = [self.gcloud_cmd, "auth", "configure-docker", "gcr.io", "--quiet"]
            subprocess.run(auth_cmd, check=True, shell=self.use_shell)
            
            # Push to registry
            push_cmd = [self.docker_cmd, "push", image_tag]
            result = subprocess.run(
                push_cmd,
                cwd=self.project_root,
                capture_output=False,
                text=True,
                check=True
            )
            
            print(f"✅ {service.name} image built and pushed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build {service.name} locally: {e}")
            print("   Tip: Ensure Docker Desktop is running")
            return False
    
    def build_image_cloud(self, service: ServiceConfig) -> bool:
        """Build Docker image using Cloud Build (slower but no local resources needed)."""
        print(f"\n🔨 Building {service.name} Docker image with Cloud Build...")
        
        # Create Dockerfile if needed
        if not self.create_dockerfile(service):
            return False
        
        image_tag = f"{self.registry}/{service.cloud_run_name}:latest"
        
        # Create cloudbuild.yaml for this build
        cloudbuild_config = {
            "steps": [{
                "name": "gcr.io/cloud-builders/docker",
                "args": ["build", "-t", image_tag, "-f", service.dockerfile, "."]
            }],
            "images": [image_tag]
        }
        
        cloudbuild_file = self.project_root / f"cloudbuild-{service.name}.yaml"
        with open(cloudbuild_file, 'w') as f:
            yaml.dump(cloudbuild_config, f)
        
        cmd = [
            self.gcloud_cmd, "builds", "submit",
            "--config", str(cloudbuild_file),
            "--timeout", "45m",  # Increased timeout for dependency installation
            "--machine-type", "e2-highcpu-8",
            "."
        ]
        
        print(f"  Building image: {image_tag}")
        print(f"  Note: Cloud Build is slower. Use --build-local for faster builds.")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False,
                text=True,
                check=True,
                shell=self.use_shell
            )
            print(f"✅ {service.name} image built successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build {service.name}: {e}")
            return False
    
    def build_image(self, service: ServiceConfig, use_local: bool = False) -> bool:
        """Build Docker image for the service."""
        if use_local:
            return self.build_image_local(service)
        else:
            return self.build_image_cloud(service)
    
    def deploy_service(self, service: ServiceConfig) -> Tuple[bool, Optional[str]]:
        """Deploy service to Cloud Run."""
        print(f"\n🚀 Deploying {service.name} to Cloud Run...")
        
        image_tag = f"{self.registry}/{service.cloud_run_name}:latest"
        
        # Build base command - automatically route traffic to new revision once healthy
        cmd = [
            self.gcloud_cmd, "run", "deploy", service.cloud_run_name,
            "--image", image_tag,
            "--platform", "managed",
            "--region", self.region,
            "--port", str(service.port),
            "--memory", service.memory,
            "--cpu", service.cpu,
            "--min-instances", str(service.min_instances),
            "--max-instances", str(service.max_instances),
            "--timeout", str(service.timeout),
            "--allow-unauthenticated",  # Remove for production
            "--no-cpu-throttling",
            "--ingress", "all"  # Allow traffic from anywhere
        ]
        
        # Add environment variables
        env_vars = []
        for key, value in service.environment_vars.items():
            env_vars.append(f"{key}={value}")
        
        # Add service-specific environment variables
        if service.name == "frontend":
            # Frontend needs API URLs - use staging URLs for consistent configuration
            staging_api_url = "https://api.staging.netrasystems.ai"
            staging_auth_url = "https://auth.staging.netrasystems.ai"
            staging_ws_url = "wss://api.staging.netrasystems.ai/ws"
            env_vars.extend([
                f"NEXT_PUBLIC_API_URL={staging_api_url}",
                f"NEXT_PUBLIC_AUTH_URL={staging_auth_url}",
                f"NEXT_PUBLIC_WS_URL={staging_ws_url}"
            ])
        
        if env_vars:
            cmd.extend(["--set-env-vars", ",".join(env_vars)])
        
        # Add service-specific configurations
        if service.name == "backend":
            # Backend needs connections to databases and all required secrets
            cmd.extend([
                "--add-cloudsql-instances", f"{self.project_id}:us-central1:netra-postgres",
                "--set-secrets", "DATABASE_URL=database-url-staging:latest,JWT_SECRET_KEY=jwt-secret-key-staging:latest,SECRET_KEY=session-secret-key-staging:latest,OPENAI_API_KEY=openai-api-key-staging:latest,FERNET_KEY=fernet-key-staging:latest,GEMINI_API_KEY=gemini-api-key-staging:latest,GOOGLE_CLIENT_ID=google-client-id-staging:latest,GOOGLE_CLIENT_SECRET=google-client-secret-staging:latest,SERVICE_SECRET=service-secret-staging:latest,CLICKHOUSE_DEFAULT_PASSWORD=clickhouse-default-password-staging:latest"
            ])
        elif service.name == "auth":
            # Auth service needs database, JWT secrets, OAuth credentials, and enhanced security
            cmd.extend([
                "--add-cloudsql-instances", f"{self.project_id}:us-central1:netra-postgres",
                "--set-secrets", "DATABASE_URL=database-url-staging:latest,JWT_SECRET_KEY=jwt-secret-staging:latest,GOOGLE_CLIENT_ID=google-client-id-staging:latest,GOOGLE_CLIENT_SECRET=google-client-secret-staging:latest,SERVICE_SECRET=service-secret-staging:latest,SERVICE_ID=service-id-staging:latest"
            ])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                shell=self.use_shell
            )
            
            # Extract service URL from output
            url = None
            for line in result.stdout.split('\n'):
                if "Service URL:" in line:
                    url = line.split("Service URL:")[1].strip()
                    break
                    
            print(f"✅ {service.name} deployed successfully")
            if url:
                print(f"   URL: {url}")
                
            # Ensure traffic is routed to the latest revision
            self.update_traffic_to_latest(service.cloud_run_name)
            
            return True, url
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to deploy {service.name}: {e.stderr}")
            return False, None
    
    def wait_for_revision_ready(self, service_name: str, max_wait: int = 60) -> bool:
        """Wait for the latest revision to be ready before routing traffic."""
        print(f"  ⏳ Waiting for {service_name} revision to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                # Check if the latest revision is ready
                cmd = [
                    self.gcloud_cmd, "run", "revisions", "list",
                    "--service", service_name,
                    "--platform", "managed",
                    "--region", self.region,
                    "--format", "value(status.conditions[0].status)",
                    "--limit", "1"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    shell=self.use_shell
                )
                
                if result.returncode == 0 and "True" in result.stdout:
                    print(f"  ✅ Revision is ready")
                    return True
                    
            except Exception:
                pass
            
            time.sleep(5)
        
        print(f"  ⚠️ Revision not ready after {max_wait} seconds")
        return False
    
    def update_traffic_to_latest(self, service_name: str) -> bool:
        """Update traffic to route 100% to the latest revision."""
        print(f"  📡 Updating traffic to latest revision for {service_name}...")
        
        # First wait for the revision to be ready
        if not self.wait_for_revision_ready(service_name):
            print(f"  ⚠️ Skipping traffic update - revision not ready")
            return False
        
        try:
            # Update traffic to send 100% to the latest revision
            cmd = [
                self.gcloud_cmd, "run", "services", "update-traffic",
                service_name,
                "--to-latest",
                "--platform", "managed",
                "--region", self.region
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                shell=self.use_shell
            )
            
            if result.returncode == 0:
                print(f"  ✅ Traffic updated to latest revision")
                return True
            else:
                # This may fail if the service doesn't exist yet or if traffic is already at latest
                # which is okay
                if "already receives 100%" in result.stderr or "not found" in result.stderr:
                    print(f"  ✓ Traffic already routing to latest revision")
                    return True
                else:
                    print(f"  ⚠️ Could not update traffic: {result.stderr[:200]}")
                    return False
                    
        except Exception as e:
            print(f"  ⚠️ Error updating traffic: {e}")
            return False
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get the URL of a deployed Cloud Run service."""
        try:
            result = subprocess.run(
                [
                    self.gcloud_cmd, "run", "services", "describe",
                    service_name,
                    "--platform", "managed",
                    "--region", self.region,
                    "--format", "value(status.url)"
                ],
                capture_output=True,
                text=True,
                check=False,
                shell=self.use_shell
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
                
        except Exception:
            pass
            
        return None
    
    def setup_secrets(self) -> bool:
        """Create necessary secrets in Secret Manager."""
        print("\n🔐 Setting up secrets in Secret Manager...")
        
        # CRITICAL: All these secrets are REQUIRED for staging deployment
        # Based on staging_secrets_requirements.xml
        # Load OAuth credentials from environment variables or use placeholders
        # NEVER store actual secrets in source code
        import os
        
        secrets = {
            # Note: Using standard psycopg2 format with sslmode=require
            # DatabaseManager will automatically convert to ssl=require for asyncpg
            "database-url-staging": "postgresql://netra_user:REPLACE_WITH_REAL_PASSWORD@34.132.142.103:5432/netra?sslmode=require",
            "jwt-secret-key-staging": "your-secure-jwt-secret-key-staging-32-chars-minimum",
            "session-secret-key-staging": "your-secure-session-secret-key-staging-32-chars-minimum", 
            "openai-api-key-staging": "sk-REPLACE_WITH_REAL_OPENAI_KEY",
            "fernet-key-staging": "REPLACE_WITH_REAL_FERNET_KEY_BASE64_32_BYTES",
            "jwt-secret-staging": "your-secure-jwt-secret-key-staging-32-chars-minimum",  # Auth service uses this name
            "google-client-id-staging": os.getenv("GOOGLE_CLIENT_ID", "REPLACE_WITH_REAL_GOOGLE_CLIENT_ID"),
            "google-client-secret-staging": os.getenv("GOOGLE_CLIENT_SECRET", "REPLACE_WITH_REAL_GOOGLE_CLIENT_SECRET"),
            # Enhanced JWT security for auth service
            "service-secret-staging": "REPLACE_WITH_SECURE_32_BYTE_HEX_STRING",
            "service-id-staging": f"netra-auth-staging-{int(time.time())}"
        }
        
        for name, value in secrets.items():
            # Check if secret exists
            result = subprocess.run(
                [self.gcloud_cmd, "secrets", "describe", name],
                capture_output=True,
                check=False,
                shell=self.use_shell
            )
            
            if result.returncode != 0:
                # Create secret
                print(f"  Creating secret: {name}")
                subprocess.run(
                    [self.gcloud_cmd, "secrets", "create", name],
                    check=True,
                    shell=self.use_shell
                )
                
                # Add secret version
                subprocess.run(
                    [self.gcloud_cmd, "secrets", "versions", "add", name, "--data-file=-"],
                    input=value.encode(),
                    check=True,
                    shell=self.use_shell
                )
            else:
                print(f"  Secret already exists: {name}")
                
        print("✅ Secrets configured")
        return True
    
    def health_check(self, service_urls: Dict[str, str]) -> bool:
        """Perform health checks on deployed services."""
        print("\n🏥 Running health checks...")
        
        import requests
        
        all_healthy = True
        
        for service_name, url in service_urls.items():
            if not url:
                print(f"  ⚠️ {service_name}: No URL available")
                continue
                
            # Determine health endpoint
            if service_name == "frontend":
                health_url = url
            else:
                health_url = f"{url}/health"
                
            print(f"  Checking {service_name} at {health_url}...")
            
            try:
                response = requests.get(health_url, timeout=10)
                if response.status_code in [200, 301, 302]:
                    print(f"  ✅ {service_name} is healthy")
                else:
                    print(f"  ❌ {service_name} returned status {response.status_code}")
                    all_healthy = False
                    
            except Exception as e:
                print(f"  ❌ {service_name} health check failed: {e}")
                all_healthy = False
                
        return all_healthy
    
    def deploy_all(self, skip_build: bool = False, use_local_build: bool = False, 
                   run_checks: bool = False) -> bool:
        """Deploy all services to GCP.
        
        Args:
            skip_build: Skip building images (use existing)
            use_local_build: Build images locally (faster) instead of Cloud Build
            run_checks: Run pre-deployment checks
        """
        print(f"🚀 Deploying Netra Apex Platform to GCP")
        print(f"   Project: {self.project_id}")
        print(f"   Region: {self.region}")
        print(f"   Build Mode: {'Local (Fast)' if use_local_build else 'Cloud Build'}")
        print(f"   Pre-checks: {'Enabled' if run_checks else 'Disabled'}")
        
        # Run pre-deployment checks if requested
        if run_checks:
            if not self.run_pre_deployment_checks():
                print("\n❌ Pre-deployment checks failed")
                print("   Fix issues and try again, or use --no-checks to skip (not recommended)")
                return False
        
        # Check prerequisites
        if not self.check_gcloud():
            return False
            
        if not self.enable_apis():
            return False
            
        if not self.setup_secrets():
            print("⚠️ Failed to setup secrets, continuing anyway...")
            
        # Deploy services in order: backend, auth, frontend
        service_urls = {}
        
        for service in self.services:
            # Build image
            if not skip_build:
                if not self.build_image(service, use_local=use_local_build):
                    print(f"❌ Failed to build {service.name}")
                    return False
                    
            # Deploy service
            success, url = self.deploy_service(service)
            if not success:
                print(f"❌ Failed to deploy {service.name}")
                return False
                
            service_urls[service.name] = url
            
            # Wait a bit for service to start
            if url:
                print(f"  Waiting for {service.name} to start...")
                time.sleep(10)
                
        # Run health checks
        print("\n" + "="*50)
        if self.health_check(service_urls):
            print("\n✅ All services deployed successfully!")
        else:
            print("\n⚠️ Some services may not be fully healthy")
            
        # Print summary
        print("\n📋 Deployment Summary:")
        print("="*50)
        for service_name, url in service_urls.items():
            if url:
                print(f"{service_name:10} : {url}")
                
        print("\n🔑 Next Steps:")
        print("1. Update secrets in Secret Manager with real values")
        print("2. Configure Cloud SQL and Redis instances")
        print("3. Set up custom domain and SSL certificates")
        print("4. Configure authentication and remove --allow-unauthenticated")
        print("5. Set up monitoring and alerting")
        
        return True
    
    def cleanup(self) -> bool:
        """Clean up deployed services."""
        print("\n🧹 Cleaning up deployments...")
        
        for service in self.services:
            print(f"  Deleting {service.cloud_run_name}...")
            result = subprocess.run(
                [
                    self.gcloud_cmd, "run", "services", "delete",
                    service.cloud_run_name,
                    "--platform", "managed",
                    "--region", self.region,
                    "--quiet"
                ],
                capture_output=True,
                check=False,
                shell=self.use_shell
            )
            
            if result.returncode == 0:
                print(f"  ✅ Deleted {service.cloud_run_name}")
            else:
                print(f"  ⚠️ Could not delete {service.cloud_run_name}")
                
        return True


def main():
    """Main entry point for GCP deployment.
    
    IMPORTANT: This is the OFFICIAL deployment script for Netra Apex.
    Do NOT create new deployment scripts. Use this with appropriate flags.
    
    Examples:
        # Default: Fast local build (no checks for testing deployment issues)
        python scripts/deploy_to_gcp.py --project netra-staging --build-local
        
        # With checks (for production readiness)
        python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks
        
        # Cloud Build (slower)
        python scripts/deploy_to_gcp.py --project netra-staging
        
        # Skip build (use existing images)
        python scripts/deploy_to_gcp.py --project netra-staging --skip-build
        
        # Clean up resources
        python scripts/deploy_to_gcp.py --project netra-staging --cleanup
    
    See SPEC/gcp_deployment.xml for comprehensive deployment guidelines.
    """
    parser = argparse.ArgumentParser(
        description="Deploy Netra Apex Platform to GCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Default deployment (fast, no checks):
    python scripts/deploy_to_gcp.py --project netra-staging --build-local
    
  With pre-deployment checks:
    python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks
    
  Cloud Build (slower):
    python scripts/deploy_to_gcp.py --project netra-staging
    
See SPEC/gcp_deployment.xml for detailed guidelines.
        """
    )
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument("--region", default="us-central1", help="GCP Region (default: us-central1)")
    parser.add_argument("--skip-build", action="store_true", 
                       help="Skip building images (use existing)")
    parser.add_argument("--build-local", action="store_true",
                       help="Build images locally (5-10x faster than Cloud Build)")
    parser.add_argument("--run-checks", action="store_true",
                       help="Run pre-deployment checks (architecture, tests, etc.) - optional for staging")
    parser.add_argument("--cleanup", action="store_true", 
                       help="Clean up deployments")
    parser.add_argument("--service-account", 
                       help="Path to service account JSON key file (default: config/netra-staging-7a1059b7cf26.json)")
    
    args = parser.parse_args()
    
    # Print warning if not using recommended flags
    if not args.cleanup and not args.build_local and not args.skip_build:
        print("\n⚠️ NOTE: Using Cloud Build (slow). Consider using --build-local for 5-10x faster builds.")
        print("   Example: python scripts/deploy_to_gcp.py --project {} --build-local\n".format(args.project))
        time.sleep(2)
    
    deployer = GCPDeployer(args.project, args.region, service_account_path=args.service_account)
    
    try:
        if args.cleanup:
            success = deployer.cleanup()
        else:
            success = deployer.deploy_all(
                skip_build=args.skip_build,
                use_local_build=args.build_local,
                run_checks=args.run_checks
            )
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Deployment failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()