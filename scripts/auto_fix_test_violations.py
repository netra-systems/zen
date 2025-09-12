#!/usr/bin/env python3
"""
Test Size Violations Analysis and Reporting Script

!!!! CRITICAL WARNING !!!!
This script is designed ONLY for analysis and reporting of test size violations.
The auto-fix capabilities are DISABLED by default and should ONLY be used:
1. In dry-run mode for planning manual refactoring
2. With explicit human review before any actual changes
3. After backing up all affected files
4. With immediate test validation after any changes

NEVER use auto-fix in production code without thorough review!

Capabilities:
1. ANALYZE test files for size violations (SAFE)
2. REPORT violations and suggest improvements (SAFE)
3. DRY-RUN mode to preview potential changes (SAFE)
4. ACTUAL fixes require explicit opt-in and multiple confirmations (DANGEROUS)

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Code Quality Analysis and Reporting
- Value Impact: Identifies technical debt for manual remediation
- Strategic/Revenue Impact: Provides metrics for prioritizing refactoring efforts
"""

import ast
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        self.analysis_only = True  # SAFETY: Default to analysis only
        
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
    """DANGEROUS: Handles splitting large test files into smaller modules
    
    WARNING: This class can break test dependencies and should only be used
    for generating suggestions, not automatic fixes.
    """
    
    def __init__(self, analyzer: TestFileAnalyzer):
        self.analyzer = analyzer
        self.safety_mode = True  # SAFETY: Prevent actual file modifications by default
    
    def split_large_file(self, file_path: str, dry_run: bool = True, force_unsafe: bool = False) -> List[str]:
        """Split a large test file into smaller modules
        
        WARNING: This operation can break test dependencies!
        
        Args:
            file_path: Path to the test file
            dry_run: If True, only simulate changes (SAFE)
            force_unsafe: Must be True to allow actual file modifications (DANGEROUS)
        """
        if not dry_run and not force_unsafe:
            raise RuntimeError(
                "SAFETY: Actual file splitting is disabled by default. "
                "Use force_unsafe=True if you really want to modify files (NOT RECOMMENDED). "
                "Consider manual refactoring instead."
            )
        
        logger.warning(f"{'SIMULATING' if dry_run else 'ACTUALLY'} splitting large file: {file_path}")
        
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
    """DANGEROUS: Handles refactoring long functions into smaller pieces
    
    WARNING: Automatic function refactoring is highly unreliable and can break test logic.
    This should ONLY be used for generating refactoring suggestions.
    """
    
    def __init__(self):
        self.max_lines = 8
        self.enabled = False  # SAFETY: Disabled by default
    
    def refactor_long_function(self, file_path: str, function_info: FunctionInfo, dry_run: bool = True, force_unsafe: bool = False) -> str:
        """Generate refactoring suggestions for a long function
        
        WARNING: Automatic refactoring is NOT RECOMMENDED!
        """
        if not self.enabled:
            return f"Function refactoring is disabled. {function_info.name} has {function_info.line_count} lines and should be manually reviewed."
        
        if not dry_run and not force_unsafe:
            raise RuntimeError(
                "SAFETY: Automatic function refactoring is disabled. "
                "This operation is too dangerous for automatic execution. "
                "Please refactor manually."
            )
        
        logger.warning(f"SUGGESTION: Function {function_info.name} in {file_path} should be refactored manually")
        
        if dry_run:
            return f"SUGGESTION: Refactor {function_info.name} ({function_info.line_count} lines) manually"
        
        # Should never reach here without force_unsafe
        raise RuntimeError("Automatic function refactoring is not supported")
    
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

class TestViolationAnalyzer:
    """Main class that analyzes and reports test violations
    
    Primary purpose: Analysis and reporting
    Secondary purpose: Generate refactoring suggestions (dry-run only)
    
    WARNING: Auto-fix capabilities are DANGEROUS and should not be used in production!
    """
    
    def __init__(self, root_dir: str = '.', safe_mode: bool = True):
        self.root_dir = root_dir
        self.safe_mode = safe_mode  # SAFETY: Enable safe mode by default
        self.analyzer = TestFileAnalyzer()
        self.splitter = TestFileSplitter(self.analyzer)
        self.refactor = FunctionRefactor()
        self.validation_results = {}  # Track test validation results
        self.backup_dir = None  # For storing backups if fixes are applied
        
        if self.safe_mode:
            logger.info("SAFE MODE ENABLED: Only analysis and dry-run operations allowed")
        
    def scan_violations(self, validate_tests: bool = False) -> Dict[str, List[TestViolation]]:
        """Scan all test files for violations
        
        Args:
            validate_tests: If True, run tests to ensure they pass before suggesting fixes
        """
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
                
                # Validate test passes if requested
                if validate_tests:
                    self._validate_test_file(file_path)
            total_files += 1
        
        logger.info(f"Scanned {total_files} test files, found {total_violations} violations in {len(violations_by_file)} files")
        
        if validate_tests and self.validation_results:
            failing_tests = [f for f, passed in self.validation_results.items() if not passed]
            if failing_tests:
                logger.warning(f"WARNING: {len(failing_tests)} test files are already failing!")
                logger.warning("These files should be fixed manually before attempting any refactoring.")
        
        return violations_by_file
    
    def _validate_test_file(self, file_path: str) -> bool:
        """Validate that a test file passes before suggesting modifications"""
        try:
            # Run pytest on the specific file
            result = subprocess.run(
                ['python', '-m', 'pytest', file_path, '-xvs', '--tb=short'],
                capture_output=True,
                text=True,
                timeout=30
            )
            passed = result.returncode == 0
            self.validation_results[file_path] = passed
            
            if not passed:
                logger.warning(f"Test file {file_path} is already failing!")
            
            return passed
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Could not validate test file {file_path}: {e}")
            self.validation_results[file_path] = False
            return False
    
    def _create_backup(self, file_path: str) -> Optional[str]:
        """Create a backup of a file before modification"""
        if not self.backup_dir:
            self.backup_dir = Path(self.root_dir) / f".test_backups_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.backup_dir.mkdir(exist_ok=True)
            logger.info(f"Created backup directory: {self.backup_dir}")
        
        try:
            relative_path = Path(file_path).relative_to(self.root_dir)
            backup_path = self.backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backed up {file_path} to {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to backup {file_path}: {e}")
            return None
    
    def analyze_and_suggest_fixes(self, violations_by_file: Dict[str, List[TestViolation]], 
                                 dry_run: bool = True, max_files: int = 20, 
                                 force_unsafe: bool = False) -> List[str]:
        """Analyze violations and suggest fixes
        
        Args:
            violations_by_file: Dictionary of files with violations
            dry_run: If True, only simulate changes (SAFE, default)
            max_files: Maximum number of files to analyze
            force_unsafe: Required to be True for actual modifications (DANGEROUS)
        
        Returns:
            List of suggested or created files
        """
        if not dry_run:
            if self.safe_mode and not force_unsafe:
                raise RuntimeError(
                    "SAFETY: Cannot perform actual fixes in safe mode. "
                    "Use dry_run=True for suggestions or explicitly set safe_mode=False "
                    "and force_unsafe=True (NOT RECOMMENDED)."
                )
            
            if not force_unsafe:
                logger.error("Actual fixes require force_unsafe=True. Switching to dry-run mode.")
                dry_run = True
        
        action = "Analyzing and suggesting fixes for" if dry_run else "DANGEROUSLY fixing"
        logger.info(f"{action} violations (dry_run={dry_run}, max_files={max_files})...")
        
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
            
            # Check if test is passing before attempting fixes
            if not dry_run and file_path in self.validation_results:
                if not self.validation_results[file_path]:
                    logger.error(f"Skipping {file_path} - tests are already failing")
                    continue
            
            # Create backup if doing actual modifications
            if not dry_run and force_unsafe:
                backup_path = self._create_backup(file_path)
                if not backup_path:
                    logger.error(f"Failed to create backup for {file_path}, skipping")
                    continue
            
            # Suggest file splitting for size violations
            if file_size_violations:
                try:
                    new_files = self.splitter.split_large_file(file_path, dry_run, force_unsafe=force_unsafe)
                    fixed_files.extend(new_files)
                    action = "Would split" if dry_run else "DANGEROUSLY split"
                    logger.info(f"{action} {file_path} into {len(new_files)} files")
                    
                    # Validate after modification if not dry-run
                    if not dry_run and new_files:
                        for new_file in new_files:
                            if os.path.exists(new_file):
                                if not self._validate_test_file(new_file):
                                    logger.error(f"WARNING: New file {new_file} has failing tests!")
                except RuntimeError as e:
                    logger.error(f"Safety check prevented file splitting: {e}")
            
            # Suggest function refactoring for function size violations
            elif function_size_violations:
                for violation in function_size_violations:
                    logger.info(f"MANUAL ACTION REQUIRED - {file_path}: {violation.details}")
                    logger.info("  Suggestion: Extract helper methods or split test logic")
        
        return fixed_files
    
    def generate_report(self, violations_by_file: Dict[str, List[TestViolation]]) -> str:
        """Generate a report of violations and fixes"""
        report_lines = []
        report_lines.append("# Test Size Violations Report")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        report_lines.append("##  WARNING: [U+FE0F] WARNING")
        report_lines.append("This report identifies test files that violate size constraints.")
        report_lines.append("**IMPORTANT:** Manual refactoring is strongly recommended over automatic fixes.")
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
            test_status = ""
            if file_path in self.validation_results:
                test_status = "  PASS: " if self.validation_results[file_path] else "  FAIL:  (FAILING)"
            
            report_lines.append(f"{i+1}. `{file_path}`{test_status}")
            report_lines.append(f"   - Max violation: {max_violation.current_size} {max_violation.violation_type.replace('_', ' ')}")
            report_lines.append(f"   - Total violations: {len(violations)}")
            
            # Add refactoring suggestions
            if max_violation.violation_type == 'file_size':
                report_lines.append(f"   - **Suggestion:** Split into multiple focused test modules")
            else:
                report_lines.append(f"   - **Suggestion:** Extract helper methods or use fixtures")
            report_lines.append("")
        
        # Add validation summary if available
        if self.validation_results:
            report_lines.append("## Test Validation Status")
            passing = sum(1 for passed in self.validation_results.values() if passed)
            total = len(self.validation_results)
            report_lines.append(f"- Tests validated: {total}")
            report_lines.append(f"- Passing: {passing}")
            report_lines.append(f"- Failing: {total - passing}")
            if total - passing > 0:
                report_lines.append("")
                report_lines.append("** WARNING: [U+FE0F] WARNING:** Some tests are already failing. Fix these before refactoring!")
            report_lines.append("")
        
        return '\n'.join(report_lines)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze test size violations and generate improvement suggestions',
        epilog='WARNING: Auto-fix capabilities are DANGEROUS and disabled by default!'
    )
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Perform dry run without making changes (SAFE, default)')
    parser.add_argument('--force-unsafe-fix', action='store_true',
                       help='DANGEROUS: Actually perform fixes (NOT RECOMMENDED)')
    parser.add_argument('--confirm-unsafe', action='store_true',
                       help='DANGEROUS: Second confirmation required for unsafe operations')
    parser.add_argument('--max-files', type=int, default=20,
                       help='Maximum number of files to analyze')
    parser.add_argument('--root-dir', default='.',
                       help='Root directory to scan')
    parser.add_argument('--report-only', action='store_true', default=True,
                       help='Only generate report, no fixes (SAFE, default)')
    parser.add_argument('--disable-safe-mode', action='store_true',
                       help='DANGEROUS: Disable safe mode protections')
    parser.add_argument('--validate-tests', action='store_true',
                       help='Run tests to validate they pass before suggesting fixes')
    parser.add_argument('--backup-dir', type=str,
                       help='Directory for storing backups (auto-generated if not specified)')
    
    args = parser.parse_args()
    
    # Safety checks
    if args.force_unsafe_fix:
        if not args.confirm_unsafe:
            logger.error(
                "SAFETY: Unsafe operations require --confirm-unsafe flag. "
                "Please reconsider using manual refactoring instead."
            )
            sys.exit(1)
        
        logger.warning("!!! DANGEROUS MODE ENABLED !!!")
        logger.warning("Auto-fix operations can break your tests!")
        logger.warning("It is STRONGLY recommended to:")
        logger.warning("1. Back up all files first")
        logger.warning("2. Use dry-run mode to preview changes")
        logger.warning("3. Manually refactor instead of using auto-fix")
        
        response = input("\nAre you ABSOLUTELY SURE you want to proceed? Type 'YES I UNDERSTAND THE RISKS': ")
        if response != 'YES I UNDERSTAND THE RISKS':
            logger.info("Operation cancelled. Good choice!")
            sys.exit(0)
    
    # Determine operation mode
    dry_run = not (args.force_unsafe_fix and args.confirm_unsafe)
    safe_mode = not args.disable_safe_mode
    
    if not dry_run and safe_mode:
        logger.error("SAFETY: Cannot perform actual fixes with safe mode enabled")
        sys.exit(1)
    
    analyzer = TestViolationAnalyzer(args.root_dir, safe_mode=safe_mode)
    
    # Scan for violations
    violations_by_file = analyzer.scan_violations(validate_tests=args.validate_tests)
    
    if not violations_by_file:
        logger.info("No test violations found!")
        return
    
    # Generate report
    report = analyzer.generate_report(violations_by_file)
    
    # Save report
    report_file = Path(args.root_dir) / 'test_violations_report.md'
    with open(report_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Report saved to: {report_file}")
    print(report)
    
    if not args.report_only and args.force_unsafe_fix:
        # Analyze and suggest fixes
        force_unsafe = args.force_unsafe_fix and args.confirm_unsafe
        
        # Set backup directory if specified
        if args.backup_dir:
            analyzer.backup_dir = Path(args.backup_dir)
        
        suggested_files = analyzer.analyze_and_suggest_fixes(
            violations_by_file, 
            dry_run=dry_run, 
            max_files=args.max_files,
            force_unsafe=force_unsafe
        )
        
        if dry_run:
            logger.info(f"Analysis complete. Suggested creating {len(suggested_files)} new files.")
            logger.info("Recommendation: Manually refactor based on these suggestions.")
        else:
            logger.warning(f"DANGEROUS: Created {len(suggested_files)} new files.")
            logger.warning("CRITICAL: Run all tests immediately to verify nothing is broken!")
            
            if analyzer.backup_dir:
                logger.info(f"Backups stored in: {analyzer.backup_dir}")
                logger.info("To restore: cp -r {backup_dir}/* {root_dir}/")
    else:
        logger.info("Report-only mode. Use --force-unsafe-fix and --confirm-unsafe for actual changes (NOT RECOMMENDED)")
        logger.info("")
        logger.info("Recommended approach:")
        logger.info("1. Review the report above")
        logger.info("2. Manually refactor files with violations")
        logger.info("3. Use established patterns like fixtures and helper functions")
        logger.info("4. Run tests after each refactoring to ensure correctness")

if __name__ == '__main__':
    main()