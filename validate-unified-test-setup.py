#!/usr/bin/env python3
"""
Unified Testing Environment Validation Script
Purpose: Verify all components are correctly configured before running tests
Business Value: Prevents wasted time on misconfigured test environments
"""

import os
import sys
import subprocess
import yaml
from pathlib import Path

# Color codes for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_status(message):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

def print_success(message):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

def print_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def check_file_exists(file_path, description):
    """Check if a file exists and print result"""
    if os.path.exists(file_path):
        print_success(f"{description}: Found")
        return True
    else:
        print_error(f"{description}: Not found at {file_path}")
        return False

def check_docker():
    """Check if Docker is available and running"""
    try:
        subprocess.run(['docker', 'info'], capture_output=True, check=True)
        print_success("Docker is running")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Docker is not running or not installed")
        return False

def check_docker_compose():
    """Check if Docker Compose is available"""
    # Try docker-compose first
    try:
        subprocess.run(['docker-compose', '--version'], capture_output=True, check=True)
        print_success("docker-compose is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Try docker compose (v2)
    try:
        subprocess.run(['docker', 'compose', 'version'], capture_output=True, check=True)
        print_success("docker compose (v2) is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Neither docker-compose nor 'docker compose' is available")
        return False

def check_compose_config():
    """Validate docker-compose configuration"""
    try:
        cmd = ['docker-compose', '-f', 'docker-compose.test.yml', '--env-file', '.env.test', 'config', '--quiet']
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0:
            print_success("Docker Compose configuration is valid")
            return True
        else:
            # Try with docker compose v2
            cmd = ['docker', 'compose', '-f', 'docker-compose.test.yml', '--env-file', '.env.test', 'config', '--quiet']
            result = subprocess.run(cmd, capture_output=True)
            
            if result.returncode == 0:
                print_success("Docker Compose configuration is valid")
                return True
            else:
                print_error(f"Docker Compose configuration error: {result.stderr.decode()}")
                return False
    except Exception as e:
        print_error(f"Failed to validate Docker Compose config: {e}")
        return False

def check_dockerfile_exists():
    """Check if required Dockerfiles exist"""
    dockerfiles = [
        ('Dockerfile.auth', 'Auth Service Dockerfile'),
        ('Dockerfile.backend', 'Backend Service Dockerfile'),
        ('frontend/Dockerfile', 'Frontend Service Dockerfile'),
        ('Dockerfile.test-runner', 'Test Runner Dockerfile')
    ]
    
    all_exist = True
    for dockerfile, description in dockerfiles:
        if not check_file_exists(dockerfile, description):
            all_exist = False
    
    return all_exist

def check_database_scripts():
    """Check if database initialization scripts exist"""
    scripts_dir = Path('database_scripts')
    required_scripts = [
        '00-init-main.sql',
        '01-init-extensions.sql',
        '02-init-users-auth.sql',
        '03-init-agents.sql',
        '04-init-supply.sql',
        '05-init-content.sql',
        '06-init-demo.sql',
        '07-init-indexes.sql'
    ]
    
    if not scripts_dir.exists():
        print_error("database_scripts directory not found")
        return False
    
    all_exist = True
    for script in required_scripts:
        script_path = scripts_dir / script
        if not check_file_exists(str(script_path), f"Database script {script}"):
            all_exist = False
    
    return all_exist

def check_env_file():
    """Check if .env.test file exists and has required variables"""
    env_file = '.env.test'
    if not os.path.exists(env_file):
        print_error(f"Environment file {env_file} not found")
        return False
    
    # Check for critical environment variables
    required_vars = [
        'DATABASE_URL',
        'AUTH_DATABASE_URL',
        'CLICKHOUSE_URL',
        'REDIS_URL',
        'SECRET_KEY',
        'JWT_SECRET_KEY',
        'AUTH_SERVICE_URL',
        'BACKEND_SERVICE_URL',
        'FRONTEND_SERVICE_URL'
    ]
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    missing_vars = []
    for var in required_vars:
        if f"{var}=" not in content:
            missing_vars.append(var)
    
    if missing_vars:
        print_error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print_success("All required environment variables are present")
        return True

def check_startup_scripts():
    """Check if startup scripts exist and are executable"""
    scripts = [
        ('start-unified-tests.sh', 'Bash startup script'),
        ('start-unified-tests.ps1', 'PowerShell startup script')
    ]
    
    all_exist = True
    for script, description in scripts:
        if not check_file_exists(script, description):
            all_exist = False
        else:
            # Check if bash script is executable (Unix systems)
            if script.endswith('.sh') and os.name != 'nt':
                if not os.access(script, os.X_OK):
                    print_warning(f"{script} is not executable. Run: chmod +x {script}")
    
    return all_exist

def check_service_directories():
    """Check if service directories exist with necessary files"""
    services = [
        ('app', 'Backend application directory'),
        ('auth_service', 'Auth service directory'),
        ('frontend', 'Frontend application directory'),
        ('alembic', 'Database migration directory')
    ]
    
    all_exist = True
    for service_dir, description in services:
        if not os.path.exists(service_dir):
            print_error(f"{description} not found: {service_dir}")
            all_exist = False
        else:
            print_success(f"{description}: Found")
    
    # Check for requirements files
    req_files = [
        ('requirements.txt', 'Backend requirements'),
        ('auth_service/requirements.txt', 'Auth service requirements'),
        ('frontend/package.json', 'Frontend dependencies')
    ]
    
    for req_file, description in req_files:
        if not check_file_exists(req_file, description):
            all_exist = False
    
    return all_exist

def check_ports_available():
    """Check if required ports are available"""
    import socket
    
    ports = [
        (3000, 'Frontend'),
        (8000, 'Backend'),
        (8001, 'Auth Service'),
        (5433, 'PostgreSQL'),
        (6380, 'Redis'),
        (8124, 'ClickHouse HTTP'),
        (9001, 'ClickHouse Native')
    ]
    
    unavailable_ports = []
    for port, service in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            unavailable_ports.append(f"{port} ({service})")
    
    if unavailable_ports:
        print_warning(f"Ports already in use: {', '.join(unavailable_ports)}")
        print_warning("This may cause conflicts. Consider stopping services using these ports.")
        return False
    else:
        print_success("All required ports are available")
        return True

def main():
    print_status("Validating Netra Unified Testing Environment Setup")
    print("=" * 60)
    
    checks = [
        ("Docker availability", check_docker),
        ("Docker Compose availability", check_docker_compose),
        ("Core configuration files", lambda: all([
            check_file_exists('docker-compose.test.yml', 'Docker Compose file'),
            check_file_exists('.env.test', 'Environment file'),
            check_file_exists('UNIFIED_TESTING_README.md', 'Documentation')
        ])),
        ("Docker Compose configuration", check_compose_config),
        ("Dockerfile existence", check_dockerfile_exists),
        ("Environment configuration", check_env_file),
        ("Database initialization scripts", check_database_scripts),
        ("Service directories and dependencies", check_service_directories),
        ("Startup scripts", check_startup_scripts),
        ("Port availability", check_ports_available)
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\nChecking {check_name}...")
        try:
            if check_func():
                passed += 1
            else:
                print_error(f"Check failed: {check_name}")
        except Exception as e:
            print_error(f"Check error ({check_name}): {e}")
    
    print("\n" + "=" * 60)
    print(f"Validation Results: {passed}/{total} checks passed")
    
    if passed == total:
        print_success("[CHECK] All checks passed! Ready to run unified tests.")
        print_status("Next steps:")
        print("  1. Run: ./start-unified-tests.sh (or .ps1 on Windows)")
        print("  2. Check: ./start-unified-tests.sh --status")
        print("  3. View logs: ./start-unified-tests.sh --logs")
        return 0
    else:
        print_error("[X] Some checks failed. Please fix the issues above before running tests.")
        print_status("Common fixes:")
        print("  - Install Docker Desktop")
        print("  - Ensure all required files are present")
        print("  - Stop conflicting services")
        return 1

if __name__ == "__main__":
    sys.exit(main())