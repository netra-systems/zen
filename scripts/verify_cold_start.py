#!/usr/bin/env python3
"""
Cold Start Verification Script for Netra Apex

This script verifies that all services can start cleanly without errors.
It performs comprehensive checks on:
1. Configuration consistency
2. Service startup readiness 
3. Port availability
4. Environment variables
5. Authentication flow
6. WebSocket connectivity

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Startup Reliability
- Value Impact: Prevents customer-facing errors during system startup
- Strategic Impact: Ensures reliable deployment and development experience
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import socket
import urllib.request
import urllib.error

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ColdStartVerifier:
    """Comprehensive cold start verification for Netra Apex."""
    
    def __init__(self):
        self.project_root = project_root
        self.results: Dict[str, Dict] = {}
        self.errors: List[str] = []
        
    def log(self, message: str, level: str = "INFO") -> None:
        """Log message with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"{timestamp} | {level:5} | {message}")
    
    def log_success(self, message: str) -> None:
        """Log success message."""
        self.log(f"[PASS] {message}", "PASS")
    
    def log_error(self, message: str) -> None:
        """Log error message."""
        self.log(f"[FAIL] {message}", "FAIL")
        self.errors.append(message)
    
    def log_warning(self, message: str) -> None:
        """Log warning message."""
        self.log(f"[WARN] {message}", "WARN")
    
    def is_port_available(self, port: int, host: str = "localhost") -> bool:
        """Check if port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0
        except Exception:
            return True
    
    def check_file_exists(self, filepath: Path, description: str) -> bool:
        """Check if file exists."""
        if filepath.exists():
            self.log_success(f"{description}: {filepath}")
            return True
        else:
            self.log_error(f"{description} missing: {filepath}")
            return False
    
    def verify_environment_files(self) -> Dict[str, bool]:
        """Verify all environment configuration files exist."""
        self.log("[CHECK] Checking environment configuration files...")
        
        files_to_check = [
            (self.project_root / ".env", "Main environment file"),
            (self.project_root / "frontend" / ".env.local", "Frontend environment file"),
            (self.project_root / "requirements.txt", "Python requirements"),
            (self.project_root / "frontend" / "package.json", "Frontend package.json"),
        ]
        
        results = {}
        for filepath, description in files_to_check:
            results[str(filepath)] = self.check_file_exists(filepath, description)
        
        return results
    
    def verify_port_availability(self) -> Dict[str, bool]:
        """Verify all required ports are available."""
        self.log("[CHECK] Checking port availability...")
        
        ports_to_check = [
            (8000, "Backend API"),
            (3000, "Frontend"),
            (8081, "Auth Service"),
            (5433, "PostgreSQL"),
            (6379, "Redis"),
            (8123, "ClickHouse HTTP"),
            (9000, "ClickHouse Native"),
        ]
        
        results = {}
        for port, service in ports_to_check:
            available = self.is_port_available(port)
            if available:
                self.log_success(f"Port {port} ({service}) is available")
            else:
                self.log_warning(f"Port {port} ({service}) is in use")
            results[f"{port}_{service}"] = available
        
        return results
    
    def verify_environment_variables(self) -> Dict[str, bool]:
        """Verify critical environment variables are set."""
        self.log("[CHECK] Checking environment variables...")
        
        # Load .env file
        env_file = self.project_root / ".env"
        env_vars = {}
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
        
        critical_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "JWT_SECRET_KEY",
            "AUTH_SERVICE_URL", 
            "NEXT_PUBLIC_API_URL",
            "NEXT_PUBLIC_WS_URL",
        ]
        
        results = {}
        for var in critical_vars:
            if var in env_vars and env_vars[var].strip():
                self.log_success(f"Environment variable {var} is set")
                results[var] = True
            else:
                self.log_error(f"Environment variable {var} is missing or empty")
                results[var] = False
        
        # Check for configuration consistency
        self.verify_configuration_consistency(env_vars)
        
        return results
    
    def verify_configuration_consistency(self, env_vars: Dict[str, str]) -> None:
        """Verify configuration consistency between files."""
        self.log("[CHECK] Checking configuration consistency...")
        
        # Check auth service URL consistency
        auth_url_main = env_vars.get("AUTH_SERVICE_URL", "")
        if "8081" in auth_url_main:
            self.log_success("Auth service URL correctly configured for port 8081")
        else:
            self.log_error(f"Auth service URL should use port 8081, found: {auth_url_main}")
        
        # Check WebSocket URL
        ws_url = env_vars.get("NEXT_PUBLIC_WS_URL", "")
        if "ws://localhost:8000" in ws_url:
            self.log_success("WebSocket URL correctly configured for port 8000")
        else:
            self.log_error(f"WebSocket URL should use port 8000, found: {ws_url}")
        
        # Check frontend .env.local
        frontend_env = self.project_root / "frontend" / ".env.local"
        if frontend_env.exists():
            with open(frontend_env, 'r') as f:
                frontend_content = f.read()
                if "AUTH_SERVICE_URL=http://localhost:8081" in frontend_content:
                    self.log_success("Frontend auth service URL correctly configured")
                else:
                    self.log_error("Frontend auth service URL should use port 8081")
    
    def verify_service_startup_readiness(self) -> Dict[str, bool]:
        """Verify services are ready to start."""
        self.log("[CHECK] Checking service startup readiness...")
        
        results = {}
        
        # Check backend directory and files
        backend_dir = self.project_root / "netra_backend" / "app"
        if backend_dir.exists():
            main_py = backend_dir / "main.py"
            if main_py.exists():
                self.log_success("Backend main.py exists")
                results["backend_main"] = True
            else:
                self.log_error("Backend main.py missing")
                results["backend_main"] = False
        else:
            self.log_error("Backend directory missing")
            results["backend_dir"] = False
        
        # Check auth service
        auth_dir = self.project_root / "auth_service"
        if auth_dir.exists():
            auth_main = auth_dir / "main.py"
            if auth_main.exists():
                self.log_success("Auth service main.py exists")
                results["auth_main"] = True
            else:
                self.log_error("Auth service main.py missing")
                results["auth_main"] = False
        else:
            self.log_error("Auth service directory missing")
            results["auth_dir"] = False
        
        # Check frontend
        frontend_dir = self.project_root / "frontend"
        if frontend_dir.exists():
            package_json = frontend_dir / "package.json"
            if package_json.exists():
                self.log_success("Frontend package.json exists")
                results["frontend_package"] = True
            else:
                self.log_error("Frontend package.json missing")
                results["frontend_package"] = False
        else:
            self.log_error("Frontend directory missing")
            results["frontend_dir"] = False
        
        return results
    
    def verify_python_imports(self) -> Dict[str, bool]:
        """Verify critical Python imports work."""
        self.log("[CHECK] Checking Python imports...")
        
        imports_to_test = [
            ("fastapi", "FastAPI framework"),
            ("sqlalchemy", "Database ORM"),
            ("redis", "Redis client"),
            ("uvicorn", "ASGI server"),
            ("pydantic", "Data validation"),
            ("jwt", "JWT tokens (PyJWT)"),
        ]
        
        results = {}
        for module, description in imports_to_test:
            try:
                __import__(module)
                self.log_success(f"Import {module} ({description}) successful")
                results[module] = True
            except ImportError as e:
                self.log_error(f"Import {module} failed: {e}")
                results[module] = False
        
        return results
    
    def test_websocket_configuration(self) -> bool:
        """Test WebSocket configuration is correct."""
        self.log("[CHECK] Testing WebSocket configuration...")
        
        # Check frontend WebSocket config
        config_file = self.project_root / "frontend" / "lib" / "secure-api-config.ts"
        if config_file.exists():
            with open(config_file, 'r') as f:
                content = f.read()
                if "ws://localhost:8000" in content:
                    self.log_success("Frontend WebSocket config uses port 8000")
                    return True
                else:
                    self.log_error("Frontend WebSocket config should use port 8000")
                    return False
        else:
            self.log_error("Frontend WebSocket config file missing")
            return False
    
    async def run_quick_startup_test(self) -> bool:
        """Run a quick startup test to see if services can start."""
        self.log("[TEST] Running quick startup test...")
        
        try:
            # Test auth service startup (dry run)
            auth_cmd = [
                sys.executable, "-c",
                """
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from auth_service.main import app
print("Auth service import successful")
"""
            ]
            
            result = subprocess.run(
                auth_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.log_success("Auth service can import successfully")
                return True
            else:
                self.log_error(f"Auth service import failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.log_error("Auth service startup test timed out")
            return False
        except Exception as e:
            self.log_error(f"Startup test failed: {e}")
            return False
    
    def generate_report(self) -> Dict:
        """Generate comprehensive verification report."""
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "project_root": str(self.project_root),
            "results": self.results,
            "errors": self.errors,
            "total_errors": len(self.errors),
            "status": "PASS" if len(self.errors) == 0 else "FAIL"
        }
    
    async def run_full_verification(self) -> Dict:
        """Run full cold start verification."""
        self.log("=" * 60)
        self.log("NETRA APEX COLD START VERIFICATION")
        self.log("=" * 60)
        
        # Run all verification steps
        self.results["environment_files"] = self.verify_environment_files()
        self.results["port_availability"] = self.verify_port_availability()
        self.results["environment_variables"] = self.verify_environment_variables()
        self.results["service_readiness"] = self.verify_service_startup_readiness()
        self.results["python_imports"] = self.verify_python_imports()
        self.results["websocket_config"] = {"test": self.test_websocket_configuration()}
        self.results["startup_test"] = {"quick_test": await self.run_quick_startup_test()}
        
        # Generate and display report
        report = self.generate_report()
        
        self.log("=" * 60)
        self.log("VERIFICATION SUMMARY")
        self.log("=" * 60)
        
        if report["status"] == "PASS":
            self.log_success("All verification checks passed! System is ready for cold start.")
        else:
            self.log_error(f"Verification failed with {report['total_errors']} errors")
            self.log("ERRORS TO FIX:")
            for i, error in enumerate(self.errors, 1):
                self.log(f"  {i}. {error}")
        
        self.log("=" * 60)
        
        return report

def main():
    """Main entry point."""
    try:
        verifier = ColdStartVerifier()
        report = asyncio.run(verifier.run_full_verification())
        
        # Save report
        report_file = verifier.project_root / "cold_start_verification_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Report saved to: {report_file}")
        
        # Exit with appropriate code
        exit_code = 0 if report["status"] == "PASS" else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()