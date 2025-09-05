#!/usr/bin/env python3
"""Test script to verify Docker configuration changes."""

import subprocess
import yaml
import sys
import json
from shared.isolated_environment import IsolatedEnvironment

def run_docker_config(compose_files):
    """Run docker-compose config and return parsed YAML."""
    cmd = ["docker-compose"] + [f"-f {f}" for f in compose_files] + ["--profile", "dev", "config"]
    cmd_str = " ".join(cmd)
    
    result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running docker-compose config: {result.stderr}")
        return None
    
    # Parse the YAML output
    return yaml.safe_load(result.stdout)

def check_service_config(config, service_name, checks):
    """Check specific service configuration."""
    print(f"\n--- Checking {service_name} ---")
    
    service = config.get('services', {}).get(service_name, {})
    if not service:
        print(f"ERROR: Service {service_name} not found!")
        return False
    
    success = True
    
    for check_name, check_fn in checks.items():
        result, message = check_fn(service)
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {check_name}: {message}")
        if not result:
            success = False
    
    return success

def check_memory_limit(min_gb):
    """Create a checker for memory limits."""
    def checker(service):
        deploy = service.get('deploy', {})
        resources = deploy.get('resources', {})
        limits = resources.get('limits', {})
        memory = limits.get('memory', '')
        
        if not memory:
            return False, "No memory limit set"
        
        # Parse memory value
        if memory.endswith('G'):
            gb = float(memory[:-1])
        elif memory.endswith('M'):
            gb = float(memory[:-1]) / 1024
        elif memory.isdigit() or (isinstance(memory, str) and memory.strip('"').isdigit()):
            # Docker sometimes converts to bytes
            bytes_val = int(memory.strip('"'))
            gb = bytes_val / (1024 * 1024 * 1024)
        else:
            return False, f"Unknown memory format: {memory}"
        
        if gb >= min_gb:
            return True, f"{gb:.1f}G (>= {min_gb}G)"
        else:
            return False, f"{gb:.1f}G (< {min_gb}G)"
    
    return checker

def check_command_syntax(service):
    """Check that command doesn't have backslashes in the middle."""
    command = service.get('command', '')
    if not command:
        return True, "No command specified"
    
    # Check for backslashes that would indicate problematic line continuations
    if '\\' in command and 'uvicorn' in command:
        # Count backslashes in uvicorn command section
        uvicorn_section = command.split('uvicorn')[1] if 'uvicorn' in command else ''
        backslash_count = uvicorn_section.count('\\')
        if backslash_count > 0:
            return False, f"Found {backslash_count} backslashes in uvicorn command (syntax error)"
    
    return True, "Command syntax looks correct"

def check_env_var(var_name, expected_value=None):
    """Create a checker for environment variables."""
    def checker(service):
        env = service.get('environment', {})
        
        if var_name not in env:
            return False, f"{var_name} not set"
        
        value = env[var_name]
        if expected_value is not None:
            if str(value) == str(expected_value):
                return True, f"{var_name}={value}"
            else:
                return False, f"{var_name}={value} (expected {expected_value})"
        else:
            return True, f"{var_name}={value}"
    
    return checker

def check_no_volumes(service):
    """Check that volumes are not defined (handled by override)."""
    volumes = service.get('volumes', [])
    if not volumes:
        return True, "No volumes defined (as expected)"
    else:
        return False, f"Found {len(volumes)} volume mounts (should be in override only)"

def main():
    print("=" * 60)
    print("Docker Configuration Test")
    print("=" * 60)
    
    # Test 1: Windows configuration
    print("\n### Testing Windows Configuration ###")
    config = run_docker_config(["docker-compose.yml", "docker-compose.windows.yml"])
    
    if config:
        all_passed = True
        
        # Check dev-backend
        passed = check_service_config(config, 'dev-backend', {
            'Memory Limit': check_memory_limit(3),
            'Command Syntax': check_command_syntax,
            'WATCHFILES_FORCE_POLLING': check_env_var('WATCHFILES_FORCE_POLLING', 'true'),
            'No Volume Mounts': check_no_volumes,
        })
        all_passed = all_passed and passed
        
        # Check dev-frontend
        passed = check_service_config(config, 'dev-frontend', {
            'Memory Limit': check_memory_limit(3),
            'WATCHPACK_POLLING': check_env_var('WATCHPACK_POLLING', 'true'),
            'CHOKIDAR_USEPOLLING': check_env_var('CHOKIDAR_USEPOLLING', 'true'),
            'NODE_OPTIONS': check_env_var('NODE_OPTIONS'),
            'No Volume Mounts': check_no_volumes,
        })
        all_passed = all_passed and passed
        
        if all_passed:
            print("\n[SUCCESS] Windows configuration: ALL CHECKS PASSED")
        else:
            print("\n[ERROR] Windows configuration: SOME CHECKS FAILED")
    
    # Test 2: Dev-minimal configuration
    print("\n### Testing Dev-Minimal Configuration ###")
    config = run_docker_config(["docker-compose.yml", "docker-compose.dev-minimal.yml"])
    
    if config:
        all_passed = True
        
        # Check dev-backend
        passed = check_service_config(config, 'dev-backend', {
            'Memory Limit': check_memory_limit(3),
        })
        all_passed = all_passed and passed
        
        # Check dev-frontend
        passed = check_service_config(config, 'dev-frontend', {
            'Memory Limit': check_memory_limit(3),
        })
        all_passed = all_passed and passed
        
        if all_passed:
            print("\n[SUCCESS] Dev-minimal configuration: ALL CHECKS PASSED")
        else:
            print("\n[ERROR] Dev-minimal configuration: SOME CHECKS FAILED")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()