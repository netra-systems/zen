#!/usr/bin/env python3
"""
Run database migrations on Cloud SQL using a dedicated Cloud Run Job.

This script:
1. Builds and pushes a lightweight migrations container
2. Creates/updates a Cloud Run Job for migrations
3. Executes the job and waits for completion
4. Reports success/failure

Usage:
    python scripts/run_cloud_migrations.py --project netra-staging --env staging
    python scripts/run_cloud_migrations.py --project netra-prod --env production
"""

import os
import sys
import subprocess
import json
import time
import argparse
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env
# Import Windows encoding SSOT
from shared.windows_encoding import setup_windows_encoding

# Fix Unicode encoding issues on Windows - using SSOT
setup_windows_encoding()


class MigrationRunner:
    """Handles database migrations for Cloud SQL via Cloud Run Jobs."""
    
    def __init__(self, project_id: str, environment: str, region: str = "us-central1"):
        self.project_id = project_id
        self.environment = environment
        self.region = region
        self.job_name = f"netra-migrations-{environment}"
        self.image_name = f"gcr.io/{project_id}/{self.job_name}:latest"
        
        # Use gcloud.cmd on Windows
        self.gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        self.docker_cmd = self._detect_container_runtime()
    
    def _detect_container_runtime(self) -> str:
        """Detect whether to use docker or podman."""
        for cmd in ["docker", "podman"]:
            try:
                subprocess.run([cmd, "--version"], capture_output=True, check=True)
                return cmd
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        raise RuntimeError("No container runtime found. Install Docker or Podman.")
    
    def build_migration_image(self) -> bool:
        """Build and push the migrations container."""
        print(f"[U+1F528] Building migrations container for {self.environment}...")
        
        # Build the image
        build_cmd = [
            self.docker_cmd, "build",
            "-f", "docker/migration.alpine.Dockerfile",
            "-t", self.image_name,
            "."
        ]
        
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f" FAIL:  Failed to build migration image: {result.stderr}")
            return False
        
        print(" PASS:  Migration image built successfully")
        
        # Configure Docker for GCR
        print("[U+1F510] Configuring Docker authentication for GCR...")
        auth_cmd = [self.gcloud_cmd, "auth", "configure-docker", "gcr.io", "--quiet"]
        subprocess.run(auth_cmd, capture_output=True)
        
        # Push the image
        print(f"[U+1F4E4] Pushing migration image to {self.image_name}...")
        push_cmd = [self.docker_cmd, "push", self.image_name]
        result = subprocess.run(push_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f" FAIL:  Failed to push migration image: {result.stderr}")
            return False
        
        print(" PASS:  Migration image pushed successfully")
        return True
    
    def create_or_update_job(self) -> bool:
        """Create or update the Cloud Run Job for migrations."""
        print(f"[U+1F680] Creating/updating Cloud Run Job: {self.job_name}...")
        
        # Build the job configuration
        job_cmd = [
            self.gcloud_cmd, "run", "jobs", "deploy", self.job_name,
            "--image", self.image_name,
            "--region", self.region,
            "--project", self.project_id,
            "--memory", "512Mi",
            "--cpu", "1",
            "--max-retries", "1",
            "--task-timeout", "600",
            "--service-account", f"netra-staging-deploy@{self.project_id}.iam.gserviceaccount.com"
        ]
        
        # Add environment-specific secrets
        secrets = [
            f"POSTGRES_HOST=postgres-host-{self.environment}:latest",
            f"POSTGRES_PORT=postgres-port-{self.environment}:latest",
            f"POSTGRES_DB=postgres-db-{self.environment}:latest",
            f"POSTGRES_USER=postgres-user-{self.environment}:latest",
            f"POSTGRES_PASSWORD=postgres-password-{self.environment}:latest"
        ]
        
        for secret in secrets:
            job_cmd.extend(["--set-secrets", secret])
        
        # Add environment variable
        job_cmd.extend(["--set-env-vars", f"ENVIRONMENT={self.environment.upper()}"])
        
        # CRITICAL: Add Cloud SQL connection for staging deployment compatibility
        # This fixes the "No such file or directory" socket connection error
        cloud_sql_instance = f"{self.project_id}:us-central1:{self.environment}-shared-postgres"
        job_cmd.extend(["--set-cloudsql-instances", cloud_sql_instance])
        
        print(f"[U+1F50C] Configuring Cloud SQL connection: {cloud_sql_instance}")
        
        result = subprocess.run(job_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            if "already exists" in result.stderr:
                print("[U+2139][U+FE0F] Job already exists, updating...")
                # Try update instead
                job_cmd[3] = "update"
                result = subprocess.run(job_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f" FAIL:  Failed to create/update job: {result.stderr}")
                return False
        
        print(f" PASS:  Cloud Run Job {self.job_name} is ready")
        return True
    
    def run_migration(self) -> bool:
        """Execute the migration job and wait for completion."""
        print(f"[U+25B6][U+FE0F] Executing migration job {self.job_name}...")
        
        # Execute the job
        run_cmd = [
            self.gcloud_cmd, "run", "jobs", "execute", self.job_name,
            "--region", self.region,
            "--project", self.project_id,
            "--wait"  # Wait for completion
        ]
        
        result = subprocess.run(run_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f" FAIL:  Migration job failed: {result.stderr}")
            
            # Try to get logs
            print("\n[U+1F4CB] Fetching job logs...")
            logs_cmd = [
                self.gcloud_cmd, "logging", "read",
                f'resource.type="cloud_run_job" AND resource.labels.job_name="{self.job_name}"',
                "--limit", "50",
                "--project", self.project_id,
                "--format", "value(textPayload)"
            ]
            logs = subprocess.run(logs_cmd, capture_output=True, text=True)
            if logs.stdout:
                print("Recent logs:")
                print(logs.stdout)
            
            return False
        
        print(" PASS:  Database migrations completed successfully!")
        return True
    
    def run(self) -> bool:
        """Run the complete migration process."""
        print(f"\n[U+1F5C4][U+FE0F] Running database migrations for {self.environment} environment")
        print(f"   Project: {self.project_id}")
        print(f"   Region: {self.region}\n")
        
        # Step 1: Build and push migration image
        if not self.build_migration_image():
            return False
        
        # Step 2: Create/update Cloud Run Job
        if not self.create_or_update_job():
            return False
        
        # Step 3: Execute migration
        if not self.run_migration():
            return False
        
        print(f"\n[U+2728] All migrations completed successfully for {self.environment}!")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run database migrations on Cloud SQL via Cloud Run Jobs"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="GCP project ID (e.g., netra-staging, netra-prod)"
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["staging", "production"],
        help="Environment to run migrations for"
    )
    parser.add_argument(
        "--region",
        default="us-central1",
        help="GCP region (default: us-central1)"
    )
    
    args = parser.parse_args()
    
    # Run migrations
    runner = MigrationRunner(
        project_id=args.project,
        environment=args.env,
        region=args.region
    )
    
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()