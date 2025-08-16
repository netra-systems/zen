#!/usr/bin/env python3
"""
Code Review Analysis Methods
ULTRA DEEP THINK: Module-based architecture - Analysis methods extracted for 300-line compliance
"""

import subprocess
from pathlib import Path
from typing import Tuple

class CodeReviewAnalysis:
    """Handles git analysis, spec alignment, performance and security checks"""
    
    def __init__(self, project_root: Path, recent_commits: int):
        self.project_root = project_root
        self.recent_commits = recent_commits
        self.recent_changes = []
        self.spec_code_conflicts = []
        self.performance_concerns = []
        self.security_issues = []
        self.issues = {"critical": [], "high": [], "medium": []}

    def run_command(self, cmd: str, cwd: str = None, timeout: int = 60) -> Tuple[bool, str]:
        """Run a shell command and return success status and output"""
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=cwd or self.project_root, timeout=timeout
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, str(e)

    def analyze_recent_changes(self):
        """Analyze recent git changes for potential issues"""
        print("\n[GIT] Analyzing Recent Changes...")
        
        self._analyze_commit_history()
        self._analyze_hotspots()
        self._analyze_large_changes()
        self._check_unstaged_changes()

    def _analyze_commit_history(self):
        """Analyze commit history"""
        success, output = self.run_command(f"git log --oneline -n {self.recent_commits}")
        if success:
            commits = output.strip().split('\n')
            self.recent_changes = commits[:10]
            print(f"  Found {len(commits)} recent commits")

    def _analyze_hotspots(self):
        """Analyze frequently changed files (hotspots)"""
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
                        if int(count) > 5:
                            hotspots.append(file)
            
            if hotspots:
                print(f"  [WARN] Found {len(hotspots)} frequently changed files (potential bug hotspots)")
                for file in hotspots[:5]:
                    self.issues["medium"].append(f"High-churn file (bug-prone): {file}")

    def _analyze_large_changes(self):
        """Analyze large recent changes"""
        success, output = self.run_command("git diff --stat HEAD~5..HEAD")
        if success:
            lines = output.strip().split('\n')
            for line in lines:
                if '|' in line and '+' in line:
                    parts = line.split('|')
                    if len(parts) == 2:
                        file = parts[0].strip()
                        changes = parts[1].strip()
                        plus_count = changes.count('+')
                        if plus_count > 50:
                            self.issues["high"].append(f"Large recent changes in: {file}")

    def _check_unstaged_changes(self):
        """Check for unstaged changes"""
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
        
        self._check_key_specifications(spec_dir)
        self._check_missing_specifications(spec_dir)

    def _check_key_specifications(self, spec_dir):
        """Check key specifications have implementations"""
        key_specs = [
            ("websockets.xml", ["app/ws_manager.py", "app/routes/websockets.py"]),
            ("subagents.xml", ["app/agents/", "app/services/agent_service.py"]),
            ("database.xml", ["app/services/database/", "app/db/"]),
            ("security.xml", ["app/auth/", "app/services/security_service.py"]),
        ]
        
        for spec_file, code_paths in key_specs:
            spec_path = spec_dir / spec_file
            if spec_path.exists():
                for code_path in code_paths:
                    full_path = self.project_root / code_path
                    if not full_path.exists():
                        self.spec_code_conflicts.append(
                            f"Spec {spec_file} exists but implementation missing: {code_path}"
                        )
                        self.issues["high"].append(
                            f"Missing implementation for spec: {spec_file} -> {code_path}"
                        )

    def _check_missing_specifications(self, spec_dir):
        """Check for code without specifications"""
        important_modules = [
            "app/services/apex_optimizer_agent/",
            "app/services/state/",
            "app/services/cache/",
        ]
        
        for module in important_modules:
            module_path = self.project_root / module
            if module_path.exists():
                module_name = module.split('/')[-2] if module.endswith('/') else module.split('/')[-1]
                spec_pattern = f"*{module_name}*.xml"
                matching_specs = list(spec_dir.glob(spec_pattern))
                if not matching_specs:
                    print(f"  [WARN] No specification found for: {module}")
                    self.issues["medium"].append(f"Code without specification: {module}")

    def check_performance_issues(self):
        """Check for potential performance problems"""
        print("\n[PERF] Checking Performance Issues...")
        
        self._check_nplus_one_queries()
        self._check_frontend_bundle_size()

    def _check_nplus_one_queries(self):
        """Check for N+1 query patterns"""
        success, output = self.run_command(
            "grep -r --include='*.py' 'for .* in .*:' app/ | grep -A 2 'db\\|query\\|select' | head -10"
        )
        if success and output:
            if 'for' in output and ('query' in output or 'select' in output):
                self.performance_concerns.append("Potential N+1 query pattern detected")
                self.issues["high"].append("Possible N+1 database query pattern")

    def _check_frontend_bundle_size(self):
        """Check frontend bundle size"""
        frontend_build = self.project_root / "frontend" / ".next"
        if frontend_build.exists():
            success, output = self.run_command("du -sh frontend/.next")
            if success:
                size_str = output.split()[0] if output else "unknown"
                print(f"  Frontend build size: {size_str}")
                if 'G' in size_str or ('M' in size_str and int(size_str.rstrip('M')) > 100):
                    self.performance_concerns.append(f"Large frontend bundle: {size_str}")
                    self.issues["medium"].append(f"Frontend bundle size is large: {size_str}")

    def check_security_issues(self):
        """Check for security vulnerabilities"""
        print("\n[SECURITY] Checking Security Issues...")
        
        self._check_hardcoded_secrets()
        self._check_sql_injection()

    def _check_hardcoded_secrets(self):
        """Check for hardcoded secrets"""
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

    def _check_sql_injection(self):
        """Check for SQL injection vulnerabilities"""
        success, output = self.run_command(
            "grep -r --include='*.py' 'f\".*SELECT\\|f\".*INSERT\\|f\".*UPDATE\\|f\".*DELETE' app/ | head -5"
        )
        if success and output:
            sql_injection_risks = len(output.strip().split('\n'))
            if sql_injection_risks > 0:
                self.security_issues.append(f"Potential SQL injection: {sql_injection_risks} instances")
                self.issues["critical"].append(f"Possible SQL injection vulnerabilities: {sql_injection_risks}")