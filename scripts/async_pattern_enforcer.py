#!/usr/bin/env python3
"""
Async Pattern Enforcer - Level 1 Immediate Technical Detection
CRITICAL: Prevents async/await type mismatches at commit time

Business Value: Protects $500K+ ARR by preventing Golden Path failures
Revenue Impact: Eliminates production async pattern violations
"""

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


@dataclass
class AsyncPatternViolation:
    """Structure for async pattern violations"""
    file_path: str
    violation_type: str
    line_number: int
    function_name: Optional[str] = None
    violation_code: str = ""
    message: str = ""
    fix_suggestion: str = ""
    severity: str = "ERROR"  # ERROR, WARNING, INFO


class AsyncPatternVisitor(ast.NodeVisitor):
    """AST visitor for detecting async pattern violations"""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.violations: List[AsyncPatternViolation] = []
        self.async_functions: Set[str] = set()
        self.sync_functions: Set[str] = set()
        self.current_function: Optional[str] = None
        self.current_function_is_async: bool = False
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit regular function definitions"""
        self._process_function(node, is_async=False)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions"""
        self._process_function(node, is_async=True)
        self.generic_visit(node)
    
    def _process_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], is_async: bool) -> None:
        """Process function definition for async patterns"""
        func_name = node.name
        prev_function = self.current_function
        prev_is_async = self.current_function_is_async
        
        self.current_function = func_name
        self.current_function_is_async = is_async
        
        if is_async:
            self.async_functions.add(func_name)
        else:
            self.sync_functions.add(func_name)
            
        # Check for async pattern violations in function signature
        self._check_function_signature_patterns(node, is_async)
        
        # Visit function body
        for child_node in ast.iter_child_nodes(node):
            if isinstance(child_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Handle nested functions
                continue
            self.visit(child_node)
        
        # Restore previous function context
        self.current_function = prev_function
        self.current_function_is_async = prev_is_async
    
    def visit_Await(self, node: ast.Await) -> None:
        """Visit await expressions"""
        if not self.current_function_is_async:
            # await used in non-async function
            violation = AsyncPatternViolation(
                file_path="",  # Will be set by caller
                violation_type="await_in_sync_function",
                line_number=node.lineno,
                function_name=self.current_function,
                violation_code=self._get_line_content(node.lineno),
                message=f"'await' used in non-async function '{self.current_function}'",
                fix_suggestion="Make function async or remove await keyword",
                severity="ERROR"
            )
            self.violations.append(violation)
        
        # Check if awaiting a sync function
        if isinstance(node.value, ast.Call):
            self._check_await_on_sync_call(node)
        
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls"""
        if self.current_function_is_async:
            # Check for missing await on async calls
            self._check_missing_await_on_async_call(node)
        
        # Check for common async pattern mistakes
        self._check_common_async_mistakes(node)
        
        self.generic_visit(node)
    
    def _check_function_signature_patterns(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], is_async: bool) -> None:
        """Check function signature for async pattern issues"""
        # Check return type annotation for async compatibility
        if hasattr(node, 'returns') and node.returns:
            return_annotation = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
            
            # Check for async return types on sync functions
            if not is_async and ('Coroutine' in return_annotation or 'Awaitable' in return_annotation):
                violation = AsyncPatternViolation(
                    file_path="",
                    violation_type="async_return_type_sync_function",
                    line_number=node.lineno,
                    function_name=node.name,
                    violation_code=self._get_line_content(node.lineno),
                    message=f"Sync function '{node.name}' has async return type annotation",
                    fix_suggestion="Make function async or change return type annotation",
                    severity="ERROR"
                )
                self.violations.append(violation)
            
            # Check for sync return types on async functions
            if is_async and not any(async_type in return_annotation 
                                   for async_type in ['Coroutine', 'Awaitable', 'AsyncGenerator']):
                # This might be OK (async functions can return sync values), so warning only
                violation = AsyncPatternViolation(
                    file_path="",
                    violation_type="sync_return_type_async_function",
                    line_number=node.lineno,
                    function_name=node.name,
                    violation_code=self._get_line_content(node.lineno),
                    message=f"Async function '{node.name}' has sync return type annotation",
                    fix_suggestion="Verify return type is correct for async function",
                    severity="WARNING"
                )
                self.violations.append(violation)
    
    def _check_await_on_sync_call(self, await_node: ast.Await) -> None:
        """Check if awaiting a known sync function call"""
        if isinstance(await_node.value, ast.Call):
            call_node = await_node.value
            if isinstance(call_node.func, ast.Name):
                func_name = call_node.func.id
                if func_name in self.sync_functions:
                    violation = AsyncPatternViolation(
                        file_path="",
                        violation_type="await_on_sync_function",
                        line_number=await_node.lineno,
                        function_name=self.current_function,
                        violation_code=self._get_line_content(await_node.lineno),
                        message=f"'await' used on sync function call '{func_name}'",
                        fix_suggestion=f"Remove 'await' or make '{func_name}' async",
                        severity="ERROR"
                    )
                    self.violations.append(violation)
    
    def _check_missing_await_on_async_call(self, call_node: ast.Call) -> None:
        """Check for missing await on async function calls"""
        if isinstance(call_node.func, ast.Name):
            func_name = call_node.func.id
            if func_name in self.async_functions:
                # Check if this call is already awaited
                parent_nodes = []
                # This is a simplified check - in a full implementation,
                # we'd need to track the AST parent chain
                violation = AsyncPatternViolation(
                    file_path="",
                    violation_type="missing_await_on_async_function",
                    line_number=call_node.lineno,
                    function_name=self.current_function,
                    violation_code=self._get_line_content(call_node.lineno),
                    message=f"Missing 'await' on async function call '{func_name}'",
                    fix_suggestion=f"Add 'await' before '{func_name}' call",
                    severity="WARNING"  # Warning because detection might have false positives
                )
                self.violations.append(violation)
    
    def _check_common_async_mistakes(self, call_node: ast.Call) -> None:
        """Check for common async pattern mistakes"""
        if isinstance(call_node.func, ast.Attribute):
            attr_name = call_node.func.attr
            
            # Check for sync methods on async objects
            sync_methods_on_async_objects = [
                'close',  # Should be aclose() 
                'read',   # Should be aread()
                'write'   # Should be awrite()
            ]
            
            if attr_name in sync_methods_on_async_objects:
                violation = AsyncPatternViolation(
                    file_path="",
                    violation_type="sync_method_on_async_object",
                    line_number=call_node.lineno,
                    function_name=self.current_function,
                    violation_code=self._get_line_content(call_node.lineno),
                    message=f"Using sync method '{attr_name}' that might have async equivalent",
                    fix_suggestion=f"Check if 'a{attr_name}()' or async equivalent is available",
                    severity="INFO"
                )
                self.violations.append(violation)
    
    def _get_line_content(self, line_number: int) -> str:
        """Get the content of a specific line"""
        if 1 <= line_number <= len(self.source_lines):
            return self.source_lines[line_number - 1].strip()
        return ""


class AsyncPatternEnforcer:
    """Main enforcer class for async pattern validation"""
    
    def __init__(self):
        self.total_files_checked = 0
        self.total_violations_found = 0
    
    def check_file(self, file_path: Path) -> List[AsyncPatternViolation]:
        """Check a single Python file for async pattern violations"""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
                source_lines = source_code.splitlines()
            
            # Parse AST
            try:
                tree = ast.parse(source_code)
            except SyntaxError as e:
                # File has syntax errors, skip async pattern checking
                violation = AsyncPatternViolation(
                    file_path=str(file_path),
                    violation_type="syntax_error",
                    line_number=e.lineno or 1,
                    violation_code="",
                    message=f"Syntax error prevents async pattern checking: {e}",
                    fix_suggestion="Fix Python syntax errors first",
                    severity="ERROR"
                )
                return [violation]
            
            # Run async pattern analysis
            visitor = AsyncPatternVisitor(source_lines)
            visitor.visit(tree)
            
            # Set file path for all violations
            for violation in visitor.violations:
                violation.file_path = str(file_path)
            
            violations.extend(visitor.violations)
            
            # Additional regex-based checks for patterns AST might miss
            regex_violations = self._regex_based_checks(file_path, source_code, source_lines)
            violations.extend(regex_violations)
            
            self.total_files_checked += 1
            self.total_violations_found += len(violations)
            
        except Exception as e:
            violation = AsyncPatternViolation(
                file_path=str(file_path),
                violation_type="file_processing_error",
                line_number=1,
                violation_code="",
                message=f"Error processing file: {e}",
                fix_suggestion="Check file permissions and encoding",
                severity="ERROR"
            )
            violations.append(violation)
        
        return violations
    
    def _regex_based_checks(self, file_path: Path, source_code: str, source_lines: List[str]) -> List[AsyncPatternViolation]:
        """Additional regex-based pattern checks"""
        violations = []
        
        # Pattern 1: await followed by non-function call (the original bug pattern)
        await_non_function_pattern = re.compile(r'await\s+(?![\w_]+\s*\()', re.MULTILINE)
        for match in await_non_function_pattern.finditer(source_code):
            line_num = source_code[:match.start()].count('\n') + 1
            violation = AsyncPatternViolation(
                file_path=str(file_path),
                violation_type="await_non_function_call",
                line_number=line_num,
                violation_code=source_lines[line_num - 1].strip() if line_num <= len(source_lines) else "",
                message="'await' used on non-function call (likely type mismatch)",
                fix_suggestion="Remove 'await' or ensure target is an async function call",
                severity="ERROR"
            )
            violations.append(violation)
        
        # Pattern 2: Common async antipatterns
        antipatterns = [
            (r'await\s+time\.sleep\s*\(', "Use 'asyncio.sleep()' instead of 'time.sleep()' in async context"),
            (r'await\s+requests\.[get|post|put|delete]', "Use 'aiohttp' or 'httpx' instead of 'requests' in async context"),
            (r'await\s+open\s*\(', "Use 'aiofiles' or async file operations instead of sync 'open()' in async context")
        ]
        
        for pattern, suggestion in antipatterns:
            for match in re.finditer(pattern, source_code, re.IGNORECASE):
                line_num = source_code[:match.start()].count('\n') + 1
                violation = AsyncPatternViolation(
                    file_path=str(file_path),
                    violation_type="async_antipattern",
                    line_number=line_num,
                    violation_code=source_lines[line_num - 1].strip() if line_num <= len(source_lines) else "",
                    message="Async antipattern detected",
                    fix_suggestion=suggestion,
                    severity="WARNING"
                )
                violations.append(violation)
        
        return violations
    
    def check_multiple_files(self, file_paths: List[Path]) -> List[AsyncPatternViolation]:
        """Check multiple files for async pattern violations"""
        all_violations = []
        
        for file_path in file_paths:
            if file_path.suffix == '.py' and file_path.exists():
                violations = self.check_file(file_path)
                all_violations.extend(violations)
        
        return all_violations
    
    def check_codebase(self, root_path: Path = None) -> List[AsyncPatternViolation]:
        """Check entire codebase for async pattern violations"""
        if root_path is None:
            root_path = Path.cwd()
        
        python_files = []
        
        # Target directories for checking
        target_dirs = [
            'netra_backend',
            'auth_service', 
            'test_framework',
            'tests',
            'scripts'
        ]
        
        for target_dir in target_dirs:
            dir_path = root_path / target_dir
            if dir_path.exists():
                python_files.extend(dir_path.rglob('*.py'))
        
        return self.check_multiple_files(python_files)


class AsyncPatternReporter:
    """Reporter for async pattern violations"""
    
    @staticmethod
    def generate_console_report(violations: List[AsyncPatternViolation]) -> str:
        """Generate human-readable console report"""
        if not violations:
            return "✅ No async pattern violations detected"
        
        report_lines = []
        report_lines.append("🔴 ASYNC PATTERN VIOLATIONS DETECTED")
        report_lines.append("=" * 60)
        
        # Group by severity
        errors = [v for v in violations if v.severity == "ERROR"]
        warnings = [v for v in violations if v.severity == "WARNING"] 
        infos = [v for v in violations if v.severity == "INFO"]
        
        for severity, violations_list in [("ERRORS", errors), ("WARNINGS", warnings), ("INFO", infos)]:
            if violations_list:
                report_lines.append(f"\n{severity} ({len(violations_list)}):")
                for violation in violations_list:
                    report_lines.append(f"  📁 {violation.file_path}:{violation.line_number}")
                    if violation.function_name:
                        report_lines.append(f"     Function: {violation.function_name}")
                    report_lines.append(f"     Code: {violation.violation_code}")
                    report_lines.append(f"     Issue: {violation.message}")
                    report_lines.append(f"     Fix: {violation.fix_suggestion}")
                    report_lines.append("")
        
        report_lines.append(f"Total violations: {len(violations)} (Errors: {len(errors)}, Warnings: {len(warnings)}, Info: {len(infos)})")
        
        if errors:
            report_lines.append("\n🚨 COMMIT BLOCKED: Fix all ERROR-level violations before committing")
        elif warnings:
            report_lines.append("\n⚠️  Consider fixing warnings to improve code quality")
        
        return "\n".join(report_lines)
    
    @staticmethod
    def generate_json_report(violations: List[AsyncPatternViolation]) -> str:
        """Generate JSON report for CI/CD integration"""
        violation_data = [asdict(v) for v in violations]
        
        errors = len([v for v in violations if v.severity == "ERROR"])
        warnings = len([v for v in violations if v.severity == "WARNING"])
        infos = len([v for v in violations if v.severity == "INFO"])
        
        return json.dumps({
            'total_violations': len(violations),
            'errors': errors,
            'warnings': warnings,
            'infos': infos,
            'violations': violation_data,
            'compliance_status': 'PASS' if errors == 0 else 'FAIL',
            'commit_allowed': errors == 0
        }, indent=2)


def collect_target_files(specified_files: List[str]) -> List[Path]:
    """Collect Python files to check"""
    if specified_files:
        return [Path(f) for f in specified_files if Path(f).exists() and Path(f).suffix == '.py']
    
    # Auto-discover Python files
    current_dir = Path.cwd()
    target_dirs = ['netra_backend', 'auth_service', 'test_framework', 'tests', 'scripts']
    
    files = []
    for target_dir in target_dirs:
        dir_path = current_dir / target_dir
        if dir_path.exists():
            files.extend(dir_path.rglob('*.py'))
    
    return files


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Async Pattern Enforcer - Prevents async/await type mismatches"
    )
    
    # Mode options
    parser.add_argument('--precommit-mode', action='store_true',
                       help='Run in pre-commit mode (strict error checking)')
    parser.add_argument('--ci-mode', action='store_true',
                       help='Run in CI mode (JSON output, strict checking)')
    parser.add_argument('--dev-mode', action='store_true',
                       help='Run in development mode (warnings allowed)')
    
    # Check options
    parser.add_argument('--check-codebase', action='store_true',
                       help='Check entire codebase')
    parser.add_argument('--install-precommit', action='store_true',
                       help='Install pre-commit hook configuration')
    
    # Severity filtering
    parser.add_argument('--errors-only', action='store_true',
                       help='Only report ERROR-level violations')
    parser.add_argument('--include-warnings', action='store_true',
                       help='Include WARNING-level violations in output')
    parser.add_argument('--include-info', action='store_true',
                       help='Include INFO-level violations in output')
    
    # Output options  
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--fail-fast', action='store_true',
                       help='Exit on first ERROR violation')
    
    # File selection
    parser.add_argument('files', nargs='*',
                       help='Python files to check (if not provided, checks target directories)')
    
    return parser


def install_precommit_hook() -> None:
    """Install pre-commit hook configuration"""
    precommit_config_path = Path('.pre-commit-config.yaml')
    
    hook_config = """
  # ASYNC PATTERN VALIDATION (Level 1 Protection)
  - id: async-await-pattern-validator
    name: Async/Await Pattern Validator  
    entry: python scripts/async_pattern_enforcer.py --precommit-mode
    language: system
    files: '\\.py$'
    stages: [commit]
    description: 'CRITICAL: Detects await/non-await mismatches and async pattern violations'
"""
    
    if precommit_config_path.exists():
        with open(precommit_config_path, 'r') as f:
            current_config = f.read()
        
        if 'async-await-pattern-validator' not in current_config:
            # Find the repos section and add our hook
            if 'repos:' in current_config:
                # Add to existing local repo section or create one
                if '- repo: local' in current_config:
                    print("⚠️  Please manually add the async pattern validator hook to your existing 'local' repo section in .pre-commit-config.yaml")
                    print("Hook configuration to add:")
                    print(hook_config)
                else:
                    # Add new local repo section
                    new_config = current_config + f"""
  - repo: local
    hooks:{hook_config}"""
                    with open(precommit_config_path, 'w') as f:
                        f.write(new_config)
                    print("✅ Added async pattern validator hook to .pre-commit-config.yaml")
            else:
                print("⚠️  .pre-commit-config.yaml exists but has unexpected format")
                print("Please manually add the async pattern validator hook")
        else:
            print("✅ Async pattern validator hook already configured")
    else:
        # Create new pre-commit config
        new_config = f"""repos:
  - repo: local
    hooks:{hook_config}"""
        with open(precommit_config_path, 'w') as f:
            f.write(new_config)
        print("✅ Created .pre-commit-config.yaml with async pattern validator hook")


def main() -> int:
    """Main enforcement orchestrator"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle special actions
    if args.install_precommit:
        install_precommit_hook()
        return 0
    
    # Collect files to check
    if args.check_codebase:
        enforcer = AsyncPatternEnforcer()
        violations = enforcer.check_codebase()
    else:
        target_files = collect_target_files(args.files)
        if not target_files:
            print("No Python files to check")
            return 0
        
        enforcer = AsyncPatternEnforcer()
        violations = enforcer.check_multiple_files(target_files)
    
    # Filter violations by severity
    filtered_violations = violations
    if args.errors_only:
        filtered_violations = [v for v in violations if v.severity == "ERROR"]
    elif not args.include_warnings and not args.include_info:
        # Default: include errors and warnings, exclude info
        filtered_violations = [v for v in violations if v.severity in ["ERROR", "WARNING"]]
    elif args.include_info and not args.include_warnings:
        # Include errors and info only
        filtered_violations = [v for v in violations if v.severity in ["ERROR", "INFO"]]
    
    # Generate report
    if args.json or args.ci_mode:
        print(AsyncPatternReporter.generate_json_report(filtered_violations))
    else:
        print(AsyncPatternReporter.generate_console_report(filtered_violations))
    
    # Check for early exit
    if args.fail_fast:
        error_violations = [v for v in filtered_violations if v.severity == "ERROR"]
        if error_violations:
            return 1
    
    # Determine exit code based on mode
    error_count = len([v for v in filtered_violations if v.severity == "ERROR"])
    
    if args.precommit_mode or args.ci_mode:
        # Strict modes: fail on any errors
        return 1 if error_count > 0 else 0
    else:
        # Development mode: always succeed but report issues
        return 0


if __name__ == "__main__":
    sys.exit(main())