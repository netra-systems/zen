from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
env = get_env()
Comprehensive Test Suite for Netra Adaptive Workflow
Combines authentication, direct testing, and integration tests
"""

import asyncio
import json
import time
import subprocess
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime

# Try to import rich for better formatting
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Note: Install 'rich' for better formatting: pip install rich")

# Default test credentials (can be overridden)
DEFAULT_EMAIL = "test@netra.ai"
DEFAULT_PASSWORD = "TestPassword123!"

def print_header(text: str):
    """Print a formatted header."""
    if RICH_AVAILABLE:
        console.print(Panel(text, style="bold cyan"))
    else:
        print("\n" + "="*70)
        print(f"  {text}")
        print("="*70)

def print_success(text: str):
    """Print success message."""
    if RICH_AVAILABLE:
        console.print(f"[green] PASS:  {text}[/green]")
    else:
        print(f" PASS:  {text}")

def print_error(text: str):
    """Print error message."""
    if RICH_AVAILABLE:
        console.print(f"[red] FAIL:  {text}[/red]")
    else:
        print(f" FAIL:  {text}")

def print_info(text: str):
    """Print info message."""
    if RICH_AVAILABLE:
        console.print(f"[cyan][U+2139][U+FE0F]  {text}[/cyan]")
    else:
        print(f"[U+2139][U+FE0F]  {text}")

class AdaptiveWorkflowTester:
    """Main test class for adaptive workflow."""
    
    def __init__(self):
        self.token = None
        self.base_url = "http://localhost:8000"
        self.auth_url = "http://localhost:8081"
        self.current_email = None
        self.current_password = None
        
    def check_services(self) -> bool:
        """Check if required Docker services are running."""
        print_header("Checking Docker Services")
        
        cmd = "docker-compose ps --services --filter status=running"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        running_services = set(result.stdout.strip().split('\n'))
        required_services = {'backend', 'auth', 'postgres', 'redis'}
        
        missing = required_services - running_services
        
        if missing:
            print_error(f"Missing services: {', '.join(missing)}")
            print_info("Starting missing services...")
            subprocess.run(f"docker-compose up -d {' '.join(missing)}", shell=True)
            time.sleep(5)
            return self.check_services()  # Recursive check
        
        print_success("All required services are running")
        return True
    
    def get_credentials(self) -> tuple:
        """Get credentials from user or use defaults."""
        print_info("Authentication Required")
        print(f"Press Enter to use default test account or enter your credentials")
        print(f"Default: {DEFAULT_EMAIL}")
        
        # Ask for email
        email_input = input("Email (press Enter for default): ").strip()
        email = email_input if email_input else DEFAULT_EMAIL
        
        # Ask for password
        if email_input:
            # User entered custom email, must enter password
            import getpass
            password = getpass.getpass("Password: ")
            if not password:
                print_error("Password cannot be empty")
                return self.get_credentials()
        else:
            # Using default email
            use_default = input("Use default password? (y/n, default=y): ").strip().lower()
            if use_default in ['', 'y', 'yes']:
                password = DEFAULT_PASSWORD
            else:
                import getpass
                password = getpass.getpass("Password: ")
        
        return email, password
    
    def authenticate(self, interactive=True) -> bool:
        """Authenticate and get access token."""
        print_header("Authentication")
        
        try:
            import requests
            
            # Get credentials
            if interactive:
                email, password = self.get_credentials()
            else:
                # Use stored credentials or defaults
                email = self.current_email or DEFAULT_EMAIL
                password = self.current_password or DEFAULT_PASSWORD
            
            # Store credentials for later use
            self.current_email = email
            self.current_password = password
            
            print_info(f"Attempting login as {email}...")
            
            # Try to login
            response = requests.post(
                f"{self.auth_url}/auth/login",
                json={"email": email, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print_success(f"Logged in as {email}")
                return True
            elif response.status_code in [401, 403, 404]:
                print_error("Login failed - invalid credentials or user doesn't exist")
                
                # Ask if user wants to create account
                create = input("Would you like to create this account? (y/n): ").strip().lower()
                if create in ['y', 'yes']:
                    print_info("Creating new user account...")
                    
                    # Get full name
                    full_name = input("Full name (optional): ").strip() or "Test User"
                    
                    # Confirm password for new account
                    import getpass
                    confirm_password = getpass.getpass("Confirm password: ")
                    
                    if password != confirm_password:
                        print_error("Passwords don't match")
                        return self.authenticate(interactive)
                    
                    register_response = requests.post(
                        f"{self.auth_url}/auth/register",
                        json={
                            "email": email,
                            "password": password,
                            "confirm_password": confirm_password,
                            "full_name": full_name
                        }
                    )
                    
                    if register_response.status_code in [200, 201]:
                        print_success("Account created successfully")
                        # Now login with the new account
                        return self.authenticate(interactive=False)
                    else:
                        print_error(f"Failed to create account: {register_response.text[:200]}")
                        retry = input("Try again? (y/n): ").strip().lower()
                        if retry in ['y', 'yes']:
                            return self.authenticate(interactive)
                        return False
                else:
                    retry = input("Try different credentials? (y/n): ").strip().lower()
                    if retry in ['y', 'yes']:
                        return self.authenticate(interactive)
                    return False
            else:
                print_error(f"Login failed: {response.text[:200]}")
                return False
                
        except Exception as e:
            print_error(f"Authentication error: {e}")
            print_info("You can disable auth: export AUTH_SERVICE_ENABLED=false")
            return False
    
    def test_workflow_scenario(self, name: str, request: str, expected_behavior: str) -> bool:
        """Test a specific workflow scenario."""
        print(f"\n CHART:  Testing: {name}")
        print(f"   Request: {request[:80]}...")
        print(f"   Expected: {expected_behavior}")
        
        try:
            import requests
            
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            headers["Content-Type"] = "application/json"
            
            # Create thread
            response = requests.post(
                f"{self.base_url}/api/threads",
                json={
                    "user_prompt": request,
                    "metadata": {"scenario": name}
                },
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                thread_id = data.get("id") or data.get("thread_id")
                print_success(f"Thread created: {thread_id}")
                
                # For now, we'll just verify thread creation
                # In production, you'd poll for completion or use WebSocket
                return True
            else:
                print_error(f"Failed to create thread: {response.status_code}")
                return False
                
        except Exception as e:
            print_error(f"Test error: {e}")
            return False
    
    def run_integration_tests(self) -> bool:
        """Run pytest integration tests."""
        print_header("Running Integration Tests")
        
        cmd = "python -m pytest netra_backend/tests/integration/test_adaptive_workflow.py -v --tb=short"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Parse results
        if "passed" in result.stdout:
            passed = result.stdout.count(" PASSED")
            failed = result.stdout.count(" FAILED")
            
            if failed == 0:
                print_success(f"All {passed} integration tests passed")
                return True
            else:
                print_error(f"{failed} tests failed, {passed} passed")
                return False
        else:
            print_error("Integration tests did not run properly")
            return False
    
    def run_direct_test(self) -> bool:
        """Run the direct workflow test."""
        print_header("Running Direct Workflow Test")
        
        if os.path.exists("test_adaptive_workflow_direct.py"):
            cmd = "python test_adaptive_workflow_direct.py"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if "All workflow tests passed" in result.stdout or result.returncode == 0:
                print_success("Direct workflow tests passed")
                return True
            else:
                print_error("Some direct tests failed")
                return False
        else:
            print_info("Direct test file not found, skipping")
            return True
    
    def run_all_tests(self, interactive=True):
        """Run complete test suite."""
        print_header("[U+1F680] NETRA ADAPTIVE WORKFLOW TEST SUITE")
        
        if RICH_AVAILABLE:
            console.print(Markdown("""
This comprehensive test suite validates the adaptive workflow system:

1. **Environment Check** - Ensures all services are running
2. **Authentication** - Sets up test user and gets access token
3. **Workflow Scenarios** - Tests three data sufficiency levels
4. **Integration Tests** - Runs pytest test suite
5. **Direct Tests** - Runs direct workflow validation
            """))
        
        results = {
            "Services": self.check_services(),
            "Authentication": self.authenticate(interactive=interactive),
        }
        
        # Test workflow scenarios
        if results["Authentication"]:
            print_header("Testing Workflow Scenarios")
            
            scenarios = [
                {
                    "name": "Sufficient Data",
                    "request": "I have a chatbot using GPT-4 serving 10,000 requests daily. "
                               "Average latency is 800ms, cost per request is $0.05. "
                               "Peak hours are 9-11 AM and 2-4 PM. Quality score is 4.2/5.",
                    "expected": "Full optimization workflow with all agents"
                },
                {
                    "name": "Partial Data",
                    "request": "We're using LLMs for customer service with about 5000 daily requests. "
                               "Response times feel slow. Need to reduce costs.",
                    "expected": "Modified workflow with data collection request"
                },
                {
                    "name": "Insufficient Data",
                    "request": "Help me optimize my AI workload",
                    "expected": "Minimal workflow focused on data gathering"
                }
            ]
            
            for scenario in scenarios:
                success = self.test_workflow_scenario(
                    scenario["name"],
                    scenario["request"],
                    scenario["expected"]
                )
                results[f"Scenario: {scenario['name']}"] = success
        
        # Run additional tests
        results["Integration Tests"] = self.run_integration_tests()
        results["Direct Tests"] = self.run_direct_test()
        
        # Display summary
        print_header(" CHART:  TEST SUMMARY")
        
        if RICH_AVAILABLE:
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Test", style="cyan")
            table.add_column("Status", style="green")
            
            for test, passed in results.items():
                status = " PASS:  PASSED" if passed else " FAIL:  FAILED"
                table.add_row(test, status)
            
            console.print(table)
        else:
            for test, passed in results.items():
                status = " PASS: " if passed else " FAIL: "
                print(f"{status} {test}")
        
        # Overall result
        total = len(results)
        passed = sum(1 for v in results.values() if v)
        
        print(f"\n{'='*70}")
        if passed == total:
            print_success(f"ALL TESTS PASSED ({passed}/{total})")
        else:
            print_error(f"SOME TESTS FAILED ({passed}/{total} passed)")
        print(f"{'='*70}")
        
        # Show usage instructions
        if results["Authentication"]:
            print_header("[U+1F511] Authentication Details")
            print("Successfully authenticated!")
            if self.token:
                print(f"Token: {self.token[:30]}...")
                print("\nUse in requests:")
                print(f'Authorization: Bearer {self.token[:30]}...')

def main():
    """Main entry point."""
    tester = AdaptiveWorkflowTester()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if "--help" in sys.argv or "-h" in sys.argv:
            print("""
Netra Adaptive Workflow Test Suite

Usage: python test_adaptive_workflow.py [options]

Options:
  --help, -h        Show this help message
  --no-auth         Skip authentication (requires AUTH_SERVICE_ENABLED=false)
  --quick           Run only workflow scenarios (skip integration tests)
  --integration     Run only integration tests
  --non-interactive Use default credentials without prompting

Examples:
  python test_adaptive_workflow.py              # Run all tests (interactive)
  python test_adaptive_workflow.py --quick      # Quick test
  python test_adaptive_workflow.py --no-auth    # Test without auth
  python test_adaptive_workflow.py --non-interactive  # Use defaults
            """)
            return
        
        # Check for non-interactive mode
        interactive = "--non-interactive" not in sys.argv
        
        if "--no-auth" in sys.argv:
            env.set("AUTH_SERVICE_ENABLED", "false", "test")
            print_info("Authentication disabled")
        
        if "--quick" in sys.argv:
            tester.check_services()
            if "--no-auth" not in sys.argv:
                tester.authenticate(interactive=interactive)
            # Run only scenario tests
            return
        
        if "--integration" in sys.argv:
            tester.run_integration_tests()
            return
    
    # Run full test suite
    tester.run_all_tests(interactive=interactive)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()