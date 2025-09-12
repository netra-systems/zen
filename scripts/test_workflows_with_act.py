#!/usr/bin/env python3
"""
Comprehensive GitHub Workflows Testing with ACT
Tests all workflows locally to validate before pushing to GitHub
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from shared.isolated_environment import IsolatedEnvironment

# Fix encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class WorkflowTester:
    """Tests GitHub workflows locally using ACT"""
    
    def __init__(self):
        self.root_dir = Path.cwd()
        self.workflows_dir = self.root_dir / ".github" / "workflows"
        self.staging_dir = self.workflows_dir / "staging-workflows"
        self.results = []
        self.issues_found = []
        
    def check_prerequisites(self) -> bool:
        """Check if ACT and Docker are available"""
        print(" SEARCH:  Checking prerequisites...")
        
        # Check ACT
        try:
            result = subprocess.run(
                ["act", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f" PASS:  ACT found: {result.stdout.strip()}")
            else:
                print(" FAIL:  ACT not found. Please install ACT first.")
                return False
        except Exception as e:
            print(f" FAIL:  Error checking ACT: {e}")
            return False
            
        # Check Docker
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f" PASS:  Docker found: {result.stdout.strip()}")
            else:
                print(" FAIL:  Docker not found or not running.")
                return False
        except Exception as e:
            print(f" FAIL:  Error checking Docker: {e}")
            return False
            
        # Check secrets file
        secrets_file = self.root_dir / ".secrets"
        if not secrets_file.exists():
            print(" WARNING: [U+FE0F]  .secrets file not found. Creating with mock values...")
            self.create_mock_secrets()
            
        return True
        
    def create_mock_secrets(self):
        """Create mock secrets file for testing"""
        secrets_content = """# ACT Secrets for local testing
GITHUB_TOKEN=mock_github_token
GCP_CREDENTIALS={"type":"service_account"}
GCP_PROJECT_ID=mock-project
DOCKER_REGISTRY=localhost:5000
STAGING_SSH_KEY=mock_ssh_key
STAGING_HOST=localhost
STAGING_USER=testuser
SLACK_WEBHOOK_URL=https://mock.webhook.url
"""
        secrets_file = self.root_dir / ".secrets"
        secrets_file.write_text(secrets_content, encoding='utf-8')
        print(" PASS:  Created .secrets file with mock values")
        
    def get_workflows(self) -> List[Path]:
        """Get all workflow files"""
        workflows = []
        
        # Main workflows
        for workflow in self.workflows_dir.glob("*.yml"):
            workflows.append(workflow)
            
        # Staging workflows
        for workflow in self.staging_dir.glob("*.yml"):
            workflows.append(workflow)
            
        return workflows
        
    def validate_workflow_syntax(self, workflow_path: Path) -> Tuple[bool, str]:
        """Validate workflow YAML syntax"""
        print(f"\n[U+1F4DD] Validating syntax: {workflow_path.name}")
        
        cmd = [
            "act", "-l",
            "-W", str(workflow_path),
            "--secret-file", ".secrets",
            "-P", "warp-custom-default=catthehacker/ubuntu:act-latest"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"   PASS:  Syntax valid")
                return True, ""
            else:
                error_msg = result.stderr or result.stdout
                print(f"   FAIL:  Syntax error: {error_msg[:200]}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            print(f"   WARNING: [U+FE0F]  Validation timeout")
            return False, "Timeout during validation"
        except Exception as e:
            print(f"   FAIL:  Validation error: {e}")
            return False, str(e)
            
    def test_workflow_dry_run(self, workflow_path: Path) -> Tuple[bool, str]:
        """Dry run a workflow with ACT"""
        print(f"\n[U+1F9EA] Testing workflow: {workflow_path.name}")
        
        # Create event file for workflow_call workflows
        event_file = None
        if "workflow_call" in workflow_path.read_text(encoding='utf-8'):
            event_file = self.create_event_file(workflow_path)
            
        cmd = [
            "act", "push",
            "-W", str(workflow_path),
            "--secret-file", ".secrets",
            "-P", "warp-custom-default=catthehacker/ubuntu:act-latest",
            "-n"  # Dry run
        ]
        
        if event_file:
            cmd.extend(["-e", str(event_file)])
            
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if "Job failed" not in result.stdout and result.returncode == 0:
                print(f"   PASS:  Dry run successful")
                return True, ""
            else:
                error_msg = self.extract_error(result.stdout, result.stderr)
                print(f"   FAIL:  Dry run failed: {error_msg[:200]}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            print(f"   WARNING: [U+FE0F]  Test timeout")
            return False, "Timeout during test"
        except Exception as e:
            print(f"   FAIL:  Test error: {e}")
            return False, str(e)
            
    def create_event_file(self, workflow_path: Path) -> Path:
        """Create event file for workflow_call workflows"""
        event_data = {
            "inputs": {
                "environment_name": "test-env",
                "pr_number": "123",
                "branch_name": "test-branch",
                "commit_sha": "abc123",
                "action": "test",
                "debug": "true"
            }
        }
        
        event_file = self.root_dir / f"act-event-{workflow_path.stem}.json"
        event_file.write_text(json.dumps(event_data, indent=2), encoding='utf-8')
        return event_file
        
    def extract_error(self, stdout: str, stderr: str) -> str:
        """Extract meaningful error from output"""
        error_patterns = [
            "Error:",
            "error:",
            "Failed",
            "failed",
            "Invalid",
            "invalid",
            "Unknown",
            "unknown"
        ]
        
        output = stderr + "\n" + stdout
        for line in output.split("\n"):
            for pattern in error_patterns:
                if pattern in line:
                    return line.strip()
                    
        return "Unknown error"
        
    def check_common_issues(self, workflow_path: Path) -> List[str]:
        """Check for common workflow issues"""
        issues = []
        content = workflow_path.read_text(encoding='utf-8')
        
        # Check for circular env references
        if "ACT: ${{ env.ACT }}" in content:
            issues.append("Circular env.ACT reference found")
            
        # Check for invalid runner labels
        if "runs-on:" in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "runs-on:" in line and "warp-custom" in line:
                    if "# ACT will override" not in lines[i]:
                        issues.append(f"Line {i+1}: Custom runner without ACT comment")
                        
        # Check for missing ACT compatibility
        if "env.ACT" not in content and "ACT" not in content:
            issues.append("No ACT compatibility checks found")
            
        return issues
        
    def fix_common_issues(self, workflow_path: Path) -> bool:
        """Attempt to fix common issues automatically"""
        print(f"\n[U+1F527] Attempting to fix issues in: {workflow_path.name}")
        content = workflow_path.read_text(encoding='utf-8')
        original_content = content
        fixed = False
        
        # Fix circular env.ACT references
        if "ACT: ${{ env.ACT }}" in content:
            content = content.replace(
                "ACT: ${{ env.ACT }}",
                "# ACT environment detection - ACT sets this automatically"
            )
            print("   PASS:  Fixed circular env.ACT reference")
            fixed = True
            
        # Save if changes were made
        if fixed:
            workflow_path.write_text(content, encoding='utf-8')
            print(f"  [U+1F4BE] Saved fixes to {workflow_path.name}")
            
        return fixed
        
    def run_tests(self):
        """Run all workflow tests"""
        print("\n" + "="*60)
        print("[U+1F680] Starting GitHub Workflows Testing with ACT")
        print("="*60)
        
        if not self.check_prerequisites():
            print("\n FAIL:  Prerequisites check failed")
            return False
            
        workflows = self.get_workflows()
        print(f"\n CHART:  Found {len(workflows)} workflows to test")
        
        for workflow in workflows:
            # Skip certain workflows
            if workflow.name in ["test-act-simple.yml"]:
                continue
                
            # Check for common issues
            issues = self.check_common_issues(workflow)
            if issues:
                print(f"\n WARNING: [U+FE0F]  Issues found in {workflow.name}:")
                for issue in issues:
                    print(f"  - {issue}")
                    self.issues_found.append({
                        "workflow": workflow.name,
                        "issue": issue
                    })
                    
                # Try to fix issues
                self.fix_common_issues(workflow)
                
            # Validate syntax
            valid, error = self.validate_workflow_syntax(workflow)
            
            self.results.append({
                "workflow": workflow.name,
                "path": str(workflow),
                "syntax_valid": valid,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
            
            if not valid and "Unknown Variable Access env" in error:
                # Try to fix and revalidate
                if self.fix_common_issues(workflow):
                    valid, error = self.validate_workflow_syntax(workflow)
                    if valid:
                        print(f"   PASS:  Fixed and validated successfully")
                        
        self.generate_report()
        return True
        
    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("[U+1F4CB] Test Report")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["syntax_valid"])
        failed = total - passed
        
        print(f"\n CHART:  Summary:")
        print(f"  Total workflows: {total}")
        print(f"   PASS:  Passed: {passed}")
        print(f"   FAIL:  Failed: {failed}")
        
        if self.issues_found:
            print(f"\n WARNING: [U+FE0F]  Issues Found ({len(self.issues_found)}):")
            for issue in self.issues_found:
                print(f"  - {issue['workflow']}: {issue['issue']}")
                
        if failed > 0:
            print(f"\n FAIL:  Failed Workflows:")
            for result in self.results:
                if not result["syntax_valid"]:
                    print(f"  - {result['workflow']}")
                    print(f"    Error: {result['error'][:100]}")
                    
        # Save report to file
        report_file = self.root_dir / "workflow-test-report.json"
        with open(report_file, "w") as f:
            json.dump({
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "timestamp": datetime.now().isoformat()
                },
                "issues": self.issues_found,
                "results": self.results
            }, f, indent=2)
            
        print(f"\n[U+1F4BE] Report saved to: {report_file}")

def main():
    """Main entry point"""
    tester = WorkflowTester()
    success = tester.run_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()