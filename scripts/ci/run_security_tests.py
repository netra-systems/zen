#!/usr/bin/env python3
"""Run security tests for the Netra platform."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List


def run_security_tests(output_file: Path) -> int:
    """Run security-specific tests and generate results."""
    
    results = {
        "test_type": "security",
        "timestamp": time.time(),
        "tests": [],
        "vulnerabilities": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "security_issues": []
        }
    }
    
    # Define security test patterns
    security_tests = [
        "test_auth_critical",
        "test_security_service",
        "test_tool_permission_service",
        "test_environment_config",
        "test.*authentication",
        "test.*authorization",
        "test.*permission",
        "test.*secret",
        "test.*token"
    ]
    
    print("=" * 60)
    print("RUNNING SECURITY TESTS")
    print("=" * 60)
    
    for test_pattern in security_tests:
        print(f"\nRunning security test: {test_pattern}")
        
        test_result = {
            "name": test_pattern,
            "status": "pending",
            "duration": 0,
            "security_checks": []
        }
        
        start_time = time.time()
        
        # Run pytest with security-focused options
        cmd = [
            sys.executable, "-m", "pytest",
            "-k", test_pattern,
            "--tb=short",
            "-v",
            "--capture=no"  # Show output for security tests
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout per test
            )
            
            test_result["duration"] = time.time() - start_time
            
            # Check for security issues in output
            output_lower = result.stdout.lower() + result.stderr.lower()
            
            # Security issue patterns to check
            security_patterns = [
                ("hardcoded password", "password"),
                ("exposed secret", "secret"),
                ("sql injection", "sql"),
                ("xss vulnerability", "xss"),
                ("csrf vulnerability", "csrf"),
                ("insecure token", "token"),
                ("weak encryption", "encryption"),
                ("missing authentication", "auth")
            ]
            
            for issue_name, pattern in security_patterns:
                if pattern in output_lower:
                    test_result["security_checks"].append({
                        "check": issue_name,
                        "found": True
                    })
                    results["summary"]["security_issues"].append({
                        "test": test_pattern,
                        "issue": issue_name
                    })
            
            if result.returncode == 0:
                test_result["status"] = "passed"
                results["summary"]["passed"] += 1
                print(f"  ✅ Passed in {test_result['duration']:.2f}s")
            else:
                test_result["status"] = "failed"
                results["summary"]["failed"] += 1
                print(f"  ❌ Failed in {test_result['duration']:.2f}s")
                
        except subprocess.TimeoutExpired:
            test_result["status"] = "timeout"
            test_result["duration"] = 180
            results["summary"]["failed"] += 1
            print(f"  ⏱️ Timeout after 180s")
        except Exception as e:
            test_result["status"] = "error"
            test_result["error"] = str(e)
            results["summary"]["failed"] += 1
            print(f"  🔥 Error: {e}")
        
        results["tests"].append(test_result)
        results["summary"]["total"] += 1
    
    # Run bandit security scanner if available
    print("\n" + "=" * 60)
    print("RUNNING STATIC SECURITY ANALYSIS")
    print("=" * 60)
    
    try:
        bandit_cmd = [
            sys.executable, "-m", "bandit",
            "-r", "app",
            "-f", "json",
            "-ll"  # Only show medium and high severity issues
        ]
        
        bandit_result = subprocess.run(
            bandit_cmd,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if bandit_result.stdout:
            bandit_data = json.loads(bandit_result.stdout)
            if "results" in bandit_data:
                for issue in bandit_data["results"]:
                    results["vulnerabilities"].append({
                        "type": "static_analysis",
                        "severity": issue.get("issue_severity", "unknown"),
                        "confidence": issue.get("issue_confidence", "unknown"),
                        "description": issue.get("issue_text", ""),
                        "file": issue.get("filename", ""),
                        "line": issue.get("line_number", 0)
                    })
                print(f"  Found {len(bandit_data['results'])} potential security issues")
        
    except Exception as e:
        print(f"  ⚠️ Could not run static security analysis: {e}")
    
    # Calculate security metrics
    results["summary"]["success_rate"] = (
        results["summary"]["passed"] / results["summary"]["total"] * 100
        if results["summary"]["total"] > 0 else 0
    )
    results["summary"]["vulnerability_count"] = len(results["vulnerabilities"])
    results["summary"]["security_issue_count"] = len(results["summary"]["security_issues"])
    
    # Save results
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 60)
    print("SECURITY TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
    
    if results["vulnerabilities"]:
        print(f"\n⚠️ Static Analysis Issues: {len(results['vulnerabilities'])}")
        severity_counts = {}
        for vuln in results["vulnerabilities"]:
            severity = vuln["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        for severity, count in severity_counts.items():
            print(f"  - {severity}: {count}")
    
    if results["summary"]["security_issues"]:
        print(f"\n🔒 Security Test Issues: {len(results['summary']['security_issues'])}")
        for issue in results["summary"]["security_issues"][:5]:
            print(f"  - {issue['test']}: {issue['issue']}")
    
    # Return failure if any security issues found
    return 0 if (results["summary"]["failed"] == 0 and 
                 len(results["vulnerabilities"]) == 0) else 1


def main():
    parser = argparse.ArgumentParser(description="Run security tests")
    parser.add_argument("--output", required=True, help="Output JSON file for results")
    
    args = parser.parse_args()
    
    return run_security_tests(Path(args.output))


if __name__ == "__main__":
    sys.exit(main())