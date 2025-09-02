from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Automated Staging Test Runner
Handles all environment setup and configuration for staging tests
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Optional
import argparse
import json
from datetime import datetime

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class StagingTestRunner:
    """Manages staging test execution with proper environment setup"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.project_root = PROJECT_ROOT
        self.is_windows = platform.system() == 'Windows'
        self.test_results = []
        
    def setup_environment(self) -> Dict[str, str]:
        """Set up all required environment variables for staging tests"""
        env = os.environ.copy()
        
        # Core environment settings
        env["ENVIRONMENT"] = "staging"
        env["PYTHONPATH"] = str(self.project_root)
        
        # Load .env.staging file if it exists
        env_staging_path = self.project_root / ".env.staging"
        if env_staging_path.exists():
            print(f"[OK] Loading staging environment from {env_staging_path}")
            self._load_env_file(env_staging_path, env)
        else:
            print("[WARNING] .env.staging file not found, using default values")
            # Set critical values if .env.staging doesn't exist
            env["E2E_OAUTH_SIMULATION_KEY"] = "25006a4abd79f48e8e7a62c2b1b87245a449348ac0a01ac69a18521c7e140444"
            env["REDIS_REQUIRED"] = "false"
            env["REDIS_FALLBACK_ENABLED"] = "true"
        
        # Ensure critical staging URLs are set
        env.setdefault("API_BASE_URL", "https://api.staging.netrasystems.ai")
        env.setdefault("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai")
        env.setdefault("FRONTEND_URL", "https://app.staging.netrasystems.ai")
        env.setdefault("WS_BASE_URL", "wss://api.staging.netrasystems.ai/ws")
        
        # Windows-specific UTF-8 encoding
        if self.is_windows:
            env["PYTHONIOENCODING"] = "utf-8"
            
        if self.verbose:
            print("\n[INFO] Environment Configuration:")
            for key in ["ENVIRONMENT", "PYTHONPATH", "E2E_OAUTH_SIMULATION_KEY", 
                       "API_BASE_URL", "AUTH_SERVICE_URL"]:
                value = env.get(key, "NOT SET")
                if key == "E2E_OAUTH_SIMULATION_KEY" and value != "NOT SET":
                    value = value[:10] + "..." if len(value) > 10 else value
                print(f"  {key}: {value}")
                
        return env
    
    def _load_env_file(self, env_file: Path, env_dict: Dict[str, str]):
        """Load environment variables from a .env file"""
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_dict[key.strip()] = value.strip()
    
    def check_services_health(self) -> bool:
        """Check if staging services are healthy"""
        print("\n[HEALTH] Checking Staging Services Health...")
        
        services = [
            ("API Backend", "https://api.staging.netrasystems.ai/health"),
            ("Auth Service", "https://auth.staging.netrasystems.ai/health"),
            ("Frontend", "https://app.staging.netrasystems.ai"),
        ]
        
        all_healthy = True
        for name, url in services:
            try:
                import requests
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    print(f"  [OK] {name}: OK (200)")
                else:
                    print(f"  [FAIL] {name}: {response.status_code}")
                    all_healthy = False
            except Exception as e:
                print(f"  [FAIL] {name}: Failed ({str(e)})")
                all_healthy = False
                
        return all_healthy
    
    def run_test_suite(self, test_path: str = None, markers: str = None, 
                       category: str = None) -> int:
        """Run the test suite with proper configuration"""
        env = self.setup_environment()
        
        # Build pytest command
        cmd = [sys.executable, "-m", "pytest"]
        
        # Add test path
        if test_path:
            cmd.append(test_path)
        else:
            # Default to E2E tests for staging
            cmd.append("tests/e2e")
        
        # Add markers
        if markers:
            cmd.extend(["-m", markers])
        elif not test_path:
            # Default to staging marker if no specific path/marker provided
            cmd.extend(["-m", "staging"])
        
        # Add verbosity and output options
        cmd.extend([
            "-v",
            "--tb=short",
            "--color=yes",
            "-p", "no:warnings",
        ])
        
        # Add test category if specified
        if category:
            cmd.extend(["--category", category])
        
        print(f"\n[RUN] Running command: {' '.join(cmd)}")
        print("=" * 60)
        
        # Run the tests
        result = subprocess.run(cmd, env=env, cwd=str(self.project_root))
        
        return result.returncode
    
    def run_mission_critical_tests(self) -> int:
        """Run mission critical WebSocket tests"""
        print("\n[CRITICAL] Running Mission Critical WebSocket Tests...")
        
        env = self.setup_environment()
        test_file = self.project_root / "tests" / "mission_critical" / "test_websocket_agent_events_suite.py"
        
        if not test_file.exists():
            print(f"[WARNING] Mission critical test file not found: {test_file}")
            return 1
            
        cmd = [sys.executable, str(test_file)]
        
        result = subprocess.run(cmd, env=env, cwd=str(self.project_root))
        return result.returncode
    
    def run_unified_test_runner(self, categories: List[str] = None) -> int:
        """Run tests using the unified test runner"""
        print("\n[INFO] Running Unified Test Runner...")
        
        env = self.setup_environment()
        cmd = [sys.executable, "unified_test_runner.py"]
        
        if categories:
            cmd.extend(["--categories"] + categories)
        else:
            # Default categories for staging
            cmd.extend(["--categories", "smoke", "integration", "api", "e2e"])
        
        cmd.extend([
            "--env", "staging",
            "--real-llm",
            "--no-coverage",
            "--fast-fail"
        ])
        
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, env=env, cwd=str(self.project_root))
        return result.returncode
    
    def run_specific_test(self, test_file: str) -> int:
        """Run a specific test file"""
        print(f"\n[TEST] Running specific test: {test_file}")
        
        env = self.setup_environment()
        
        # Check if it's a pytest-style test path (contains ::)
        if "::" in test_file:
            # Direct pytest path - use as is
            cmd = [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"]
        else:
            # File path - check if it exists
            test_path = self.project_root / test_file
            if not test_path.exists():
                print(f"[WARNING] Test file not found: {test_path}")
                return 1
            cmd = [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"]
        
        result = subprocess.run(cmd, env=env, cwd=str(self.project_root))
        return result.returncode
    
    def generate_report(self, results: List[Dict]) -> None:
        """Generate a test execution report"""
        report_path = self.project_root / f"staging_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "environment": "staging",
            "results": results,
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.get("status") == "passed"),
                "failed": sum(1 for r in results if r.get("status") == "failed"),
            }
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n[REPORT] Test report saved to: {report_path}")

def main():
    """Main entry point for the staging test runner"""
    parser = argparse.ArgumentParser(
        description="Automated Staging Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all staging E2E tests
  python run_staging_tests.py
  
  # Run specific test file
  python run_staging_tests.py --test tests/e2e/test_staging_e2e_comprehensive.py
  
  # Run mission critical tests
  python run_staging_tests.py --mission-critical
  
  # Run with unified test runner
  python run_staging_tests.py --unified
  
  # Check service health only
  python run_staging_tests.py --health-check
        """
    )
    
    parser.add_argument("--test", help="Specific test file to run")
    parser.add_argument("--markers", "-m", help="Pytest markers to use")
    parser.add_argument("--category", help="Test category to run")
    parser.add_argument("--unified", action="store_true", 
                       help="Use unified test runner")
    parser.add_argument("--mission-critical", action="store_true",
                       help="Run mission critical tests")
    parser.add_argument("--health-check", action="store_true",
                       help="Only check service health")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--categories", nargs="+",
                       help="Categories for unified test runner")
    
    args = parser.parse_args()
    
    runner = StagingTestRunner(verbose=args.verbose)
    
    print("Netra Staging Test Runner")
    print("=" * 60)
    
    # Health check
    if args.health_check or not args.mission_critical:
        if not runner.check_services_health():
            print("\n[WARNING] Some services are not healthy")
            if args.health_check:
                return 1
    
    if args.health_check:
        return 0
    
    # Run requested tests
    exit_code = 0
    
    if args.mission_critical:
        exit_code = runner.run_mission_critical_tests()
    elif args.unified:
        exit_code = runner.run_unified_test_runner(args.categories)
    elif args.test:
        exit_code = runner.run_specific_test(args.test)
    else:
        # Default: run staging E2E tests
        exit_code = runner.run_test_suite(
            test_path=args.test,
            markers=args.markers,
            category=args.category
        )
    
    # Print summary
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("[SUCCESS] Tests completed successfully!")
    else:
        print(f"[FAILED] Tests failed with exit code: {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
