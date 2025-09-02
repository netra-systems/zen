#!/usr/bin/env python
"""Script to find SSOT violations in agent code.

This script scans agent files for common SSOT violations and patterns that should
be refactored to use canonical implementations.
"""

import argparse
import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Define violation patterns
VIOLATION_PATTERNS = {
    "custom_json_parsing": {
        "patterns": [
            r"def.*extract.*json",
            r"def.*parse.*json",
            r"def.*repair.*json",
            r"json\.loads.*except",
            r"re\.search.*\{.*\}",
            r"def.*fix.*json"
        ],
        "canonical": "netra_backend.app.core.serialization.unified_json_handler",
        "severity": "HIGH",
        "description": "Custom JSON parsing instead of unified handler"
    },
    "custom_hash_generation": {
        "patterns": [
            r"hashlib\.(sha256|md5|sha1)",
            r"def.*generate.*hash",
            r"def.*create.*cache.*key"
        ],
        "canonical": "netra_backend.app.services.cache.cache_helpers.CacheHelpers",
        "severity": "MEDIUM",
        "description": "Custom hash generation instead of CacheHelpers"
    },
    "direct_env_access": {
        "patterns": [
            r"os\.environ\[",
            r"os\.environ\.get",
            r"os\.getenv",
            r"environ\[\"",
            r"environ\['"
        ],
        "canonical": "shared.isolated_environment.IsolatedEnvironment",
        "severity": "HIGH",
        "description": "Direct environment access instead of IsolatedEnvironment"
    },
    "custom_retry_logic": {
        "patterns": [
            r"for.*attempt.*in.*range",
            r"while.*retry",
            r"max_retries.*=",
            r"retry_count.*<"
        ],
        "canonical": "netra_backend.app.core.resilience.unified_retry_handler",
        "severity": "MEDIUM",
        "description": "Custom retry logic instead of UnifiedRetryHandler"
    },
    "stored_db_session": {
        "patterns": [
            r"self\.db_session\s*=",
            r"self\.session\s*=.*Session",
            r"self\._session\s*="
        ],
        "canonical": "netra_backend.app.database.session_manager.DatabaseSessionManager",
        "severity": "CRITICAL",
        "description": "Database session stored in instance variable"
    },
    "stored_user_data": {
        "patterns": [
            r"self\.user_id\s*=",
            r"self\.thread_id\s*=",
            r"self\.run_id\s*=",
            r"self\._user_id\s*="
        ],
        "canonical": "netra_backend.app.agents.supervisor.user_execution_context.UserExecutionContext",
        "severity": "CRITICAL",
        "description": "User data stored in instance variables"
    },
    "custom_websocket": {
        "patterns": [
            r"websocket\.send",
            r"ws\.send",
            r"await.*send_json",
            r"self\.websocket\."
        ],
        "canonical": "netra_backend.app.agents.mixins.websocket_bridge_adapter",
        "severity": "HIGH",
        "description": "Direct WebSocket manipulation instead of adapter"
    },
    "missing_context_param": {
        "patterns": [],  # Special check via AST
        "canonical": "UserExecutionContext parameter",
        "severity": "HIGH",
        "description": "Missing UserExecutionContext parameter"
    }
}


class SSOTViolationFinder:
    """Find SSOT violations in Python code."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.violations: Dict[str, List[Dict]] = {}
        
    def scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single file for violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Check regex patterns
            for violation_type, config in VIOLATION_PATTERNS.items():
                if violation_type == "missing_context_param":
                    # Handle AST-based checks
                    if self._check_missing_context(content):
                        violations.append({
                            "type": violation_type,
                            "file": str(file_path),
                            "line": 0,
                            "severity": config["severity"],
                            "description": config["description"],
                            "canonical": config["canonical"]
                        })
                else:
                    for pattern in config["patterns"]:
                        for i, line in enumerate(lines, 1):
                            if re.search(pattern, line):
                                violations.append({
                                    "type": violation_type,
                                    "file": str(file_path),
                                    "line": i,
                                    "code": line.strip(),
                                    "severity": config["severity"],
                                    "description": config["description"],
                                    "canonical": config["canonical"]
                                })
                                
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
            
        return violations
    
    def _check_missing_context(self, content: str) -> bool:
        """Check if class __init__ is missing UserExecutionContext parameter."""
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's an agent class
                    if "Agent" in node.name or "Core" in node.name:
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                                # Check parameters
                                params = [arg.arg for arg in item.args.args]
                                if "context" not in params:
                                    return True
        except:
            pass
        return False
    
    def scan_agent(self, agent_name: str) -> Dict[str, List[Dict]]:
        """Scan a specific agent for violations."""
        agent_paths = [
            self.base_path / "netra_backend" / "app" / "agents" / f"{agent_name}.py",
            self.base_path / "netra_backend" / "app" / "agents" / agent_name,
            self.base_path / "netra_backend" / "app" / "agents" / f"{agent_name}_sub_agent.py",
        ]
        
        all_violations = []
        
        for path in agent_paths:
            if path.is_file():
                violations = self.scan_file(path)
                all_violations.extend(violations)
            elif path.is_dir():
                for py_file in path.glob("**/*.py"):
                    violations = self.scan_file(py_file)
                    all_violations.extend(violations)
        
        return all_violations
    
    def scan_all_agents(self) -> Dict[str, List[Dict]]:
        """Scan all agents for violations."""
        agents_dir = self.base_path / "netra_backend" / "app" / "agents"
        
        if not agents_dir.exists():
            print(f"Agents directory not found: {agents_dir}")
            return {}
        
        all_violations = {}
        
        # Scan all Python files in agents directory
        for py_file in agents_dir.glob("**/*.py"):
            # Skip test files and __pycache__
            if "__pycache__" in str(py_file) or "test_" in py_file.name:
                continue
                
            violations = self.scan_file(py_file)
            if violations:
                agent_name = py_file.stem
                if agent_name not in all_violations:
                    all_violations[agent_name] = []
                all_violations[agent_name].extend(violations)
        
        return all_violations
    
    def generate_report(self, violations: Dict[str, List[Dict]]) -> str:
        """Generate a markdown report of violations."""
        report = ["# SSOT Violation Report\n"]
        report.append(f"Total files with violations: {len(violations)}\n")
        
        # Summary by severity
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        type_counts = {}
        
        for file_violations in violations.values():
            for v in file_violations:
                severity_counts[v["severity"]] = severity_counts.get(v["severity"], 0) + 1
                type_counts[v["type"]] = type_counts.get(v["type"], 0) + 1
        
        report.append("\n## Summary by Severity\n")
        for severity, count in severity_counts.items():
            if count > 0:
                report.append(f"- **{severity}**: {count} violations\n")
        
        report.append("\n## Summary by Type\n")
        for vtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            report.append(f"- **{vtype}**: {count} violations\n")
        
        # Detailed violations
        report.append("\n## Detailed Violations\n")
        
        # Sort by severity
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            severity_violations = []
            for agent, file_violations in violations.items():
                for v in file_violations:
                    if v["severity"] == severity:
                        severity_violations.append((agent, v))
            
            if severity_violations:
                report.append(f"\n### {severity} Severity\n")
                for agent, v in severity_violations:
                    report.append(f"\n**{agent}** - {v['file']}:{v['line']}\n")
                    report.append(f"- Type: {v['type']}\n")
                    report.append(f"- Description: {v['description']}\n")
                    if 'code' in v:
                        report.append(f"- Code: `{v['code']}`\n")
                    report.append(f"- Use instead: `{v['canonical']}`\n")
        
        return "".join(report)


def main():
    parser = argparse.ArgumentParser(description="Find SSOT violations in agent code")
    parser.add_argument("--agent", help="Specific agent to scan")
    parser.add_argument("--output", help="Output file for report (default: stdout)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--base-path", default=".", help="Base path of the project")
    
    args = parser.parse_args()
    
    finder = SSOTViolationFinder(args.base_path)
    
    if args.agent:
        print(f"Scanning agent: {args.agent}")
        violations = {args.agent: finder.scan_agent(args.agent)}
    else:
        print("Scanning all agents...")
        violations = finder.scan_all_agents()
    
    if args.json:
        import json
        output = json.dumps(violations, indent=2)
    else:
        output = finder.generate_report(violations)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Report written to {args.output}")
    else:
        print(output)
    
    # Return exit code based on violations
    total_violations = sum(len(v) for v in violations.values())
    if total_violations > 0:
        print(f"\n[WARNING] Found {total_violations} SSOT violations")
        return 1
    else:
        print("\n[SUCCESS] No SSOT violations found")
        return 0


if __name__ == "__main__":
    exit(main())