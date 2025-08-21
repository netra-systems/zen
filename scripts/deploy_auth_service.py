#!/usr/bin/env python3
"""
Deploy Auth Service to all environments
Handles Docker build, push, and Cloud Run deployment
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthServiceDeployer:
    """Deploy auth service to GCP"""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.project_id = os.getenv("GCP_PROJECT_ID", "netra-staging")
        self.region = os.getenv("GCP_REGION", "us-central1")
        self.service_name = "netra-auth-service"
        self.image_name = f"gcr.io/{self.project_id}/auth-service"
        
    def build_docker_image(self) -> bool:
        """Build auth service Docker image"""
        logger.info("Building auth service Docker image...")
        
        cmd = [
            "docker", "build",
            "-f", "Dockerfile.auth",
            "-t", f"{self.image_name}:latest",
            "-t", f"{self.image_name}:{self.environment}",
            "."
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Docker build failed: {result.stderr}")
            return False
        
        logger.info("Docker image built successfully")
        return True
    
    def push_docker_image(self) -> bool:
        """Push Docker image to GCR"""
        logger.info("Pushing Docker image to GCR...")
        
        # Configure docker for GCR
        auth_cmd = ["gcloud", "auth", "configure-docker"]
        subprocess.run(auth_cmd, check=True)
        
        # Push both tags
        for tag in ["latest", self.environment]:
            cmd = ["docker", "push", f"{self.image_name}:{tag}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Docker push failed: {result.stderr}")
                return False
        
        logger.info("Docker image pushed successfully")
        return True
    
    def deploy_to_cloud_run(self) -> bool:
        """Deploy auth service to Cloud Run"""
        logger.info(f"Deploying auth service to {self.environment}...")
        
        cmd = [
            "gcloud", "run", "deploy", self.service_name,
            "--image", f"{self.image_name}:latest",
            "--platform", "managed",
            "--region", self.region,
            "--project", self.project_id,
            "--allow-unauthenticated",
            "--port", "8080",
            "--memory", "512Mi",
            "--cpu", "1",
            "--min-instances", "1",
            "--max-instances", "10",
            "--set-env-vars", self._get_env_vars()
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Deployment failed: {result.stderr}")
            return False
        
        logger.info("Auth service deployed successfully")
        return True
    
    def _get_env_vars(self) -> str:
        """Get environment variables for deployment"""
        env_vars = {
            "ENVIRONMENT": self.environment,
            "SERVICE_NAME": "auth-service",
            "LOG_LEVEL": "INFO",
            "JWT_SECRET": f"projects/{self.project_id}/secrets/jwt-secret/versions/latest",
            "DATABASE_URL": f"projects/{self.project_id}/secrets/database-url/versions/latest",
            "REDIS_URL": f"projects/{self.project_id}/secrets/redis-url/versions/latest",
            "CORS_ORIGINS": self._get_cors_origins()
        }
        
        return ",".join([f"{k}={v}" for k, v in env_vars.items()])
    
    def _get_cors_origins(self) -> str:
        """Get CORS origins based on environment"""
        if self.environment == "production":
            return "https://netrasystems.ai,https://app.netrasystems.ai,https://auth.netrasystems.ai"
        else:
            return "https://app.staging.netrasystems.ai,https://auth.staging.netrasystems.ai,https://api.staging.netrasystems.ai,https://backend.staging.netrasystems.ai,http://localhost:3000,http://localhost:8000,http://localhost:8080"
    
    def update_terraform(self) -> bool:
        """Update Terraform configuration"""
        logger.info("Updating Terraform configuration...")
        
        os.chdir("terraform-gcp")
        
        # Initialize Terraform
        subprocess.run(["terraform", "init"], check=True)
        
        # Plan changes
        result = subprocess.run(
            ["terraform", "plan", "-out=auth-service.tfplan"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Terraform plan failed: {result.stderr}")
            return False
        
        # Apply changes
        apply = input("Apply Terraform changes? (yes/no): ")
        if apply.lower() == "yes":
            subprocess.run(["terraform", "apply", "auth-service.tfplan"], check=True)
            logger.info("Terraform changes applied")
        
        os.chdir("..")
        return True
    
    def run_health_check(self) -> bool:
        """Run health check on deployed service"""
        logger.info("Running health check...")
        
        # Get service URL
        cmd = [
            "gcloud", "run", "services", "describe",
            self.service_name,
            "--platform", "managed",
            "--region", self.region,
            "--project", self.project_id,
            "--format", "value(status.url)"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error("Failed to get service URL")
            return False
        
        service_url = result.stdout.strip()
        health_url = f"{service_url}/health"
        
        # Check health endpoint
        import requests
        try:
            response = requests.get(health_url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Health check passed: {response.json()}")
                return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        
        return False
    
    def deploy(self) -> bool:
        """Full deployment pipeline"""
        steps = [
            ("Building Docker image", self.build_docker_image),
            ("Pushing to GCR", self.push_docker_image),
            ("Deploying to Cloud Run", self.deploy_to_cloud_run),
            ("Running health check", self.run_health_check)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"\n{step_name}...")
            if not step_func():
                logger.error(f"Failed at step: {step_name}")
                return False
        
        logger.info("\n✅ Auth service deployment complete!")
        return True


def main():
    """Main deployment function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy Auth Service")
    parser.add_argument(
        "--env",
        choices=["staging", "production"],
        default="staging",
        help="Deployment environment"
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip Docker build"
    )
    parser.add_argument(
        "--terraform-only",
        action="store_true",
        help="Only update Terraform"
    )
    
    args = parser.parse_args()
    
    deployer = AuthServiceDeployer(args.env)
    
    if args.terraform_only:
        return 0 if deployer.update_terraform() else 1
    
    if args.skip_build:
        logger.info("Skipping Docker build...")
        if not deployer.push_docker_image():
            return 1
        if not deployer.deploy_to_cloud_run():
            return 1
        if not deployer.run_health_check():
            return 1
    else:
        if not deployer.deploy():
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())