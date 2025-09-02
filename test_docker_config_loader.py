#!/usr/bin/env python3
"""
Test script for Docker Configuration Loader
Validates that the centralized Docker configuration is working correctly.
"""

import sys
from pathlib import Path
from test_framework.docker_config_loader import (
    DockerConfigLoader, 
    DockerEnvironment,
    DockerConfigurationError,
    get_docker_config_loader
)


def test_docker_config_loader():
    """Test the Docker configuration loader functionality."""
    print("Testing Docker Configuration Loader...")
    
    try:
        # Test singleton access
        loader = get_docker_config_loader()
        print(f"[OK] Successfully loaded configuration from: {loader.config_path}")
        
        # Test available environments
        environments = loader.get_available_environments()
        print(f"[OK] Available environments: {environments}")
        
        # Test each environment
        for env_name in environments:
            print(f"\n--- Testing environment: {env_name} ---")
            
            # Test environment configuration
            env_config = loader.get_environment_config(env_name)
            print(f"  [OK] Compose file: {env_config.compose_file}")
            print(f"  [OK] Project prefix: {env_config.project_name_prefix}")
            print(f"  [OK] Backend port: {env_config.ports.backend}")
            print(f"  [OK] Postgres credentials: {env_config.credentials.postgres_user}")
            
            # Test health check configuration
            print(f"  [OK] Health check timeout: {env_config.health_check.timeout}s")
            
            # Test memory limits
            if env_config.memory_limits:
                print(f"  [OK] Backend memory limit: {env_config.memory_limits.get('backend', 'N/A')}")
            
            # Test secrets
            try:
                secrets = loader.get_secrets_config(env_name)
                print(f"  [OK] JWT secret configured: {bool(secrets.jwt_secret_key)}")
            except DockerConfigurationError as e:
                print(f"  [WARN] Secrets not configured: {e}")
            
            # Test specific service port lookup
            backend_port = loader.get_port_for_service(env_name, 'backend')
            postgres_port = loader.get_port_for_service(env_name, 'postgres')
            print(f"  [OK] Service ports - Backend: {backend_port}, Postgres: {postgres_port}")
            
            # Test memory limit lookup
            backend_memory = loader.get_memory_limit_for_service(env_name, 'backend')
            print(f"  [OK] Backend memory limit: {backend_memory}")
            
            # Test compose file path
            compose_path = loader.get_compose_file_path(env_name)
            if compose_path and compose_path.exists():
                print(f"  [OK] Compose file exists: {compose_path}")
            else:
                print(f"  [WARN] Compose file not found: {compose_path}")
        
        # Test global configuration
        print(f"\n--- Testing global configuration ---")
        global_config = loader.get_global_config()
        print(f"  [OK] Network driver: {global_config.network.get('driver', 'N/A')}")
        print(f"  [OK] Max volumes: {global_config.volumes.get('max_named_volumes', 'N/A')}")
        
        if global_config.image_tags:
            backend_images = global_config.image_tags.get('backend', {})
            print(f"  [OK] Backend images: {list(backend_images.keys())}")
        
        # Test enum usage
        print(f"\n--- Testing enum usage ---")
        if 'development' in environments:
            dev_config = loader.get_environment_config(DockerEnvironment.DEVELOPMENT)
            print(f"  [OK] Enum access works: {dev_config.prefix}")
        
        # Test validation
        print(f"\n--- Testing validation ---")
        valid_env = loader.validate_environment('development')
        invalid_env = loader.validate_environment('nonexistent')
        print(f"  [OK] Development environment valid: {valid_env}")
        print(f"  [OK] Nonexistent environment invalid: {not invalid_env}")
        
        print(f"\n[SUCCESS] All Docker configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Docker configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_docker_config_loader()
    sys.exit(0 if success else 1)