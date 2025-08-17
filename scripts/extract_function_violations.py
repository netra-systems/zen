#!/usr/bin/env python3
"""Extract and prioritize function length violations for agent-based fixing"""
import ast
import os
from pathlib import Path
from typing import List, Tuple
import json

class FunctionViolationExtractor:
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.violations = []
        
    def check_file(self, file_path: Path) -> List[dict]:
        """Check a single file for function violations"""
        violations = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_lines = self._count_function_lines(node)
                    if func_lines > 8:
                        violations.append({
                            'file': str(file_path),
                            'function': node.name,
                            'lines': func_lines,
                            'start_line': node.lineno,
                            'end_line': node.end_lineno,
                            'is_async': isinstance(node, ast.AsyncFunctionDef),
                            'is_critical': self._is_critical_path(file_path, node.name)
                        })
        except:
            pass
        return violations
    
    def _count_function_lines(self, node) -> int:
        """Count non-empty, non-comment lines in function"""
        if node.end_lineno and node.lineno:
            return node.end_lineno - node.lineno + 1
        return 0
    
    def _is_critical_path(self, file_path: Path, func_name: str) -> bool:
        """Check if function is in critical agent/data paths"""
        critical_patterns = [
            'agents/supervisor',
            'agents/data_sub_agent', 
            'agents/corpus_admin',
            'agents/triage_sub_agent',
            'llm/',
            'services/websocket',
            'auth/',
            'core/'
        ]
        path_str = str(file_path).replace('\\', '/')
        return any(pattern in path_str for pattern in critical_patterns)
    
    def scan_directory(self) -> List[dict]:
        """Scan all Python files for violations"""
        for py_file in self.root_path.rglob("*.py"):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
            violations = self.check_file(py_file)
            self.violations.extend(violations)
        return self.violations
    
    def prioritize_violations(self) -> List[dict]:
        """Sort violations by priority"""
        # Sort by: critical path first, then by line count
        return sorted(self.violations, 
                     key=lambda x: (-x['is_critical'], -x['lines']))

def main():
    extractor = FunctionViolationExtractor(".")
    print("Scanning for function violations...")
    extractor.scan_directory()
    prioritized = extractor.prioritize_violations()
    
    # Get top 1000 violations
    top_violations = prioritized[:1000]
    
    # Group by file for efficiency
    files_with_violations = {}
    for v in top_violations:
        if v['file'] not in files_with_violations:
            files_with_violations[v['file']] = []
        files_with_violations[v['file']].append(v)
    
    # Save results
    with open('function_violations_top1000.json', 'w') as f:
        json.dump({
            'total_violations': len(extractor.violations),
            'top_1000': top_violations,
            'files_to_fix': list(files_with_violations.keys()),
            'file_violations': files_with_violations
        }, f, indent=2)
    
    print(f"Found {len(extractor.violations)} total violations")
    print(f"Extracted top 1000 violations across {len(files_with_violations)} files")
    print(f"Critical path violations: {sum(1 for v in top_violations if v['is_critical'])}")
    print("Results saved to function_violations_top1000.json")
    
    # Print summary
    print("\nTop 10 worst violations:")
    for i, v in enumerate(top_violations[:10], 1):
        print(f"{i}. {v['function']}() in {v['file']}: {v['lines']} lines")

if __name__ == "__main__":
    main()