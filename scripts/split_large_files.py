#!/usr/bin/env python3
"""
Automated File Splitting Tool for Netra Codebase
Splits large test files (>300 lines) into focused modules

Priority: P0 - CRITICAL for architecture compliance
Author: Claude Code Assistant
Date: 2025-08-14
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class SplitPoint:
    """Represents a logical split point in a file"""
    class_name: str
    start_line: int
    end_line: int
    test_methods: List[str]
    estimated_lines: int


@dataclass
class FileAnalysis:
    """Analysis result for a large file"""
    filepath: str
    total_lines: int
    imports_section: str
    split_points: List[SplitPoint]
    suggested_modules: List[str]


class TestFileSplitter:
    """Splits large test files while maintaining functionality"""
    
    def __init__(self, max_lines: int = 300):
        self.max_lines = max_lines
        self.base_dir = Path(__file__).parent.parent
        
    def analyze_file(self, filepath: str) -> FileAnalysis:
        """Analyze file structure to determine optimal split points"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Extract imports section
        imports_end = self._find_imports_end(lines)
        imports_section = '\n'.join(lines[:imports_end])
        
        # Parse AST to find class boundaries
        tree = ast.parse(content)
        split_points = self._analyze_classes(tree, lines)
        
        # Generate suggested module names
        suggested_modules = self._suggest_module_names(
            filepath, split_points
        )
        
        return FileAnalysis(
            filepath=filepath,
            total_lines=len(lines),
            imports_section=imports_section,
            split_points=split_points,
            suggested_modules=suggested_modules
        )
    
    def _find_imports_end(self, lines: List[str]) -> int:
        """Find where imports section ends"""
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not (
                stripped.startswith('"""') or 
                stripped.startswith('#') or
                stripped.startswith('import ') or
                stripped.startswith('from ') or
                stripped == '' or
                'import' in stripped
            ):
                return i
        return 0
    
    def _analyze_classes(self, tree: ast.AST, lines: List[str]) -> List[SplitPoint]:
        """Extract test classes and their boundaries"""
        split_points = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith('Test'):
                    methods = self._extract_test_methods(node)
                    start_line = node.lineno - 1
                    end_line = self._find_class_end(node, lines)
                    
                    split_points.append(SplitPoint(
                        class_name=node.name,
                        start_line=start_line,
                        end_line=end_line,
                        test_methods=methods,
                        estimated_lines=end_line - start_line
                    ))
        
        return sorted(split_points, key=lambda x: x.start_line)
    
    def _extract_test_methods(self, class_node: ast.ClassDef) -> List[str]:
        """Extract test method names from class"""
        methods = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('test_'):
                    methods.append(node.name)
        return methods
    
    def _find_class_end(self, class_node: ast.ClassDef, lines: List[str]) -> int:
        """Find the last line of a class"""
        # Start from class definition line
        start_line = class_node.lineno - 1
        
        # Find next class or end of file
        for i in range(start_line + 1, len(lines)):
            line = lines[i].strip()
            if line.startswith('class ') and not line.startswith('    '):
                return i - 1
        
        return len(lines) - 1
    
    def _suggest_module_names(self, filepath: str, split_points: List[SplitPoint]) -> List[str]:
        """Generate descriptive module names based on test classes"""
        base_name = Path(filepath).stem
        module_names = []
        
        for point in split_points:
            # Convert class name to module name
            class_lower = point.class_name.lower()
            if class_lower.startswith('test'):
                class_lower = class_lower[4:]  # Remove 'test' prefix
            
            module_name = f"{base_name}_{class_lower}.py"
            module_names.append(module_name)
        
        return module_names
    
    def split_file(self, analysis: FileAnalysis) -> List[str]:
        """Split file into multiple modules"""
        with open(analysis.filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        created_files = []
        base_dir = Path(analysis.filepath).parent
        
        for i, split_point in enumerate(analysis.split_points):
            module_name = analysis.suggested_modules[i]
            module_path = base_dir / module_name
            
            # Create module content
            content = self._create_module_content(
                analysis.imports_section,
                lines,
                split_point
            )
            
            # Write module file
            with open(module_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            created_files.append(str(module_path))
            print(f"Created: {module_path} ({split_point.estimated_lines} lines)")
        
        return created_files
    
    def _create_module_content(self, imports: str, lines: List[str], split_point: SplitPoint) -> str:
        """Create content for a split module"""
        content_lines = []
        
        # Add file header
        content_lines.append(f'"""')
        content_lines.append(f'Test module: {split_point.class_name}')
        content_lines.append(f'Split from large test file for architecture compliance')
        content_lines.append(f'Test methods: {len(split_point.test_methods)}')
        content_lines.append(f'"""')
        content_lines.append('')
        
        # Add imports
        content_lines.append(imports)
        content_lines.append('')
        
        # Add class content
        class_lines = lines[split_point.start_line:split_point.end_line + 1]
        content_lines.extend([line.rstrip() for line in class_lines])
        
        return '\n'.join(content_lines)


def _initialize_splitter_and_files():
    """Initialize splitter and priority files list"""
    splitter = TestFileSplitter()
    priority_files = [
        "app/tests/agents/test_supervisor_consolidated_comprehensive.py",
        "app/tests/services/test_tool_permission_service_comprehensive.py", 
        "app/tests/services/test_quality_gate_service_comprehensive.py",
        "app/tests/core/test_async_utils.py", "app/tests/core/test_missing_tests_11_30.py"
    ]
    return splitter, priority_files

def _check_file_exists(filepath, relative_path):
    """Check if file exists and handle missing files"""
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return False
    return True

def _analyze_and_display_file(splitter, filepath, relative_path):
    """Analyze file and display basic information"""
    print(f"\n{'='*60}\nAnalyzing: {relative_path}\n{'='*60}")
    analysis = splitter.analyze_file(str(filepath))
    print(f"Total lines: {analysis.total_lines}")
    print(f"Test classes found: {len(analysis.split_points)}")
    return analysis

def _check_file_size_limit(analysis, splitter):
    """Check if file is within size limit"""
    if analysis.total_lines <= splitter.max_lines:
        print("File is within size limit")
        return True
    return False

def _display_split_suggestions(analysis):
    """Display split suggestions"""
    print(f"\nSuggested split into {len(analysis.split_points)} modules:")
    for i, (point, module) in enumerate(zip(analysis.split_points, analysis.suggested_modules)):
        print(f"  {i+1}. {module}\n     Class: {point.class_name}")
        print(f"     Lines: {point.estimated_lines}\n     Methods: {len(point.test_methods)}")

def _get_user_confirmations(relative_path):
    """Get user confirmations for splitting and removal"""
    split_confirm = input(f"\nSplit {relative_path}? (y/N): ").lower() == 'y'
    remove_confirm = False
    if split_confirm:
        remove_confirm = input(f"Remove original file? (y/N): ").lower() == 'y'
    return split_confirm, remove_confirm

def _handle_file_splitting(splitter, analysis, relative_path, filepath, split_confirm, remove_confirm):
    """Handle file splitting process"""
    if split_confirm:
        created_files = splitter.split_file(analysis)
        print(f"\nSuccessfully split into {len(created_files)} modules")
        if remove_confirm:
            filepath.unlink()
            print(f"Removed: {relative_path}")
    else:
        print("Skipped")

def _print_completion_message():
    """Print completion message"""
    print(f"\n{'='*60}\nFile splitting complete!\nRemember to:")
    print("   1. Update any imports in other files\n   2. Run tests to verify functionality")
    print(f"   3. Update test discovery patterns if needed\n{'='*60}")

def main():
    """Main execution function"""
    splitter, priority_files = _initialize_splitter_and_files()
    base_dir = Path(__file__).parent.parent
    for relative_path in priority_files:
        filepath = base_dir / relative_path
        if not _check_file_exists(filepath, relative_path): continue
        try:
            analysis = _analyze_and_display_file(splitter, filepath, relative_path)
            if _check_file_size_limit(analysis, splitter): continue
            _display_split_suggestions(analysis)
            split_confirm, remove_confirm = _get_user_confirmations(relative_path)
            _handle_file_splitting(splitter, analysis, relative_path, filepath, split_confirm, remove_confirm)
        except Exception as e:
            print(f"Error processing {relative_path}: {e}")
    _print_completion_message()


if __name__ == "__main__":
    main()