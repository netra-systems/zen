"""
Docker image build and push management for GCP deployments.
"""

import os
import json
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class DockerImage:
    """Docker image configuration."""
    service_name: str
    dockerfile_path: str
    context_path: str
    registry_url: str
    tag: str
    platform: str = "linux/amd64"
    
    @property
    def full_image_name(self) -> str:
        """Get full image name with registry and tag."""
        return f"{self.registry_url}/{self.service_name}:{self.tag}"

class DockerImageManager:
    """Manages Docker image building and pushing to GCP Artifact Registry."""
    
    def __init__(self, project_id: str, region: str = "us-central1"):
        self.project_id = project_id
        self.region = region
        self.registry_url = f"{region}-docker.pkg.dev/{project_id}/netra-apex"
        
    def build_image(self, image: DockerImage, build_args: Optional[Dict[str, str]] = None) -> bool:
        """
        Build a Docker image for a service.
        
        Args:
            image: Docker image configuration
            build_args: Optional build arguments
            
        Returns:
            True if build successful, False otherwise
        """
        try:
            logger.info(f"Building Docker image for {image.service_name}")
            
            # Construct build command
            cmd = [
                "docker", "build",
                "-t", image.full_image_name,
                "-f", image.dockerfile_path,
                "--platform", image.platform
            ]
            
            # Add build arguments
            if build_args:
                for key, value in build_args.items():
                    cmd.extend(["--build-arg", f"{key}={value}"])
            
            # Add context path
            cmd.append(image.context_path)
            
            # Execute build
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"Docker build failed: {result.stderr}")
                return False
                
            logger.info(f"Successfully built image: {image.full_image_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error building Docker image: {str(e)}")
            return False
    
    def push_image(self, image: DockerImage, retry_count: int = 3) -> bool:
        """
        Push Docker image to GCP Artifact Registry.
        
        Args:
            image: Docker image configuration
            retry_count: Number of retry attempts
            
        Returns:
            True if push successful, False otherwise
        """
        for attempt in range(retry_count):
            try:
                logger.info(f"Pushing image {image.full_image_name} (attempt {attempt + 1}/{retry_count})")
                
                result = subprocess.run(
                    ["docker", "push", image.full_image_name],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully pushed image: {image.full_image_name}")
                    return True
                    
                logger.warning(f"Push attempt {attempt + 1} failed: {result.stderr}")
                
                if attempt < retry_count - 1:
                    # Retry with exponential backoff
                    import time
                    time.sleep(2 ** attempt)
                    
            except Exception as e:
                logger.error(f"Error pushing image: {str(e)}")
                
        return False
    
    def configure_docker_auth(self) -> bool:
        """
        Configure Docker authentication for GCP Artifact Registry.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            logger.info("Configuring Docker authentication for GCP")
            
            # Use gcloud to configure Docker
            result = subprocess.run(
                ["gcloud", "auth", "configure-docker", f"{self.region}-docker.pkg.dev", "--quiet"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to configure Docker auth: {result.stderr}")
                return False
                
            logger.info("Docker authentication configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error configuring Docker auth: {str(e)}")
            return False
    
    def build_and_push_services(self, services: List[Dict[str, str]]) -> Dict[str, bool]:
        """
        Build and push Docker images for multiple services.
        
        Args:
            services: List of service configurations
            
        Returns:
            Dictionary mapping service names to success status
        """
        results = {}
        
        # Configure Docker authentication first
        if not self.configure_docker_auth():
            logger.error("Failed to configure Docker authentication")
            return {s['name']: False for s in services}
        
        for service in services:
            image = DockerImage(
                service_name=service['name'],
                dockerfile_path=service.get('dockerfile', 'Dockerfile'),
                context_path=service.get('context', '.'),
                registry_url=self.registry_url,
                tag=service.get('tag', 'latest')
            )
            
            # Build image
            if not self.build_image(image):
                results[service['name']] = False
                continue
            
            # Push image
            results[service['name']] = self.push_image(image)
        
        return results
    
    def get_latest_image_digest(self, service_name: str) -> Optional[str]:
        """
        Get the latest image digest from the registry.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Image digest if found, None otherwise
        """
        try:
            cmd = [
                "gcloud", "artifacts", "docker", "images", "describe",
                f"{self.registry_url}/{service_name}:latest",
                f"--project={self.project_id}",
                "--format=json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get('image_summary', {}).get('digest')
                
        except Exception as e:
            logger.error(f"Error getting image digest: {str(e)}")
            
        return None
    
    def cleanup_old_images(self, service_name: str, keep_count: int = 5) -> bool:
        """
        Clean up old Docker images from the registry.
        
        Args:
            service_name: Name of the service
            keep_count: Number of recent images to keep
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            logger.info(f"Cleaning up old images for {service_name}, keeping {keep_count} most recent")
            
            # List all images for the service
            cmd = [
                "gcloud", "artifacts", "docker", "images", "list",
                f"{self.registry_url}/{service_name}",
                f"--project={self.project_id}",
                "--sort-by=~CREATE_TIME",
                "--format=json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode != 0:
                logger.error(f"Failed to list images: {result.stderr}")
                return False
            
            images = json.loads(result.stdout)
            
            # Delete old images
            if len(images) > keep_count:
                for image in images[keep_count:]:
                    digest = image.get('version')
                    if digest:
                        delete_cmd = [
                            "gcloud", "artifacts", "docker", "images", "delete",
                            f"{self.registry_url}/{service_name}@{digest}",
                            f"--project={self.project_id}",
                            "--quiet"
                        ]
                        subprocess.run(delete_cmd, check=False)
                        logger.info(f"Deleted old image: {digest}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up images: {str(e)}")
            return False