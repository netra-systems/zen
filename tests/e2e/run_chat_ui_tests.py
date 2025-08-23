#!/usr/bin/env python3
"""
Chat UI/UX Test Runner

Runs comprehensive chat UI tests with proper setup and reporting.
Designed to expose current frontend issues by running tests that SHOULD FAIL.

Usage:
    python tests/e2e/run_chat_ui_tests.py [--headless] [--video] [--report]

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & Quality Assurance
- Value Impact: Identifies UI/UX issues preventing optimal user experience
- Strategic Impact: Ensures chat platform reliability for all customer segments
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional
import json
import time
from datetime import datetime


class ChatUITestRunner:
    """Test runner for chat UI/UX comprehensive tests"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.test_file = self.project_root / "tests" / "e2e" / "test_chat_ui_flow_comprehensive.py"
        self.report_dir = self.project_root / "test_reports"
        self.report_dir.mkdir(exist_ok=True)
    
    def setup_environment(self) -> bool:
        """Setup test environment and dependencies"""
        print("🔧 Setting up test environment...")
        
        try:
            # Check if playwright is installed
            result = subprocess.run(["playwright", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Playwright not installed. Installing...")
                subprocess.run([sys.executable, "-m", "pip", "install", 
                              "playwright", "pytest-playwright", "pytest-asyncio"], 
                             check=True)
                subprocess.run(["playwright", "install"], check=True)
            
            print("✅ Environment setup complete")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Environment setup failed: {e}")
            return False
    
    def start_frontend_server(self) -> Optional[subprocess.Popen]:
        """Start the frontend development server"""
        print("🚀 Starting frontend development server...")
        
        frontend_dir = self.project_root / "frontend"
        if not frontend_dir.exists():
            print("❌ Frontend directory not found")
            return None
        
        try:
            # Start Next.js dev server
            process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for server to start
            print("⏳ Waiting for frontend server to start...")
            time.sleep(10)
            
            # Check if server is running
            import requests
            try:
                response = requests.get("http://localhost:3000", timeout=5)
                if response.status_code == 200:
                    print("✅ Frontend server started successfully")
                    return process
            except requests.RequestException:
                pass
            
            print("⚠️ Frontend server may not be ready yet, continuing...")
            return process
            
        except FileNotFoundError:
            print("❌ npm not found. Please install Node.js")
            return None
        except Exception as e:
            print(f"❌ Failed to start frontend server: {e}")
            return None
    
    def run_tests(self, headless: bool = True, record_video: bool = False) -> bool:
        """Run the comprehensive chat UI tests"""
        print("🧪 Running chat UI/UX comprehensive tests...")
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest", 
            str(self.test_file),
            "-v",
            "--tb=short",
            "--asyncio-mode=auto"
        ]
        
        # Add playwright options
        if headless:
            cmd.extend(["--browser-channel", "chrome"])
        else:
            cmd.extend(["--headed"])
        
        if record_video:
            cmd.extend(["--video", "on"])
        
        # Add HTML report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.report_dir / f"chat_ui_test_report_{timestamp}.html"
        cmd.extend(["--html", str(report_file), "--self-contained-html"])
        
        print(f"📊 Test report will be saved to: {report_file}")
        print(f"🔍 Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root)
            
            if result.returncode == 0:
                print("✅ All tests passed (unexpected - tests should expose issues)")
                return True
            else:
                print("❌ Tests failed (expected - these tests expose UI issues)")
                print("📋 Check the test report for detailed failure analysis")
                return False
                
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return False
    
    def generate_summary_report(self) -> None:
        """Generate a summary report of test issues found"""
        print("📋 Generating test summary report...")
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "test_purpose": "Expose chat UI/UX issues",
            "expected_result": "Most tests should FAIL to identify problems",
            "test_categories": [
                "Frontend Loading & Initialization",
                "Chat Interface Rendering", 
                "Message Input & Submission",
                "Thread Creation & Management",
                "UI State Synchronization",
                "Loading States & Error Handling",
                "Responsive Design & Mobile",
                "User Feedback & Notifications",
                "Complete Chat Flow Integration"
            ],
            "common_issues_to_expect": [
                "Slow page loading times",
                "Missing UI components", 
                "Non-functional message input",
                "Broken thread management",
                "Poor WebSocket connection handling",
                "Missing loading indicators",
                "Broken mobile layout",
                "Lack of user feedback mechanisms"
            ],
            "next_steps": [
                "Review failed test details",
                "Fix identified UI/UX issues",
                "Re-run tests to verify fixes",
                "Implement missing features",
                "Improve error handling",
                "Enhance mobile experience"
            ]
        }
        
        summary_file = self.report_dir / f"chat_ui_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📄 Summary report saved to: {summary_file}")


def main():
    """Main test runner entry point"""
    parser = argparse.ArgumentParser(description="Run comprehensive chat UI/UX tests")
    parser.add_argument("--headless", action="store_true", 
                       help="Run tests in headless mode")
    parser.add_argument("--video", action="store_true",
                       help="Record videos of test runs")
    parser.add_argument("--report", action="store_true", 
                       help="Generate detailed summary report")
    parser.add_argument("--no-server", action="store_true",
                       help="Skip starting frontend server (assume already running)")
    
    args = parser.parse_args()
    
    runner = ChatUITestRunner()
    
    print("🎯 Chat UI/UX Comprehensive Test Runner")
    print("=" * 50)
    print("Purpose: Identify and expose frontend UI/UX issues")
    print("Expected: Most tests should FAIL initially")
    print("=" * 50)
    
    # Setup environment
    if not runner.setup_environment():
        print("❌ Environment setup failed, exiting")
        sys.exit(1)
    
    # Start frontend server
    server_process = None
    if not args.no_server:
        server_process = runner.start_frontend_server()
        if not server_process:
            print("❌ Failed to start frontend server")
            response = input("Continue without starting server? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)
    
    try:
        # Run tests
        test_success = runner.run_tests(
            headless=args.headless,
            record_video=args.video
        )
        
        # Generate report
        if args.report:
            runner.generate_summary_report()
        
        print("\n" + "=" * 50)
        if test_success:
            print("✅ Tests completed successfully")
            print("⚠️  Note: If all tests passed, UI issues may not be properly exposed")
        else:
            print("❌ Tests failed (this is expected for issue identification)")
            print("📋 Review test reports to identify specific UI/UX problems")
        print("=" * 50)
        
        return 0 if test_success else 1
        
    finally:
        # Cleanup server process
        if server_process:
            print("🛑 Stopping frontend server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()


if __name__ == "__main__":
    sys.exit(main())