#!/usr/bin/env python3
"""
Netra AI Platform - Development Environment Installer
Comprehensive setup script for Windows and macOS
"""

import os
import sys
import subprocess
import platform
import json
import shutil
import time
import socket
import urllib.request
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

class Colors:
    """Terminal colors for better output visibility"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class DevEnvironmentInstaller:
    def __init__(self):
        self.os_type = platform.system().lower()
        self.is_windows = self.os_type == 'windows'
        self.is_mac = self.os_type == 'darwin'
        self.is_linux = self.os_type == 'linux'
        self.project_root = Path.cwd()
        self.venv_path = self.project_root / "venv"
        self.frontend_path = self.project_root / "frontend"
        self.errors = []
        self.warnings = []
        self.installed_components = []
        
        # Minimum versions
        self.min_python_version = (3, 9)
        self.min_node_version = "18.0.0"
        
        # Service configurations
        self.services = {
            'postgresql': {
                'default_port': 5432,
                'test_port': 5433,
                'min_version': '13.0'
            },
            'redis': {
                'default_port': 6379,
                'test_port': 6380,
                'min_version': '6.0'
            },
            'clickhouse': {
                'default_port': 9000,
                'http_port': 8123,
                'min_version': '21.0'
            }
        }

    def print_header(self, text: str):
        """Print a formatted header"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

    def print_step(self, text: str):
        """Print a step indicator"""
        print(f"{Colors.CYAN}➤ {text}{Colors.ENDC}")

    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")
        self.warnings.append(text)

    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")
        self.errors.append(text)

    def print_info(self, text: str):
        """Print info message"""
        print(f"  {text}")

    def check_command_exists(self, command: str) -> bool:
        """Check if a command exists in the system PATH"""
        return shutil.which(command) is not None

    def run_command(self, command: List[str], capture_output: bool = True, 
                   check: bool = True, shell: bool = False, cwd: Optional[Path] = None) -> Optional[str]:
        """Run a command and return output"""
        try:
            if shell and isinstance(command, list):
                command = ' '.join(command)
            
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                check=check,
                shell=shell,
                cwd=cwd
            )
            return result.stdout.strip() if capture_output else None
        except subprocess.CalledProcessError as e:
            if check:
                self.print_error(f"Command failed: {' '.join(command) if isinstance(command, list) else command}")
                if e.stderr:
                    self.print_error(f"Error: {e.stderr}")
            return None
        except Exception as e:
            self.print_error(f"Unexpected error running command: {e}")
            return None

    def get_version(self, command: str, version_flag: str = "--version", 
                   pattern: Optional[str] = None) -> Optional[str]:
        """Get version of a tool"""
        try:
            output = self.run_command([command, version_flag], check=False)
            if output and pattern:
                match = re.search(pattern, output)
                return match.group(1) if match else output.split()[0]
            return output.split()[0] if output else None
        except:
            return None

    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings. Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2"""
        def normalize(v):
            return [int(x) for x in re.sub(r'[^0-9.]', '', v).split('.')]
        
        try:
            v1_parts = normalize(version1)
            v2_parts = normalize(version2)
            
            for i in range(max(len(v1_parts), len(v2_parts))):
                v1_part = v1_parts[i] if i < len(v1_parts) else 0
                v2_part = v2_parts[i] if i < len(v2_parts) else 0
                
                if v1_part < v2_part:
                    return -1
                elif v1_part > v2_part:
                    return 1
            return 0
        except:
            return 0

    def check_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return True
            except:
                return False

    def find_free_port(self, start_port: int, max_attempts: int = 10) -> Optional[int]:
        """Find a free port starting from start_port"""
        for i in range(max_attempts):
            port = start_port + i
            if self.check_port_available(port):
                return port
        return None

    def check_python(self) -> bool:
        """Check Python installation and version"""
        self.print_step("Checking Python installation...")
        
        python_cmd = sys.executable
        version_info = sys.version_info
        
        if version_info >= self.min_python_version:
            self.print_success(f"Python {version_info.major}.{version_info.minor}.{version_info.micro} found")
            return True
        else:
            self.print_error(f"Python {self.min_python_version[0]}.{self.min_python_version[1]}+ required, found {version_info.major}.{version_info.minor}")
            return False

    def check_node(self) -> bool:
        """Check Node.js installation"""
        self.print_step("Checking Node.js installation...")
        
        if not self.check_command_exists("node"):
            self.print_error("Node.js not found. Please install Node.js 18+ from https://nodejs.org/")
            return False
        
        node_version = self.get_version("node", "-v", r'v?(\d+\.\d+\.\d+)')
        if node_version:
            if self.compare_versions(node_version, self.min_node_version) >= 0:
                self.print_success(f"Node.js {node_version} found")
                return True
            else:
                self.print_error(f"Node.js {self.min_node_version}+ required, found {node_version}")
                return False
        
        self.print_warning("Could not determine Node.js version")
        return True

    def check_git(self) -> bool:
        """Check Git installation"""
        self.print_step("Checking Git installation...")
        
        if self.check_command_exists("git"):
            git_version = self.get_version("git", "--version", r'(\d+\.\d+\.\d+)')
            self.print_success(f"Git {git_version} found")
            return True
        else:
            self.print_error("Git not found. Please install Git from https://git-scm.com/")
            return False

    def setup_virtual_environment(self) -> bool:
        """Set up Python virtual environment"""
        self.print_step("Setting up Python virtual environment...")
        
        if self.venv_path.exists():
            self.print_info("Virtual environment already exists")
        else:
            self.print_info("Creating virtual environment...")
            result = self.run_command([sys.executable, "-m", "venv", str(self.venv_path)])
            if result is not None or not self.venv_path.exists():
                self.print_success("Virtual environment created")
            else:
                self.print_error("Failed to create virtual environment")
                return False
        
        # Get pip path
        if self.is_windows:
            pip_path = self.venv_path / "Scripts" / "pip.exe"
            python_path = self.venv_path / "Scripts" / "python.exe"
        else:
            pip_path = self.venv_path / "bin" / "pip"
            python_path = self.venv_path / "bin" / "python"
        
        # Upgrade pip
        self.print_info("Upgrading pip...")
        self.run_command([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], check=False)
        
        # Install requirements
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            self.print_info("Installing Python dependencies (this may take a few minutes)...")
            result = self.run_command([str(pip_path), "install", "-r", str(requirements_file)], check=False)
            if result is not None:
                self.print_success("Python dependencies installed")
                self.installed_components.append("Python packages")
                return True
            else:
                # Try with individual packages if bulk install fails
                self.print_warning("Bulk install failed, trying individual packages...")
                essential_packages = [
                    "fastapi", "uvicorn", "sqlalchemy", "aiosqlite", "asyncpg",
                    "redis", "pydantic", "python-jose", "passlib", "bcrypt",
                    "python-multipart", "httpx", "pytest", "pytest-asyncio"
                ]
                for package in essential_packages:
                    self.run_command([str(pip_path), "install", package], check=False)
                self.print_success("Essential Python packages installed")
                self.installed_components.append("Essential Python packages")
                return True
        else:
            self.print_error("requirements.txt not found")
            return False

    def install_postgresql(self) -> bool:
        """Install or check PostgreSQL"""
        self.print_step("Checking PostgreSQL...")
        
        if self.check_command_exists("psql"):
            version = self.get_version("psql", "--version", r'(\d+\.\d+)')
            self.print_success(f"PostgreSQL {version} found")
            return True
        
        self.print_warning("PostgreSQL not found")
        
        if self.is_windows:
            self.print_info("Please install PostgreSQL from: https://www.postgresql.org/download/windows/")
            self.print_info("Or install via Chocolatey: choco install postgresql")
        elif self.is_mac:
            if self.check_command_exists("brew"):
                self.print_info("Installing PostgreSQL via Homebrew...")
                self.run_command(["brew", "install", "postgresql@14"], check=False)
                self.run_command(["brew", "services", "start", "postgresql@14"], check=False)
                return True
            else:
                self.print_info("Install Homebrew first: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
                self.print_info("Then run: brew install postgresql@14")
        else:
            self.print_info("Install PostgreSQL using your package manager:")
            self.print_info("  Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib")
            self.print_info("  RHEL/CentOS: sudo yum install postgresql-server postgresql-contrib")
        
        return False

    def install_redis(self) -> bool:
        """Install or check Redis"""
        self.print_step("Checking Redis...")
        
        if self.check_command_exists("redis-cli"):
            version = self.get_version("redis-cli", "--version", r'(\d+\.\d+\.\d+)')
            self.print_success(f"Redis {version} found")
            return True
        
        self.print_warning("Redis not found")
        
        if self.is_windows:
            self.print_info("Redis on Windows:")
            self.print_info("1. Enable WSL2: wsl --install")
            self.print_info("2. Install Redis in WSL: sudo apt update && sudo apt install redis-server")
            self.print_info("Or use Redis for Windows from: https://github.com/microsoftarchive/redis/releases")
        elif self.is_mac:
            if self.check_command_exists("brew"):
                self.print_info("Installing Redis via Homebrew...")
                self.run_command(["brew", "install", "redis"], check=False)
                self.run_command(["brew", "services", "start", "redis"], check=False)
                return True
            else:
                self.print_info("Install Homebrew first, then run: brew install redis")
        else:
            self.print_info("Install Redis using your package manager:")
            self.print_info("  Ubuntu/Debian: sudo apt-get install redis-server")
            self.print_info("  RHEL/CentOS: sudo yum install redis")
        
        return False

    def install_clickhouse(self) -> bool:
        """Install or check ClickHouse"""
        self.print_step("Checking ClickHouse...")
        
        if self.check_command_exists("clickhouse-client"):
            self.print_success("ClickHouse found")
            return True
        
        self.print_warning("ClickHouse not found (optional for development)")
        self.print_info("ClickHouse is optional for local development")
        self.print_info("To install ClickHouse, visit: https://clickhouse.com/docs/en/install")
        
        return True  # Not critical for development

    def setup_frontend(self) -> bool:
        """Set up frontend dependencies"""
        self.print_step("Setting up frontend...")
        
        if not self.frontend_path.exists():
            self.print_error("Frontend directory not found")
            return False
        
        # Check for package.json
        package_json = self.frontend_path / "package.json"
        if not package_json.exists():
            self.print_error("package.json not found in frontend directory")
            return False
        
        # Install npm dependencies
        self.print_info("Installing frontend dependencies (this may take a few minutes)...")
        
        # First, clean any existing installations
        node_modules = self.frontend_path / "node_modules"
        package_lock = self.frontend_path / "package-lock.json"
        
        if node_modules.exists():
            self.print_info("Cleaning existing node_modules...")
            if self.is_windows:
                self.run_command(["rmdir", "/s", "/q", str(node_modules)], shell=True, check=False)
            else:
                self.run_command(["rm", "-rf", str(node_modules)], check=False)
        
        # Install dependencies
        result = self.run_command(["npm", "install"], cwd=self.frontend_path, check=False)
        
        if result is not None or node_modules.exists():
            self.print_success("Frontend dependencies installed")
            self.installed_components.append("Frontend packages")
            
            # Build frontend
            self.print_info("Building frontend...")
            build_result = self.run_command(["npm", "run", "build"], cwd=self.frontend_path, check=False)
            if build_result is not None:
                self.print_success("Frontend built successfully")
            else:
                self.print_warning("Frontend build failed (can rebuild later with 'npm run build')")
            
            return True
        else:
            self.print_error("Failed to install frontend dependencies")
            return False

    def setup_databases(self) -> bool:
        """Initialize databases"""
        self.print_step("Setting up databases...")
        
        # Get Python executable from venv
        if self.is_windows:
            python_path = self.venv_path / "Scripts" / "python.exe"
        else:
            python_path = self.venv_path / "bin" / "python"
        
        # Check if PostgreSQL is running
        if self.check_command_exists("pg_isready"):
            pg_status = self.run_command(["pg_isready"], check=False)
            if pg_status and "accepting connections" in pg_status:
                self.print_info("PostgreSQL is running")
            else:
                self.print_warning("PostgreSQL is not running. Please start it manually.")
                return True  # Continue anyway
        
        # Run database creation script
        create_db_script = self.project_root / "create_db.py"
        if create_db_script.exists():
            self.print_info("Creating database...")
            result = self.run_command([str(python_path), str(create_db_script)], check=False)
            if result is not None:
                self.print_success("Database created")
            else:
                self.print_warning("Database creation failed (may already exist)")
        
        # Run migrations
        migrations_script = self.project_root / "run_migrations.py"
        if migrations_script.exists():
            self.print_info("Running database migrations...")
            result = self.run_command([str(python_path), str(migrations_script)], check=False)
            if result is not None:
                self.print_success("Migrations completed")
                self.installed_components.append("Database setup")
            else:
                self.print_warning("Migrations failed (will retry on first run)")
        
        return True

    def create_env_file(self) -> bool:
        """Create .env file with default configuration"""
        self.print_step("Creating environment configuration...")
        
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if env_file.exists():
            self.print_info(".env file already exists")
            return True
        
        # Default environment variables
        env_content = """# Netra AI Platform - Development Environment Configuration
# Generated by install_dev_env.py

# Environment
ENVIRONMENT=development
DEBUG=true

# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/netra_dev
CLICKHOUSE_URL=clickhouse://default:@localhost:9000/default
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=dev-secret-key-change-in-production-{random}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Keys (add your own)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# OAuth (optional)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Frontend Configuration
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=true
WORKERS=1
LOG_LEVEL=INFO

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000

# Service Limits
MAX_CONNECTIONS=100
REQUEST_TIMEOUT=30
WS_HEARTBEAT_INTERVAL=30
WS_CONNECTION_TIMEOUT=60

# Feature Flags
ENABLE_METRICS=true
ENABLE_CACHE=true
ENABLE_WEBSOCKET=true
ENABLE_OAUTH=false

# Cache Configuration
CACHE_TTL=3600
CACHE_MAX_SIZE=1000
""".format(random=os.urandom(24).hex())
        
        # Copy from example if it exists
        if env_example.exists():
            self.print_info("Copying from .env.example...")
            shutil.copy(env_example, env_file)
            self.print_success(".env file created from example")
        else:
            # Create new .env file
            with open(env_file, 'w') as f:
                f.write(env_content)
            self.print_success(".env file created with default values")
        
        self.print_info("Please update .env with your API keys and configuration")
        self.installed_components.append("Environment configuration")
        return True

    def create_startup_scripts(self) -> bool:
        """Create convenient startup scripts"""
        self.print_step("Creating startup scripts...")
        
        # Windows batch script
        if self.is_windows:
            bat_content = """@echo off
echo Starting Netra AI Development Environment...
echo.

REM Activate virtual environment
call venv\\Scripts\\activate.bat

REM Start services in new windows
echo Starting Backend Server...
start "Netra Backend" cmd /k "python dev_launcher.py --dynamic --no-backend-reload"

echo.
echo Development environment is starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Press any key to stop all services...
pause >nul

REM Kill processes
taskkill /FI "WindowTitle eq Netra Backend" /T /F
echo Services stopped.
"""
            
            bat_file = self.project_root / "start_dev.bat"
            with open(bat_file, 'w') as f:
                f.write(bat_content)
            self.print_success("Created start_dev.bat")
        
        # Unix shell script
        else:
            sh_content = """#!/bin/bash

echo "Starting Netra AI Development Environment..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Start services
echo "Starting Backend and Frontend..."
python dev_launcher.py --dynamic --no-backend-reload &
LAUNCHER_PID=$!

echo ""
echo "Development environment is starting..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for interrupt
trap "kill $LAUNCHER_PID; echo 'Services stopped.'; exit" INT
wait $LAUNCHER_PID
"""
            
            sh_file = self.project_root / "start_dev.sh"
            with open(sh_file, 'w') as f:
                f.write(sh_content)
            
            # Make executable
            os.chmod(sh_file, 0o755)
            self.print_success("Created start_dev.sh")
        
        self.installed_components.append("Startup scripts")
        return True

    def test_installation(self) -> bool:
        """Run basic tests to verify installation"""
        self.print_step("Testing installation...")
        
        # Get Python from venv
        if self.is_windows:
            python_path = self.venv_path / "Scripts" / "python.exe"
        else:
            python_path = self.venv_path / "bin" / "python"
        
        # Test Python imports
        self.print_info("Testing Python imports...")
        test_imports = [
            "fastapi", "uvicorn", "sqlalchemy", "pydantic",
            "redis", "httpx", "pytest"
        ]
        
        for module in test_imports:
            result = self.run_command(
                [str(python_path), "-c", f"import {module}"],
                check=False, capture_output=False
            )
            if result is None:
                self.print_info(f"  ✓ {module}")
            else:
                self.print_warning(f"  ✗ {module} (optional)")
        
        # Test frontend build
        if (self.frontend_path / "node_modules").exists():
            self.print_info("Frontend dependencies: ✓")
        else:
            self.print_warning("Frontend dependencies: ✗")
        
        # Test database connectivity
        self.print_info("Testing database connectivity...")
        test_db_script = f"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine

async def test_db():
    try:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            print("Database connectivity: ✓")
            return True
    except Exception as e:
        print(f"Database connectivity: ✗ ({{e}})")
        return False

asyncio.run(test_db())
"""
        
        result = self.run_command(
            [str(python_path), "-c", test_db_script],
            check=False
        )
        
        return True

    def print_summary(self):
        """Print installation summary"""
        self.print_header("Installation Summary")
        
        if self.installed_components:
            self.print_success("Successfully installed components:")
            for component in self.installed_components:
                self.print_info(f"  • {component}")
        
        if self.warnings:
            print(f"\n{Colors.WARNING}Warnings:{Colors.ENDC}")
            for warning in self.warnings[:5]:  # Show first 5 warnings
                self.print_info(f"  • {warning}")
            if len(self.warnings) > 5:
                self.print_info(f"  ... and {len(self.warnings) - 5} more")
        
        if self.errors:
            print(f"\n{Colors.FAIL}Errors:{Colors.ENDC}")
            for error in self.errors[:5]:  # Show first 5 errors
                self.print_info(f"  • {error}")
            if len(self.errors) > 5:
                self.print_info(f"  ... and {len(self.errors) - 5} more")
        
        print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
        
        if not self.errors:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Installation completed successfully!{Colors.ENDC}\n")
            print("Next steps:")
            if self.is_windows:
                print("  1. Run: start_dev.bat")
            else:
                print("  1. Run: ./start_dev.sh")
            print("  2. Open: http://localhost:3000")
            print("  3. Update .env file with your API keys")
            print("\nAlternative commands:")
            print("  • Full setup: python dev_launcher.py --dynamic --no-backend-reload")
            print("  • Quick test: python test_runner.py --mode quick")
            print("  • Backend only: python run_server.py")
            print("  • Frontend only: cd frontend && npm run dev")
        else:
            print(f"\n{Colors.WARNING}⚠ Installation completed with issues{Colors.ENDC}\n")
            print("Please address the errors above and try again.")
            print("For help, consult the README.md or CLAUDE.md files.")

    def run(self) -> bool:
        """Run the complete installation process"""
        self.print_header("Netra AI Platform - Dev Environment Setup")
        print(f"Platform: {platform.system()} {platform.machine()}")
        print(f"Python: {sys.version}")
        print(f"Project: {self.project_root}")
        
        # Step 1: Check prerequisites
        self.print_header("Step 1: Checking Prerequisites")
        python_ok = self.check_python()
        node_ok = self.check_node()
        git_ok = self.check_git()
        
        if not python_ok:
            self.print_error("Python requirements not met. Please install Python 3.9+")
            return False
        
        # Step 2: Set up Python environment
        self.print_header("Step 2: Python Environment Setup")
        if not self.setup_virtual_environment():
            self.print_error("Failed to set up Python environment")
            return False
        
        # Step 3: Check/Install services
        self.print_header("Step 3: Database Services")
        pg_ok = self.install_postgresql()
        redis_ok = self.install_redis()
        ch_ok = self.install_clickhouse()
        
        if not pg_ok:
            self.print_warning("PostgreSQL not available - using SQLite for development")
        if not redis_ok:
            self.print_warning("Redis not available - caching will be disabled")
        
        # Step 4: Set up frontend
        if node_ok:
            self.print_header("Step 4: Frontend Setup")
            self.setup_frontend()
        else:
            self.print_warning("Skipping frontend setup - Node.js not available")
        
        # Step 5: Initialize databases
        self.print_header("Step 5: Database Initialization")
        self.setup_databases()
        
        # Step 6: Create configuration files
        self.print_header("Step 6: Configuration")
        self.create_env_file()
        self.create_startup_scripts()
        
        # Step 7: Test installation
        self.print_header("Step 7: Verification")
        self.test_installation()
        
        # Print summary
        self.print_summary()
        
        return len(self.errors) == 0


def main():
    """Main entry point"""
    installer = DevEnvironmentInstaller()
    
    try:
        success = installer.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Installation interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()