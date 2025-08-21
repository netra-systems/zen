#!/usr/bin/env python3
"""
Staging Configuration Alignment Module
Ensures staging deployment aligns with unified configuration system

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Zero configuration-related deployment failures
- Value Impact: Prevents $15K MRR loss from staging misconfigurations
- Revenue Impact: Ensures staging validates production deployments correctly
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.configuration.schemas import (
    StagingConfig, SecretReference, SECRET_CONFIG
)
from netra_backend.app.core.environment_constants import Environment

@dataclass
class StagingDeploymentConfig:
    """Unified staging deployment configuration."""
    
    # GCP Configuration
    project_id: str = "netra-staging"
    project_id_numerical: str = "701982941522"
    region: str = "us-central1"
    registry: str = "us-central1-docker.pkg.dev"
    
    # Service names (aligned with domain mapping)
    backend_service: str = "netra-backend-staging"
    frontend_service: str = "netra-frontend-staging"
    auth_service: str = "netra-auth-service"
    
    # Cloud SQL Instance
    cloudsql_instance: str = "netra-staging:us-central1:staging-shared-postgres"
    
    # URLs
    api_url: str = "https://api.staging.netrasystems.ai"
    frontend_url: str = "https://app.staging.netrasystems.ai"
    auth_url: str = "https://auth.staging.netrasystems.ai"
    ws_url: str = "wss://api.staging.netrasystems.ai/ws"
    
    # Resource configurations
    backend_memory: str = "1Gi"
    backend_cpu: str = "1"
    backend_min_instances: int = 0
    backend_max_instances: int = 10
    
    frontend_memory: str = "512Mi"
    frontend_cpu: str = "1"
    frontend_min_instances: int = 0
    frontend_max_instances: int = 10
    
    auth_memory: str = "1Gi"
    auth_cpu: str = "1"
    auth_min_instances: int = 1
    auth_max_instances: int = 2


class StagingConfigurationManager:
    """Manages staging configuration alignment with central config."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.deployment_config = StagingDeploymentConfig()
        self.staging_config = self._load_staging_config()
        self.secret_mappings = self._build_secret_mappings()
    
    def _load_staging_config(self) -> StagingConfig:
        """Load staging configuration from unified system."""
        # Set environment to staging for config loading
        os.environ['ENVIRONMENT'] = Environment.STAGING.value
        
        # Create staging config instance
        return StagingConfig()
    
    def _build_secret_mappings(self) -> Dict[str, str]:
        """Build secret name mappings for staging."""
        mappings = {}
        
        # Map secrets based on SECRET_CONFIG
        for secret_ref in SECRET_CONFIG:
            staging_name = f"{secret_ref.name}-staging"
            mappings[secret_ref.name] = staging_name
        
        # Add staging-specific secrets
        mappings.update({
            "database-url": "database-url-staging",
            "redis-url": "redis-url-staging",
            "clickhouse-url": "clickhouse-url-staging"
        })
        
        return mappings
    
    def get_backend_env_vars(self) -> Dict[str, str]:
        """Get environment variables for backend service."""
        return {
            "ENVIRONMENT": "staging",
            "SERVICE_NAME": "backend",
            "LOG_LEVEL": "INFO",
            "PYTHONUNBUFFERED": "1",
            "API_BASE_URL": self.deployment_config.api_url,
            "FRONTEND_URL": self.deployment_config.frontend_url,
            "AUTH_SERVICE_URL": self.deployment_config.auth_url,
            "AUTH_SERVICE_ENABLED": "true",
            "K_SERVICE": self.deployment_config.backend_service,
            "CORS_ORIGINS": f"{self.deployment_config.frontend_url},{self.deployment_config.api_url}",
            # Service modes for staging
            "REDIS_MODE": "shared",
            "CLICKHOUSE_MODE": "shared",
            "LLM_MODE": "shared"
        }
    
    def get_frontend_env_vars(self) -> Dict[str, str]:
        """Get environment variables for frontend service."""
        return {
            "NODE_ENV": "production",
            "NEXT_PUBLIC_API_URL": self.deployment_config.api_url,
            "NEXT_PUBLIC_WS_URL": self.deployment_config.ws_url,
            "NEXT_PUBLIC_AUTH_URL": self.deployment_config.auth_url,
            "NEXT_PUBLIC_ENVIRONMENT": "staging",
            # Add required env vars for consistency (even though frontend doesn't use them)
            "ENVIRONMENT": "staging",
            "SERVICE_NAME": "frontend",
            "LOG_LEVEL": "INFO"
        }
    
    def get_auth_env_vars(self) -> Dict[str, str]:
        """Get environment variables for auth service."""
        return {
            "ENVIRONMENT": "staging",
            "SERVICE_NAME": "auth",
            "LOG_LEVEL": "INFO",
            "PYTHONUNBUFFERED": "1",
            "PORT": "8001",
            "FRONTEND_URL": self.deployment_config.frontend_url,
            "API_URL": self.deployment_config.api_url,
            "K_SERVICE": self.deployment_config.auth_service,
            "CORS_ORIGINS": f"{self.deployment_config.frontend_url},{self.deployment_config.api_url}"
        }
    
    def get_backend_secrets(self) -> List[str]:
        """Get secret references for backend service."""
        return [
            f"DATABASE_URL={self.secret_mappings['database-url']}:latest",
            f"REDIS_URL={self.secret_mappings.get('redis-url', 'redis-url-staging')}:latest",
            f"CLICKHOUSE_URL={self.secret_mappings.get('clickhouse-url', 'clickhouse-url-staging')}:latest",
            f"GEMINI_API_KEY={self.secret_mappings['gemini-api-key']}:latest",
            f"JWT_SECRET_KEY={self.secret_mappings['jwt-secret-key']}:latest",
            f"FERNET_KEY={self.secret_mappings['fernet-key']}:latest",
            f"LANGFUSE_SECRET_KEY={self.secret_mappings.get('langfuse-secret-key', 'langfuse-secret-key-staging')}:latest",
            f"LANGFUSE_PUBLIC_KEY={self.secret_mappings.get('langfuse-public-key', 'langfuse-public-key-staging')}:latest",
            f"GITHUB_TOKEN={self.secret_mappings.get('github-token', 'github-token-staging')}:latest"
        ]
    
    def get_auth_secrets(self) -> List[str]:
        """Get secret references for auth service."""
        return [
            f"DATABASE_URL={self.secret_mappings['database-url']}:latest",
            f"JWT_SECRET_KEY={self.secret_mappings['jwt-secret-key']}:latest",
            f"FERNET_KEY={self.secret_mappings['fernet-key']}:latest",
            f"GOOGLE_CLIENT_ID={self.secret_mappings['google-client-id']}:latest",
            f"GOOGLE_CLIENT_SECRET={self.secret_mappings['google-client-secret']}:latest"
        ]
    
    def generate_gcloud_deploy_command(self, service: str) -> List[str]:
        """Generate gcloud run deploy command for a service."""
        base_cmd = [
            "gcloud", "run", "deploy",
            "--platform", "managed",
            "--region", self.deployment_config.region,
            "--project", self.deployment_config.project_id,
            "--allow-unauthenticated",
            "--quiet"
        ]
        
        if service == "backend":
            return base_cmd + [
                self.deployment_config.backend_service,
                "--image", f"{self.deployment_config.registry}/{self.deployment_config.project_id}/netra-containers/backend:staging",
                "--port", "8080",
                "--memory", self.deployment_config.backend_memory,
                "--cpu", self.deployment_config.backend_cpu,
                "--min-instances", str(self.deployment_config.backend_min_instances),
                "--max-instances", str(self.deployment_config.backend_max_instances),
                "--set-env-vars", self._format_env_vars(self.get_backend_env_vars()),
                "--add-cloudsql-instances", self.deployment_config.cloudsql_instance,
                "--set-secrets", ",".join(self.get_backend_secrets())
            ]
        
        elif service == "frontend":
            return base_cmd + [
                self.deployment_config.frontend_service,
                "--image", f"{self.deployment_config.registry}/{self.deployment_config.project_id}/netra-containers/frontend:staging",
                "--port", "3000",
                "--memory", self.deployment_config.frontend_memory,
                "--cpu", self.deployment_config.frontend_cpu,
                "--min-instances", str(self.deployment_config.frontend_min_instances),
                "--max-instances", str(self.deployment_config.frontend_max_instances),
                "--set-env-vars", self._format_env_vars(self.get_frontend_env_vars())
            ]
        
        elif service == "auth":
            return base_cmd + [
                self.deployment_config.auth_service,
                "--image", f"{self.deployment_config.registry}/{self.deployment_config.project_id}/netra-containers/auth:staging",
                "--port", "8001",
                "--memory", self.deployment_config.auth_memory,
                "--cpu", self.deployment_config.auth_cpu,
                "--min-instances", str(self.deployment_config.auth_min_instances),
                "--max-instances", str(self.deployment_config.auth_max_instances),
                "--set-env-vars", self._format_env_vars(self.get_auth_env_vars()),
                "--add-cloudsql-instances", self.deployment_config.cloudsql_instance,
                "--set-secrets", ",".join(self.get_auth_secrets())
            ]
        
        else:
            raise ValueError(f"Unknown service: {service}")
    
    def _format_env_vars(self, env_vars: Dict[str, str]) -> str:
        """Format environment variables for gcloud command."""
        return ",".join([f"{k}={v}" for k, v in env_vars.items()])
    
    def validate_configuration(self) -> tuple[bool, List[str]]:
        """Validate staging configuration completeness."""
        issues = []
        
        # Check required environment variables
        required_env_vars = [
            "ENVIRONMENT", "SERVICE_NAME", "LOG_LEVEL"
        ]
        
        for service in ["backend", "frontend", "auth"]:
            env_vars = getattr(self, f"get_{service}_env_vars")()
            for var in required_env_vars:
                if var not in env_vars:
                    issues.append(f"{service}: Missing required env var {var}")
        
        # Check secret mappings
        for secret_ref in SECRET_CONFIG:
            if secret_ref.name not in self.secret_mappings:
                issues.append(f"Missing secret mapping for {secret_ref.name}")
        
        # Validate URLs
        urls = [
            self.deployment_config.api_url,
            self.deployment_config.frontend_url,
            self.deployment_config.auth_url
        ]
        
        for url in urls:
            if not url.startswith("https://"):
                issues.append(f"URL should use HTTPS: {url}")
        
        return len(issues) == 0, issues
    
    def export_configuration(self, output_file: Optional[Path] = None) -> None:
        """Export configuration to JSON file."""
        config_data = {
            "deployment": {
                "project_id": self.deployment_config.project_id,
                "region": self.deployment_config.region,
                "services": {
                    "backend": self.deployment_config.backend_service,
                    "frontend": self.deployment_config.frontend_service,
                    "auth": self.deployment_config.auth_service
                },
                "urls": {
                    "api": self.deployment_config.api_url,
                    "frontend": self.deployment_config.frontend_url,
                    "auth": self.deployment_config.auth_url,
                    "websocket": self.deployment_config.ws_url
                }
            },
            "environment_variables": {
                "backend": self.get_backend_env_vars(),
                "frontend": self.get_frontend_env_vars(),
                "auth": self.get_auth_env_vars()
            },
            "secrets": {
                "backend": self.get_backend_secrets(),
                "auth": self.get_auth_secrets()
            },
            "resources": {
                "backend": {
                    "memory": self.deployment_config.backend_memory,
                    "cpu": self.deployment_config.backend_cpu,
                    "min_instances": self.deployment_config.backend_min_instances,
                    "max_instances": self.deployment_config.backend_max_instances
                },
                "frontend": {
                    "memory": self.deployment_config.frontend_memory,
                    "cpu": self.deployment_config.frontend_cpu,
                    "min_instances": self.deployment_config.frontend_min_instances,
                    "max_instances": self.deployment_config.frontend_max_instances
                },
                "auth": {
                    "memory": self.deployment_config.auth_memory,
                    "cpu": self.deployment_config.auth_cpu,
                    "min_instances": self.deployment_config.auth_min_instances,
                    "max_instances": self.deployment_config.auth_max_instances
                }
            }
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            print(f"Configuration exported to {output_file}")
        else:
            print(json.dumps(config_data, indent=2))


def main():
    """Main function for testing configuration alignment."""
    manager = StagingConfigurationManager()
    
    print("=== Staging Configuration Alignment ===\n")
    
    # Validate configuration
    is_valid, issues = manager.validate_configuration()
    
    if is_valid:
        print("[OK] Configuration is valid and aligned\n")
    else:
        print("[ERROR] Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print()
    
    # Export configuration
    output_file = Path(__file__).parent / "staging_deployment_config.json"
    manager.export_configuration(output_file)
    
    # Print sample commands
    print("\n=== Sample Deployment Commands ===\n")
    
    for service in ["backend", "frontend", "auth"]:
        cmd = manager.generate_gcloud_deploy_command(service)
        print(f"{service.upper()}:")
        print(" ".join(cmd))
        print()


if __name__ == "__main__":
    main()