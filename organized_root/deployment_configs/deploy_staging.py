#!/usr/bin/env python3
"""
Netra Reliable Staging Deployment Script
Python equivalent of deploy-staging-reliable.ps1
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


# Configuration
PROJECT_ID = "netra-staging"
REGION = "us-central1"
REGISTRY = f"{REGION}-docker.pkg.dev"
REGISTRY_PATH = f"{REGISTRY}/{PROJECT_ID}/netra-containers"
BUILD_CONTEXT = "."  # Assuming the script is run from the project root

# Service names (MUST match Cloud Run service names exactly)
BACKEND_SERVICE = "netra-backend-staging"
FRONTEND_SERVICE = "netra-frontend-staging"
AUTH_SERVICE = "netra-auth-service"

# URLs for frontend build
STAGING_API_URL = "https://api.staging.netrasystems.ai"
STAGING_WS_URL = "wss://api.staging.netrasystems.ai/ws"

# Colors for terminal output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'
    ENDC = '\033[0m'


def print_colored(message: str, color: str = Colors.ENDC):
    """Print colored output to terminal."""
    print(f"{color}{message}{Colors.ENDC}")


def run_command(cmd: List[str], check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e


def check_command_exists(cmd: str) -> bool:
    """Check if a command exists in the system PATH."""
    try:
        # On Windows, use 'where' command to check if the command exists
        if sys.platform == "win32":
            result = subprocess.run(["where", cmd], capture_output=True, text=True)
            return result.returncode == 0
        else:
            subprocess.run([cmd, "--version"], capture_output=True, check=False)
            return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def check_prerequisites():
    """Check if all required tools are installed."""
    print_colored("Checking prerequisites...", Colors.YELLOW)
    missing_tools = []
    
    if not check_command_exists("gcloud"):
        missing_tools.append("gcloud (Google Cloud SDK)")
    
    if not check_command_exists("docker"):
        missing_tools.append("docker")
    
    if missing_tools:
        print_colored(f"Error: Missing required tools: {', '.join(missing_tools)}", Colors.RED)
        print_colored("Please install the missing tools and ensure they are in your system's PATH.", Colors.RED)
        sys.exit(1)
    
    # Check if Docker daemon is running
    try:
        run_command(["docker", "info"], capture_output=True)
    except subprocess.CalledProcessError:
        print_colored("Error: Docker daemon is not running or not responding. Please start Docker.", Colors.RED)
        sys.exit(1)
    
    print_colored("  [OK] Prerequisites met", Colors.GREEN)


def ensure_authentication(skip_auth: bool = False) -> Optional[str]:
    """Ensure proper GCP authentication."""
    if skip_auth:
        print_colored("[1/5] Skipping authentication setup (Warning: Deployment or Push may fail if not already authenticated)...", Colors.YELLOW)
        return None
    
    print_colored("Ensuring proper authentication...", Colors.YELLOW)
    
    # Check for key file in multiple locations
    script_dir = Path(__file__).parent
    key_paths = [
        os.environ.get("GCP_STAGING_SA_KEY_PATH"),
        script_dir / "gcp-staging-sa-key.json",
        script_dir / "secrets" / "gcp-staging-sa-key.json",
        script_dir / "terraform-gcp" / "gcp-staging-sa-key.json",
        Path.home() / ".gcp" / "staging-sa-key.json"
    ]
    
    key_file = None
    for path in key_paths:
        if path and Path(path).exists():
            key_file = str(path)
            print_colored(f"  Found key file: {key_file}", Colors.GREEN)
            break
    
    if not key_file:
        print_colored("  No service account key found!", Colors.RED)
        print_colored("  Running setup script to create one...", Colors.YELLOW)
        
        # Run setup script
        setup_script_path = script_dir / "setup-staging-auth.ps1"
        if setup_script_path.exists():
            try:
                run_command(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(setup_script_path)])
            except subprocess.CalledProcessError:
                print_colored("Failed to execute setup script!", Colors.RED)
                sys.exit(1)
            
            # Define keyfile location after setup and verify
            key_file = str(script_dir / "gcp-staging-sa-key.json")
            if not Path(key_file).exists():
                print_colored(f"Setup script ran, but key file was not created at {key_file}!", Colors.RED)
                sys.exit(1)
        else:
            print_colored(f"Setup script not found at {setup_script_path}!", Colors.RED)
            sys.exit(1)
    
    # Authenticate with service account
    print_colored("  Authenticating with service account...", Colors.YELLOW)
    try:
        run_command(["gcloud", "auth", "activate-service-account", f"--key-file={key_file}"])
    except subprocess.CalledProcessError:
        print_colored("  Authentication failed, retrying...", Colors.YELLOW)
        time.sleep(2)
        try:
            run_command(["gcloud", "auth", "activate-service-account", f"--key-file={key_file}"])
        except subprocess.CalledProcessError:
            print_colored("Authentication failed after retry!", Colors.RED)
            sys.exit(1)
    
    # Configure Docker
    print_colored("  Configuring Docker authentication...", Colors.YELLOW)
    try:
        run_command(["gcloud", "auth", "configure-docker", REGISTRY, "--quiet"])
    except subprocess.CalledProcessError:
        print_colored("Failed to configure Docker authentication!", Colors.RED)
        sys.exit(1)
    
    # Set project
    try:
        run_command(["gcloud", "config", "set", "project", PROJECT_ID, "--quiet"])
    except subprocess.CalledProcessError:
        print_colored("Failed to set GCP project!", Colors.RED)
        sys.exit(1)
    
    print_colored("  [OK] Authentication configured successfully", Colors.GREEN)
    return key_file


def push_image_with_retry(image: str, max_retries: int = 3, skip_auth: bool = False) -> bool:
    """Push Docker image with retry logic."""
    for i in range(1, max_retries + 1):
        print_colored(f"  Pushing {image} (attempt {i}/{max_retries})...", Colors.CYAN)
        
        try:
            run_command(["docker", "push", image])
            print_colored("    [OK] Pushed successfully", Colors.GREEN)
            return True
        except subprocess.CalledProcessError as e:
            if i < max_retries:
                print_colored(f"    Push failed (Exit Code {e.returncode}). Review the error above.", Colors.YELLOW)
                if not skip_auth:
                    print_colored("    Re-authenticating and retrying...", Colors.YELLOW)
                    try:
                        ensure_authentication()
                    except Exception:
                        print_colored("Re-authentication failed during retry!", Colors.RED)
                else:
                    print_colored("    Cannot re-authenticate because skip_auth was used.", Colors.YELLOW)
                time.sleep(5)
    
    return False


def get_cloud_run_url(service_name: str) -> Optional[str]:
    """Get the URL of a Cloud Run service."""
    try:
        result = run_command([
            "gcloud", "run", "services", "describe", service_name,
            "--platform", "managed",
            "--region", REGION,
            "--project", PROJECT_ID,
            "--format", "value(status.url)"
        ], capture_output=True)
        
        url = result.stdout.strip()
        if url:
            return url
        return None
    except subprocess.CalledProcessError:
        print_colored(f"Failed to retrieve URL for {service_name}.", Colors.RED)
        return None


def build_docker_images(auth_service_exists: bool):
    """Build all Docker images."""
    print_colored("[2/5] Building Docker images...", Colors.GREEN)
    
    # Backend
    print_colored("  Building backend...", Colors.CYAN)
    try:
        run_command([
            "docker", "build",
            "-f", "Dockerfile.backend",
            "-t", f"{REGISTRY_PATH}/backend:staging",
            "-t", f"{REGISTRY_PATH}/backend:latest",
            BUILD_CONTEXT
        ])
    except subprocess.CalledProcessError:
        print_colored("Backend build failed!", Colors.RED)
        sys.exit(1)
    
    # Frontend
    print_colored("  Building frontend...", Colors.CYAN)
    script_dir = Path(__file__).parent
    
    if (script_dir / "Dockerfile.frontend.staging").exists():
        dockerfile = "Dockerfile.frontend.staging"
    elif (script_dir / "Dockerfile.frontend.optimized").exists():
        dockerfile = "Dockerfile.frontend.optimized"
    else:
        dockerfile = "Dockerfile"  # Fallback
    
    print_colored(f"  Using Dockerfile: {dockerfile}", Colors.CYAN)
    
    try:
        run_command([
            "docker", "build",
            "-f", dockerfile,
            "--build-arg", f"NEXT_PUBLIC_API_URL={STAGING_API_URL}",
            "--build-arg", f"NEXT_PUBLIC_WS_URL={STAGING_WS_URL}",
            "-t", f"{REGISTRY_PATH}/frontend:staging",
            "-t", f"{REGISTRY_PATH}/frontend:latest",
            BUILD_CONTEXT
        ])
    except subprocess.CalledProcessError:
        print_colored("Frontend build failed!", Colors.RED)
        sys.exit(1)
    
    # Auth Service
    if auth_service_exists:
        print_colored("  Building auth service...", Colors.CYAN)
        try:
            run_command([
                "docker", "build",
                "-f", "Dockerfile.auth",
                "-t", f"{REGISTRY_PATH}/auth:staging",
                "-t", f"{REGISTRY_PATH}/auth:latest",
                BUILD_CONTEXT
            ])
        except subprocess.CalledProcessError:
            print_colored("Auth service build failed!", Colors.RED)
            sys.exit(1)
    
    print_colored("  [OK] All images built successfully", Colors.GREEN)


def push_images(auth_service_exists: bool, skip_auth: bool = False):
    """Push all Docker images to Artifact Registry."""
    print_colored("[3/5] Pushing images to Artifact Registry...", Colors.GREEN)
    
    images = [
        f"{REGISTRY_PATH}/backend:staging",
        f"{REGISTRY_PATH}/frontend:staging"
    ]
    
    if auth_service_exists:
        images.append(f"{REGISTRY_PATH}/auth:staging")
    
    for image in images:
        if not push_image_with_retry(image, skip_auth=skip_auth):
            print_colored(f"Failed to push {image} after multiple attempts!", Colors.RED)
            sys.exit(1)
    
    print_colored("  [OK] All images pushed successfully", Colors.GREEN)


def run_migrations(skip_migrations: bool = False):
    """Run database migrations."""
    if skip_migrations:
        print_colored("[3.5/5] Skipping database migrations (skip_migrations flag)", Colors.YELLOW)
        return
    
    print_colored("[3.5/5] Running database migrations...", Colors.GREEN)
    
    script_dir = Path(__file__).parent
    migration_script_path = script_dir / "run-staging-migrations.ps1"
    
    if migration_script_path.exists():
        print_colored("  Checking and running migrations if needed...", Colors.CYAN)
        
        try:
            run_command(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(migration_script_path)])
            print_colored("  Migrations completed successfully", Colors.GREEN)
        except subprocess.CalledProcessError as e:
            print_colored("  Warning: Migration check returned non-zero exit code", Colors.YELLOW)
            print_colored("  Continuing with deployment (migrations may have already been applied)", Colors.YELLOW)
    else:
        print_colored("  Migration script not found, skipping migrations", Colors.YELLOW)
        print_colored(f"  Expected at: {migration_script_path}", Colors.GRAY)


def deploy_services(auth_service_exists: bool):
    """Deploy all services to Cloud Run."""
    print_colored("[4/5] Deploying services to Cloud Run...", Colors.GREEN)
    
    # Deploy Backend
    print_colored("  Deploying backend...", Colors.CYAN)
    try:
        run_command([
            "gcloud", "run", "deploy", BACKEND_SERVICE,
            "--image", f"{REGISTRY_PATH}/backend:staging",
            "--platform", "managed",
            "--region", REGION,
            "--project", PROJECT_ID,
            "--allow-unauthenticated",
            "--port", "8080",
            "--memory", "1Gi",
            "--cpu", "1",
            "--min-instances", "0",
            "--max-instances", "10",
            "--set-env-vars=ENVIRONMENT=staging,SERVICE_NAME=backend",
            "--add-cloudsql-instances=netra-staging:us-central1:staging-shared-postgres",
            "--set-secrets=DATABASE_URL=database-url-staging:latest,GEMINI_API_KEY=gemini-api-key-staging:latest,JWT_SECRET_KEY=jwt-secret-staging:latest,FERNET_KEY=fernet-key-staging:latest",
            "--quiet"
        ])
    except subprocess.CalledProcessError:
        print_colored("Backend deployment failed!", Colors.RED)
        sys.exit(1)
    
    # Deploy Frontend
    print_colored("  Deploying frontend...", Colors.CYAN)
    try:
        run_command([
            "gcloud", "run", "deploy", FRONTEND_SERVICE,
            "--image", f"{REGISTRY_PATH}/frontend:staging",
            "--platform", "managed",
            "--region", REGION,
            "--project", PROJECT_ID,
            "--allow-unauthenticated",
            "--port", "3000",
            "--memory", "512Mi",
            "--cpu", "1",
            "--min-instances", "0",
            "--max-instances", "10",
            f"--set-env-vars=NODE_ENV=production,NEXT_PUBLIC_API_URL={STAGING_API_URL},NEXT_PUBLIC_WS_URL={STAGING_WS_URL}",
            "--quiet"
        ])
    except subprocess.CalledProcessError:
        print_colored("Frontend deployment failed!", Colors.RED)
        sys.exit(1)
    
    # Deploy Auth Service if exists
    if auth_service_exists:
        print_colored("  Deploying auth service...", Colors.CYAN)
        try:
            run_command([
                "gcloud", "run", "deploy", AUTH_SERVICE,
                "--image", f"{REGISTRY_PATH}/auth:staging",
                "--platform", "managed",
                "--region", REGION,
                "--project", PROJECT_ID,
                "--allow-unauthenticated",
                "--port", "8001",
                "--memory", "1Gi",
                "--cpu", "1",
                "--min-instances", "1",
                "--max-instances", "2",
                "--set-env-vars=ENVIRONMENT=staging,SERVICE_NAME=auth",
                "--add-cloudsql-instances=netra-staging:us-central1:staging-shared-postgres",
                "--set-secrets=DATABASE_URL=database-url-staging:latest,JWT_SECRET_KEY=jwt-secret-staging:latest,FERNET_KEY=fernet-key-staging:latest,GOOGLE_CLIENT_ID=google-client-id-staging:latest,GOOGLE_CLIENT_SECRET=google-client-secret-staging:latest",
                "--quiet"
            ])
        except subprocess.CalledProcessError:
            print_colored("Auth service deployment failed!", Colors.RED)
            sys.exit(1)
    
    print_colored("  [OK] All services deployed successfully", Colors.GREEN)


def run_health_checks(backend_url: str, frontend_url: str):
    """Run health checks on deployed services."""
    print_colored("")
    print_colored("Running health checks (waiting 10s for services to stabilize)...", Colors.YELLOW)
    time.sleep(10)
    
    if backend_url:
        try:
            import urllib.request
            response = urllib.request.urlopen(f"{backend_url}/health", timeout=30)
            if response.getcode() == 200:
                print_colored("  [OK] Backend is healthy", Colors.GREEN)
            else:
                print_colored(f"  [WARN] Backend returned status code {response.getcode()}", Colors.YELLOW)
        except Exception as e:
            print_colored(f"  [WARN] Backend health check failed (service may still be starting): {e}", Colors.YELLOW)
    
    if frontend_url:
        try:
            import urllib.request
            response = urllib.request.urlopen(frontend_url, timeout=30)
            if response.getcode() == 200:
                print_colored("  [OK] Frontend is accessible", Colors.GREEN)
            else:
                print_colored(f"  [WARN] Frontend returned status code {response.getcode()}", Colors.YELLOW)
        except Exception as e:
            print_colored(f"  [WARN] Frontend check failed (service may still be starting): {e}", Colors.YELLOW)


def run_error_monitoring(skip_error_monitoring: bool = False):
    """Run post-deployment error monitoring."""
    if skip_error_monitoring:
        print_colored("")
        print_colored("Skipping error monitoring check...", Colors.YELLOW)
        return
    
    print_colored("")
    print_colored("Running post-deployment error monitoring...", Colors.YELLOW)
    
    # Record deployment time for error analysis
    deployment_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    # Wait a moment for any immediate errors to appear in GCP Error Reporting
    print_colored("  Waiting 15s for logs to propagate...", Colors.CYAN)
    time.sleep(15)
    
    script_dir = Path(__file__).parent
    error_monitor_path = script_dir / "scripts" / "staging_error_monitor.py"
    
    if error_monitor_path.exists():
        print_colored("  Checking for deployment-related errors...", Colors.CYAN)
        
        # Check if python/python3 is available
        python_cmd = "python3" if check_command_exists("python3") else "python"
        
        if check_command_exists(python_cmd):
            try:
                result = run_command([
                    python_cmd, str(error_monitor_path),
                    "--deployment-time", deployment_time,
                    "--project-id", PROJECT_ID,
                    "--service", "netra-backend"
                ], check=False)
                
                if result.returncode == 0:
                    print_colored("  [OK] No critical deployment errors detected", Colors.GREEN)
                elif result.returncode == 1:
                    print_colored("  [ERROR] Critical deployment errors detected!", Colors.RED)
                    print_colored("  Consider rolling back the deployment.", Colors.YELLOW)
                    
                    # Check if the session is interactive
                    if sys.stdin.isatty():
                        continue_deploy = input("Continue despite errors? (y/N): ")
                        if continue_deploy.lower() != "y":
                            print_colored("Deployment marked as failed by user due to critical errors.", Colors.RED)
                            sys.exit(1)
                    else:
                        # If non-interactive (CI/CD), fail the deployment automatically
                        print_colored("Deployment failed automatically due to critical errors detected in non-interactive mode.", Colors.RED)
                        sys.exit(1)
                else:
                    print_colored(f"  [WARN] Error monitoring script failed unexpectedly (Exit Code: {result.returncode})", Colors.YELLOW)
            except Exception as e:
                print_colored(f"  [WARN] Failed to run error monitoring: {e}", Colors.YELLOW)
        else:
            print_colored("  [WARN] Python executable (python or python3) not found. Cannot run error monitoring.", Colors.YELLOW)
    else:
        print_colored(f"  [WARN] Error monitoring script not found at {error_monitor_path}", Colors.YELLOW)


def save_deployment_info(frontend_url: str, backend_url: str, auth_url: str):
    """Save deployment information to JSON file."""
    deployment_info = {
        "frontend_url": frontend_url,
        "backend_url": backend_url,
        "auth_url": auth_url,
        "project_id": PROJECT_ID,
        "region": REGION,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        script_dir = Path(__file__).parent
        json_path = script_dir / "deployment-info.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(deployment_info, f, indent=2)
        print_colored("Deployment info saved to deployment-info.json", Colors.YELLOW)
    except Exception:
        print_colored("Warning: Failed to save deployment-info.json", Colors.YELLOW)


def run_pre_deployment_tests(skip_tests: bool = False) -> bool:
    """Run pre-deployment validation tests."""
    if skip_tests:
        print_colored("[PRE-DEPLOY] Skipping pre-deployment tests (--skip-tests flag)", Colors.YELLOW)
        return True
    
    print_colored("[PRE-DEPLOY] Running pre-deployment validation...", Colors.GREEN)
    
    # Step 1: Run critical path tests
    print_colored("  Running critical path tests...", Colors.CYAN)
    try:
        result = run_command([
            "python", "-m", "test_framework.test_runner",
            "--level", "critical",
            "--fast-fail",
            "--no-coverage"
        ], check=False, capture_output=True)
        
        if result.returncode != 0:
            print_colored("  [FAIL] Critical path tests failed", Colors.RED)
            print_colored("  Output:", Colors.RED)
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return False
        print_colored("  [OK] Critical path tests passed", Colors.GREEN)
    except Exception as e:
        print_colored(f"  [FAIL] Failed to run critical tests: {e}", Colors.RED)
        return False
    
    # Step 2: Validate staging configuration
    print_colored("  Validating staging configuration...", Colors.CYAN)
    try:
        script_path = Path(__file__).parent.parent.parent / "scripts" / "validate_staging_config.py"
        if script_path.exists():
            result = run_command(["python", str(script_path)], check=False, capture_output=True)
            if result.returncode != 0:
                print_colored("  [FAIL] Configuration validation failed", Colors.RED)
                print_colored("  Run 'python scripts/validate_staging_config.py' for details", Colors.YELLOW)
                return False
            print_colored("  [OK] Configuration validation passed", Colors.GREEN)
        else:
            print_colored("  [WARN] Configuration validator not found, skipping", Colors.YELLOW)
    except Exception as e:
        print_colored(f"  [WARN] Configuration validation skipped: {e}", Colors.YELLOW)
    
    # Step 3: Test startup sequence
    print_colored("  Testing startup sequence simulation...", Colors.CYAN)
    try:
        script_path = Path(__file__).parent.parent.parent / "scripts" / "test_staging_startup.py"
        if script_path.exists():
            result = run_command([
                "python", str(script_path), "--simulate"
            ], check=False, capture_output=True)
            if result.returncode != 0:
                print_colored("  [FAIL] Startup sequence test failed", Colors.RED)
                return False
            print_colored("  [OK] Startup sequence test passed", Colors.GREEN)
        else:
            print_colored("  [WARN] Startup tester not found, skipping", Colors.YELLOW)
    except Exception as e:
        print_colored(f"  [WARN] Startup test skipped: {e}", Colors.YELLOW)
    
    print_colored("  [OK] Pre-deployment validation passed", Colors.GREEN)
    return True


def main():
    """Main function to orchestrate the deployment."""
    parser = argparse.ArgumentParser(description="Netra Reliable Staging Deployment")
    parser.add_argument("--skip-health-checks", action="store_true", help="Skip health checks after deployment")
    parser.add_argument("--skip-auth", action="store_true", help="Skip authentication setup")
    parser.add_argument("--build-only", action="store_true", help="Build images only, don't deploy")
    parser.add_argument("--deploy-only", action="store_true", help="Deploy only, don't build")
    parser.add_argument("--skip-error-monitoring", action="store_true", help="Skip error monitoring after deployment")
    parser.add_argument("--skip-migrations", action="store_true", help="Skip database migrations")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pre-deployment tests (NOT RECOMMENDED)")
    
    args = parser.parse_args()
    
    print_colored("=" * 48, Colors.BLUE)
    print_colored("    NETRA RELIABLE STAGING DEPLOYMENT", Colors.BLUE)
    print_colored("=" * 48, Colors.BLUE)
    print("")
    
    # Check if auth service exists
    script_dir = Path(__file__).parent
    auth_service_exists = (script_dir / "Dockerfile.auth").exists()
    
    # Pre-Step: Check Prerequisites
    check_prerequisites()
    
    # Pre-Deployment Validation
    if not args.deploy_only:
        if not run_pre_deployment_tests(args.skip_tests):
            print_colored("\n[FAILED] PRE-DEPLOYMENT TESTS FAILED", Colors.RED)
            print_colored("Deployment aborted to prevent pushing broken code to staging.", Colors.RED)
            print_colored("Fix the issues and try again, or use --skip-tests to bypass (NOT RECOMMENDED).", Colors.YELLOW)
            sys.exit(1)
    
    # Step 1: Authentication
    print_colored("[1/5] Setting up authentication...", Colors.GREEN)
    key_file = ensure_authentication(args.skip_auth)
    
    if not args.deploy_only:
        # Step 2: Build Docker images
        build_docker_images(auth_service_exists)
        
        # Step 3: Push images
        push_images(auth_service_exists, args.skip_auth)
        
        print_colored("  [OK] All images pushed successfully", Colors.GREEN)
    
    if args.build_only:
        print("")
        print_colored("Build completed. Skipping deployment.", Colors.YELLOW)
        sys.exit(0)
    
    # Step 3.5: Run Database Migrations
    run_migrations(args.skip_migrations)
    
    # Step 4: Deploy to Cloud Run
    deploy_services(auth_service_exists)
    
    # Step 5: Get service URLs and Post-Deployment Checks
    print_colored("[5/5] Retrieving service URLs and running checks...", Colors.GREEN)
    
    backend_url = get_cloud_run_url(BACKEND_SERVICE)
    frontend_url = get_cloud_run_url(FRONTEND_SERVICE)
    auth_url = get_cloud_run_url(AUTH_SERVICE) if auth_service_exists else ""
    
    # Health checks
    if not args.skip_health_checks:
        run_health_checks(backend_url, frontend_url)
    
    # Error monitoring
    run_error_monitoring(args.skip_error_monitoring)
    
    # Summary
    print("")
    print_colored("=" * 48, Colors.GREEN)
    print_colored("    DEPLOYMENT COMPLETED SUCCESSFULLY", Colors.GREEN)
    print_colored("=" * 48, Colors.GREEN)
    print("")
    print_colored("Service URLs:", Colors.CYAN)
    if frontend_url:
        print_colored(f"  Frontend:  {frontend_url}", Colors.GREEN)
    if backend_url:
        print_colored(f"  Backend:   {backend_url}", Colors.GREEN)
    if auth_url:
        print_colored(f"  Auth:      {auth_url}", Colors.GREEN)
    
    print("")
    print_colored("Custom domains (if configured):", Colors.CYAN)
    print_colored("  Frontend:  https://app.staging.netrasystems.ai", Colors.BLUE)
    print_colored("  Backend:   https://api.staging.netrasystems.ai", Colors.BLUE)
    print("")
    
    # Save deployment info
    save_deployment_info(frontend_url, backend_url, auth_url)


if __name__ == "__main__":
    main()