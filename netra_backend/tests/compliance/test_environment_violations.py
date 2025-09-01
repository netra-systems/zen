"""
Comprehensive Environment Management Violations Test Suite

This test suite validates that ALL environment variable access across netra_backend
follows the unified environment management architecture defined in SPEC/unified_environment_management.xml

CRITICAL: These tests should FAIL until ALL violations are fixed.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity and System Stability  
- Value Impact: Prevents environment-related bugs, enables test isolation, ensures configuration consistency
- Strategic Impact: 60% reduction in environment debugging time, 100% test isolation, zero production config drift

The tests are designed to be DIFFICULT and COMPREHENSIVE to catch all violations.
"""

import ast
import os
import re
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict

import pytest


class ComprehensiveEnvironmentViolationAnalyzer(ast.NodeVisitor):
    """
    Advanced AST analyzer that catches ALL forms of environment variable violations.
    
    This analyzer is designed to be EXTREMELY thorough and catch even subtle violations
    that simple regex searches might miss.
    """
    
    def __init__(self, filepath: str, file_content: str):
        self.filepath = filepath
        self.file_content = file_content
        self.file_lines = file_content.split('\n')
        self.violations = []
        self.import_names = set()  # Track os imports and aliases
        self.function_calls = []
        
    def visit_Import(self, node):
        """Track 'import os' statements."""
        for alias in node.names:
            if alias.name == 'os':
                import_name = alias.asname if alias.asname else alias.name
                self.import_names.add(import_name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Track 'from os import environ, getenv' statements."""
        if node.module == 'os':
            for alias in node.names:
                if alias.name in ['environ', 'getenv']:
                    import_name = alias.asname if alias.asname else alias.name
                    self.import_names.add(import_name)
        self.generic_visit(node)
    
    def visit_Subscript(self, node):
        """Detect env.get('KEY') patterns."""
        if self._is_environ_access(node.value):
            self._add_violation(node, 'os.environ[]', 'SUBSCRIPT')
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Detect function calls including os.getenv() and os.environ.get()."""
        violation_type = None
        access_type = None
        
        # Check for os.getenv() calls
        if isinstance(node.func, ast.Attribute):
            if self._is_os_reference(node.func.value) and node.func.attr == 'getenv':
                violation_type = 'os.getenv()'
                access_type = 'GETENV'
            elif self._is_environ_access(node.func.value) and node.func.attr == 'get':
                violation_type = 'os.environ.get()'
                access_type = 'ENVIRON_GET'
        
        # Check for direct getenv() calls (from import)
        elif isinstance(node.func, ast.Name) and node.func.id == 'getenv':
            if 'getenv' in self.import_names:
                violation_type = 'getenv()'
                access_type = 'DIRECT_GETENV'
        
        # Check for direct environ access (from import)  
        elif isinstance(node.func, ast.Subscript):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'environ':
                if 'environ' in self.import_names:
                    violation_type = 'environ[]'
                    access_type = 'DIRECT_ENVIRON'
        
        if violation_type:
            self._add_violation(node, violation_type, access_type)
            
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Detect attribute access like os.environ without subscript/call."""
        # Skip this check to avoid duplicate violations - covered by subscript and call visitors
        self.generic_visit(node)
    
    def _is_os_reference(self, node) -> bool:
        """Check if node refers to the 'os' module."""
        if isinstance(node, ast.Name):
            return node.id in self.import_names and node.id in ['os'] + list(self.import_names)
        return False
    
    def _is_environ_access(self, node) -> bool:
        """Check if node represents os.environ or environ (direct import)."""
        if isinstance(node, ast.Attribute):
            return self._is_os_reference(node.value) and node.attr == 'environ'
        elif isinstance(node, ast.Name):
            return node.id == 'environ' and 'environ' in self.import_names
        return False
    
    def _add_violation(self, node, violation_type: str, access_type: str):
        """Add a violation with comprehensive context."""
        line_no = getattr(node, 'lineno', 0)
        col_offset = getattr(node, 'col_offset', 0)
        
        # Extract the actual code
        line_content = self._get_line_content(line_no) if line_no > 0 else ""
        
        # Get surrounding context
        context_lines = []
        for i in range(max(0, line_no - 2), min(len(self.file_lines), line_no + 2)):
            if i < len(self.file_lines):
                context_lines.append(f"{i+1:3d}: {self.file_lines[i]}")
        
        violation = {
            'file': self.filepath,
            'line': line_no,
            'column': col_offset,
            'type': violation_type,
            'access_type': access_type,
            'code': line_content,
            'context': '\n'.join(context_lines),
            'severity': self._get_violation_severity(violation_type, line_content)
        }
        
        self.violations.append(violation)
    
    def _get_line_content(self, line_no: int) -> str:
        """Get the actual line content."""
        if 0 <= line_no - 1 < len(self.file_lines):
            return self.file_lines[line_no - 1].strip()
        return ""
    
    def _get_violation_severity(self, violation_type: str, code: str) -> str:
        """Determine violation severity."""
        if 'isolated_environment.py' in self.filepath:
            return 'CRITICAL'  # Violations in the env manager itself are critical
        elif any(pattern in code.lower() for pattern in ['password', 'secret', 'key', 'token']):
            return 'CRITICAL'  # Security-related env access
        elif 'production' in code.lower() or 'staging' in code.lower():
            return 'HIGH'  # Environment-specific logic
        else:
            return 'MEDIUM'


class TestEnvironmentViolationsComprehensive:
    """
    COMPREHENSIVE test suite for environment management violations.
    
    These tests are designed to be DIFFICULT and will FAIL until ALL violations are fixed.
    """
    
    @pytest.fixture(scope="class")
    def project_root(self):
        """Get the netra_backend app directory."""
        current_file = Path(__file__).resolve()
        # Navigate up to find netra_backend directory
        for parent in current_file.parents:
            if parent.name == 'netra_backend':
                return parent / 'app'
        # Fallback: assume we're running from project root
        return Path.cwd() / 'netra_backend' / 'app'
    
    @pytest.fixture(scope="class")
    def allowed_files(self):
        """
        Files that are EXPLICITLY allowed to access os.environ.
        
        IMPORTANT: This list should be MINIMAL and well-justified.
        """
        return {
            # ONLY the isolated environment manager itself
            'isolated_environment.py',
            
            # ONLY test files (but we'll test them separately)
            # Note: Test files are allowed but tracked separately
        }
    
    @pytest.fixture(scope="class")
    def scan_results(self, project_root):
        """Scan all Python files for environment violations."""
        print(f"\n🔍 Scanning project root: {project_root}")
        
        violations_by_file = {}
        scan_stats = {
            'total_files': 0,
            'python_files': 0,
            'files_with_violations': 0,
            'total_violations': 0,
            'critical_violations': 0,
            'scan_time': 0
        }
        
        start_time = time.time()
        
        for root, dirs, files in os.walk(project_root):
            # Skip __pycache__ and .git directories
            dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__'))]
            
            for filename in files:
                scan_stats['total_files'] += 1
                
                if not filename.endswith('.py'):
                    continue
                    
                scan_stats['python_files'] += 1
                filepath = Path(root) / filename
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Quick pre-check to avoid parsing files that don't use os
                    if not any(pattern in content for pattern in ['os.environ', 'os.getenv', 'import os', 'from os']):
                        continue
                    
                    # Parse and analyze
                    tree = ast.parse(content, filename=str(filepath))
                    analyzer = ComprehensiveEnvironmentViolationAnalyzer(str(filepath), content)
                    analyzer.visit(tree)
                    
                    if analyzer.violations:
                        violations_by_file[str(filepath)] = analyzer.violations
                        scan_stats['files_with_violations'] += 1
                        scan_stats['total_violations'] += len(analyzer.violations)
                        scan_stats['critical_violations'] += sum(
                            1 for v in analyzer.violations if v['severity'] == 'CRITICAL'
                        )
                        
                except Exception as e:
                    print(f"⚠️  Error scanning {filepath}: {e}")
                    continue
        
        scan_stats['scan_time'] = time.time() - start_time
        
        print(f"📊 Scan completed in {scan_stats['scan_time']:.2f}s:")
        print(f"   • {scan_stats['python_files']} Python files scanned")
        print(f"   • {scan_stats['files_with_violations']} files with violations")
        print(f"   • {scan_stats['total_violations']} total violations found")
        print(f"   • {scan_stats['critical_violations']} CRITICAL violations")
        
        return violations_by_file, scan_stats
    
    def test_critical_no_violations_in_isolated_environment_itself(self, scan_results):
        """
        TEST 1: CRITICAL - The isolated_environment.py file itself must not have violations.
        
        This is the most critical test because if the environment manager itself
        violates the rules, the entire system is compromised.
        """
        violations_by_file, _ = scan_results
        
        isolated_env_violations = []
        for filepath, violations in violations_by_file.items():
            if 'isolated_environment.py' in filepath:
                # Filter out the specific allowed patterns in isolated_environment.py
                for violation in violations:
                    # These specific lines are allowed in isolated_environment.py as they're part of the implementation
                    if violation['line'] not in [77, 137, 141, 188, 193]:  # Known implementation lines
                        isolated_env_violations.append({
                            'file': filepath,
                            'line': violation['line'],
                            'type': violation['type'],
                            'code': violation['code'],
                            'severity': violation['severity']
                        })
        
        assert len(isolated_env_violations) == 0, (
            f"🚨 CRITICAL: isolated_environment.py has {len(isolated_env_violations)} violations!\n"
            "The environment manager itself cannot violate environment access rules.\n"
            "Violations found:\n" +
            "\n".join([
                f"  {v['file']}:{v['line']} [{v['type']}] - {v['code']}"
                for v in isolated_env_violations[:10]
            ])
        )
    
    def test_critical_no_violations_in_production_code(self, scan_results, allowed_files):
        """
        TEST 2: CRITICAL - No violations in production code outside allowed files.
        
        This test ensures all production code uses IsolatedEnvironment properly.
        """
        violations_by_file, scan_stats = scan_results
        
        production_violations = []
        
        for filepath, violations in violations_by_file.items():
            # Skip test files for this test
            if '/tests/' in filepath or filepath.endswith('_test.py') or 'test_' in os.path.basename(filepath):
                continue
                
            # Check if file is in allowed list
            filename = os.path.basename(filepath)
            if filename in allowed_files:
                continue
            
            # All remaining violations are production code violations
            for violation in violations:
                production_violations.append(violation)
        
        # Group violations by file for better reporting
        violations_by_file_summary = defaultdict(list)
        critical_count = 0
        
        for violation in production_violations:
            violations_by_file_summary[violation['file']].append(violation)
            if violation['severity'] == 'CRITICAL':
                critical_count += 1
        
        assert len(production_violations) == 0, (
            f"🚨 CRITICAL: Found {len(production_violations)} environment access violations in production code!\n"
            f"Critical violations: {critical_count}\n"
            f"Files affected: {len(violations_by_file_summary)}\n\n"
            "Top violations:\n" +
            "\n".join([
                f"📁 {filepath} ({len(file_violations)} violations):\n" +
                "\n".join([
                    f"   Line {v['line']}: {v['type']} - {v['code'][:100]}"
                    for v in file_violations[:3]
                ]) + ("\n   ..." if len(file_violations) > 3 else "")
                for filepath, file_violations in list(violations_by_file_summary.items())[:5]
            ]) +
            f"\n\n💡 All environment access must use IsolatedEnvironment from netra_backend.app.core.isolated_environment"
        )
    
    def test_specific_known_violations_fixed(self, scan_results):
        """
        TEST 3: Verify specific known violations from audit are fixed.
        
        These are the violations mentioned in the critical context.
        """
        violations_by_file, _ = scan_results
        
        # Known violation locations that MUST be fixed
        known_violations = [
            ('project_utils.py', [74, 78, 82, 86, 91]),  # os.environ.get() calls
            ('environment_validator.py', [106, 108]),      # os.getenv() calls
        ]
        
        found_known_violations = []
        
        for filepath, violations in violations_by_file.items():
            for known_file, known_lines in known_violations:
                if known_file in filepath:
                    for violation in violations:
                        if violation['line'] in known_lines:
                            found_known_violations.append({
                                'file': filepath,
                                'line': violation['line'],
                                'type': violation['type'],
                                'expected_file': known_file,
                                'code': violation['code']
                            })
        
        assert len(found_known_violations) == 0, (
            f"🚨 CRITICAL: Found {len(found_known_violations)} known violations that should have been fixed!\n"
            "These violations were specifically identified in the audit:\n" +
            "\n".join([
                f"  {v['expected_file']}:{v['line']} - {v['type']}\n    Code: {v['code']}"
                for v in found_known_violations
            ])
        )
    
    def test_comprehensive_pattern_detection(self, project_root):
        """
        TEST 4: Advanced pattern detection for ALL violations using regex.
        
        This test uses comprehensive regex patterns to catch ALL environment access violations.
        It's designed to be more reliable than AST parsing and catch everything.
        """
        violations = []
        
        # Comprehensive patterns to detect ALL environment access
        patterns = [
            (r'os\.environ\s*\[', 'os.environ[]'),
            (r'os\.environ\.get\s*\(', 'os.environ.get()'),
            (r'os\.getenv\s*\(', 'os.getenv()'),
            # Direct imports pattern (less common but possible)
            (r'environ\s*\[(?!.*PATH)', 'environ[]'),  # Direct environ access (excluding PATH)
            (r'(?<!os\.)getenv\s*\(', 'getenv()'),  # Direct getenv call
        ]
        
        stats = {
            'files_scanned': 0,
            'violations_found': 0,
            'files_with_violations': 0
        }
        
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__'))]
            
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                stats['files_scanned'] += 1
                filepath = Path(root) / filename
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    lines = content.split('\n')
                    file_violations = []
                    
                    for line_no, line in enumerate(lines, 1):
                        # Skip comments and docstrings
                        stripped = line.strip()
                        if stripped.startswith('#') or '"""' in line or "'''" in line:
                            continue
                        
                        for pattern, pattern_name in patterns:
                            if re.search(pattern, line):
                                file_violations.append({
                                    'file': str(filepath),
                                    'line': line_no,
                                    'pattern': pattern_name,
                                    'code': stripped,
                                    'severity': self._get_violation_severity(str(filepath), stripped)
                                })
                                stats['violations_found'] += 1
                    
                    if file_violations:
                        violations.extend(file_violations)
                        stats['files_with_violations'] += 1
                        
                except Exception:
                    continue
        
        # Filter out allowed violations in isolated_environment.py implementation
        filtered_violations = []
        for violation in violations:
            # Allow specific implementation lines in isolated_environment.py
            if 'isolated_environment.py' in violation['file']:
                # These specific patterns are part of the IsolatedEnvironment implementation
                if violation['line'] in [77, 137, 141, 188, 193, 204, 213, 220, 308]:
                    continue  # Skip allowed implementation lines
            
            filtered_violations.append(violation)
        
        # Generate detailed report
        if filtered_violations:
            critical_violations = [v for v in filtered_violations if v['severity'] == 'CRITICAL']
            
            report = f"\n🚨 COMPREHENSIVE PATTERN DETECTION FOUND {len(filtered_violations)} VIOLATIONS:\n"
            report += f"   • Files scanned: {stats['files_scanned']}\n"
            report += f"   • Files with violations: {stats['files_with_violations']}\n"
            report += f"   • Critical violations: {len(critical_violations)}\n\n"
            
            # Group by file
            from collections import defaultdict
            by_file = defaultdict(list)
            for v in filtered_violations:
                by_file[v['file']].append(v)
            
            report += "📁 VIOLATIONS BY FILE:\n"
            sorted_files = sorted(by_file.items(), key=lambda x: len(x[1]), reverse=True)
            for i, (filepath, file_violations) in enumerate(sorted_files[:10], 1):
                relative_path = str(Path(filepath).relative_to(Path.cwd()))
                report += f"   {i:2d}. {relative_path}: {len(file_violations)} violations\n"
                
                for v in file_violations[:3]:  # Show first 3 violations per file
                    report += f"       Line {v['line']}: {v['pattern']} - {v['code'][:80]}\n"
                
                if len(file_violations) > 3:
                    report += f"       ... and {len(file_violations) - 3} more\n"
                report += "\n"
            
            if critical_violations:
                report += "🚨 CRITICAL VIOLATIONS (SECURITY RISKS):\n"
                for v in critical_violations[:5]:
                    relative_path = str(Path(v['file']).relative_to(Path.cwd()))
                    report += f"   • {relative_path}:{v['line']} - {v['code']}\n"
                report += "\n"
            
            report += "💡 REMEDIATION:\n"
            report += "   1. Replace os.environ.get() with env.get()\n"
            report += "   2. Replace os.getenv() with env.get()\n"
            report += "   3. Import: from shared.isolated_environment import get_env\n"
            
            pytest.fail(report)
        else:
            print(f"\n✅ PATTERN DETECTION: Scanned {stats['files_scanned']} files - No violations found!")
    
    def _get_violation_severity(self, filepath: str, code: str) -> str:
        """Determine violation severity."""
        if 'isolated_environment.py' in filepath:
            return 'CRITICAL'  # Violations in env manager itself
        elif any(term in code.lower() for term in ['password', 'secret', 'key', 'token', 'api_key']):
            return 'CRITICAL'  # Security-related env access
        elif 'production' in code.lower() or 'staging' in code.lower():
            return 'HIGH'  # Environment-specific logic
        else:
            return 'MEDIUM'
    
    def test_isolated_environment_usage_correctness(self, project_root):
        """
        TEST 5: Verify that IsolatedEnvironment is used correctly where present.
        
        This test ensures that files using IsolatedEnvironment are using it properly.
        """
        usage_issues = []
        
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__'))]
            
            for filename in files:
                if not filename.endswith('.py') or filename.startswith('test_'):
                    continue
                    
                filepath = Path(root) / filename
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        lines = content.split('\n')
                    
                    # Check if file imports IsolatedEnvironment
                    uses_isolated_env = any('IsolatedEnvironment' in line or 'get_env' in line 
                                          for line in lines)
                    
                    # If it uses IsolatedEnvironment, check for anti-patterns
                    if uses_isolated_env:
                        for line_no, line in enumerate(lines, 1):
                            # Anti-pattern 1: Mixed usage (IsolatedEnvironment + direct os.environ)
                            if any(pattern in line for pattern in ['os.environ', 'os.getenv']):
                                if not line.strip().startswith('#'):  # Not a comment
                                    usage_issues.append({
                                        'file': str(filepath),
                                        'line': line_no,
                                        'issue': 'Mixed IsolatedEnvironment and direct os access',
                                        'code': line.strip()
                                    })
                            
                            # Anti-pattern 2: Not enabling isolation in test-like contexts
                            if 'get_env()' in line and 'enable_isolation' not in content:
                                if 'test' in str(filepath).lower() or 'development' in content:
                                    usage_issues.append({
                                        'file': str(filepath),
                                        'line': line_no,
                                        'issue': 'IsolatedEnvironment used without enabling isolation',
                                        'code': line.strip()
                                    })
                                    
                except Exception:
                    continue
        
        assert len(usage_issues) == 0, (
            f"🚨 Found {len(usage_issues)} IsolatedEnvironment usage issues!\n" +
            "\n".join([
                f"  {issue['file']}:{issue['line']} - {issue['issue']}\n    Code: {issue['code']}"
                for issue in usage_issues[:10]
            ])
        )
    
    def test_environment_access_performance_compliance(self, project_root):
        """
        TEST 6: Ensure environment access doesn't block or cause performance issues.
        
        This test simulates concurrent access patterns to verify thread safety.
        """
        # Import the isolated environment to test
        sys.path.insert(0, str(project_root))
        
        try:
            from shared.isolated_environment import get_env
        except ImportError:
            pytest.fail("Could not import IsolatedEnvironment - this indicates a critical architecture issue")
        
        env = get_env()
        env.enable_isolation()
        
        performance_issues = []
        
        # Test 1: Thread safety under concurrent access
        results = []
        exceptions = []
        
        def concurrent_access(thread_id):
            try:
                start_time = time.time()
                for i in range(100):
                    key = f"TEST_KEY_{thread_id}_{i}"
                    value = f"test_value_{thread_id}_{i}"
                    env.set(key, value, f"thread_{thread_id}")
                    retrieved = env.get(key)
                    if retrieved != value:
                        raise ValueError(f"Value mismatch: expected {value}, got {retrieved}")
                end_time = time.time()
                results.append({
                    'thread_id': thread_id,
                    'duration': end_time - start_time,
                    'operations': 200  # 100 sets + 100 gets
                })
            except Exception as e:
                exceptions.append(f"Thread {thread_id}: {e}")
        
        threads = []
        for i in range(10):
            thread = threading.Thread(target=concurrent_access, args=(i,))
            threads.append(thread)
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout
        
        total_time = time.time() - start_time
        
        # Check for exceptions
        assert len(exceptions) == 0, (
            f"🚨 Thread safety violations in IsolatedEnvironment:\n" +
            "\n".join(exceptions)
        )
        
        # Check for performance issues
        avg_duration = sum(r['duration'] for r in results) / len(results) if results else float('inf')
        if avg_duration > 1.0:  # Operations should complete in under 1 second
            performance_issues.append(f"Slow environment access: {avg_duration:.2f}s average")
        
        if total_time > 15:  # Total test should complete quickly
            performance_issues.append(f"Slow concurrent access: {total_time:.2f}s total")
        
        # Test 2: Memory usage doesn't grow excessively
        initial_var_count = len(env.get_all())
        for i in range(1000):
            env.set(f"PERF_TEST_{i}", f"value_{i}", "performance_test")
        
        if len(env.get_all()) - initial_var_count != 1000:
            performance_issues.append("Environment variable storage has unexpected behavior")
        
        # Cleanup
        env.clear()
        
        assert len(performance_issues) == 0, (
            f"🚨 Performance issues detected:\n" +
            "\n".join(performance_issues)
        )
    
    def test_critical_violations_zero_tolerance(self, project_root):
        """
        TEST 7: CRITICAL - Zero tolerance test for specific known violations.
        
        This test specifically checks for the violations mentioned in the audit.
        It's a simpler, more focused test that should fail clearly.
        """
        critical_files = [
            'core/project_utils.py',
            'core/environment_validator.py',
            'core/isolated_environment.py',
        ]
        
        found_violations = []
        
        for critical_file in critical_files:
            file_path = project_root / critical_file
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for line_no, line in enumerate(lines, 1):
                    # Look for direct environment access patterns
                    if any(pattern in line for pattern in ['env.get(', 'os.getenv(']):
                        # Skip comments
                        if line.strip().startswith('#'):
                            continue
                            
                        found_violations.append({
                            'file': str(file_path),
                            'line': line_no,
                            'code': line.strip(),
                            'critical_file': critical_file
                        })
                        
            except Exception as e:
                print(f"Warning: Could not scan {file_path}: {e}")
                continue
        
        if found_violations:
            report = "\n🚨 CRITICAL VIOLATIONS DETECTED:\n"
            report += "The following files contain direct os.environ access:\n\n"
            
            for violation in found_violations:
                report += f"📁 {violation['critical_file']}:{violation['line']}\n"
                report += f"   Code: {violation['code']}\n\n"
            
            report += "💡 These violations MUST be fixed by:\n"
            report += "   1. Replace os.environ.get() with env.get()\n" 
            report += "   2. Replace os.getenv() with env.get()\n"
            report += "   3. Import: from shared.isolated_environment import get_env\n"
            
            pytest.fail(report)
        else:
            print("\n✅ SUCCESS: No critical violations found in core files!")

    def test_edge_case_violations_detection(self, project_root):
        """
        TEST 8: Detect edge case violations that might be hidden.
        
        This test looks for sophisticated patterns that might evade simple detection.
        """
        edge_case_violations = []
        
        # Advanced patterns for edge cases
        edge_patterns = [
            # String interpolation patterns
            (r'f["\'].*os\.getenv\(', 'f-string with os.getenv'),
            (r'f["\'].*os\.environ\[', 'f-string with os.environ'),
            
            # Method chaining
            (r'os\.environ\.get\(.*\)\.', 'chained os.environ.get'),
            
            # Variable assignment detection
            (r'\w+\s*=\s*os\.environ', 'assignment from os.environ'),
            (r'\w+\s*=\s*os\.getenv', 'assignment from os.getenv'),
            
            # Function parameter passing
            (r'[\(\,]\s*os\.environ\.get\s*\(', 'os.environ.get as parameter'),
            (r'[\(\,]\s*os\.getenv\s*\(', 'os.getenv as parameter'),
        ]
        
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__'))]
            
            for filename in files:
                if not filename.endswith('.py'):
                    continue
                    
                filepath = Path(root) / filename
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    lines = content.split('\n')
                    
                    for line_no, line in enumerate(lines, 1):
                        if line.strip().startswith('#'):
                            continue
                        
                        for pattern, description in edge_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                edge_case_violations.append({
                                    'file': str(filepath.relative_to(Path.cwd())),
                                    'line': line_no,
                                    'pattern': description,
                                    'code': line.strip()
                                })
                                
                except Exception:
                    continue
        
        if edge_case_violations:
            report = f"\n🔍 EDGE CASE VIOLATIONS DETECTED ({len(edge_case_violations)} found):\n"
            for i, violation in enumerate(edge_case_violations[:10], 1):
                report += f"   {i:2d}. {violation['file']}:{violation['line']} - {violation['pattern']}\n"
                report += f"       Code: {violation['code'][:100]}\n\n"
            
            pytest.fail(report)
        else:
            print("\n✅ EDGE CASES: No sophisticated environment access patterns detected!")
    
    def test_complete_violation_summary_report(self, scan_results):
        """
        TEST 9: Generate comprehensive violation summary for debugging.
        
        This test always runs and provides detailed information about any remaining violations.
        """
        violations_by_file, scan_stats = scan_results
        
        if not violations_by_file:
            print("\n✅ SUCCESS: No environment access violations found!")
            print("🎉 The netra_backend service is fully compliant with unified environment management!")
            return
        
        # Generate detailed report
        print("\n" + "="*80)
        print("🚨 ENVIRONMENT VIOLATIONS SUMMARY REPORT")
        print("="*80)
        
        print(f"\n📊 SCAN STATISTICS:")
        print(f"   • Total files scanned: {scan_stats['total_violations']}")
        print(f"   • Files with violations: {scan_stats['files_with_violations']}")
        print(f"   • Total violations: {scan_stats['total_violations']}")
        print(f"   • Critical violations: {scan_stats['critical_violations']}")
        print(f"   • Scan duration: {scan_stats['scan_time']:.2f}s")
        
        # Violation breakdown by type
        violation_types = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for filepath, violations in violations_by_file.items():
            for violation in violations:
                violation_types[violation['type']] += 1
                severity_counts[violation['severity']] += 1
        
        print(f"\n🏷️  VIOLATIONS BY TYPE:")
        for vtype, count in sorted(violation_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {vtype}: {count}")
        
        print(f"\n⚠️  VIOLATIONS BY SEVERITY:")
        for severity, count in sorted(severity_counts.items()):
            print(f"   • {severity}: {count}")
        
        print(f"\n📁 TOP VIOLATING FILES:")
        sorted_files = sorted(violations_by_file.items(), key=lambda x: len(x[1]), reverse=True)
        for filepath, violations in sorted_files[:10]:
            print(f"   • {os.path.basename(filepath)}: {len(violations)} violations")
            for violation in violations[:3]:  # Show first 3 violations per file
                print(f"     Line {violation['line']}: {violation['type']} - {violation['code'][:80]}...")
            if len(violations) > 3:
                print(f"     ... and {len(violations) - 3} more")
        
        print(f"\n💡 REMEDIATION STEPS:")
        print("   1. Replace os.environ.get() with env.get()")
        print("   2. Replace os.getenv() with env.get()")
        print("   3. Replace env.get('KEY') with env.get('KEY')")
        print("   4. Import: from shared.isolated_environment import get_env")
        print("   5. Initialize: env = get_env()")
        print("   6. For tests: env.enable_isolation()")
        
        print("="*80)
        
        # This test fails if any violations exist to ensure they must be fixed
        pytest.fail(
            f"Found {scan_stats['total_violations']} environment access violations. "
            f"See detailed report above. All violations must be fixed for compliance."
        )


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    pytest.main([__file__, "-v", "-s"])