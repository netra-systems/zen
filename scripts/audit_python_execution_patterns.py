#!/usr/bin/env python3
"""
Audit Python execution patterns for Issue #1176 remediation.

This script comprehensively scans the codebase for Python execution patterns
that may be affected by environment restrictions.
"""

import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime
import argparse

class PythonExecutionAuditor:
    """Audit Python execution patterns in codebase."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(project_root),
            "files_scanned": 0,
            "patterns_found": {
                "sys_executable": [],
                "subprocess_python": [],
                "shell_python": [],
                "direct_python_calls": [],
                "shebang_python": [],
            },
            "summary": {},
            "recommendations": []
        }

    def scan_codebase(self):
        """Scan entire codebase for Python execution patterns."""
        print("Scanning codebase for Python execution patterns...")

        # Scan Python files
        python_files = list(self.project_root.rglob("*.py"))
        for file_path in python_files:
            if self._should_skip_file(file_path):
                continue
            self._scan_python_file(file_path)

        # Scan shell scripts
        shell_files = list(self.project_root.rglob("*.sh")) + list(self.project_root.rglob("*.bash"))
        for file_path in shell_files:
            self._scan_shell_file(file_path)

        # Scan configuration files
        config_files = (
            list(self.project_root.rglob("*.yaml")) +
            list(self.project_root.rglob("*.yml")) +
            list(self.project_root.rglob("*.json")) +
            list(self.project_root.rglob("docker-compose*.yml"))
        )
        for file_path in config_files:
            self._scan_config_file(file_path)

        self._generate_summary()
        self._generate_recommendations()

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped during scanning."""
        skip_patterns = [
            ".git", "__pycache__", ".pytest_cache", "node_modules",
            ".venv", "venv", ".env", "build", "dist", ".tox"
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _scan_python_file(self, file_path: Path):
        """Scan Python file for execution patterns."""
        try:
            content = file_path.read_text(encoding='utf-8')
            self.results["files_scanned"] += 1

            # Check shebang
            if content.startswith('#!'):
                first_line = content.split('\n')[0]
                if 'python' in first_line:
                    self.results["patterns_found"]["shebang_python"].append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "line": 1,
                        "content": first_line.strip(),
                        "type": "shebang"
                    })

            # Parse AST for sys.executable usage
            try:
                tree = ast.parse(content)
                self._analyze_ast(tree, file_path)
            except SyntaxError:
                pass  # Skip files with syntax errors

            # Search for subprocess patterns with regex
            self._scan_subprocess_patterns(content, file_path)

        except Exception as e:
            print(f"Warning: Could not scan {file_path}: {e}")

    def _analyze_ast(self, tree: ast.AST, file_path: Path):
        """Analyze AST for Python execution patterns."""
        for node in ast.walk(tree):
            # Look for sys.executable
            if (isinstance(node, ast.Attribute) and
                isinstance(node.value, ast.Name) and
                node.value.id == 'sys' and
                node.attr == 'executable'):

                self.results["patterns_found"]["sys_executable"].append({
                    "file": str(file_path.relative_to(self.project_root)),
                    "line": node.lineno,
                    "type": "sys.executable",
                    "context": "AST analysis"
                })

    def _scan_subprocess_patterns(self, content: str, file_path: Path):
        """Scan for subprocess patterns using regex."""
        lines = content.split('\n')

        # Patterns to look for
        patterns = [
            (r'subprocess\.run\s*\(\s*\[.*?["\']python["\']', "subprocess_python"),
            (r'subprocess\.call\s*\(\s*\[.*?["\']python["\']', "subprocess_python"),
            (r'subprocess\.Popen\s*\(\s*\[.*?["\']python["\']', "subprocess_python"),
            (r'subprocess\.check_output\s*\(\s*\[.*?["\']python["\']', "subprocess_python"),
            (r'os\.system\s*\(\s*["\'].*?python', "direct_python_calls"),
            (r'os\.popen\s*\(\s*["\'].*?python', "direct_python_calls"),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, category in patterns:
                if re.search(pattern, line):
                    self.results["patterns_found"][category].append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "line": i,
                        "content": line.strip(),
                        "type": category,
                        "pattern": pattern
                    })

    def _scan_shell_file(self, file_path: Path):
        """Scan shell file for Python execution."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            for i, line in enumerate(lines, 1):
                if re.search(r'\bpython\b', line) and not line.strip().startswith('#'):
                    self.results["patterns_found"]["shell_python"].append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "line": i,
                        "content": line.strip(),
                        "type": "shell_script"
                    })

        except Exception as e:
            print(f"Warning: Could not scan shell file {file_path}: {e}")

    def _scan_config_file(self, file_path: Path):
        """Scan configuration file for Python references."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            for i, line in enumerate(lines, 1):
                if re.search(r'["\'].*python.*["\']', line):
                    self.results["patterns_found"]["direct_python_calls"].append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "line": i,
                        "content": line.strip(),
                        "type": "config_file"
                    })

        except Exception as e:
            print(f"Warning: Could not scan config file {file_path}: {e}")

    def _generate_summary(self):
        """Generate summary statistics."""
        self.results["summary"] = {
            "total_files_scanned": self.results["files_scanned"],
            "pattern_counts": {
                category: len(instances)
                for category, instances in self.results["patterns_found"].items()
            },
            "files_affected": len(set(
                instance["file"]
                for instances in self.results["patterns_found"].values()
                for instance in instances
            )),
            "high_priority_files": self._identify_high_priority_files()
        }

    def _identify_high_priority_files(self) -> List[str]:
        """Identify files that need immediate attention."""
        high_priority = set()

        # Files with multiple pattern types
        file_pattern_counts = {}
        for instances in self.results["patterns_found"].values():
            for instance in instances:
                file_path = instance["file"]
                file_pattern_counts[file_path] = file_pattern_counts.get(file_path, 0) + 1

        # Files with 3+ patterns are high priority
        for file_path, count in file_pattern_counts.items():
            if count >= 3:
                high_priority.add(file_path)

        # Critical infrastructure files
        critical_patterns = [
            "tests/unified_test_runner.py",
            "run_unit_tests_simple.py",
            "execute_issue_1176_tests.py",
        ]

        for pattern in critical_patterns:
            for instances in self.results["patterns_found"].values():
                for instance in instances:
                    if pattern in instance["file"]:
                        high_priority.add(instance["file"])

        return sorted(list(high_priority))

    def _generate_recommendations(self):
        """Generate remediation recommendations."""
        recommendations = []

        # Immediate actions
        sys_executable_count = len(self.results["patterns_found"]["sys_executable"])
        if sys_executable_count > 0:
            recommendations.append({
                "priority": "HIGH",
                "category": "sys.executable",
                "description": f"Replace {sys_executable_count} instances of sys.executable with environment-aware function",
                "action": "Use get_compatible_python_executable() from detect_execution_environment module",
                "files_affected": len(set(i["file"] for i in self.results["patterns_found"]["sys_executable"]))
            })

        # Subprocess patterns
        subprocess_count = len(self.results["patterns_found"]["subprocess_python"])
        if subprocess_count > 0:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "subprocess",
                "description": f"Update {subprocess_count} subprocess calls to use environment-aware Python executable",
                "action": "Replace hardcoded 'python' with dynamic executable detection",
                "files_affected": len(set(i["file"] for i in self.results["patterns_found"]["subprocess_python"]))
            })

        # Shebang lines
        shebang_count = len(self.results["patterns_found"]["shebang_python"])
        if shebang_count > 0:
            recommendations.append({
                "priority": "LOW",
                "category": "shebang",
                "description": f"Consider standardizing {shebang_count} shebang lines to #!/usr/bin/env python3",
                "action": "Update shebang lines for Claude Code compatibility",
                "files_affected": len(set(i["file"] for i in self.results["patterns_found"]["shebang_python"]))
            })

        self.results["recommendations"] = recommendations

    def generate_report(self, output_path: Path = None):
        """Generate comprehensive audit report."""
        if output_path is None:
            output_path = self.project_root / "PYTHON_EXECUTION_AUDIT_REPORT.json"

        # Save JSON report
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        # Generate human-readable report
        markdown_path = output_path.with_suffix('.md')
        self._generate_markdown_report(markdown_path)

        print(f"Audit complete!")
        print(f"JSON report: {output_path}")
        print(f"Markdown report: {markdown_path}")

        return output_path

    def _generate_markdown_report(self, output_path: Path):
        """Generate human-readable markdown report."""
        content = f"""# Python Execution Patterns Audit Report

**Generated:** {self.results['timestamp']}
**Project:** {self.results['project_root']}

## Executive Summary

- **Files Scanned:** {self.results['summary']['total_files_scanned']}
- **Files Affected:** {self.results['summary']['files_affected']}
- **Total Patterns Found:** {sum(self.results['summary']['pattern_counts'].values())}

## Pattern Breakdown

"""

        for category, count in self.results['summary']['pattern_counts'].items():
            if count > 0:
                content += f"### {category.replace('_', ' ').title()}\n"
                content += f"**Count:** {count}\n\n"

                instances = self.results['patterns_found'][category][:10]  # Show first 10
                for instance in instances:
                    content += f"- `{instance['file']}:{instance['line']}` - {instance.get('content', 'N/A')}\n"

                if len(self.results['patterns_found'][category]) > 10:
                    content += f"  ... and {len(self.results['patterns_found'][category]) - 10} more\n"
                content += "\n"

        content += "## High Priority Files\n\n"
        for file_path in self.results['summary']['high_priority_files']:
            content += f"- {file_path}\n"

        content += "\n## Recommendations\n\n"
        for rec in self.results['recommendations']:
            content += f"### {rec['priority']} Priority: {rec['category']}\n"
            content += f"**Description:** {rec['description']}\n"
            content += f"**Action:** {rec['action']}\n"
            content += f"**Files Affected:** {rec['files_affected']}\n\n"

        with open(output_path, 'w') as f:
            f.write(content)

def main():
    """Main function for CLI usage."""
    parser = argparse.ArgumentParser(description="Audit Python execution patterns")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(),
                       help="Project root directory")
    parser.add_argument("--output", type=Path,
                       help="Output file path")
    parser.add_argument("--generate-report", action="store_true",
                       help="Generate comprehensive report")

    args = parser.parse_args()

    auditor = PythonExecutionAuditor(args.project_root)

    if args.generate_report:
        auditor.scan_codebase()
        auditor.generate_report(args.output)
    else:
        print("Use --generate-report to run the audit")

if __name__ == "__main__":
    main()