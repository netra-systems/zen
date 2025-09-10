"""Redis SSOT Import Source Validation Unit Tests

MISSION CRITICAL: These tests validate that all Redis manager imports
follow SSOT compliance to prevent the 5-competing-managers issue
causing WebSocket 1011 errors and $500K+ ARR chat functionality failures.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability & Chat Reliability  
- Value Impact: Prevents Redis fragmentation causing WebSocket failures
- Strategic Impact: Protects $500K+ ARR from chat system instability

DESIGNED TO FAIL INITIALLY:
- Tests should FAIL showing 5+ competing Redis managers
- Tests prove business impact before consolidation
- Guides Redis SSOT remediation strategy
"""

import ast
import os
import unittest
from pathlib import Path
from typing import List, Dict, Set, Tuple


class TestRedisImportSourceValidation(unittest.TestCase):
    """Unit tests validating Redis import SSOT compliance.
    
    These tests are designed to FAIL initially, proving the existence
    of multiple competing Redis managers that cause WebSocket 1011 errors.
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.project_root = Path("/Users/anthony/Desktop/netra-apex")
        self.primary_redis_ssot = "netra_backend.app.redis_manager"
        self.allowed_redis_imports = {
            self.primary_redis_ssot,
            # Test utilities are allowed
            "test_framework.redis_test_utils.test_redis_manager",
        }
        
    def test_redis_manager_import_sources_ssot_compliance(self):
        """DESIGNED TO FAIL: Test that all Redis managers use primary SSOT.
        
        This test should FAIL initially, showing:
        - 5+ competing Redis manager implementations
        - 248+ files with fragmented Redis imports
        - Non-SSOT import patterns causing resource conflicts
        
        Expected failures:
        - netra_backend.app.db.redis_manager (competing manager)
        - netra_backend.app.cache.redis_cache_manager (competing manager)
        - netra_backend.app.managers.redis_manager (competing manager)
        - auth_service.auth_core.redis_manager (competing manager)
        """
        violations = self._scan_redis_import_violations()
        
        # This assertion should FAIL initially
        self.assertEqual(
            len(violations),
            0,
            f"CRITICAL: Found {len(violations)} Redis SSOT violations causing WebSocket 1011 errors:\n" +
            self._format_violations_report(violations)
        )
    
    def test_competing_redis_manager_detection(self):
        """DESIGNED TO FAIL: Test detection of competing Redis manager classes.
        
        This test should FAIL showing multiple RedisManager class definitions
        that create connection pool conflicts and resource contention.
        """
        competing_managers = self._find_competing_redis_managers()
        
        # This assertion should FAIL initially 
        self.assertEqual(
            len(competing_managers),
            1,  # Only primary SSOT should exist
            f"CRITICAL: Found {len(competing_managers)} competing Redis managers causing resource conflicts:\n" +
            "\n".join([f"  - {manager}" for manager in competing_managers]) +
            f"\n\nPrimary SSOT: {self.primary_redis_ssot}.RedisManager" +
            "\n\nThese competing managers cause WebSocket 1011 errors and chat functionality failures."
        )
    
    def test_redis_import_pattern_consistency(self):
        """DESIGNED TO FAIL: Test that all Redis imports follow consistent patterns.
        
        This test should FAIL showing inconsistent import patterns:
        - from netra_backend.app.redis_manager import redis_manager
        - from netra_backend.app.db.redis_manager import RedisManager  
        - from netra_backend.app.cache.redis_cache_manager import RedisCacheManager
        """
        import_patterns = self._analyze_redis_import_patterns()
        
        # This assertion should FAIL initially
        self.assertEqual(
            len(import_patterns),
            1,  # Only one SSOT import pattern should exist
            f"CRITICAL: Found {len(import_patterns)} different Redis import patterns causing confusion:\n" +
            self._format_import_patterns_report(import_patterns) +
            "\n\nExpected single SSOT pattern: 'from netra_backend.app.redis_manager import redis_manager'"
        )
    
    def test_redis_client_initialization_ssot_compliance(self):
        """DESIGNED TO FAIL: Test that Redis client initialization follows SSOT.
        
        This test should FAIL showing multiple Redis client initialization
        patterns that create separate connection pools.
        """
        client_init_patterns = self._find_redis_client_initializations()
        
        # This assertion should FAIL initially
        self.assertLessEqual(
            len(client_init_patterns),
            2,  # Only SSOT manager + test utilities allowed
            f"CRITICAL: Found {len(client_init_patterns)} Redis client initialization patterns:\n" +
            self._format_client_init_report(client_init_patterns) +
            "\n\nMultiple initialization patterns create separate connection pools causing WebSocket failures."
        )
    
    def test_redis_connection_pool_sharing_validation(self):
        """DESIGNED TO FAIL: Test that all Redis operations share connection pool.
        
        This test should FAIL showing evidence of multiple Redis connection
        pools that don't share resources effectively.
        """
        connection_pool_evidence = self._analyze_connection_pool_usage()
        
        # This assertion should FAIL initially
        self.assertTrue(
            connection_pool_evidence["uses_shared_pool"],
            f"CRITICAL: Redis connection pool not properly shared:\n" +
            f"  - Shared pool usage: {connection_pool_evidence['uses_shared_pool']}\n" +
            f"  - Separate pools detected: {connection_pool_evidence['separate_pools_count']}\n" +
            f"  - Pool creation locations: {connection_pool_evidence['pool_locations']}\n" +
            "\n\nSeparate connection pools cause resource contention and WebSocket 1011 errors."
        )
    
    def _scan_redis_import_violations(self) -> List[Dict]:
        """Scan for Redis import SSOT violations across codebase."""
        violations = []
        
        # Scan Python files for Redis imports
        for python_file in self._find_python_files():
            try:
                violations.extend(self._check_file_redis_imports(python_file))
            except Exception as e:
                # Log error but continue scanning
                print(f"Warning: Error scanning {python_file}: {e}")
        
        return violations
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        
        # Focus on main application directories
        scan_dirs = [
            "netra_backend/app",
            "auth_service", 
            "shared",
            "test_framework",
        ]
        
        for scan_dir in scan_dirs:
            full_path = self.project_root / scan_dir
            if full_path.exists():
                python_files.extend(full_path.rglob("*.py"))
        
        return python_files
    
    def _check_file_redis_imports(self, file_path: Path) -> List[Dict]:
        """Check individual file for Redis import violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to find imports
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if 'redis' in alias.name.lower() and 'manager' in alias.name.lower():
                            if alias.name not in self.allowed_redis_imports:
                                violations.append({
                                    'file': str(file_path),
                                    'line': node.lineno,
                                    'type': 'direct_import',
                                    'import': alias.name,
                                    'violation': f"Non-SSOT Redis import: {alias.name}"
                                })
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and 'redis' in node.module.lower() and 'manager' in node.module.lower():
                        if node.module not in self.allowed_redis_imports:
                            for alias in node.names:
                                violations.append({
                                    'file': str(file_path),
                                    'line': node.lineno,
                                    'type': 'from_import',
                                    'module': node.module,
                                    'import': alias.name,
                                    'violation': f"Non-SSOT Redis import: from {node.module} import {alias.name}"
                                })
        
        except Exception as e:
            # Return error as violation for investigation
            violations.append({
                'file': str(file_path),
                'line': 0,
                'type': 'parse_error',
                'error': str(e),
                'violation': f"Could not parse file: {e}"
            })
        
        return violations
    
    def _find_competing_redis_managers(self) -> List[str]:
        """Find all Redis manager class definitions."""
        managers = []
        
        for python_file in self._find_python_files():
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for class definitions containing "Redis" and "Manager"
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if 'redis' in node.name.lower() and 'manager' in node.name.lower():
                            relative_path = python_file.relative_to(self.project_root)
                            managers.append(f"{relative_path}::{node.name}")
            
            except Exception:
                continue  # Skip files that can't be parsed
        
        return managers
    
    def _analyze_redis_import_patterns(self) -> Dict[str, int]:
        """Analyze different Redis import patterns used."""
        patterns = {}
        
        for python_file in self._find_python_files():
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for Redis-related imports
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if (line.startswith('from ') or line.startswith('import ')) and 'redis' in line.lower():
                        if 'manager' in line.lower():
                            patterns[line] = patterns.get(line, 0) + 1
            
            except Exception:
                continue
        
        return patterns
    
    def _find_redis_client_initializations(self) -> List[Dict]:
        """Find Redis client initialization patterns."""
        initializations = []
        
        for python_file in self._find_python_files():
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for Redis client creation patterns
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    line_lower = line.lower()
                    if (('redis.from_url' in line_lower or 
                         'redis(' in line_lower or
                         'redis.redis(' in line_lower) and
                        'test' not in str(python_file).lower()):
                        
                        initializations.append({
                            'file': str(python_file),
                            'line': i,
                            'pattern': line.strip(),
                            'type': 'client_creation'
                        })
            
            except Exception:
                continue
        
        return initializations
    
    def _analyze_connection_pool_usage(self) -> Dict:
        """Analyze Redis connection pool usage patterns."""
        analysis = {
            'uses_shared_pool': False,
            'separate_pools_count': 0,
            'pool_locations': []
        }
        
        # Count Redis manager instances
        managers = self._find_competing_redis_managers()
        analysis['separate_pools_count'] = len(managers)
        analysis['pool_locations'] = managers
        
        # Shared pool is used only if single SSOT manager exists
        analysis['uses_shared_pool'] = len(managers) <= 1
        
        return analysis
    
    def _format_violations_report(self, violations: List[Dict]) -> str:
        """Format violations into readable report."""
        if not violations:
            return "No violations found"
        
        report = f"\n\n=== REDIS SSOT VIOLATIONS ({len(violations)} total) ===\n"
        
        # Group by violation type
        by_type = {}
        for violation in violations:
            vtype = violation.get('type', 'unknown')
            if vtype not in by_type:
                by_type[vtype] = []
            by_type[vtype].append(violation)
        
        for vtype, items in by_type.items():
            report += f"\n{vtype.upper()} ({len(items)} violations):\n"
            for item in items[:10]:  # Limit to first 10 per type
                report += f"  - {item['file']}:{item.get('line', '?')} - {item['violation']}\n"
            if len(items) > 10:
                report += f"  ... and {len(items) - 10} more\n"
        
        return report
    
    def _format_import_patterns_report(self, patterns: Dict[str, int]) -> str:
        """Format import patterns into readable report."""
        if not patterns:
            return "No import patterns found"
        
        report = f"\n\n=== REDIS IMPORT PATTERNS ({len(patterns)} unique) ===\n"
        for pattern, count in sorted(patterns.items(), key=lambda x: x[1], reverse=True):
            report += f"  {count:3d}x: {pattern}\n"
        
        return report
    
    def _format_client_init_report(self, initializations: List[Dict]) -> str:
        """Format client initialization patterns into readable report."""
        if not initializations:
            return "No client initializations found"
        
        report = f"\n\n=== REDIS CLIENT INITIALIZATIONS ({len(initializations)} total) ===\n"
        for init in initializations[:15]:  # Limit to first 15
            report += f"  - {init['file']}:{init['line']} - {init['pattern']}\n"
        
        if len(initializations) > 15:
            report += f"  ... and {len(initializations) - 15} more\n"
        
        return report
    

if __name__ == "__main__":
    # Run tests independently for debugging
    import unittest
    unittest.main()