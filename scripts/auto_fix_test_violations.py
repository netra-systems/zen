#!/usr/bin/env python3
"""
Auto Fix Test Size Violations Script

This script automatically fixes test size violations by:
1. Splitting large test files (>300 lines) into smaller modules
2. Extracting helper methods from long functions (>8 lines)
3. Maintaining test functionality and imports

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity, Code Quality
- Value Impact: Enables faster test execution and better maintainability
- Strategic/Revenue Impact: Reduces technical debt and improves developer productivity
"""

import os
import re
import ast
import sys
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TestViolation:
    """Represents a test size violation"""
    file_path: str
    violation_type: str  # 'file_size' or 'function_size'
    current_size: int
    limit: int
    details: Optional[str] = None

@dataclass
class FunctionInfo:
    """Information about a function in a test file"""
    name: str
    start_line: int
    end_line: int
    line_count: int
    is_test: bool
    is_async: bool
    content: str
    decorators: List[str]

@dataclass
class ClassInfo:
    """Information about a test class"""
    name: str
    start_line: int
    end_line: int
    line_count: int
    functions: List[FunctionInfo]
    content: str

class TestFileAnalyzer:
    """Analyzes test files for violations and structure"""
    
    def __init__(self):
        self.file_size_limit = 300
        self.function_size_limit = 8
        
    def find_test_files(self, root_dir: str) -> List[str]:
        """Find all test files in the project"""
        test_files = []
        
        # Only scan specific project directories
        project_test_dirs = [
            os.path.join(root_dir, 'app', 'tests'),
            os.path.join(root_dir, 'tests'),
            os.path.join(root_dir, 'auth_service', 'tests'),
            os.path.join(root_dir, 'frontend', 'tests')
        ]
        
        for test_dir in project_test_dirs:
            if not os.path.exists(test_dir):
                continue
                
            for root, dirs, files in os.walk(test_dir):
                # Skip virtual environment, __pycache__ and other common dirs
                dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', 'venv_test', 'node_modules', '__pycache__', '.git']]
                
                for file in files:
                    if file.startswith('test_') and file.endswith('.py'):
                        test_files.append(os.path.join(root, file))
        
        return test_files
    
    def analyze_file_structure(self, file_path: str) -> Tuple[List[ClassInfo], List[FunctionInfo], List[str]]:
        """Analyze the structure of a test file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Handle common syntax issues that break AST parsing
            if '\\' in content and not content.endswith('\n'):
                content += '\n'
            
            tree = ast.parse(content)
            lines = content.split('\n')
            
            classes = []
            functions = []
            imports = []
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(ast.get_source_segment(content, node))
            
            # Extract classes and functions
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    class_info = self._extract_class_info(node, lines, content)
                    classes.append(class_info)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_info = self._extract_function_info(node, lines, content)
                    functions.append(func_info)
            
            return classes, functions, imports
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return [], [], []
    
    def _extract_class_info(self, node: ast.ClassDef, lines: List[str], content: str) -> ClassInfo:
        """Extract information about a class"""
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 10
        
        class_functions = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function_info(item, lines, content)
                class_functions.append(func_info)
        
        class_content = '\n'.join(lines[start_line-1:end_line])
        
        return ClassInfo(
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            line_count=end_line - start_line + 1,
            functions=class_functions,
            content=class_content
        )
    
    def _extract_function_info(self, node: ast.FunctionDef, lines: List[str], content: str) -> FunctionInfo:
        """Extract information about a function"""
        start_line = node.lineno
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 10
        
        decorators = [ast.get_source_segment(content, d) for d in node.decorator_list]
        func_content = '\n'.join(lines[start_line-1:end_line])
        
        return FunctionInfo(
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            line_count=end_line - start_line + 1,
            is_test=node.name.startswith('test_'),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            content=func_content,
            decorators=decorators
        )
    
    def find_violations(self, file_path: str) -> List[TestViolation]:
        """Find all violations in a test file"""
        violations = []
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return violations
        
        # Check file size
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                line_count = len(lines)
        except (UnicodeDecodeError, OSError) as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return violations
        
        if line_count > self.file_size_limit:
            violations.append(TestViolation(
                file_path=file_path,
                violation_type='file_size',
                current_size=line_count,
                limit=self.file_size_limit,
                details=f"File has {line_count} lines, limit is {self.file_size_limit}"
            ))
        
        # Check function sizes using simple line counting if AST fails
        try:
            classes, functions, _ = self.analyze_file_structure(file_path)
            self._check_function_violations(violations, file_path, classes, functions)
        except Exception as e:
            logger.warning(f"AST analysis failed for {file_path}, using simple line counting: {e}")
            self._check_function_violations_simple(violations, file_path, lines)
        
        return violations
    
    def _check_function_violations(self, violations: List[TestViolation], file_path: str, 
                                  classes: List[ClassInfo], functions: List[FunctionInfo]):
        """Check function violations using AST analysis"""
        # Check standalone functions
        for func in functions:
            if func.line_count > self.function_size_limit:
                violations.append(TestViolation(
                    file_path=file_path,
                    violation_type='function_size',
                    current_size=func.line_count,
                    limit=self.function_size_limit,
                    details=f"Function '{func.name}' has {func.line_count} lines"
                ))
        
        # Check class methods
        for cls in classes:
            for func in cls.functions:
                if func.line_count > self.function_size_limit:
                    violations.append(TestViolation(
                        file_path=file_path,
                        violation_type='function_size',
                        current_size=func.line_count,
                        limit=self.function_size_limit,
                        details=f"Method '{cls.name}.{func.name}' has {func.line_count} lines"
                    ))
    
    def _check_function_violations_simple(self, violations: List[TestViolation], file_path: str, lines: List[str]):
        """Check function violations using simple regex pattern matching"""
        current_function = None
        function_start = 0
        indent_level = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
                
            # Detect function/method definitions
            if re.match(r'^\s*(async\s+)?def\s+\w+', line):
                # Finish previous function if any
                if current_function:
                    func_lines = i - function_start
                    if func_lines > self.function_size_limit:
                        violations.append(TestViolation(
                            file_path=file_path,
                            violation_type='function_size',
                            current_size=func_lines,
                            limit=self.function_size_limit,
                            details=f"Function '{current_function}' has {func_lines} lines"
                        ))
                
                # Start new function
                current_function = re.search(r'def\s+(\w+)', line).group(1)
                function_start = i
                indent_level = len(line) - len(line.lstrip())
            
            # Check if we're still in the function based on indentation
            elif current_function and line.strip():
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and not line.startswith(' ' * (indent_level + 1)):
                    # Function ended
                    func_lines = i - function_start
                    if func_lines > self.function_size_limit:
                        violations.append(TestViolation(
                            file_path=file_path,
                            violation_type='function_size',
                            current_size=func_lines,
                            limit=self.function_size_limit,
                            details=f"Function '{current_function}' has {func_lines} lines"
                        ))
                    current_function = None
        
        # Handle last function
        if current_function:
            func_lines = len(lines) - function_start
            if func_lines > self.function_size_limit:
                violations.append(TestViolation(
                    file_path=file_path,
                    violation_type='function_size',
                    current_size=func_lines,
                    limit=self.function_size_limit,
                    details=f"Function '{current_function}' has {func_lines} lines"
                ))

class TestFileSplitter:
    """Handles splitting large test files into smaller modules"""
    
    def __init__(self, analyzer: TestFileAnalyzer):
        self.analyzer = analyzer
    
    def split_large_file(self, file_path: str, dry_run: bool = True) -> List[str]:
        """Split a large test file into smaller modules"""
        logger.info(f"Splitting large file: {file_path}")
        
        classes, functions, imports = self.analyzer.analyze_file_structure(file_path)
        
        # Read original file
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
            lines = original_content.split('\n')
        
        # Determine split strategy based on file size
        line_count = len(lines)
        if line_count > 900:
            # Split into 3+ files
            return self._split_into_multiple_files(file_path, classes, functions, imports, lines, dry_run)
        elif line_count > 450:
            # Split into 2 files
            return self._split_into_two_files(file_path, classes, functions, imports, lines, dry_run)
        else:
            # Extract utilities
            return self._extract_utilities(file_path, classes, functions, imports, lines, dry_run)
    
    def _split_into_multiple_files(self, file_path: str, classes: List[ClassInfo], 
                                 functions: List[FunctionInfo], imports: List[str], 
                                 lines: List[str], dry_run: bool) -> List[str]:
        """Split file into 3+ smaller files based on test categories"""
        base_name = Path(file_path).stem
        base_dir = Path(file_path).parent
        
        # Categorize classes and functions
        categories = self._categorize_tests(classes, functions)
        
        new_files = []
        for category, items in categories.items():
            if not items:
                continue
                
            new_file_path = base_dir / f"{base_name}_{category}.py"
            new_files.append(str(new_file_path))
            
            if not dry_run:
                self._create_split_file(new_file_path, items, imports, lines)
        
        # Create utilities file if needed
        utilities = self._extract_helper_functions(functions)
        if utilities:
            utils_file_path = base_dir / f"{base_name}_utils.py"
            new_files.append(str(utils_file_path))
            
            if not dry_run:
                self._create_utilities_file(utils_file_path, utilities, imports)
        
        return new_files
    
    def _split_into_two_files(self, file_path: str, classes: List[ClassInfo], 
                            functions: List[FunctionInfo], imports: List[str], 
                            lines: List[str], dry_run: bool) -> List[str]:
        """Split file into 2 files based on test complexity"""
        base_name = Path(file_path).stem
        base_dir = Path(file_path).parent
        
        # Split by complexity/type
        core_items = []
        extended_items = []
        
        for cls in classes:
            if 'critical' in cls.name.lower() or 'core' in cls.name.lower():
                core_items.append(cls)
            else:
                extended_items.append(cls)
        
        # If split is uneven, balance it
        if len(core_items) < len(extended_items) // 3:
            # Move some items to core
            move_count = len(extended_items) // 2 - len(core_items)
            for _ in range(min(move_count, len(extended_items))):
                core_items.append(extended_items.pop())
        
        new_files = []
        
        # Core file
        if core_items:
            core_file_path = base_dir / f"{base_name}_core.py"
            new_files.append(str(core_file_path))
            if not dry_run:
                self._create_split_file(core_file_path, core_items, imports, lines)
        
        # Extended file
        if extended_items:
            extended_file_path = base_dir / f"{base_name}_extended.py"
            new_files.append(str(extended_file_path))
            if not dry_run:
                self._create_split_file(extended_file_path, extended_items, imports, lines)
        
        return new_files
    
    def _extract_utilities(self, file_path: str, classes: List[ClassInfo], 
                          functions: List[FunctionInfo], imports: List[str], 
                          lines: List[str], dry_run: bool) -> List[str]:
        """Extract shared utilities from a moderately large file"""
        base_name = Path(file_path).stem
        base_dir = Path(file_path).parent
        
        # Find utility functions (fixtures, helpers, etc.)
        utilities = []
        remaining_items = []
        
        for func in functions:
            if (not func.is_test and 
                ('fixture' in func.decorators or 
                 'helper' in func.name.lower() or 
                 'util' in func.name.lower())):
                utilities.append(func)
            else:
                remaining_items.append(func)
        
        new_files = []
        
        # Create utilities file if we found any
        if utilities:
            utils_file_path = base_dir / f"{base_name}_utils.py"
            new_files.append(str(utils_file_path))
            
            if not dry_run:
                self._create_utilities_file(utils_file_path, utilities, imports)
                
                # Update original file to import from utils
                self._update_file_with_utils_import(file_path, utils_file_path, utilities)
        
        return new_files
    
    def _categorize_tests(self, classes: List[ClassInfo], functions: List[FunctionInfo]) -> Dict[str, List]:
        """Categorize tests based on their names and content"""
        categories = defaultdict(list)
        
        for cls in classes:
            category = self._determine_category(cls.name)
            categories[category].append(cls)
        
        for func in functions:
            if func.is_test:
                category = self._determine_category(func.name)
                categories[category].append(func)
        
        return dict(categories)
    
    def _determine_category(self, name: str) -> str:
        """Determine category based on test name"""
        name_lower = name.lower()
        
        if 'integration' in name_lower:
            return 'integration'
        elif 'e2e' in name_lower or 'end_to_end' in name_lower:
            return 'e2e'
        elif 'performance' in name_lower or 'perf' in name_lower:
            return 'performance'
        elif 'security' in name_lower or 'auth' in name_lower:
            return 'security'
        elif 'websocket' in name_lower or 'ws' in name_lower:
            return 'websocket'
        elif 'database' in name_lower or 'db' in name_lower:
            return 'database'
        elif 'agent' in name_lower:
            return 'agent'
        elif 'api' in name_lower:
            return 'api'
        else:
            return 'core'
    
    def _extract_helper_functions(self, functions: List[FunctionInfo]) -> List[FunctionInfo]:
        """Extract helper/utility functions"""
        return [f for f in functions if not f.is_test and 
                ('helper' in f.name.lower() or 'util' in f.name.lower() or 
                 'fixture' in [d.lower() for d in f.decorators])]
    
    def _create_split_file(self, file_path: Path, items: List, imports: List[str], original_lines: List[str]):
        """Create a new split test file"""
        content_parts = []
        
        # Add file header
        content_parts.append('"""')
        content_parts.append(f'Test module split from original file')
        content_parts.append(f'Generated by auto_fix_test_violations.py')
        content_parts.append('"""')
        content_parts.append('')
        
        # Add imports
        for imp in imports:
            if imp and imp.strip():
                content_parts.append(imp.strip())
        content_parts.append('')
        
        # Add items (classes/functions)
        for item in items:
            if hasattr(item, 'content'):
                content_parts.append(item.content)
                content_parts.append('')
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_parts))
        
        logger.info(f"Created split file: {file_path}")
    
    def _create_utilities_file(self, file_path: Path, utilities: List[FunctionInfo], imports: List[str]):
        """Create a utilities file with helper functions"""
        content_parts = []
        
        # Add file header
        content_parts.append('"""')
        content_parts.append('Test utilities and helper functions')
        content_parts.append('Generated by auto_fix_test_violations.py')
        content_parts.append('"""')
        content_parts.append('')
        
        # Add imports (filter to only what's needed)
        for imp in imports:
            if imp and imp.strip():
                content_parts.append(imp.strip())
        content_parts.append('')
        
        # Add utility functions
        for util in utilities:
            content_parts.append(util.content)
            content_parts.append('')
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_parts))
        
        logger.info(f"Created utilities file: {file_path}")
    
    def _update_file_with_utils_import(self, original_file: str, utils_file: Path, utilities: List[FunctionInfo]):
        """Update original file to import from utilities file"""
        # This is a simplified implementation
        # In practice, you'd want more sophisticated import handling
        utils_module = utils_file.stem
        
        with open(original_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add import at the top
        import_line = f"from .{utils_module} import {', '.join([u.name for u in utilities])}"
        
        # Insert after existing imports
        lines = content.split('\n')
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                insert_pos = i + 1
        
        lines.insert(insert_pos, import_line)
        
        with open(original_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

class FunctionRefactor:
    """Handles refactoring long functions into smaller pieces"""
    
    def __init__(self):
        self.max_lines = 8
    
    def refactor_long_function(self, file_path: str, function_info: FunctionInfo, dry_run: bool = True) -> str:
        """Refactor a long function by extracting helper methods"""
        logger.info(f"Refactoring function {function_info.name} in {file_path}")
        
        if dry_run:
            return f"Would refactor {function_info.name} ({function_info.line_count} lines)"
        
        # This is a simplified implementation
        # Real implementation would need sophisticated AST manipulation
        return self._extract_setup_and_assertions(function_info)
    
    def _extract_setup_and_assertions(self, func_info: FunctionInfo) -> str:
        """Extract setup code and assertions into helper methods"""
        lines = func_info.content.split('\n')
        
        # Find patterns to extract
        setup_lines = []
        assertion_lines = []
        main_logic = []
        
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith('assert '):
                assertion_lines.append(line)
            elif any(keyword in line_stripped for keyword in ['setup', 'prepare', 'init']):
                setup_lines.append(line)
            else:
                main_logic.append(line)
        
        # Create helper methods
        helpers = []
        
        if len(setup_lines) > 2:
            helpers.append(self._create_setup_helper(setup_lines))
        
        if len(assertion_lines) > 2:
            helpers.append(self._create_assertion_helper(assertion_lines))
        
        return '\n'.join(helpers)
    
    def _create_setup_helper(self, setup_lines: List[str]) -> str:
        """Create a setup helper method"""
        return f"""
    def _setup_test_data(self):
        \"\"\"Setup test data and configurations\"\"\"
{chr(10).join(setup_lines)}
"""
    
    def _create_assertion_helper(self, assertion_lines: List[str]) -> str:
        """Create an assertion helper method"""
        return f"""
    def _verify_results(self, results):
        \"\"\"Verify test results and assertions\"\"\"
{chr(10).join(assertion_lines)}
"""

class TestViolationFixer:
    """Main class that orchestrates fixing test violations"""
    
    def __init__(self, root_dir: str = '.'):
        self.root_dir = root_dir
        self.analyzer = TestFileAnalyzer()
        self.splitter = TestFileSplitter(self.analyzer)
        self.refactor = FunctionRefactor()
        
    def scan_violations(self) -> Dict[str, List[TestViolation]]:
        """Scan all test files for violations"""
        logger.info("Scanning for test violations...")
        
        test_files = self.analyzer.find_test_files(self.root_dir)
        violations_by_file = {}
        
        total_files = 0
        total_violations = 0
        
        for file_path in test_files:
            violations = self.analyzer.find_violations(file_path)
            if violations:
                violations_by_file[file_path] = violations
                total_violations += len(violations)
            total_files += 1
        
        logger.info(f"Scanned {total_files} test files, found {total_violations} violations in {len(violations_by_file)} files")
        return violations_by_file
    
    def fix_violations(self, violations_by_file: Dict[str, List[TestViolation]], dry_run: bool = True, max_files: int = 20):
        """Fix violations in test files"""
        logger.info(f"Fixing violations (dry_run={dry_run}, max_files={max_files})...")
        
        # Sort files by severity (largest violations first)
        sorted_files = sorted(violations_by_file.items(), 
                            key=lambda x: max(v.current_size for v in x[1]), 
                            reverse=True)
        
        fixed_files = []
        
        for i, (file_path, violations) in enumerate(sorted_files[:max_files]):
            logger.info(f"Fixing {file_path} ({i+1}/{min(max_files, len(sorted_files))})")
            
            # Group violations by type
            file_size_violations = [v for v in violations if v.violation_type == 'file_size']
            function_size_violations = [v for v in violations if v.violation_type == 'function_size']
            
            # Fix file size violations first
            if file_size_violations:
                new_files = self.splitter.split_large_file(file_path, dry_run)
                fixed_files.extend(new_files)
                logger.info(f"Split {file_path} into {len(new_files)} files")
            
            # Fix function size violations
            elif function_size_violations:
                for violation in function_size_violations:
                    # Would need function info to refactor
                    logger.info(f"Would refactor function in {file_path}: {violation.details}")
        
        return fixed_files
    
    def generate_report(self, violations_by_file: Dict[str, List[TestViolation]]) -> str:
        """Generate a report of violations and fixes"""
        report_lines = []
        report_lines.append("# Test Size Violations Report")
        report_lines.append("")
        
        total_violations = sum(len(violations) for violations in violations_by_file.values())
        file_violations = sum(1 for violations in violations_by_file.values() 
                            for v in violations if v.violation_type == 'file_size')
        function_violations = total_violations - file_violations
        
        report_lines.append(f"**Total Violations:** {total_violations}")
        report_lines.append(f"- File size violations: {file_violations}")
        report_lines.append(f"- Function size violations: {function_violations}")
        report_lines.append("")
        
        # Top 20 worst violators
        sorted_files = sorted(violations_by_file.items(), 
                            key=lambda x: max(v.current_size for v in x[1]), 
                            reverse=True)
        
        report_lines.append("## Top 20 Worst Violators")
        report_lines.append("")
        
        for i, (file_path, violations) in enumerate(sorted_files[:20]):
            max_violation = max(violations, key=lambda v: v.current_size)
            report_lines.append(f"{i+1}. `{file_path}`")
            report_lines.append(f"   - Max violation: {max_violation.current_size} {max_violation.violation_type.replace('_', ' ')}")
            report_lines.append(f"   - Total violations: {len(violations)}")
            report_lines.append("")
        
        return '\n'.join(report_lines)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Auto-fix test size violations')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Perform dry run without making changes')
    parser.add_argument('--fix', action='store_true',
                       help='Actually perform fixes (overrides dry-run)')
    parser.add_argument('--max-files', type=int, default=20,
                       help='Maximum number of files to fix')
    parser.add_argument('--root-dir', default='.',
                       help='Root directory to scan')
    parser.add_argument('--report-only', action='store_true',
                       help='Only generate report, no fixes')
    
    args = parser.parse_args()
    
    # Override dry-run if --fix is specified
    dry_run = args.dry_run and not args.fix
    
    fixer = TestViolationFixer(args.root_dir)
    
    # Scan for violations
    violations_by_file = fixer.scan_violations()
    
    if not violations_by_file:
        logger.info("No test violations found!")
        return
    
    # Generate report
    report = fixer.generate_report(violations_by_file)
    
    # Save report
    report_file = Path(args.root_dir) / 'test_violations_report.md'
    with open(report_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Report saved to: {report_file}")
    print(report)
    
    if not args.report_only:
        # Fix violations
        fixed_files = fixer.fix_violations(violations_by_file, dry_run, args.max_files)
        
        if dry_run:
            logger.info(f"Dry run complete. Would create {len(fixed_files)} new files.")
        else:
            logger.info(f"Fixed violations, created {len(fixed_files)} new files.")

if __name__ == '__main__':
    main()