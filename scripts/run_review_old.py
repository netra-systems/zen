#!/usr/bin/env python3
"""
Comprehensive Code Review Script
Implements SPEC/review.xml for automated code quality validation
"""

import subprocess
import sys
import json
import os
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import re

class CodeReviewer:
    def __init__(self, mode: str = "full", focus: str = None, recent_commits: int = 20):
        self.mode = mode
        self.focus = focus
        self.recent_commits = recent_commits
        self.issues = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        self.smoke_test_results = {}
        self.spec_code_conflicts = []
        self.ai_issues_found = []
        self.performance_concerns = []
        self.security_issues = []
        self.recent_changes = []
        self.project_root = Path(__file__).parent.parent
        
    def run_command(self, cmd: str, cwd: str = None, timeout: int = 60) -> Tuple[bool, str]:
        """Run a shell command and return success status and output"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd or self.project_root,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, str(e)
    
    def run_smoke_tests(self):
        """Run critical system smoke tests"""
        print("\n[SMOKE TESTS] Running Critical Smoke Tests...")
        
        tests = [
            ("Backend Imports", "python -c \"from app.main import app; print('✓ FastAPI app imports successfully')\""),
            ("Database Config", "python -c \"from app.db.postgres import get_engine; print('✓ Database connection configured')\""),
            ("Redis Manager", "python -c \"from app.redis_manager import RedisManager; print('✓ Redis manager available')\""),
            ("Supervisor Agent", "python -c \"from app.agents.supervisor import SupervisorAgent; print('✓ Supervisor agent loads')\""),
            ("Agent Service", "python -c \"from app.services.agent_service import AgentService; print('✓ Agent service available')\""),
            ("Tool Dispatcher", "python -c \"from app.agents.tool_dispatcher import ToolDispatcher; print('✓ Tool dispatcher functional')\""),
            ("WebSocket Manager", "python -c \"from app.ws_manager import WebSocketManager; print('✓ WebSocket manager loads')\""),
            ("Message Handler", "python -c \"from app.services.websocket.message_handler import MessageHandler; print('✓ Message handler available')\""),
        ]
        
        all_passed = True
        for test_name, cmd in tests:
            success, output = self.run_command(cmd)
            self.smoke_test_results[test_name] = success
            
            if success:
                print(f"  [PASS] {test_name}")
            else:
                print(f"  [FAIL] {test_name}")
                self.issues["critical"].append(f"Smoke test failed: {test_name}")
                all_passed = False
                if self.mode == "quick":
                    print(f"     Error: {output[:200]}")
        
        # Frontend tests
        print("\n  [FRONTEND] Testing Frontend...")
        frontend_tests = [
            ("Frontend Lint", "cd frontend && npm run lint --silent"),
            ("TypeScript Check", "cd frontend && npm run type-check"),
        ]
        
        for test_name, cmd in frontend_tests:
            success, output = self.run_command(cmd, timeout=120)
            self.smoke_test_results[test_name] = success
            
            if success:
                print(f"  [PASS] {test_name}")
            else:
                print(f"  [WARN] {test_name}: FAIL (non-critical)")
                self.issues["medium"].append(f"Frontend check failed: {test_name}")
        
        # Quick import test
        print("\n  [IMPORTS] Running Import Tests...")
        success, output = self.run_command("python test_runner.py --mode quick", timeout=180)
        self.smoke_test_results["Import Tests"] = success
        
        if success:
            print(f"  [PASS] Import Tests")
        else:
            print(f"  [FAIL] Import Tests")
            self.issues["critical"].append("Import validation tests failed")
            all_passed = False
        
        return all_passed
    
    def analyze_recent_changes(self):
        """Analyze recent git changes for potential issues"""
        print("\n[GIT] Analyzing Recent Changes...")
        
        # Get recent commits
        success, output = self.run_command(f"git log --oneline -n {self.recent_commits}")
        if success:
            commits = output.strip().split('\n')
            self.recent_changes = commits[:10]  # Store first 10 for report
            print(f"  Found {len(commits)} recent commits")
        
        # Get files with most changes (hotspots)
        success, output = self.run_command(
            "git log --pretty=format: --name-only | sort | uniq -c | sort -rg | head -20"
        )
        if success:
            hotspots = []
            for line in output.strip().split('\n'):
                if line.strip():
                    parts = line.strip().split(None, 1)
                    if len(parts) == 2:
                        count, file = parts
                        if int(count) > 5:  # Files changed more than 5 times
                            hotspots.append(file)
            
            if hotspots:
                print(f"  [WARN] Found {len(hotspots)} frequently changed files (potential bug hotspots)")
                for file in hotspots[:5]:
                    self.issues["medium"].append(f"High-churn file (bug-prone): {file}")
        
        # Check for large recent changes
        success, output = self.run_command("git diff --stat HEAD~5..HEAD")
        if success:
            lines = output.strip().split('\n')
            for line in lines:
                if '|' in line and '+' in line:
                    parts = line.split('|')
                    if len(parts) == 2:
                        file = parts[0].strip()
                        changes = parts[1].strip()
                        # Check for files with many changes
                        plus_count = changes.count('+')
                        if plus_count > 50:
                            self.issues["high"].append(f"Large recent changes in: {file}")
        
        # Check unstaged changes
        success, output = self.run_command("git status --short")
        if success and output.strip():
            unstaged_files = output.strip().split('\n')
            if len(unstaged_files) > 0:
                print(f"  [WARN] Found {len(unstaged_files)} files with unstaged changes")
                if len(unstaged_files) > 10:
                    self.issues["medium"].append(f"Many unstaged changes ({len(unstaged_files)} files)")
    
    def check_spec_code_alignment(self):
        """Check alignment between specifications and code"""
        print("\n[SPEC] Checking Spec-Code Alignment...")
        
        spec_dir = self.project_root / "SPEC"
        if not spec_dir.exists():
            self.issues["high"].append("SPEC directory not found")
            return
        
        # Check key specifications
        key_specs = [
            ("websockets.xml", ["app/ws_manager.py", "app/routes/websockets.py"]),
            ("subagents.xml", ["app/agents/", "app/services/agent_service.py"]),
            ("database.xml", ["app/services/database/", "app/db/"]),
            ("security.xml", ["app/auth/", "app/services/security_service.py"]),
        ]
        
        for spec_file, code_paths in key_specs:
            spec_path = spec_dir / spec_file
            if spec_path.exists():
                # Check if corresponding code exists
                for code_path in code_paths:
                    full_path = self.project_root / code_path
                    if not full_path.exists():
                        self.spec_code_conflicts.append(
                            f"Spec {spec_file} exists but implementation missing: {code_path}"
                        )
                        self.issues["high"].append(
                            f"Missing implementation for spec: {spec_file} -> {code_path}"
                        )
        
        # Check for code without specs (sampling)
        important_modules = [
            "app/services/apex_optimizer_agent/",
            "app/services/state/",
            "app/services/cache/",
        ]
        
        for module in important_modules:
            module_path = self.project_root / module
            if module_path.exists():
                # Check if there's a corresponding spec
                module_name = module.split('/')[-2] if module.endswith('/') else module.split('/')[-1]
                spec_pattern = f"*{module_name}*.xml"
                matching_specs = list(spec_dir.glob(spec_pattern))
                if not matching_specs:
                    print(f"  [WARN] No specification found for: {module}")
                    self.issues["medium"].append(f"Code without specification: {module}")
    
    def detect_ai_coding_issues(self):
        """Detect common issues from AI-assisted coding"""
        print("\n[AI] Detecting AI Coding Issues...")
        
        if self.focus == "ai-issues" or self.mode == "full":
            # Check for duplicate function implementations
            self._check_duplicates()
            
            # Check for type mismatches
            self._check_type_consistency()
            
            # Check for incomplete error handling
            self._check_error_handling()
            
            # Check for common AI patterns
            self._check_ai_patterns()
    
    def _check_duplicates(self):
        """Check for duplicate implementations"""
        # Search for common utility function patterns
        patterns = [
            ("get_config", "app/"),
            ("validate_", "app/"),
            ("format_", "app/"),
            ("parse_", "app/"),
        ]
        
        for pattern, search_dir in patterns:
            success, output = self.run_command(
                f"grep -r --include='*.py' '^def {pattern}' {search_dir} | head -20"
            )
            if success and output:
                lines = output.strip().split('\n')
                if len(lines) > 3:  # Multiple definitions found
                    functions = {}
                    for line in lines:
                        if ':def ' in line:
                            parts = line.split(':def ')
                            if len(parts) == 2:
                                file = parts[0]
                                func = parts[1].split('(')[0]
                                if func not in functions:
                                    functions[func] = []
                                functions[func].append(file)
                    
                    for func, files in functions.items():
                        if len(files) > 1:
                            self.ai_issues_found.append(f"Duplicate function '{func}' in {len(files)} files")
                            self.issues["medium"].append(f"Duplicate implementation: {func}")
    
    def _check_type_consistency(self):
        """Check for type definition consistency"""
        # Check for 'any' types in TypeScript
        success, output = self.run_command(
            "grep -r --include='*.ts' --include='*.tsx' ': any' frontend/types/ | head -10"
        )
        if success and output:
            any_count = len(output.strip().split('\n'))
            if any_count > 0:
                self.ai_issues_found.append(f"Found {any_count} uses of 'any' type in TypeScript")
                self.issues["medium"].append(f"TypeScript 'any' types found: {any_count} instances")
        
        # Check for missing type hints in Python
        success, output = self.run_command(
            "grep -r --include='*.py' '^def .*):$' app/ | head -20"
        )
        if success and output:
            lines = output.strip().split('\n')
            missing_types = 0
            for line in lines:
                if '-> ' not in line:
                    missing_types += 1
            
            if missing_types > 5:
                self.ai_issues_found.append(f"Found {missing_types} functions without return type hints")
                self.issues["medium"].append(f"Missing type hints: {missing_types} functions")
    
    def _check_error_handling(self):
        """Check for incomplete error handling"""
        # Check for bare except clauses
        success, output = self.run_command(
            "grep -r --include='*.py' 'except:' app/ | head -10"
        )
        if success and output:
            bare_except_count = len(output.strip().split('\n'))
            if bare_except_count > 0:
                self.ai_issues_found.append(f"Found {bare_except_count} bare except clauses")
                self.issues["high"].append(f"Bare except clauses (catches all errors): {bare_except_count}")
        
        # Check for unhandled promises in TypeScript
        success, output = self.run_command(
            "grep -r --include='*.ts' --include='*.tsx' '\\.then(' frontend/ | grep -v '\\.catch(' | head -10"
        )
        if success and output:
            unhandled = len(output.strip().split('\n'))
            if unhandled > 0:
                self.ai_issues_found.append(f"Potential unhandled promises: {unhandled}")
                self.issues["medium"].append(f"Promises without error handling: {unhandled}")
    
    def _check_ai_patterns(self):
        """Check for common AI coding patterns that may be problematic"""
        # Check for TODO/FIXME comments (often left by AI)
        success, output = self.run_command(
            "grep -r --include='*.py' --include='*.ts' --include='*.tsx' 'TODO\\|FIXME' . | head -20"
        )
        if success and output:
            todo_count = len(output.strip().split('\n'))
            if todo_count > 10:
                self.ai_issues_found.append(f"Found {todo_count} TODO/FIXME comments")
                self.issues["low"].append(f"Unresolved TODO/FIXME comments: {todo_count}")
        
        # Check for console.log statements (debugging artifacts)
        success, output = self.run_command(
            "grep -r --include='*.ts' --include='*.tsx' 'console\\.log' frontend/ | head -10"
        )
        if success and output:
            console_count = len(output.strip().split('\n'))
            if console_count > 0:
                self.ai_issues_found.append(f"Found {console_count} console.log statements")
                self.issues["medium"].append(f"Debug console.log statements in production code: {console_count}")
    
    def check_performance_issues(self):
        """Check for potential performance problems"""
        print("\n[PERF] Checking Performance Issues...")
        
        # Check for N+1 query patterns
        success, output = self.run_command(
            "grep -r --include='*.py' 'for .* in .*:' app/ | grep -A 2 'db\\|query\\|select' | head -10"
        )
        if success and output:
            if 'for' in output and ('query' in output or 'select' in output):
                self.performance_concerns.append("Potential N+1 query pattern detected")
                self.issues["high"].append("Possible N+1 database query pattern")
        
        # Check frontend bundle size (if build exists)
        frontend_build = self.project_root / "frontend" / ".next"
        if frontend_build.exists():
            # This is a simplified check - in reality you'd want more sophisticated analysis
            success, output = self.run_command("du -sh frontend/.next")
            if success:
                size_str = output.split()[0] if output else "unknown"
                print(f"  Frontend build size: {size_str}")
                # Check if size is concerning (this is a rough heuristic)
                if 'G' in size_str or ('M' in size_str and int(size_str.rstrip('M')) > 100):
                    self.performance_concerns.append(f"Large frontend bundle: {size_str}")
                    self.issues["medium"].append(f"Frontend bundle size is large: {size_str}")
    
    def check_security_issues(self):
        """Check for security vulnerabilities"""
        print("\n[SECURITY] Checking Security Issues...")
        
        # Check for hardcoded secrets
        patterns = [
            ("API_KEY", "=\\s*[\"'][A-Za-z0-9]{20,}[\"']"),
            ("SECRET", "=\\s*[\"'][A-Za-z0-9]{20,}[\"']"),
            ("PASSWORD", "=\\s*[\"'][^\"']+[\"']"),
        ]
        
        for name, pattern in patterns:
            success, output = self.run_command(
                f"grep -r --include='*.py' --include='*.ts' '{pattern}' . | grep -v test | head -5"
            )
            if success and output:
                lines = output.strip().split('\n')
                for line in lines:
                    if 'test' not in line.lower() and 'mock' not in line.lower():
                        self.security_issues.append(f"Potential hardcoded {name}")
                        self.issues["critical"].append(f"Possible hardcoded credential: {name}")
                        break
        
        # Check for SQL injection vulnerabilities
        success, output = self.run_command(
            "grep -r --include='*.py' 'f\".*SELECT\\|f\".*INSERT\\|f\".*UPDATE\\|f\".*DELETE' app/ | head -5"
        )
        if success and output:
            self.security_issues.append("Potential SQL injection vulnerability")
            self.issues["critical"].append("Possible SQL injection - using f-strings in queries")
    
    def _add_report_header(self, report: List[str]) -> None:
        """Add header to the report."""
        report.append(f"# Code Review Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

    def _add_executive_summary(self, report: List[str]) -> None:
        """Add executive summary section."""
        report.append("## Executive Summary")
        report.append(f"- Review Type: {self.mode.upper()}")
        if self.focus:
            report.append(f"- Focus Area: {self.focus}")
        report.append(f"- Critical Issues Found: {len(self.issues['critical'])}")
        report.append(f"- High Priority Issues: {len(self.issues['high'])}")
        report.append(f"- Medium Priority Issues: {len(self.issues['medium'])}")
        report.append(f"- Low Priority Issues: {len(self.issues['low'])}")
        report.append("")

    def _add_system_health(self, report: List[str]) -> None:
        """Add system health section."""
        report.append("## System Health")
        report.append("### Smoke Test Results")
        for test, passed in self.smoke_test_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            report.append(f"- {test}: {status}")
        report.append("")

    def _add_recent_changes(self, report: List[str]) -> None:
        """Add recent changes section if changes exist."""
        if not self.recent_changes:
            return
        report.append("## Recent Changes Analysis")
        report.append("### Recent Commits")
        for commit in self.recent_changes[:5]:
            report.append(f"- {commit}")
        report.append("")

    def _add_spec_conflicts(self, report: List[str]) -> None:
        """Add spec-code alignment issues if any exist."""
        if not self.spec_code_conflicts:
            return
        report.append("## Spec-Code Alignment Issues")
        for conflict in self.spec_code_conflicts:
            report.append(f"- {conflict}")
        report.append("")

    def _add_ai_issues(self, report: List[str]) -> None:
        """Add AI coding issues section if any exist."""
        if not self.ai_issues_found:
            return
        report.append("## AI Coding Issues Detected")
        for issue in self.ai_issues_found:
            report.append(f"- {issue}")
        report.append("")

    def _add_performance_concerns(self, report: List[str]) -> None:
        """Add performance concerns section if any exist."""
        if not self.performance_concerns:
            return
        report.append("## Performance Concerns")
        for concern in self.performance_concerns:
            report.append(f"- {concern}")
        report.append("")

    def _add_security_issues(self, report: List[str]) -> None:
        """Add security issues section if any exist."""
        if not self.security_issues:
            return
        report.append("## Security Issues")
        for issue in self.security_issues:
            report.append(f"- [WARNING] {issue}")
        report.append("")

    def _add_critical_action_items(self, report: List[str]) -> None:
        """Add critical action items if any exist."""
        if not self.issues["critical"]:
            return
        report.append("### Critical (Must fix immediately)")
        for i, issue in enumerate(self.issues["critical"], 1):
            report.append(f"{i}. {issue}")
        report.append("")

    def _add_high_action_items(self, report: List[str]) -> None:
        """Add high priority action items if any exist."""
        if not self.issues["high"]:
            return
        report.append("### High (Fix before next release)")
        for i, issue in enumerate(self.issues["high"], 1):
            report.append(f"{i}. {issue}")
        report.append("")

    def _add_medium_action_items(self, report: List[str]) -> None:
        """Add medium priority action items if any exist."""
        if not self.issues["medium"]:
            return
        report.append("### Medium (Fix in next sprint)")
        for i, issue in enumerate(self.issues["medium"][:10], 1):
            report.append(f"{i}. {issue}")
        if len(self.issues["medium"]) > 10:
            report.append(f"... and {len(self.issues['medium']) - 10} more")
        report.append("")

    def _add_recommendations(self, report: List[str]) -> None:
        """Add recommendations section."""
        report.append("## Recommendations")
        
        if len(self.issues["critical"]) > 0:
            report.append("- **URGENT**: Address critical issues before any new development")
        if len(self.ai_issues_found) > 5:
            report.append("- Consider manual review of recent AI-generated code")
        if len(self.spec_code_conflicts) > 0:
            report.append("- Update specifications to match current implementation")
        if len(self.security_issues) > 0:
            report.append("- Conduct thorough security audit immediately")
        if len(self.performance_concerns) > 0:
            report.append("- Profile application performance and optimize hotspots")

    def _add_report_footer(self, report: List[str]) -> None:
        """Add footer to the report."""
        report.append("")
        report.append("---")
        report.append("*Generated by run_review.py implementing SPEC/review.xml*")

    def generate_report(self):
        """Generate comprehensive review report"""
        report = []
        
        self._add_report_header(report)
        self._add_executive_summary(report)
        self._add_system_health(report)
        self._add_recent_changes(report)
        self._add_spec_conflicts(report)
        self._add_ai_issues(report)
        self._add_performance_concerns(report)
        self._add_security_issues(report)
        
        report.append("## Action Items")
        self._add_critical_action_items(report)
        self._add_high_action_items(report)
        self._add_medium_action_items(report)
        
        self._add_recommendations(report)
        self._add_report_footer(report)
        
        return "\n".join(report)
    
    def save_report(self, report: str):
        """Save report to file"""
        reports_dir = self.project_root / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"code_review_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n[REPORT] Report saved to: {report_file}")
        return report_file
    
    def run(self) -> bool:
        """Execute the complete review process"""
        self._print_header()
        if not self._run_smoke_tests_if_needed():
            return False
        self._run_analysis_steps()
        report = self.generate_report()
        self._display_summary()
        self.save_report(report)
        return self._determine_final_status()

    def _print_header(self) -> None:
        """Print review header information."""
        print("=" * 60)
        print("NETRA CODE REVIEW SYSTEM")
        print(f"   Mode: {self.mode.upper()}")
        if self.focus:
            print(f"   Focus: {self.focus}")
        print("=" * 60)

    def _run_smoke_tests_if_needed(self) -> bool:
        """Run smoke tests if needed and return success status."""
        if self.mode == "ai-focus":
            return True
        all_passed = self.run_smoke_tests()
        if not all_passed and self.mode == "quick":
            print("\n❌ Critical smoke tests failed. Stopping review.")
            print("   Fix critical issues before continuing.")
            return False
        return True

    def _run_analysis_steps(self) -> None:
        """Run all analysis steps based on mode."""
        self.analyze_recent_changes()
        if self.mode != "quick":
            self.check_spec_code_alignment()
        self.detect_ai_coding_issues()
        if self.mode == "full":
            self.check_performance_issues()
        if self.mode != "quick":
            self.check_security_issues()

    def _display_summary(self) -> None:
        """Display review summary."""
        print("\n" + "=" * 60)
        print("REVIEW SUMMARY")
        print("=" * 60)
        self._display_critical_issues()
        self._display_high_issues()
        self._display_totals()

    def _display_critical_issues(self) -> None:
        """Display critical issues summary."""
        if len(self.issues["critical"]) > 0:
            print(f"[CRITICAL] Issues: {len(self.issues['critical'])}")
            for issue in self.issues["critical"][:3]:
                print(f"   - {issue}")

    def _display_high_issues(self) -> None:
        """Display high priority issues summary."""
        if len(self.issues["high"]) > 0:
            print(f"[HIGH] Priority Issues: {len(self.issues['high'])}")
            for issue in self.issues["high"][:3]:
                print(f"   - {issue}")

    def _display_totals(self) -> None:
        """Display total issues count."""
        total_issues = sum(len(issues) for issues in self.issues.values())
        print(f"\n[TOTAL] Issues Found: {total_issues}")
        print(f"   Critical: {len(self.issues['critical'])}")
        print(f"   High: {len(self.issues['high'])}")
        print(f"   Medium: {len(self.issues['medium'])}")
        print(f"   Low: {len(self.issues['low'])}")

    def _determine_final_status(self) -> bool:
        """Determine and display final review status."""
        if len(self.issues["critical"]) > 0:
            print("\n[FAILED] Review FAILED - Critical issues must be addressed")
            return False
        elif len(self.issues["high"]) > 5:
            print("\n[WARNING] Review PASSED with warnings - Many high priority issues")
            return True
        else:
            print("\n[PASSED] Review PASSED")
            return True


def main():
    parser = argparse.ArgumentParser(description="Run comprehensive code review")
    parser.add_argument(
        "--mode",
        choices=["quick", "standard", "full", "ai-focus"],
        default="standard",
        help="Review mode (quick=5min, standard=10min, full=15min)"
    )
    parser.add_argument(
        "--focus",
        choices=["ai-issues", "security", "performance", "spec-alignment"],
        help="Focus area for targeted review"
    )
    parser.add_argument(
        "--recent-commits",
        type=int,
        default=20,
        help="Number of recent commits to analyze"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report (automatic in full mode)"
    )
    
    args = parser.parse_args()
    
    # Create and run reviewer
    reviewer = CodeReviewer(
        mode=args.mode,
        focus=args.focus,
        recent_commits=args.recent_commits
    )
    
    success = reviewer.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()