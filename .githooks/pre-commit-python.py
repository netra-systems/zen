#!/usr/bin/env python
# Windows: This hook is executed via conda run python
# Unix: This hook is executed directly via python3/python
"""
Pre-commit Hook for Architecture Enforcement
Enforces CLAUDE.md architectural rules before allowing commits:
- 450-line file limit
- 25-line function limit  
- No test stubs in production code
- Fast execution optimized for git hooks
"""

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Load configuration
CONFIG_FILE = Path(__file__).parent / "config.json"
DEFAULT_CONFIG = {
    "precommit_checks_enabled": True,
    "max_file_lines": 300,
    "max_function_lines": 8
}

def load_config() -> Dict[str, Any]:
    """Load configuration from config.json"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Failed to load config.json: {e}")
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

config = load_config()

# Check if pre-commit checks are enabled
if not config.get("precommit_checks_enabled", True):
    print("[INFO] Pre-commit architecture checks are temporarily disabled")
    print(f"[INFO] Reason: {config.get('disabled_reason', 'Not specified')}")
    print(f"[INFO] To re-enable: Set 'precommit_checks_enabled': true in .githooks/config.json")
    sys.exit(0)

class FastArchitectureEnforcer:
    """Fast architecture enforcement for git pre-commit hooks"""
    
    def __init__(self):
        self.MAX_FILE_LINES = config.get("max_file_lines", 300)
        self.MAX_FUNCTION_LINES = config.get("max_function_lines", 8)
        self.violations = []
        self.staged_files = self._get_staged_files()
        
    def _get_staged_files(self) -> Set[str]:
        """Get list of staged files from git"""
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                capture_output=True,
                text=True,
                check=True
            )
            return set(result.stdout.strip().split('\n'))
        except subprocess.CalledProcessError:
            return set()
    
    def check_staged_files(self) -> bool:
        """Check only staged files for violations"""
        violations_found = False
        
        for filepath in self.staged_files:
            if not filepath or not os.path.exists(filepath):
                continue
                
            if self._should_skip(filepath):
                continue
            
            # Check file size
            if self._check_file_size(filepath):
                violations_found = True
            
            # Check function complexity for Python files
            if filepath.endswith('.py') and self._check_function_complexity(filepath):
                violations_found = True
                
            # Check for test stubs in production code
            if filepath.endswith('.py') and self._check_test_stubs(filepath):
                violations_found = True
        
        return violations_found
    
    def _check_file_size(self, filepath: str) -> bool:
        """Check if file exceeds 300 lines"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                if lines > self.MAX_FILE_LINES:
                    print(f"[VIOLATION] FILE SIZE: {filepath}")
                    print(f"   {lines} lines (max: {self.MAX_FILE_LINES})")
                    print(f"   Split this file into smaller modules")
                    return True
        except Exception as e:
            print(f"[WARNING] Error reading {filepath}: {e}")
        return False
    
    def _check_function_complexity(self, filepath: str) -> bool:
        """Check for functions exceeding 8 lines"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            violations_found = False
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    lines = self._count_function_lines(node)
                    if lines > self.MAX_FUNCTION_LINES:
                        print(f"[VIOLATION] FUNCTION COMPLEXITY: {filepath}")
                        print(f"   Function '{node.name}()' has {lines} lines (max: {self.MAX_FUNCTION_LINES})")
                        print(f"   Break this function into smaller functions")
                        violations_found = True
            
            return violations_found
        except Exception as e:
            print(f"[WARNING] Error parsing {filepath}: {e}")
            return False
    
    def _check_test_stubs(self, filepath: str) -> bool:
        """Check for test stubs in production code"""
        if 'test' in filepath or filepath.startswith('app/tests'):
            return False
            
        suspicious_patterns = [
            (r'# Mock implementation', 'Mock implementation comment'),
            (r'# Test stub', 'Test stub comment'),
            (r'""".*test implementation.*"""', 'Test implementation docstring'),
            (r'""".*for testing.*"""', 'For testing docstring'),
            (r'return \[{"id": "1"', 'Hardcoded test data'),
            (r'return {"test": "data"}', 'Test data return'),
            (r'return {"status": "ok"}', 'Static status return'),
            (r'def \w+\(\*args, \*\*kwargs\).*return {', 'Args/kwargs with static return'),
        ]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                for pattern, description in suspicious_patterns:
                    if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                        print(f"[VIOLATION] TEST STUB IN PRODUCTION: {filepath}")
                        print(f"   Found: {description}")
                        print(f"   Replace with real implementation")
                        return True
        except Exception as e:
            print(f"[WARNING] Error reading {filepath}: {e}")
            
        return False
    
    def _should_skip(self, filepath: str) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            '__pycache__',
            'node_modules',
            '.git',
            'migrations',
            'test_reports',
            'docs',
            '.pytest_cache',
            'htmlcov',
            'coverage',
            'logs',
            'temp',
            'venv'
        ]
        return any(pattern in filepath for pattern in skip_patterns)
    
    def _count_function_lines(self, node) -> int:
        """Count actual code lines in function (excluding docstrings)"""
        if not node.body:
            return 0
        
        # Skip docstring if present
        start_idx = 0
        if (len(node.body) > 0 and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant)):
            start_idx = 1
        
        if start_idx >= len(node.body):
            return 0
            
        # Count lines from first real statement to last
        first_line = node.body[start_idx].lineno
        last_line = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else node.body[-1].lineno
        return last_line - first_line + 1

def main():
    """Main pre-commit hook execution"""
    print("[ARCH] Checking architecture compliance...")
    
    enforcer = FastArchitectureEnforcer()
    
    if not enforcer.staged_files:
        print("[PASS] No files staged for commit")
        return 0
    
    # Only check Python and TypeScript files
    relevant_files = [f for f in enforcer.staged_files 
                     if f.endswith(('.py', '.ts')) and not enforcer._should_skip(f)]
    
    if not relevant_files:
        print("[PASS] No relevant files to check")
        return 0
    
    print(f"[INFO] Checking {len(relevant_files)} staged files...")
    
    violations_found = enforcer.check_staged_files()
    
    if violations_found:
        print("\n" + "="*60)
        print("[FAIL] COMMIT BLOCKED - Architecture violations found!")
        print("="*60)
        print("\n[RULES] Architecture rules (from CLAUDE.md):")
        print("   [U+2022] Files must be <=450 lines")
        print("   [U+2022] Functions must be <=8 lines")
        print("   [U+2022] No test stubs in production code")
        print("\n[ACTION] Fix violations and try committing again")
        print("[CMD] Run: python scripts/check_architecture_compliance.py --path .")
        return 1
    else:
        print("[PASS] All architecture rules satisfied!")
        return 0

if __name__ == "__main__":
    sys.exit(main())