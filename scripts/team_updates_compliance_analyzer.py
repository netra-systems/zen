"""Compliance Analyzer - Checks architecture compliance status."""

import asyncio
import ast
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class ComplianceAnalyzer:
    """Analyzes codebase compliance with architecture rules."""
    
    def __init__(self, project_root: Path):
        """Initialize with project root."""
        self.project_root = project_root
        self.compliance_script = project_root / "scripts" / "check_architecture_compliance.py"
        self.max_lines = 300
        self.max_function_lines = 8
    
    async def analyze(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Check architecture compliance status."""
        line_violations = await self.check_300_line_violations()
        function_violations = await self.check_8_line_violations()
        trends = self.get_compliance_trends()
        
        return {
            "compliance_status": self._determine_status(line_violations, function_violations),
            "line_violations": line_violations,
            "function_violations": function_violations,
            "compliance_trends": trends,
            "compliance_violations": len(line_violations) + len(function_violations)
        }
    
    async def check_300_line_violations(self) -> List[Dict]:
        """Find files exceeding 300 lines."""
        violations = []
        
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                lines = py_file.read_text().split('\n')
                if len(lines) > self.max_lines:
                    violations.append({
                        "file": str(py_file.relative_to(self.project_root)),
                        "lines": len(lines),
                        "excess": len(lines) - self.max_lines
                    })
            except Exception:
                continue
        
        return sorted(violations, key=lambda x: x["excess"], reverse=True)[:10]
    
    async def check_8_line_violations(self) -> List[Dict]:
        """Find functions exceeding 8 lines."""
        violations = []
        
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            file_violations = self._check_functions_in_file(py_file)
            violations.extend(file_violations)
        
        return sorted(violations, key=lambda x: x["excess"], reverse=True)[:10]
    
    def get_compliance_trends(self) -> Dict[str, Any]:
        """Show compliance improvement/degradation."""
        # Run compliance check script if available
        if self.compliance_script.exists():
            try:
                result = subprocess.run(
                    ["python", str(self.compliance_script), "--json"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return self._parse_compliance_output(result.stdout)
            except Exception:
                pass
        
        return {"improving": False, "total_violations": 0}
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_dirs = {
            "venv", ".venv", "node_modules", ".git",
            "__pycache__", ".pytest_cache", "migrations"
        }
        
        for parent in file_path.parents:
            if parent.name in skip_dirs:
                return True
        
        return file_path.name.startswith("test_") or file_path.suffix != ".py"
    
    def _check_functions_in_file(self, file_path: Path) -> List[Dict]:
        """Check functions in a single file."""
        violations = []
        
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_lines = self._count_function_lines(node)
                    if func_lines > self.max_function_lines:
                        violations.append({
                            "file": str(file_path.relative_to(self.project_root)),
                            "function": node.name,
                            "lines": func_lines,
                            "excess": func_lines - self.max_function_lines
                        })
        except Exception:
            pass
        
        return violations
    
    def _count_function_lines(self, node: ast.FunctionDef) -> int:
        """Count lines in a function."""
        if not node.body:
            return 0
        
        # Count actual code lines, not docstrings
        first_stmt = node.body[0]
        if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Str):
            # Skip docstring
            body = node.body[1:]
        else:
            body = node.body
        
        if not body:
            return 0
        
        start_line = body[0].lineno
        end_line = body[-1].end_lineno or body[-1].lineno
        return end_line - start_line + 1
    
    def _determine_status(self, line_viols: List, func_viols: List) -> str:
        """Determine overall compliance status."""
        total = len(line_viols) + len(func_viols)
        
        if total == 0:
            return "fully_compliant"
        elif total <= 5:
            return "mostly_compliant"
        elif total <= 15:
            return "partially_compliant"
        else:
            return "non_compliant"
    
    def _parse_compliance_output(self, output: str) -> Dict[str, Any]:
        """Parse compliance script output."""
        try:
            import json
            data = json.loads(output)
            return {
                "improving": data.get("trend") == "improving",
                "total_violations": data.get("total_violations", 0),
                "fixed_recently": data.get("fixed_recently", 0)
            }
        except Exception:
            return {"improving": False, "total_violations": 0}