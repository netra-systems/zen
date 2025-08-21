"""
Cloud Run service deployment management for GCP.
"""

import os
import json
import subprocess
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class CloudRunService:
    """Cloud Run service configuration."""
    name: str
    image: str
    region: str
    project_id: str
    memory: str = "512Mi"
    cpu: str = "1"
    min_instances: int = 0
    max_instances: int = 10
    port: int = 8000
    env_vars: Optional[Dict[str, str]] = None
    secrets: Optional[List[str]] = None
    vpc_connector: Optional[str] = None
    service_account: Optional[str] = None
    allow_unauthenticated: bool = False
    timeout: int = 300

class CloudRunDeployer:
    """Manages Cloud Run service deployments."""
    
    def __init__(self, project_id: str, region: str = "us-central1"):
        self.project_id = project_id
        self.region = region
        
    def deploy_service(self, service: CloudRunService, retry_count: int = 3) -> bool:
        """
        Deploy a service to Cloud Run.
        
        Args:
            service: Cloud Run service configuration
            retry_count: Number of retry attempts
            
        Returns:
            True if deployment successful, False otherwise
        """
        for attempt in range(retry_count):
            try:
                logger.info(f"Deploying {service.name} to Cloud Run (attempt {attempt + 1}/{retry_count})")
                
                # Build deployment command
                cmd = self._build_deploy_command(service)
                
                # Execute deployment
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully deployed {service.name}")
                    
                    # Set IAM policy if needed
                    if service.allow_unauthenticated:
                        self._set_unauthenticated_access(service.name)
                    
                    return True
                    
                logger.warning(f"Deployment attempt {attempt + 1} failed: {result.stderr}")
                
                if attempt < retry_count - 1:
                    # Exponential backoff
                    time.sleep(2 ** attempt)
                    
            except Exception as e:
                logger.error(f"Error deploying service: {str(e)}")
                
        return False
    
    def _build_deploy_command(self, service: CloudRunService) -> List[str]:
        """Build the gcloud run deploy command."""
        cmd = [
            "gcloud", "run", "deploy", service.name,
            "--image", service.image,
            "--region", service.region,
            "--project", self.project_id,
            "--platform", "managed",
            "--memory", service.memory,
            "--cpu", service.cpu,
            "--min-instances", str(service.min_instances),
            "--max-instances", str(service.max_instances),
            "--port", str(service.port),
            "--timeout", str(service.timeout),
            "--quiet"
        ]
        
        # Add environment variables
        if service.env_vars:
            env_str = ",".join([f"{k}={v}" for k, v in service.env_vars.items()])
            cmd.extend(["--set-env-vars", env_str])
        
        # Add secrets
        if service.secrets:
            for secret in service.secrets:
                cmd.extend(["--set-secrets", secret])
        
        # Add VPC connector
        if service.vpc_connector:
            cmd.extend(["--vpc-connector", service.vpc_connector])
        
        # Add service account
        if service.service_account:
            cmd.extend(["--service-account", service.service_account])
        
        # Allow unauthenticated access
        if service.allow_unauthenticated:
            cmd.append("--allow-unauthenticated")
        else:
            cmd.append("--no-allow-unauthenticated")
        
        return cmd
    
    def _set_unauthenticated_access(self, service_name: str) -> bool:
        """Set IAM policy to allow unauthenticated access."""
        try:
            cmd = [
                "gcloud", "run", "services", "add-iam-policy-binding", service_name,
                "--region", self.region,
                "--project", self.project_id,
                "--member", "allUsers",
                "--role", "roles/run.invoker",
                "--quiet"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                logger.info(f"Set unauthenticated access for {service_name}")
                return True
            else:
                logger.error(f"Failed to set IAM policy: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting IAM policy: {str(e)}")
            return False
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """
        Get the URL of a deployed Cloud Run service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service URL if found, None otherwise
        """
        try:
            cmd = [
                "gcloud", "run", "services", "describe", service_name,
                "--region", self.region,
                "--project", self.project_id,
                "--format", "json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("status", {}).get("url")
                
        except Exception as e:
            logger.error(f"Error getting service URL: {str(e)}")
            
        return None
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """
        Get the status of a Cloud Run service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service status dictionary
        """
        try:
            cmd = [
                "gcloud", "run", "services", "describe", service_name,
                "--region", self.region,
                "--project", self.project_id,
                "--format", "json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "ready": data.get("status", {}).get("conditions", [{}])[0].get("status") == "True",
                    "url": data.get("status", {}).get("url"),
                    "latest_revision": data.get("status", {}).get("latestReadyRevisionName"),
                    "traffic": data.get("status", {}).get("traffic", [])
                }
                
        except Exception as e:
            logger.error(f"Error getting service status: {str(e)}")
            
        return {"ready": False}
    
    def update_traffic_split(self, service_name: str, traffic_config: Dict[str, int]) -> bool:
        """
        Update traffic split between revisions.
        
        Args:
            service_name: Name of the service
            traffic_config: Dictionary mapping revision names to traffic percentages
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            traffic_args = []
            for revision, percentage in traffic_config.items():
                traffic_args.append(f"{revision}={percentage}")
            
            cmd = [
                "gcloud", "run", "services", "update-traffic", service_name,
                "--region", self.region,
                "--project", self.project_id,
                "--to-revisions", ",".join(traffic_args),
                "--quiet"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                logger.info(f"Updated traffic split for {service_name}")
                return True
            else:
                logger.error(f"Failed to update traffic: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating traffic split: {str(e)}")
            return False
    
    def rollback_service(self, service_name: str, revision: Optional[str] = None) -> bool:
        """
        Rollback a service to a previous revision.
        
        Args:
            service_name: Name of the service
            revision: Specific revision to rollback to (optional)
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            if revision:
                # Rollback to specific revision
                return self.update_traffic_split(service_name, {revision: 100})
            else:
                # Get previous revision
                cmd = [
                    "gcloud", "run", "revisions", "list",
                    "--service", service_name,
                    "--region", self.region,
                    "--project", self.project_id,
                    "--format", "json",
                    "--limit", "2"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    revisions = json.loads(result.stdout)
                    if len(revisions) >= 2:
                        previous_revision = revisions[1]["metadata"]["name"]
                        return self.update_traffic_split(service_name, {previous_revision: 100})
                        
        except Exception as e:
            logger.error(f"Error rolling back service: {str(e)}")
            
        return False
    
    def delete_service(self, service_name: str) -> bool:
        """
        Delete a Cloud Run service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            cmd = [
                "gcloud", "run", "services", "delete", service_name,
                "--region", self.region,
                "--project", self.project_id,
                "--quiet"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                logger.info(f"Deleted service {service_name}")
                return True
            else:
                logger.error(f"Failed to delete service: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting service: {str(e)}")
            return False