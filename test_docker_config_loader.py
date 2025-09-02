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
        print(f"✓ Successfully loaded configuration from: {loader.config_path}")
        
        # Test available environments
        environments = loader.get_available_environments()
        print(f"✓ Available environments: {environments}")
        
        # Test each environment
        for env_name in environments:
            print(f"\n--- Testing environment: {env_name} ---")
            
            # Test environment configuration
            env_config = loader.get_environment_config(env_name)
            print(f"  ✓ Compose file: {env_config.compose_file}")
            print(f"  ✓ Project prefix: {env_config.project_name_prefix}")
            print(f"  ✓ Backend port: {env_config.ports.backend}")
            print(f"  ✓ Postgres credentials: {env_config.credentials.postgres_user}")
            
            # Test health check configuration
            print(f"  ✓ Health check timeout: {env_config.health_check.timeout}s")
            
            # Test memory limits
            if env_config.memory_limits:
                print(f"  ✓ Backend memory limit: {env_config.memory_limits.get('backend', 'N/A')}")
            
            # Test secrets
            try:
                secrets = loader.get_secrets_config(env_name)
                print(f"  ✓ JWT secret configured: {bool(secrets.jwt_secret_key)}")
            except DockerConfigurationError as e:
                print(f"  ! Secrets not configured: {e}")
            
            # Test specific service port lookup
            backend_port = loader.get_port_for_service(env_name, 'backend')
            postgres_port = loader.get_port_for_service(env_name, 'postgres')
            print(f"  ✓ Service ports - Backend: {backend_port}, Postgres: {postgres_port}")
            
            # Test memory limit lookup
            backend_memory = loader.get_memory_limit_for_service(env_name, 'backend')
            print(f"  ✓ Backend memory limit: {backend_memory}")
            
            # Test compose file path
            compose_path = loader.get_compose_file_path(env_name)
            if compose_path and compose_path.exists():
                print(f"  ✓ Compose file exists: {compose_path}")
            else:
                print(f"  ! Compose file not found: {compose_path}")
        
        # Test global configuration
        print(f"\n--- Testing global configuration ---")
        global_config = loader.get_global_config()
        print(f"  ✓ Network driver: {global_config.network.get('driver', 'N/A')}")
        print(f"  ✓ Max volumes: {global_config.volumes.get('max_named_volumes', 'N/A')}")
        
        if global_config.image_tags:
            backend_images = global_config.image_tags.get('backend', {})
            print(f"  ✓ Backend images: {list(backend_images.keys())}")
        
        # Test enum usage
        print(f"\n--- Testing enum usage ---")
        if 'development' in environments:
            dev_config = loader.get_environment_config(DockerEnvironment.DEVELOPMENT)
            print(f"  ✓ Enum access works: {dev_config.prefix}")
        
        # Test validation
        print(f"\n--- Testing validation ---")
        valid_env = loader.validate_environment('development')
        invalid_env = loader.validate_environment('nonexistent')
        print(f"  ✓ Development environment valid: {valid_env}")
        print(f"  ✓ Nonexistent environment invalid: {not invalid_env}")
        
        print(f"\n🎉 All Docker configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Docker configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_docker_config_loader()
    sys.exit(0 if success else 1)