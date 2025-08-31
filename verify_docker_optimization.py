#!/usr/bin/env python3
"""
Verify Docker Configuration Compliance with SPEC/docker_volume_optimization.xml
"""

import yaml
import os
import sys
from pathlib import Path

def check_volume_count(compose_file):
    """Check that volume count is under the limit"""
    with open(compose_file, 'r') as f:
        config = yaml.safe_load(f)
    
    volumes = config.get('volumes', {})
    volume_count = len(volumes)
    
    print(f"[OK] Volume count: {volume_count}/10 maximum")
    
    if volume_count > 10:
        print(f"[ERROR] Too many volumes! {volume_count} > 10")
        return False
    
    return True

def check_resource_limits(compose_file):
    """Check that all services have resource limits"""
    with open(compose_file, 'r') as f:
        config = yaml.safe_load(f)
    
    services = config.get('services', {})
    services_without_limits = []
    total_memory = 0
    total_cpu = 0
    
    for service_name, service_config in services.items():
        deploy = service_config.get('deploy', {})
        resources = deploy.get('resources', {})
        limits = resources.get('limits', {})
        
        if not limits:
            services_without_limits.append(service_name)
        else:
            # Parse memory
            memory = limits.get('memory', '0')
            if memory.endswith('M'):
                total_memory += int(memory[:-1])
            elif memory.endswith('G'):
                total_memory += int(memory[:-1]) * 1024
            
            # Parse CPU
            cpu = limits.get('cpus', '0')
            total_cpu += float(cpu)
    
    if services_without_limits:
        print(f"[ERROR] Services without resource limits: {', '.join(services_without_limits)}")
        return False
    
    print(f"[OK] All services have resource limits")
    print(f"  Total memory: {total_memory}MB (limit: 3072MB)")
    print(f"  Total CPU: {total_cpu} cores (limit: 2.0)")
    
    if total_memory > 3072:
        print(f"[ERROR] Total memory exceeds limit: {total_memory}MB > 3072MB")
        return False
    
    if total_cpu > 2.01:  # Allow small floating point errors
        print(f"[ERROR] Total CPU exceeds limit: {total_cpu} > 2.0")
        return False
    
    return True

def check_no_code_volumes(compose_file):
    """Check that no code volumes are used"""
    with open(compose_file, 'r') as f:
        config = yaml.safe_load(f)
    
    volumes = config.get('volumes', {})
    code_volume_patterns = ['_code', '_pycache', '_node_modules', '_scripts', '_spec']
    
    code_volumes = []
    for volume_name in volumes.keys():
        if any(pattern in volume_name.lower() for pattern in code_volume_patterns):
            code_volumes.append(volume_name)
    
    if code_volumes:
        print(f"[ERROR] Code volumes found (should be in image): {', '.join(code_volumes)}")
        return False
    
    print("[OK] No code volumes found (code is in images)")
    return True

def check_dockerfiles():
    """Check that Dockerfiles copy code into image"""
    docker_dir = Path('docker')
    dockerfiles = list(docker_dir.glob('*.Dockerfile'))
    
    all_good = True
    for dockerfile in dockerfiles:
        if 'test' in dockerfile.name or 'development' in dockerfile.name:
            continue  # Skip test/dev dockerfiles
            
        with open(dockerfile, 'r') as f:
            content = f.read()
            
        if 'COPY' not in content:
            print(f"[ERROR] {dockerfile.name}: No COPY commands found")
            all_good = False
        elif any(x in content for x in ['./netra_backend', './auth_service', './frontend', './shared', 'COPY .', '/app/public', '.next']):
            print(f"[OK] {dockerfile.name}: Copies application code into image")
        else:
            print(f"[WARNING] {dockerfile.name}: Check COPY commands")
    
    return all_good

def main():
    """Run all verification checks"""
    print("Docker Configuration Compliance Check")
    print("=" * 50)
    
    compose_file = 'docker-compose.yml'
    
    if not os.path.exists(compose_file):
        print(f"[ERROR] {compose_file} not found")
        return 1
    
    checks = [
        ("Volume Count", lambda: check_volume_count(compose_file)),
        ("Resource Limits", lambda: check_resource_limits(compose_file)),
        ("No Code Volumes", lambda: check_no_code_volumes(compose_file)),
        ("Dockerfiles", check_dockerfiles),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n{check_name}:")
        print("-" * 30)
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("[SUCCESS] All checks passed! Docker configuration is optimized.")
        print("\nNext steps:")
        print("1. Run: docker system prune -af --volumes")
        print("2. Run: docker-compose --profile dev up --build")
        return 0
    else:
        print("[FAILED] Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())