#!/usr/bin/env python3
"""
Automated File Splitting Tool
Automatically splits files exceeding the 450-line boundary.
Follows CLAUDE.md requirements: intelligent splitting strategies.
"""

import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SplitSuggestion:
    """File splitting suggestion."""
    original_file: str
    suggested_splits: List[Dict[str, Any]]
    split_strategy: str
    confidence: float

class FileSplitter:
    """Intelligent file splitting utility."""
    
    def __init__(self, project_root: str = "."):
        """Initialize file splitter."""
        self.project_root = Path(project_root)
        self.max_lines = 300
    
    def analyze_file_for_splitting(self, file_path: Path) -> Optional[SplitSuggestion]:
        """Analyze file and suggest splitting strategy."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            if len(lines) <= self.max_lines:
                return None
            
            # Parse Python AST for intelligent splitting
            if file_path.suffix == '.py':
                return self._analyze_python_file(file_path, content, lines)
            elif file_path.suffix in ['.ts', '.tsx']:
                return self._analyze_typescript_file(file_path, content, lines)
            
            return None
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None
    
    def _analyze_python_file(self, file_path: Path, content: str, lines: List[str]) -> SplitSuggestion:
        """Analyze Python file for splitting opportunities."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._fallback_split_suggestion(file_path, lines)
        
        # Extract top-level elements
        classes = []
        functions = []
        imports = []
        constants = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(self._extract_class_info(node, lines))
            elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                functions.append(self._extract_function_info(node, lines))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(self._extract_import_info(node, lines))
            elif isinstance(node, ast.Assign) and node.col_offset == 0:
                constants.append(self._extract_constant_info(node, lines))
        
        # Determine best splitting strategy
        if len(classes) >= 2:
            return self._suggest_class_based_split(file_path, classes, imports, lines)
        elif len(functions) >= 4:
            return self._suggest_function_based_split(file_path, functions, imports, lines)
        else:
            return self._suggest_logical_split(file_path, content, lines)
    
    def _analyze_typescript_file(self, file_path: Path, content: str, lines: List[str]) -> SplitSuggestion:
        """Analyze TypeScript file for splitting opportunities."""
        # Extract interfaces, types, and components
        interfaces = re.findall(r'^interface\s+(\w+)', content, re.MULTILINE)
        types = re.findall(r'^type\s+(\w+)', content, re.MULTILINE)
        components = re.findall(r'^(?:export\s+)?(?:const|function)\s+(\w+)', content, re.MULTILINE)
        
        suggested_splits = []
        
        if len(interfaces) >= 2:
            # Split by interfaces
            for interface in interfaces[:3]:
                suggested_splits.append({
                    "name": f"{file_path.stem}_{interface.lower()}.ts",
                    "content_pattern": f"interface {interface}",
                    "type": "interface"
                })
        
        if len(components) >= 2:
            # Split by components
            for component in components[:3]:
                suggested_splits.append({
                    "name": f"{component}.tsx" if file_path.suffix == '.tsx' else f"{component}.ts",
                    "content_pattern": f"(const|function) {component}",
                    "type": "component"
                })
        
        return SplitSuggestion(
            original_file=str(file_path),
            suggested_splits=suggested_splits,
            split_strategy="typescript_modular",
            confidence=0.8
        )
    
    def _extract_class_info(self, node: ast.ClassDef, lines: List[str]) -> Dict[str, Any]:
        """Extract class information."""
        return {
            "name": node.name,
            "start_line": node.lineno,
            "end_line": getattr(node, 'end_lineno', node.lineno + 10),
            "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
        }
    
    def _extract_function_info(self, node: ast.FunctionDef, lines: List[str]) -> Dict[str, Any]:
        """Extract function information."""
        return {
            "name": node.name,
            "start_line": node.lineno,
            "end_line": getattr(node, 'end_lineno', node.lineno + 5),
            "args": [arg.arg for arg in node.args.args]
        }
    
    def _extract_import_info(self, node: ast.AST, lines: List[str]) -> Dict[str, Any]:
        """Extract import information."""
        return {
            "line": node.lineno,
            "content": lines[node.lineno - 1] if node.lineno <= len(lines) else ""
        }
    
    def _extract_constant_info(self, node: ast.Assign, lines: List[str]) -> Dict[str, Any]:
        """Extract constant information."""
        return {
            "line": node.lineno,
            "content": lines[node.lineno - 1] if node.lineno <= len(lines) else ""
        }
    
    def _suggest_class_based_split(self, file_path: Path, classes: List[Dict], imports: List[Dict], lines: List[str]) -> SplitSuggestion:
        """Suggest splitting by classes."""
        suggested_splits = []
        
        for class_info in classes:
            suggested_splits.append({
                "name": f"{class_info['name'].lower()}.py",
                "content_start": class_info['start_line'],
                "content_end": class_info['end_line'],
                "type": "class",
                "description": f"Class {class_info['name']} with {len(class_info['methods'])} methods"
            })
        
        return SplitSuggestion(
            original_file=str(file_path),
            suggested_splits=suggested_splits,
            split_strategy="class_based",
            confidence=0.9
        )
    
    def _suggest_function_based_split(self, file_path: Path, functions: List[Dict], imports: List[Dict], lines: List[str]) -> SplitSuggestion:
        """Suggest splitting by function groups."""
        # Group functions by naming patterns or purpose
        function_groups = self._group_functions_by_pattern(functions)
        
        suggested_splits = []
        for group_name, group_functions in function_groups.items():
            suggested_splits.append({
                "name": f"{file_path.stem}_{group_name}.py",
                "functions": group_functions,
                "type": "function_group",
                "description": f"Function group: {group_name}"
            })
        
        return SplitSuggestion(
            original_file=str(file_path),
            suggested_splits=suggested_splits,
            split_strategy="function_based",
            confidence=0.7
        )
    
    def _suggest_logical_split(self, file_path: Path, content: str, lines: List[str]) -> SplitSuggestion:
        """Suggest logical splitting based on content analysis."""
        # Look for logical boundaries (comments, blank lines, etc.)
        split_points = self._find_logical_split_points(lines)
        
        suggested_splits = []
        for i, point in enumerate(split_points):
            suggested_splits.append({
                "name": f"{file_path.stem}_part{i+1}.py",
                "start_line": point["start"],
                "end_line": point["end"],
                "type": "logical",
                "description": f"Logical section {i+1}"
            })
        
        return SplitSuggestion(
            original_file=str(file_path),
            suggested_splits=suggested_splits,
            split_strategy="logical",
            confidence=0.6
        )
    
    def _fallback_split_suggestion(self, file_path: Path, lines: List[str]) -> SplitSuggestion:
        """Fallback splitting suggestion."""
        lines_per_split = self.max_lines
        num_splits = (len(lines) + lines_per_split - 1) // lines_per_split
        
        suggested_splits = []
        for i in range(num_splits):
            start = i * lines_per_split
            end = min((i + 1) * lines_per_split, len(lines))
            
            suggested_splits.append({
                "name": f"{file_path.stem}_part{i+1}{file_path.suffix}",
                "start_line": start + 1,
                "end_line": end,
                "type": "simple",
                "description": f"Simple split part {i+1}"
            })
        
        return SplitSuggestion(
            original_file=str(file_path),
            suggested_splits=suggested_splits,
            split_strategy="simple",
            confidence=0.3
        )
    
    def _group_functions_by_pattern(self, functions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group functions by naming patterns."""
        groups = {}
        
        for func in functions:
            name = func['name']
            
            # Group by common prefixes
            if name.startswith('_'):
                group = 'private'
            elif name.startswith('test_'):
                group = 'tests'
            elif name.startswith('get_'):
                group = 'getters'
            elif name.startswith('set_'):
                group = 'setters'
            elif name.startswith('create_'):
                group = 'creators'
            elif name.startswith('update_'):
                group = 'updaters'
            elif name.startswith('delete_'):
                group = 'deleters'
            else:
                group = 'main'
            
            if group not in groups:
                groups[group] = []
            groups[group].append(func)
        
        return groups
    
    def _find_logical_split_points(self, lines: List[str]) -> List[Dict[str, int]]:
        """Find logical points to split the file."""
        split_points = []
        current_start = 1
        
        for i, line in enumerate(lines):
            # Look for major section separators
            if (line.strip().startswith('#') and len(line.strip()) > 10) or \
               (line.strip() == '' and i > 0 and lines[i-1].strip() == ''):
                
                if i - current_start > 50:  # Minimum section size
                    split_points.append({
                        "start": current_start,
                        "end": i
                    })
                    current_start = i + 1
        
        # Add final section
        if current_start < len(lines):
            split_points.append({
                "start": current_start,
                "end": len(lines)
            })
        
        return split_points
    
    def scan_for_oversized_files(self) -> List[SplitSuggestion]:
        """Scan project for files exceeding size limits."""
        oversized_files = []
        patterns = ['app/**/*.py', 'scripts/**/*.py', 'frontend/**/*.ts', 'frontend/**/*.tsx']
        
        for pattern in patterns:
            for file_path in self.project_root.glob(pattern):
                if self._should_skip_file(file_path):
                    continue
                
                suggestion = self.analyze_file_for_splitting(file_path)
                if suggestion:
                    oversized_files.append(suggestion)
        
        return oversized_files
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            '__pycache__', 'node_modules', '.git', 
            'test_', 'migrations', 'venv', '.venv'
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def generate_split_report(self) -> str:
        """Generate comprehensive splitting report."""
        suggestions = self.scan_for_oversized_files()
        
        if not suggestions:
            return "No files exceed the 450-line boundary. Excellent compliance!"
        
        report = ["FILE SPLITTING ANALYSIS", "=" * 50, ""]
        
        for suggestion in suggestions:
            report.append(f"FILE: {suggestion.original_file}")
            report.append(f"STRATEGY: {suggestion.split_strategy}")
            report.append(f"CONFIDENCE: {suggestion.confidence:.1%}")
            report.append("SUGGESTED SPLITS:")
            
            for split in suggestion.suggested_splits:
                report.append(f"  [U+2022] {split['name']} ({split['type']})")
                if 'description' in split:
                    report.append(f"    {split['description']}")
            
            report.append("")
        
        report.extend([
            "RECOMMENDATIONS:",
            "1. Start with high-confidence suggestions (>80%)",
            "2. Review class-based splits first (easiest)",
            "3. Test thoroughly after splitting",
            "4. Update imports and dependencies",
            ""
        ])
        
        return "\n".join(report)

def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Automated file splitting for boundary compliance'
    )
    parser.add_argument('--scan', action='store_true', help='Scan for oversized files')
    parser.add_argument('--report', action='store_true', help='Generate splitting report')
    parser.add_argument('--file', help='Analyze specific file')
    
    args = parser.parse_args()
    
    splitter = FileSplitter()
    
    if args.report or args.scan:
        report = splitter.generate_split_report()
        print(report)
    elif args.file:
        file_path = Path(args.file)
        suggestion = splitter.analyze_file_for_splitting(file_path)
        if suggestion:
            print(f"Splitting suggestion for {file_path}:")
            print(f"Strategy: {suggestion.split_strategy}")
            print(f"Confidence: {suggestion.confidence:.1%}")
            for split in suggestion.suggested_splits:
                print(f"   ->  {split['name']}")
        else:
            print(f"File {file_path} is within size limits or cannot be analyzed")
    else:
        print("Use --scan, --report, or --file <path> to analyze files")

if __name__ == "__main__":
    main()