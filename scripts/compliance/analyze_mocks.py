#!/usr/bin/env python3
"""
Comprehensive mock analysis script to identify all mocked tests/functions.
Finds mocks without justifications and categorizes them for remediation.
"""

import ast
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class MockUsage:
    """Represents a single mock usage instance"""
    file_path: str
    line_number: int
    mock_type: str  # 'patch', 'Mock', 'MagicMock', 'AsyncMock', etc.
    function_name: Optional[str]
    class_name: Optional[str]
    has_justification: bool
    context: str  # The actual line of code
    target: Optional[str]  # What's being mocked (for patches)


class MockAnalyzer:
    """Analyzes codebase for mock usage and justifications"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.mock_patterns = {
            'patch_decorator': r'@patch\(',
            'mock_patch': r'@mock\.patch\(',
            'patch_object': r'patch\.object\(',
            'patch_dict': r'patch\.dict\(',
            'patch_multiple': r'patch\.multiple\(',
            'mock_call': r'Mock\(\)',
            'magic_mock': r'MagicMock\(\)',
            'async_mock': r'AsyncMock\(\)',
            'property_mock': r'PropertyMock\(\)',
            'create_autospec': r'create_autospec\(',
        }
        
        self.justification_patterns = [
            r'@mock_justified\(',
            r'#\s*Mock justification:',
            r'#\s*Justification:',
            r'#\s*JUSTIFICATION:',
            r'""".*[Jj]ustification.*"""',
            r'#\s*Required for.*test',
            r'#\s*Necessary because',
            r'#\s*Mock needed',
        ]
        
        self.results: List[MockUsage] = []
    
    def find_test_files(self) -> List[Path]:
        """Find all test files in the project"""
        test_files = []
        patterns = [
            "tests/**/*.py",
            "test_framework/**/*.py",
            "**/test_*.py",
            "**/*_test.py",
        ]
        
        for pattern in patterns:
            test_files.extend(self.root_path.glob(pattern))
        
        # Remove duplicates and sort
        return sorted(set(test_files))
    
    def analyze_file(self, file_path: Path) -> List[MockUsage]:
        """Analyze a single file for mock usage"""
        mocks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Parse AST for structured analysis
            tree = ast.parse(content)
            
            # Find mocks in decorators
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_name = node.name
                    class_name = self._get_class_name(node, tree)
                    
                    for decorator in node.decorator_list:
                        if self._is_mock_decorator(decorator):
                            line_num = decorator.lineno
                            has_just = self._has_justification(lines, line_num - 1)
                            target = self._extract_patch_target(decorator)
                            
                            mocks.append(MockUsage(
                                file_path=str(file_path.relative_to(self.root_path)),
                                line_number=line_num,
                                mock_type=self._get_decorator_type(decorator),
                                function_name=func_name,
                                class_name=class_name,
                                has_justification=has_just,
                                context=lines[line_num - 1].strip() if line_num <= len(lines) else "",
                                target=target
                            ))
            
            # Find inline mock usage
            for i, line in enumerate(lines, 1):
                for mock_type, pattern in self.mock_patterns.items():
                    if 'decorator' not in mock_type and re.search(pattern, line):
                        # Skip if already found as decorator
                        if not any(m.line_number == i for m in mocks):
                            has_just = self._has_justification(lines, i - 1)
                            
                            mocks.append(MockUsage(
                                file_path=str(file_path.relative_to(self.root_path)),
                                line_number=i,
                                mock_type=mock_type,
                                function_name=self._get_function_context(tree, i),
                                class_name=self._get_class_context(tree, i),
                                has_justification=has_just,
                                context=line.strip(),
                                target=None
                            ))
        
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
        
        return mocks
    
    def _is_mock_decorator(self, decorator) -> bool:
        """Check if AST node is a mock decorator"""
        if isinstance(decorator, ast.Name):
            return decorator.id in ['patch', 'mock']
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr in ['patch', 'object', 'dict', 'multiple']
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id in ['patch', 'mock', 'mock_justified']
            elif isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr in ['patch', 'object', 'dict', 'multiple']
        return False
    
    def _get_decorator_type(self, decorator) -> str:
        """Get the type of mock decorator"""
        if isinstance(decorator, ast.Attribute):
            return f"patch_{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                return f"patch_{decorator.func.attr}"
        return "patch_decorator"
    
    def _extract_patch_target(self, decorator) -> Optional[str]:
        """Extract what's being patched from decorator"""
        if isinstance(decorator, ast.Call) and decorator.args:
            if isinstance(decorator.args[0], ast.Constant):
                return decorator.args[0].value
        return None
    
    def _has_justification(self, lines: List[str], line_idx: int) -> bool:
        """Check if there's a justification near the mock"""
        # Check 3 lines before and 1 after
        start = max(0, line_idx - 3)
        end = min(len(lines), line_idx + 2)
        
        for i in range(start, end):
            for pattern in self.justification_patterns:
                if re.search(pattern, lines[i], re.IGNORECASE):
                    return True
        return False
    
    def _get_class_name(self, node, tree) -> Optional[str]:
        """Get the class name containing this node"""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for child in ast.walk(parent):
                    if child == node:
                        return parent.name
        return None
    
    def _get_function_context(self, tree, line_num: int) -> Optional[str]:
        """Get function name containing this line"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    if node.lineno <= line_num <= (node.end_lineno or node.lineno):
                        return node.name
        return None
    
    def _get_class_context(self, tree, line_num: int) -> Optional[str]:
        """Get class name containing this line"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    if node.lineno <= line_num <= (node.end_lineno or node.lineno):
                        return node.name
        return None
    
    def analyze_all(self) -> Dict:
        """Analyze all test files and generate report"""
        test_files = self.find_test_files()
        print(f"Found {len(test_files)} test files to analyze")
        
        for file_path in test_files:
            mocks = self.analyze_file(file_path)
            self.results.extend(mocks)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate comprehensive report of mock usage"""
        report = {
            'total_mocks': len(self.results),
            'mocks_without_justification': sum(1 for m in self.results if not m.has_justification),
            'mocks_with_justification': sum(1 for m in self.results if m.has_justification),
            'by_type': defaultdict(int),
            'by_file': defaultdict(list),
            'top_mocked_targets': defaultdict(int),
            'top_unjustified': []
        }
        
        # Categorize by type
        for mock in self.results:
            report['by_type'][mock.mock_type] += 1
            report['by_file'][mock.file_path].append(mock)
            if mock.target:
                report['top_mocked_targets'][mock.target] += 1
        
        # Find top unjustified mocks
        unjustified = [m for m in self.results if not m.has_justification]
        report['top_unjustified'] = sorted(unjustified, key=lambda x: x.file_path)[:100]
        
        return report
    
    def print_summary(self, report: Dict):
        """Print a summary of the analysis"""
        print("\n" + "="*80)
        print("MOCK USAGE ANALYSIS REPORT")
        print("="*80)
        
        print(f"\nTotal Mocks Found: {report['total_mocks']}")
        print(f"  - With Justification: {report['mocks_with_justification']}")
        print(f"  - Without Justification: {report['mocks_without_justification']}")
        
        print("\nMocks by Type:")
        for mock_type, count in sorted(report['by_type'].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {mock_type}: {count}")
        
        print("\nTop 10 Most Mocked Targets:")
        for target, count in sorted(report['top_mocked_targets'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {target}: {count} times")
        
        print("\nFiles with Most Unjustified Mocks:")
        file_counts = defaultdict(int)
        for mock in report['top_unjustified']:
            file_counts[mock.file_path] += 1
        
        for file_path, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  - {file_path}: {count} unjustified mocks")
    
    def export_unjustified_list(self, report: Dict, output_file: str = "unjustified_mocks.json"):
        """Export list of unjustified mocks for processing"""
        unjustified_data = []
        for mock in report['top_unjustified']:
            unjustified_data.append({
                'file': mock.file_path,
                'line': mock.line_number,
                'type': mock.mock_type,
                'function': mock.function_name,
                'class': mock.class_name,
                'context': mock.context,
                'target': mock.target
            })
        
        with open(output_file, 'w') as f:
            json.dump(unjustified_data, f, indent=2)
        
        print(f"\nExported {len(unjustified_data)} unjustified mocks to {output_file}")


def main():
    """Main entry point"""
    analyzer = MockAnalyzer()
    report = analyzer.analyze_all()
    analyzer.print_summary(report)
    analyzer.export_unjustified_list(report)
    
    # Return exit code based on violations
    if report['mocks_without_justification'] > 0:
        print(f"\n WARNING: [U+FE0F]  Found {report['mocks_without_justification']} mocks without justification!")
        print("These need to be either:")
        print("  1. Converted to real implementations")
        print("  2. Justified with @mock_justified decorator or comment")
        return 1
    else:
        print("\n PASS:  All mocks have justifications!")
        return 0


if __name__ == "__main__":
    exit(main())