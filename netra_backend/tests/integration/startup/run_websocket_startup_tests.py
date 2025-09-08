#!/usr/bin/env python3
"""
WebSocket Startup Integration Test Runner

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Reliability  
- Value Impact: Ensures WebSocket infrastructure is properly tested for chat delivery
- Strategic Impact: Validates system startup readiness for revenue-generating chat interactions

This script runs the comprehensive WebSocket startup integration tests to validate
that all WebSocket components are properly initialized during system startup.

Usage:
    python run_websocket_startup_tests.py [options]
    
Options:
    --verbose: Enable verbose output
    --fast-fail: Stop on first test failure
    --performance: Include performance tests
    --security: Include security tests  
    --multi-user: Include multi-user isolation tests
    --chat-events: Include critical chat events tests
    --all: Run all test categories
    
Examples:
    python run_websocket_startup_tests.py --all --verbose
    python run_websocket_startup_tests.py --chat-events --fast-fail
    python run_websocket_startup_tests.py --multi-user --performance
"""

import sys
import os
import asyncio
import argparse
import subprocess
import time
from typing import List, Dict, Any
import logging
from pathlib import Path

# Add parent directories to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent.parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class WebSocketStartupTestRunner:
    """Test runner for WebSocket startup integration tests."""
    
    def __init__(self):
        """Initialize test runner."""
        self.test_file = current_dir / "test_websocket_phase_comprehensive.py"
        self.start_time = None
        self.end_time = None
        self.test_results = {}
        
    def build_pytest_command(self, args: argparse.Namespace) -> List[str]:
        """Build pytest command based on arguments."""
        cmd = ["python", "-m", "pytest", str(self.test_file)]
        
        # Add verbosity
        if args.verbose:
            cmd.append("-vvs")
        else:
            cmd.append("-v")
            
        # Add fail-fast option
        if args.fast_fail:
            cmd.append("-x")
            
        # Add test markers based on options
        markers = []
        
        if args.websocket or args.all:
            markers.append("websocket")
            
        if args.startup or args.all:
            markers.append("startup")
            
        if args.business_value or args.all:
            markers.append("business_value")
            
        if args.multi_user or args.all:
            markers.append("multi_user")
            
        if args.chat_events or args.all:
            markers.append("chat_events")
            
        if args.performance or args.all:
            markers.append("performance")
            
        if args.security or args.all:
            markers.append("security")
            
        if args.error_recovery or args.all:
            markers.append("error_recovery")
            
        # Add marker filter if any markers specified
        if markers and not args.all:
            marker_expression = " or ".join(markers)
            cmd.extend(["-m", marker_expression])
            
        # Add timeout
        cmd.extend(["--timeout=60"])
        
        # Add output formatting
        cmd.extend(["--tb=short"])
        
        return cmd
        
    def run_tests(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Run the WebSocket startup integration tests."""
        logger.info("Starting WebSocket Startup Integration Tests")
        logger.info(f"Test file: {self.test_file}")
        
        # Build pytest command
        cmd = self.build_pytest_command(args)
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Set environment variables for testing
        test_env = os.environ.copy()
        test_env.update({
            "ENVIRONMENT": "test",
            "TESTING": "true",
            "LOG_LEVEL": "INFO" if args.verbose else "WARNING",
            "WEBSOCKET_TEST_MODE": "integration",
            "USE_MOCK_COMPONENTS": "false",  # Use real components for integration tests
            "DISABLE_EXTERNAL_DEPENDENCIES": "true"  # Disable external service calls
        })
        
        # Record start time
        self.start_time = time.time()
        
        try:
            # Run the tests
            result = subprocess.run(
                cmd,
                env=test_env,
                capture_output=True,
                text=True,
                cwd=current_dir,
                timeout=300  # 5 minute timeout for entire test suite
            )
            
            # Record end time
            self.end_time = time.time()
            
            # Parse results
            self.test_results = {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "duration_seconds": self.end_time - self.start_time,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            return self.test_results
            
        except subprocess.TimeoutExpired:
            logger.error("Test suite timed out after 5 minutes")
            self.test_results = {
                "success": False,
                "return_code": -1,
                "duration_seconds": time.time() - self.start_time,
                "stdout": "",
                "stderr": "Test suite timed out"
            }
            return self.test_results
            
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            self.test_results = {
                "success": False,
                "return_code": -2,
                "duration_seconds": time.time() - self.start_time if self.start_time else 0,
                "stdout": "",
                "stderr": str(e)
            }
            return self.test_results
            
    def print_results(self, results: Dict[str, Any]) -> None:
        """Print test results summary."""
        print("\n" + "="*80)
        print("WEBSOCKET STARTUP INTEGRATION TEST RESULTS")
        print("="*80)
        
        duration = results.get("duration_seconds", 0)
        success = results.get("success", False)
        
        print(f"Status: {'✅ PASSED' if success else '❌ FAILED'}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Return Code: {results.get('return_code', 'Unknown')}")
        
        # Print stdout if available
        stdout = results.get("stdout", "").strip()
        if stdout:
            print(f"\nTest Output:")
            print("-" * 40)
            print(stdout)
            
        # Print stderr if available and tests failed
        stderr = results.get("stderr", "").strip()
        if stderr and not success:
            print(f"\nError Output:")
            print("-" * 40)
            print(stderr)
            
        # Extract test summary from output
        self._extract_test_summary(stdout)
        
        print("="*80)
        
    def _extract_test_summary(self, stdout: str) -> None:
        """Extract and display test summary from pytest output."""
        if not stdout:
            return
            
        lines = stdout.split('\n')
        
        # Look for pytest summary lines
        summary_lines = []
        in_summary = False
        
        for line in lines:
            if "short test summary" in line.lower() or "test session starts" in line:
                in_summary = True
                continue
                
            if in_summary and ("passed" in line or "failed" in line or "error" in line):
                summary_lines.append(line.strip())
                
        if summary_lines:
            print(f"\nTest Summary:")
            print("-" * 40)
            for line in summary_lines[-5:]:  # Show last 5 summary lines
                if line:
                    print(line)


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run WebSocket Startup Integration Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Test category options
    parser.add_argument("--websocket", action="store_true", 
                       help="Run WebSocket infrastructure tests")
    parser.add_argument("--startup", action="store_true",
                       help="Run system startup sequence tests") 
    parser.add_argument("--business-value", action="store_true",
                       help="Run business value delivery tests")
    parser.add_argument("--multi-user", action="store_true",
                       help="Run multi-user isolation tests")
    parser.add_argument("--chat-events", action="store_true",
                       help="Run critical chat WebSocket events tests")
    parser.add_argument("--performance", action="store_true",
                       help="Run performance and reliability tests")
    parser.add_argument("--security", action="store_true", 
                       help="Run security and authentication tests")
    parser.add_argument("--error-recovery", action="store_true",
                       help="Run error handling and recovery tests")
    parser.add_argument("--all", action="store_true",
                       help="Run all test categories")
    
    # Execution options
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--fast-fail", "-x", action="store_true", 
                       help="Stop on first test failure")
    
    args = parser.parse_args()
    
    # If no specific categories selected, default to basic websocket and startup tests
    if not any([args.websocket, args.startup, args.business_value, args.multi_user, 
               args.chat_events, args.performance, args.security, args.error_recovery, args.all]):
        args.websocket = True
        args.startup = True
        
    # Create and run test runner
    runner = WebSocketStartupTestRunner()
    results = runner.run_tests(args)
    runner.print_results(results)
    
    # Exit with appropriate code
    sys.exit(0 if results.get("success", False) else 1)


if __name__ == "__main__":
    main()