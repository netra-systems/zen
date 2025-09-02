#!/usr/bin/env python3
"""
Example usage of Docker Configuration Loader

This demonstrates how to use the centralized Docker environment configuration
as a Single Source of Truth (SSOT) for Docker operations.

CLAUDE.md compliance: Uses centralized configuration to prevent drift and errors.
"""

from test_framework.docker_config_loader import (
    DockerConfigLoader,
    DockerEnvironment,
    get_docker_config_loader
)


def example_usage():
    """Example of how to use Docker configuration loader in practice."""
    
    # Get singleton loader instance
    config = get_docker_config_loader()
    
    # Example 1: Get environment configuration
    print("=== Environment Configuration Example ===")
    test_env = config.get_environment_config(DockerEnvironment.TEST)
    print(f"Test environment compose file: {test_env.compose_file}")
    print(f"Test backend port: {test_env.ports.backend}")
    print(f"Test postgres credentials: {test_env.credentials.postgres_user}")
    print(f"Test health check timeout: {test_env.health_check.timeout}s")
    
    # Example 2: Quick service port lookup
    print("\n=== Quick Service Port Lookup ===")
    backend_port = config.get_port_for_service('development', 'backend')
    postgres_port = config.get_port_for_service('development', 'postgres')
    redis_port = config.get_port_for_service('development', 'redis')
    print(f"Development ports - Backend: {backend_port}, Postgres: {postgres_port}, Redis: {redis_port}")
    
    # Example 3: Memory limits for resource management
    print("\n=== Memory Limits Example ===")
    backend_memory = config.get_memory_limit_for_service('test', 'backend')
    auth_memory = config.get_memory_limit_for_service('test', 'auth')
    print(f"Test environment memory - Backend: {backend_memory}, Auth: {auth_memory}")
    
    # Example 4: Global configuration
    print("\n=== Global Configuration Example ===")
    global_config = config.get_global_config()
    print(f"Network driver: {global_config.network.get('driver')}")
    print(f"Max named volumes: {global_config.volumes.get('max_named_volumes')}")
    
    backend_images = global_config.image_tags.get('backend', {})
    print(f"Available backend images: {list(backend_images.keys())}")
    print(f"Development backend image: {backend_images.get('development')}")
    
    # Example 5: Environment validation
    print("\n=== Environment Validation Example ===")
    environments = ['development', 'test', 'alpine_test', 'nonexistent']
    for env in environments:
        is_valid = config.validate_environment(env)
        status = "valid" if is_valid else "invalid"
        print(f"Environment '{env}': {status}")
    
    # Example 6: Compose file paths
    print("\n=== Compose File Paths Example ===")
    for env_name in config.get_available_environments():
        compose_path = config.get_compose_file_path(env_name)
        exists = "exists" if compose_path and compose_path.exists() else "missing"
        print(f"{env_name}: {compose_path} ({exists})")
    
    # Example 7: Secrets handling
    print("\n=== Secrets Configuration Example ===")
    try:
        dev_secrets = config.get_secrets_config('development')
        print(f"Development JWT secret configured: {bool(dev_secrets.jwt_secret_key)}")
        print(f"Development service secret configured: {bool(dev_secrets.service_secret)}")
    except Exception as e:
        print(f"Could not load development secrets: {e}")


def docker_manager_integration_example():
    """Example of how to integrate with Docker management tools."""
    
    config = get_docker_config_loader()
    
    # Example: Building Docker command from configuration
    print("\n=== Docker Integration Example ===")
    
    environment = DockerEnvironment.TEST
    env_config = config.get_environment_config(environment)
    
    # Build docker-compose command with proper configuration
    compose_cmd = [
        "docker-compose",
        "-f", str(config.get_compose_file_path(environment)),
        "-p", env_config.project_name_prefix,
        "up", "-d"
    ]
    
    print(f"Docker compose command: {' '.join(compose_cmd)}")
    
    # Example: Environment variables for services
    print(f"\nEnvironment variables for {environment.value}:")
    for key, value in env_config.environment_variables.items():
        print(f"  {key.upper()}={value}")
    
    # Example: Health check configuration
    hc = env_config.health_check
    print(f"\nHealth check config:")
    print(f"  Timeout: {hc.timeout}s")
    print(f"  Retries: {hc.retries}")
    print(f"  Interval: {hc.interval}s")
    print(f"  Start period: {hc.start_period}s")
    
    # Example: Resource limits
    print(f"\nResource limits:")
    for service, memory in env_config.memory_limits.items():
        cpu = env_config.cpu_limits.get(service, 'N/A')
        print(f"  {service}: {memory} memory, {cpu} CPU")


if __name__ == "__main__":
    print("Docker Configuration Loader - Usage Examples\n")
    
    try:
        example_usage()
        docker_manager_integration_example()
        
        print("\n[SUCCESS] All examples completed successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Example failed: {e}")
        import traceback
        traceback.print_exc()