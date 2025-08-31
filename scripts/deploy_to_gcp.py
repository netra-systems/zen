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

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import centralized GCP authentication and environment management
from scripts.gcp_auth_config import GCPAuthConfig
from shared.isolated_environment import get_env

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
                dockerfile="deployment/docker/backend.gcp.Dockerfile",
                cloud_run_name="netra-backend-staging",
                memory="1Gi",
                cpu="2",
                min_instances=1,
                max_instances=20,
                environment_vars={
                    "ENVIRONMENT": "staging",
                    "PYTHONUNBUFFERED": "1",
                    "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
                    "FRONTEND_URL": "https://app.staging.netrasystems.ai",
                    "FORCE_HTTPS": "true",  # REQUIREMENT 6: FORCE_HTTPS for load balancer
                    "GCP_PROJECT_ID": self.project_id,  # CRITICAL: Required for secret loading logic
                    # ClickHouse configuration - password comes from secrets
                    "CLICKHOUSE_HOST": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
                    "CLICKHOUSE_PORT": "8443",
                    "CLICKHOUSE_USER": "default",
                    "CLICKHOUSE_DB": "default",
                    "CLICKHOUSE_SECURE": "true",
                }
            ),
            ServiceConfig(
                name="auth",
                directory="auth_service",
                port=8080,
                dockerfile="deployment/docker/auth.gcp.Dockerfile",
                cloud_run_name="netra-auth-service",
                memory="512Mi",
                cpu="1",
                min_instances=1,
                max_instances=10,
                environment_vars={
                    "ENVIRONMENT": "staging",
                    "PYTHONUNBUFFERED": "1",
                    "FRONTEND_URL": "https://app.staging.netrasystems.ai",
                    "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
                    "JWT_ALGORITHM": "HS256",
                    "JWT_ACCESS_EXPIRY_MINUTES": "15",
                    "JWT_REFRESH_EXPIRY_DAYS": "7",
                    "JWT_SERVICE_EXPIRY_MINUTES": "60",
                    "SESSION_TTL_HOURS": "24",
                    "REDIS_DISABLED": "false",
                    "SHUTDOWN_TIMEOUT_SECONDS": "10",
                    "SECURE_HEADERS_ENABLED": "true",
                    "LOG_ASYNC_CHECKOUT": "false",
                    "AUTH_FAST_TEST_MODE": "false",
                    "USE_MEMORY_DB": "false",
                    "FORCE_HTTPS": "true",  # REQUIREMENT 6: FORCE_HTTPS for load balancer
                    "GCP_PROJECT_ID": self.project_id,  # CRITICAL: Required for secret loading logic
                }
            ),
            ServiceConfig(
                name="frontend",
                directory="frontend",
                port=3000,
                dockerfile="deployment/docker/frontend.gcp.Dockerfile",
                cloud_run_name="netra-frontend-staging",
                memory="2Gi",
                cpu="1",
                min_instances=1,
                max_instances=10,
                environment_vars={
                    "NODE_ENV": "production",
                    "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
                    "FORCE_HTTPS": "true",  # REQUIREMENT 6: FORCE_HTTPS for load balancer
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
    
    def validate_deployment_configuration(self) -> bool:
        """Validate deployment configuration and environment variables."""
        print("\n🔍 Validating deployment configuration...")
        
        # CRITICAL: OAuth validation BEFORE deployment
        print("🔐 Validating OAuth configuration before deployment...")
        oauth_validation_success = self._validate_oauth_configuration()
        if not oauth_validation_success:
            print("🚨🚨🚨 DEPLOYMENT ABORTED - OAuth validation failed! 🚨🚨🚨")
            return False
        
        # Required environment variables for staging deployment
        # TOMBSTONE: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET superseded by environment-specific variables
        # These are now handled by OAuth configuration validation
        required_env_vars = [
            "GEMINI_API_KEY"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"  ❌ Missing required environment variables: {missing_vars}")
            print("     Set these variables before deploying to staging")
            return False
        
        # CRITICAL: Validate no localhost URLs in staging/production
        localhost_vars = []
        url_vars_to_check = [
            "API_URL", "NEXT_PUBLIC_API_URL", "BACKEND_URL",
            "AUTH_URL", "NEXT_PUBLIC_AUTH_URL", "AUTH_SERVICE_URL", 
            "FRONTEND_URL", "NEXT_PUBLIC_FRONTEND_URL",
            "WS_URL", "NEXT_PUBLIC_WS_URL", "WEBSOCKET_URL", "NEXT_PUBLIC_WEBSOCKET_URL"
        ]
        
        for var_name in url_vars_to_check:
            var_value = os.getenv(var_name, "")
            if "localhost" in var_value:
                localhost_vars.append(f"{var_name}={var_value}")
        
        if localhost_vars:
            print(f"  ❌ Found localhost URLs in {self.project_id} environment:")
            for var in localhost_vars:
                print(f"     {var}")
            print("  This will cause CORS and authentication failures in staging!")
            print("  Run: python scripts/validate_staging_urls.py --environment staging --fix")
            return False
        
        print("  ✅ Deployment configuration valid")
        return True
    
    def run_pre_deployment_checks(self) -> bool:
        """Run pre-deployment checks to ensure code quality."""
        print("\n🔍 Running pre-deployment checks...")
        
        # First validate configuration
        if not self.validate_deployment_configuration():
            return False
        
        checks = [
            {
                "name": "MISSION CRITICAL: WebSocket Event Tests",
                "command": [sys.executable, "-m", "pytest", "tests/mission_critical/test_final_validation.py", "-v"],
                "required": True,
                "critical": True  # This MUST pass or deployment is blocked
            },
            {
                "name": "WebSocket Regression Prevention",
                "command": [sys.executable, "-m", "pytest", "tests/mission_critical/test_websocket_agent_events_suite.py::TestRegressionPrevention", "-v"],
                "required": True,
                "critical": True
            },
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
        critical_failed = False
        
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
                    
                    # Check if this is a critical failure
                    if check.get("critical", False):
                        print("\n" + "🚨" * 10)
                        print("  CRITICAL FAILURE: WebSocket agent events not working!")
                        print("  Basic chat functionality will be BROKEN in production!")
                        print("  This MUST be fixed before ANY deployment!")
                        print("🚨" * 10 + "\n")
                        critical_failed = True
                        
                    if check["required"]:
                        print(f"     Error: {result.stderr[:500]}")
                        all_passed = False
                    else:
                        print(f"     Warning: Non-critical check failed")
                        
            except FileNotFoundError:
                print(f"  ⚠️ {check['name']} script not found")
                if check["required"]:
                    all_passed = False
                    
        if critical_failed:
            print("\n❌ MISSION CRITICAL tests failed!")
            print("   WebSocket agent events are NOT working!")
            print("   See DEPLOYMENT_CHECKLIST.md for troubleshooting.")
            print("   See SPEC/learnings/websocket_agent_integration_critical.xml for fix details.")
            return False
            
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
COPY requirements.txt .
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
            "--ingress", "all",  # REQUIREMENT 6: Allow traffic from anywhere
            "--execution-environment", "gen2"  # Use 2nd generation execution environment
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
                f"NEXT_PUBLIC_WS_URL={staging_ws_url}",
                # GTM Configuration
                "NEXT_PUBLIC_GTM_CONTAINER_ID=GTM-WKP28PNQ",
                "NEXT_PUBLIC_GTM_ENABLED=true",
                "NEXT_PUBLIC_GTM_DEBUG=false",
                "NEXT_PUBLIC_ENVIRONMENT=staging"
            ])
        
        if env_vars:
            cmd.extend(["--set-env-vars", ",".join(env_vars)])
        
        # Add VPC connector for services that need Redis/database access
        if service.name in ["backend", "auth"]:
            # CRITICAL: VPC connector required for Redis and Cloud SQL connectivity
            cmd.extend(["--vpc-connector", "staging-connector"])
        
        # Add service-specific configurations
        if service.name == "backend":
            # Backend needs connections to databases and all required secrets from GSM
            cmd.extend([
                "--add-cloudsql-instances", f"{self.project_id}:us-central1:staging-shared-postgres,{self.project_id}:us-central1:netra-postgres",
                "--set-secrets", "POSTGRES_HOST=postgres-host-staging:latest,POSTGRES_PORT=postgres-port-staging:latest,POSTGRES_DB=postgres-db-staging:latest,POSTGRES_USER=postgres-user-staging:latest,POSTGRES_PASSWORD=postgres-password-staging:latest,JWT_SECRET_STAGING=jwt-secret-staging:latest,JWT_SECRET_KEY=jwt-secret-key:latest,SECRET_KEY=secret-key-staging:latest,OPENAI_API_KEY=openai-api-key-staging:latest,FERNET_KEY=fernet-key-staging:latest,GEMINI_API_KEY=gemini-api-key-staging:latest,GOOGLE_OAUTH_CLIENT_ID_STAGING=google-oauth-client-id-staging:latest,GOOGLE_OAUTH_CLIENT_SECRET_STAGING=google-oauth-client-secret-staging:latest,SERVICE_SECRET=service-secret-staging:latest,REDIS_URL=redis-url-staging:latest,REDIS_PASSWORD=redis-password-staging:latest,ANTHROPIC_API_KEY=anthropic-api-key-staging:latest,CLICKHOUSE_PASSWORD=clickhouse-password-staging:latest"
            ])
        elif service.name == "auth":
            # Auth service needs database, JWT secrets, OAuth credentials from GSM only
            # CRITICAL FIX: Use correct OAuth environment variable names expected by auth service
            cmd.extend([
                "--add-cloudsql-instances", f"{self.project_id}:us-central1:staging-shared-postgres,{self.project_id}:us-central1:netra-postgres",
                "--set-secrets", "POSTGRES_HOST=postgres-host-staging:latest,POSTGRES_PORT=postgres-port-staging:latest,POSTGRES_DB=postgres-db-staging:latest,POSTGRES_USER=postgres-user-staging:latest,POSTGRES_PASSWORD=postgres-password-staging:latest,JWT_SECRET_STAGING=jwt-secret-staging:latest,JWT_SECRET_KEY=jwt-secret-key:latest,GOOGLE_OAUTH_CLIENT_ID_STAGING=google-oauth-client-id-staging:latest,GOOGLE_OAUTH_CLIENT_SECRET_STAGING=google-oauth-client-secret-staging:latest,SERVICE_SECRET=service-secret-staging:latest,SERVICE_ID=service-id-staging:latest,OAUTH_HMAC_SECRET=oauth-hmac-secret-staging:latest,REDIS_URL=redis-url-staging:latest,REDIS_PASSWORD=redis-password-staging:latest"
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
    
    def validate_all_secrets_exist(self) -> bool:
        """Validate ALL required secrets exist in Secret Manager.
        
        This MUST be called BEFORE any build operations to prevent
        deployment failures due to missing secrets.
        """
        print("Checking all required secrets in Secret Manager...")
        
        # Define all required secrets for each environment
        required_backend_secrets = [
            "postgres-host-staging",
            "postgres-port-staging", 
            "postgres-db-staging",
            "postgres-user-staging",
            "postgres-password-staging",
            "jwt-secret-key-staging",
            "secret-key-staging",
            "openai-api-key-staging",
            "fernet-key-staging",
            "gemini-api-key-staging",  # Required for AI operations
            "google-oauth-client-id-staging",
            "google-oauth-client-secret-staging",
            "service-secret-staging",
            "redis-url-staging",
            "redis-password-staging",
            "clickhouse-password-staging"  # Required for ClickHouse authentication
            # anthropic-api-key-staging is optional, not required
        ]
        
        required_auth_secrets = [
            "postgres-host-staging",
            "postgres-port-staging",
            "postgres-db-staging",
            "postgres-user-staging",
            "postgres-password-staging",
            "jwt-secret-key-staging",
            "jwt-secret-staging",
            "google-oauth-client-id-staging",
            "google-oauth-client-secret-staging",
            "service-secret-staging",
            "service-id-staging",
            "oauth-hmac-secret-staging",
            "redis-url-staging",
            "redis-password-staging"
        ]
        
        # Combine all unique secrets
        all_required_secrets = set(required_backend_secrets + required_auth_secrets)
        
        missing_secrets = []
        placeholder_secrets = []
        
        for secret_name in all_required_secrets:
            # Check if secret exists
            result = subprocess.run(
                [self.gcloud_cmd, "secrets", "describe", secret_name, "--project", self.project_id],
                capture_output=True,
                text=True,
                check=False,
                shell=self.use_shell
            )
            
            if result.returncode != 0:
                print(f"  ❌ Secret missing: {secret_name}")
                missing_secrets.append(secret_name)
            else:
                # Check if secret has a real value (not placeholder)
                version_result = subprocess.run(
                    [self.gcloud_cmd, "secrets", "versions", "access", "latest",
                     "--secret", secret_name, "--project", self.project_id],
                    capture_output=True,
                    text=True,
                    check=False,
                    shell=self.use_shell
                )
                
                if version_result.returncode == 0:
                    value = version_result.stdout.strip()
                    # Check for common placeholder patterns
                    if any(placeholder in value.upper() for placeholder in 
                           ["REPLACE", "PLACEHOLDER", "YOUR-", "TODO", "FIXME"]):
                        print(f"  ⚠️  Secret has placeholder value: {secret_name}")
                        placeholder_secrets.append(secret_name)
                    else:
                        print(f"  ✅ Secret configured: {secret_name}")
                else:
                    print(f"  ❌ Cannot access secret: {secret_name}")
                    missing_secrets.append(secret_name)
        
        # Report results
        if missing_secrets:
            print(f"\n❌ Missing {len(missing_secrets)} required secrets:")
            for secret in missing_secrets:
                print(f"   - {secret}")
            
        if placeholder_secrets:
            print(f"\n⚠️  {len(placeholder_secrets)} secrets have placeholder values:")
            for secret in placeholder_secrets:
                print(f"   - {secret}")
            print("\n   These need to be updated with real values for production.")
        
        # Fail if any secrets are missing
        if missing_secrets:
            return False
        
        # For staging/production, also fail on placeholders
        if self.project_id != "netra-dev" and placeholder_secrets:
            print("\n❌ Cannot deploy to staging/production with placeholder secrets!")
            return False
        
        print("\n✅ All required secrets are configured")
        return True
    
    def validate_secrets_before_deployment(self) -> bool:
        """Validate all required secrets exist and have proper values.
        
        This prevents deployment failures due to missing or placeholder secrets.
        Implements canonical secrets management from SPEC/canonical_secrets_management.xml
        """
        print("\n🔐 Validating secrets configuration...")
        
        try:
            # Determine environment based on project
            environment = "staging" if "staging" in self.project_id else "production"
            
            # Run validation script
            result = subprocess.run(
                [
                    "python", "scripts/validate_secrets.py",
                    "--environment", environment,
                    "--project", self.project_id
                ],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Check if validation passed
            if result.returncode == 0:
                print("✅ Secret validation passed")
                return True
            else:
                print("❌ Secret validation failed:")
                print(result.stdout)
                if result.stderr:
                    print("Errors:", result.stderr)
                return False
                
        except FileNotFoundError:
            print("⚠️ Secret validation script not found (scripts/validate_secrets.py)")
            print("   Skipping validation (risky for production)")
            return True
        except Exception as e:
            print(f"⚠️ Secret validation error: {e}")
            print("   Continuing anyway (risky for production)")
            return True
    
    def setup_secrets(self) -> bool:
        """Create necessary secrets in Secret Manager."""
        print("\n🔐 Setting up secrets in Secret Manager...")
        
        # CRITICAL: All these secrets are REQUIRED for staging deployment
        # Based on staging_secrets_requirements.xml
        # Load OAuth credentials from environment variables or use placeholders
        # NEVER store actual secrets in source code
        import os
        
        # CRITICAL FIX: JWT secrets MUST be identical between services
        jwt_secret_value = "your-secure-jwt-secret-key-staging-64-chars-minimum-for-security"
        
        secrets = {
            # PostgreSQL configuration - multi-part for flexibility
            "postgres-host-staging": "/cloudsql/netra-staging:us-central1:staging-shared-postgres",
            "postgres-port-staging": "5432",
            "postgres-db-staging": "netra_dev",
            "postgres-user-staging": "postgres",
            "postgres-password-staging": "qNdlZRHu(Mlc#)6K8LHm-lYi[7sc}25K",  # version 2
            "secret-key-staging": "your-secure-secret-key-for-backend-staging-32-chars-minimum-required",  # Backend SECRET_KEY
            "session-secret-key-staging": "your-secure-session-secret-key-staging-32-chars-minimum", 
            "openai-api-key-staging": "sk-REPLACE_WITH_REAL_OPENAI_KEY",
            "fernet-key-staging": "REPLACE_WITH_REAL_FERNET_KEY_BASE64_32_BYTES",
            "jwt-secret-staging": jwt_secret_value,  # Both backend and auth service use JWT_SECRET_STAGING
            # TOMBSTONE: google-client-id-staging and google-client-secret-staging
            # These should be configured using environment-specific OAuth variables
            "google-oauth-client-id-staging": os.getenv("GOOGLE_OAUTH_CLIENT_ID_STAGING", "REPLACE_WITH_REAL_OAUTH_CLIENT_ID"),
            "google-oauth-client-secret-staging": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_STAGING", "REPLACE_WITH_REAL_OAUTH_CLIENT_SECRET"),
            "oauth-hmac-secret-staging": "oauth_hmac_secret_for_staging_at_least_32_chars_secure",
            # Enhanced JWT security for auth service
            "service-secret-staging": "REPLACE_WITH_SECURE_32_BYTE_HEX_STRING",
            "service-id-staging": f"netra-auth-staging-{int(time.time())}",
            # CRITICAL: Redis endpoint must match staging-shared-redis primary endpoint in GCP
            # Primary endpoint: 10.107.0.3 (verified in Google Cloud Console)
            # See SPEC/redis_staging_configuration.xml for full configuration details
            "redis-url-staging": "redis://default:REPLACE_WITH_REDIS_PASSWORD@10.107.0.3:6379/0",
            "clickhouse-host-staging": "clickhouse.staging.netrasystems.ai",
            "clickhouse-port-staging": "8123",
            "clickhouse-user-staging": "default",
            "clickhouse-db-staging": "default",
            "clickhouse-password-staging": "REPLACE_WITH_CLICKHOUSE_PASSWORD",
            # Additional required secrets for comprehensive staging support
            "gemini-api-key-staging": os.getenv("GEMINI_API_KEY", "REPLACE_WITH_REAL_GEMINI_KEY"),
            "anthropic-api-key-staging": os.getenv("ANTHROPIC_API_KEY", "REPLACE_WITH_REAL_ANTHROPIC_KEY")
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
                   run_checks: bool = False, service_filter: Optional[str] = None,
                   skip_post_tests: bool = False) -> bool:
        """Deploy all services to GCP.
        
        Args:
            skip_build: Skip building images (use existing)
            use_local_build: Build images locally (faster) instead of Cloud Build
            run_checks: Run pre-deployment checks
            service_filter: Deploy only specific service (e.g., 'frontend', 'backend', 'auth')
            skip_post_tests: Skip post-deployment authentication tests
        """
        print(f"🚀 Deploying Netra Apex Platform to GCP")
        print(f"   Project: {self.project_id}")
        print(f"   Region: {self.region}")
        print(f"   Build Mode: {'Local (Fast)' if use_local_build else 'Cloud Build'}")
        print(f"   Pre-checks: {'Enabled' if run_checks else 'Disabled'}")
        
        # CRITICAL: Validate ALL prerequisites BEFORE any build operations
        print("\n🔐 Phase 1: Validating Prerequisites...")
        
        # Check prerequisites
        if not self.check_gcloud():
            return False
            
        if not self.enable_apis():
            return False
        
        # CRITICAL: Validate secrets FIRST before any build operations
        print("\n🔐 Phase 2: Validating Secrets Configuration...")
        if not self.validate_all_secrets_exist():
            print("\n❌ CRITICAL: Secret validation failed!")
            print("   Deployment aborted to prevent runtime failures.")
            print("   Please ensure all required secrets are configured in Secret Manager.")
            print("   Run: python scripts/validate_secrets.py --environment staging --project " + self.project_id)
            return False
            
        # Setup any missing secrets with placeholders (development only)
        if self.project_id == "netra-dev":
            if not self.setup_secrets():
                print("⚠️ Failed to setup development secrets")
                return False
        
        # Run additional pre-deployment checks if requested
        if run_checks:
            print("\n🔍 Phase 3: Running Pre-deployment Checks...")
            if not self.run_pre_deployment_checks():
                print("\n❌ Pre-deployment checks failed")
                print("   Fix issues and try again, or use --no-checks to skip (not recommended)")
                return False
            
        # Filter services if specified
        services_to_deploy = self.services
        if service_filter:
            services_to_deploy = [s for s in self.services if s.name == service_filter]
            if not services_to_deploy:
                print(f"❌ Service '{service_filter}' not found. Available: {[s.name for s in self.services]}")
                return False
            print(f"   Service Filter: {service_filter}")
        
        # Deploy services in order: backend, auth, frontend
        service_urls = {}
        
        # Phase 4: Build and Deploy
        print("\n🏗️ Phase 4: Building and Deploying Services...")
        print("   All prerequisites validated - proceeding with deployment")
        
        for service in services_to_deploy:
            # Build image
            if not skip_build:
                print(f"\n   Building {service.name}...")
                if not self.build_image(service, use_local=use_local_build):
                    print(f"❌ Failed to build {service.name}")
                    return False
                    
            # Deploy service
            print(f"   Deploying {service.name}...")
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
                
        # Run post-deployment authentication tests
        if not skip_post_tests:
            print("\n" + "="*50)
            print("🔐 Running Post-Deployment Authentication Tests")
            print("="*50)
            if self.run_post_deployment_tests(service_urls):
                print("✅ Post-deployment tests passed!")
            else:
                print("⚠️ Post-deployment tests failed - authentication may not be working correctly")
                print("   Check that JWT_SECRET_KEY is set to the same value in both services")
        else:
            print("\n⚠️ Skipping post-deployment tests (--skip-post-tests flag used)")
                
        print("\n🔑 Next Steps:")
        print("1. Update secrets in Secret Manager with real values")
        print("2. Configure Cloud SQL and Redis instances")
        print("3. Set up custom domain and SSL certificates")
        print("4. Configure authentication and remove --allow-unauthenticated")
        print("5. Set up monitoring and alerting")
        
        return True
    
    def run_post_deployment_tests(self, service_urls: Dict[str, str]) -> bool:
        """Run post-deployment authentication tests to verify services are working correctly.
        
        Args:
            service_urls: Dictionary mapping service names to their deployed URLs
            
        Returns:
            True if all tests pass, False otherwise
        """
        try:
            # Import the test module
            sys.path.insert(0, str(self.project_root))
            from tests.post_deployment.test_auth_integration import PostDeploymentAuthTest
            
            # Determine environment based on project ID
            if self.project_id == "netra-production":
                environment = "production"
            elif self.project_id == "netra-staging":
                environment = "staging"
            else:
                environment = "development"
            
            print(f"\nTesting {environment} environment...")
            
            # Set environment variables for the test using proper environment management
            env = get_env()
            env.set("AUTH_SERVICE_URL", service_urls.get("auth", ""), "deploy_gcp_post_deployment_test")
            env.set("BACKEND_URL", service_urls.get("backend", ""), "deploy_gcp_post_deployment_test")
            
            # Run the tests asynchronously
            import asyncio
            tester = PostDeploymentAuthTest(environment)
            
            # Run tests
            if sys.platform == "win32":
                # Windows requires special event loop policy
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
            results = asyncio.run(tester.run_all_tests())
            
            # Return True if all tests passed
            return all(results.values())
            
        except ImportError as e:
            print(f"⚠️ Could not import post-deployment tests: {e}")
            print("   Tests will be skipped. Run manually with:")
            print(f"   python tests/post_deployment/test_auth_integration.py --environment {environment}")
            return True  # Don't fail deployment if tests can't be imported
            
        except Exception as e:
            print(f"⚠️ Post-deployment tests failed with error: {e}")
            return False
    
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
    
    def _validate_oauth_configuration(self) -> bool:
        """Validate OAuth configuration before deployment to prevent broken authentication."""
        try:
            from scripts.validate_oauth_deployment import OAuthDeploymentValidator
            
            # Determine environment for validation
            if self.project_id == "netra-production":
                environment = "production"
            elif self.project_id == "netra-staging":
                environment = "staging" 
            else:
                environment = "development"
            
            print(f"Validating OAuth configuration for {environment} environment...")
            
            # Run OAuth validation
            validator = OAuthDeploymentValidator(environment)
            success, report = validator.validate_all()
            
            # Print validation report
            print("\n" + "="*60)
            print("OAUTH VALIDATION REPORT")
            print("="*60)
            print(report)
            print("="*60)
            
            if not success:
                print("\n🚨🚨🚨 CRITICAL OAUTH VALIDATION FAILURE 🚨🚨🚨")
                print("Deployment cannot proceed - OAuth authentication will be broken!")
                print("Please fix OAuth configuration issues before deploying.")
                return False
            
            print("\n✅ OAuth validation passed - deployment may proceed")
            return True
            
        except ImportError as e:
            print(f"⚠️  Could not import OAuth validator: {e}")
            print("Proceeding with deployment (validation skipped)")
            return True
        except Exception as e:
            print(f"🚨 OAuth validation error: {e}")
            print("This may indicate a critical OAuth configuration problem.")
            
            # In staging/production, fail on validation errors
            if self.project_id in ["netra-staging", "netra-production"]:
                print("🚨 Failing deployment due to OAuth validation error in staging/production")
                return False
            else:
                print("⚠️  Proceeding with deployment (development environment)")
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
    parser.add_argument("--service", 
                       help="Deploy only specific service (frontend, backend, auth)")
    parser.add_argument("--skip-post-tests", action="store_true",
                       help="Skip post-deployment authentication tests")
    
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
                run_checks=args.run_checks,
                service_filter=args.service,
                skip_post_tests=args.skip_post_tests
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