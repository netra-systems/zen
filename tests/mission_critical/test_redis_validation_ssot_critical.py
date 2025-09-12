
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Mission Critical Test: Redis Validation SSOT Compliance

This test is a DEPLOYMENT BLOCKER that validates Redis validation logic follows
SSOT principles across all services. Currently FAILS due to multiple duplicate
implementations that violate architectural tenets.

BUSINESS IMPACT: High
- Redis validation inconsistencies can cause cascade failures
- Multiple implementations lead to different behaviors across services
- SSOT violations undermine system reliability and maintainability

CURRENT VIOLATIONS DETECTED:
1. Backend: netra_backend.app.core.health_checkers.check_redis_health()
2. Auth Service: auth_service.services.health_check_service._check_redis_health()  
3. Analytics Service: analytics_service.analytics_core.database.connection.RedisHealthChecker.check_health()

These must be consolidated into a single, canonical Redis validation implementation.

Expected to FAIL until Redis validation is properly centralized.
"""

import ast
import asyncio
import inspect
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestContext, CategoryType
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class RedisValidationSsotCriticalTest(SSotBaseTestCase):
    """
    Mission Critical Redis Validation SSOT Compliance Test.
    
    This test MUST pass before any deployment. It validates that Redis
    validation logic follows SSOT principles and is not duplicated
    across multiple services.
    
    DEPLOYMENT BLOCKER: This test will FAIL until SSOT violations are fixed.
    """
    
    def setUp(self):
        """Set up test context for Redis validation SSOT compliance."""
        super().setUp()
        self.context = SsotTestContext(
            test_id=f"redis_ssot_{int(time.time())}",
            test_name="Redis Validation SSOT Critical Compliance",
            test_category=CategoryType.MISSION_CRITICAL,
            metadata={
                "deployment_blocker": True,
                "ssot_category": "redis_validation",
                "expected_failures": 3,  # Number of SSOT violations
                "business_impact": "HIGH"
            }
        )
        self.metrics.start_timing()
        
        # Known Redis validation implementations (SSOT violations)
        self.known_violations = {
            "backend_redis_health": "netra_backend/app/core/health_checkers.py",
            "auth_redis_health": "auth_service/services/health_check_service.py", 
            "analytics_redis_health": "analytics_service/analytics_core/database/connection.py"
        }
        
        # Expected SSOT location (does not exist yet - should be created)
        self.expected_ssot_location = "shared/redis_validation"
        
    def test_redis_validation_ssot_violations_detected(self):
        """
        CRITICAL: Test that multiple Redis validation implementations exist.
        
        This test MUST FAIL to demonstrate current SSOT violations.
        When this test passes, it indicates SSOT violations have been resolved.
        """
        logger.info(" ALERT:  TESTING: Redis validation SSOT violations (Expected to FAIL)")
        
        violations_found = self._scan_for_redis_validation_implementations()
        
        # Record metrics
        self.metrics.record_custom("violations_detected", len(violations_found))
        self.metrics.record_custom("violation_details", violations_found)
        
        # CRITICAL: This assertion MUST FAIL with current violations
        # When Redis validation is properly centralized, this will pass
        assert len(violations_found) <= 1, (
            f" ALERT:  SSOT VIOLATION: Found {len(violations_found)} Redis validation implementations. "
            f"ONLY ONE implementation should exist in the SSOT location. "
            f"Violations: {list(violations_found.keys())}"
        )
        
        logger.error(f"UNEXPECTED: Only {len(violations_found)} Redis validation implementations found. "
                    f"Expected 3+ violations. System may already be compliant or scan failed.")
    
    def test_redis_validation_interface_consistency(self):
        """
        Test that Redis validation interfaces are inconsistent across services.
        
        This demonstrates why SSOT is critical - different services have
        different interfaces and return formats.
        """
        logger.info(" SEARCH:  TESTING: Redis validation interface consistency")
        
        implementations = self._analyze_redis_validation_interfaces()
        
        if len(implementations) < 2:
            pytest.skip("Not enough Redis validation implementations found for interface analysis")
        
        # Compare interfaces between implementations
        interface_mismatches = self._compare_validation_interfaces(implementations)
        
        self.metrics.record_custom("interface_implementations", len(implementations))
        self.metrics.record_custom("interface_mismatches", len(interface_mismatches))
        
        # Should find interface inconsistencies (demonstrating SSOT need)
        assert len(interface_mismatches) == 0, (
            f" ALERT:  INTERFACE INCONSISTENCY: Found {len(interface_mismatches)} interface mismatches "
            f"between Redis validation implementations. This proves the need for SSOT: {interface_mismatches}"
        )
    
    def test_redis_validation_behavior_consistency(self):
        """
        Test that Redis validation behaviors are consistent across services.
        
        This test examines the actual validation logic to detect differences
        in error handling, timeout values, and response formats.
        """
        logger.info(" SEARCH:  TESTING: Redis validation behavior consistency")
        
        implementations = self._extract_redis_validation_behaviors()
        
        if len(implementations) < 2:
            pytest.skip("Not enough Redis validation implementations found for behavior analysis")
        
        behavior_differences = self._compare_validation_behaviors(implementations)
        
        self.metrics.record_custom("behavior_implementations", len(implementations))
        self.metrics.record_custom("behavior_differences", len(behavior_differences))
        
        # Should find behavioral differences (demonstrating SSOT need)
        assert len(behavior_differences) == 0, (
            f" ALERT:  BEHAVIOR INCONSISTENCY: Found {len(behavior_differences)} behavioral differences "
            f"between Redis validation implementations: {behavior_differences}"
        )
    
    def test_redis_ssot_location_exists(self):
        """
        Test that a single Redis validation SSOT location exists.
        
        This test checks for the expected centralized Redis validation
        implementation that should replace all scattered implementations.
        """
        logger.info(" SEARCH:  TESTING: Redis validation SSOT location existence")
        
        # Check for expected SSOT location
        project_root = Path(__file__).parent.parent.parent
        expected_paths = [
            project_root / "shared" / "redis_validation.py",
            project_root / "shared" / "validation" / "redis_health.py",
            project_root / "shared" / "health" / "redis_validator.py"
        ]
        
        ssot_found = False
        ssot_path = None
        
        for path in expected_paths:
            if path.exists():
                ssot_found = True
                ssot_path = path
                break
        
        self.metrics.record_custom("ssot_location_found", ssot_found)
        self.metrics.record_custom("ssot_path", str(ssot_path) if ssot_path else None)
        
        # This should FAIL until SSOT is implemented
        assert ssot_found, (
            f" ALERT:  MISSING SSOT: No Redis validation SSOT implementation found. "
            f"Expected at one of: {[str(p) for p in expected_paths]}"
        )
    
    def test_services_use_redis_ssot(self):
        """
        Test that all services use the centralized Redis validation SSOT.
        
        This test checks that services import and use the SSOT implementation
        instead of maintaining their own Redis validation logic.
        """
        logger.info(" SEARCH:  TESTING: Services use Redis validation SSOT")
        
        service_imports = self._check_service_redis_imports()
        
        # Count services using SSOT vs local implementations
        ssot_users = 0
        local_implementers = 0
        
        for service, import_info in service_imports.items():
            if import_info.get("uses_ssot", False):
                ssot_users += 1
            if import_info.get("has_local_impl", False):
                local_implementers += 1
        
        self.metrics.record_custom("ssot_users", ssot_users)
        self.metrics.record_custom("local_implementers", local_implementers)
        
        # This should FAIL until services migrate to SSOT
        assert local_implementers == 0, (
            f" ALERT:  SSOT VIOLATION: {local_implementers} services still have local Redis validation. "
            f"All services must use centralized SSOT. Service details: {service_imports}"
        )
        
        assert ssot_users >= 3, (
            f" ALERT:  INCOMPLETE MIGRATION: Only {ssot_users} services use Redis SSOT. "
            f"Expected at least 3 services (backend, auth, analytics) to use SSOT."
        )
    
    def _scan_for_redis_validation_implementations(self) -> Dict[str, Dict[str, Any]]:
        """
        Scan codebase for Redis validation implementations.
        
        Returns:
            Dictionary of implementation details keyed by identifier
        """
        implementations = {}
        project_root = Path(__file__).parent.parent.parent
        
        # Search patterns for Redis validation
        search_patterns = [
            "check_redis_health",
            "redis_health_check", 
            "_check_redis_health",
            "check_redis",
            "RedisHealthChecker",
            "redis.*ping",
            "redis.*connectivity"
        ]
        
        # Service directories to scan
        service_dirs = [
            "netra_backend",
            "auth_service", 
            "analytics_service",
            "shared",
            "test_framework"
        ]
        
        for service_dir in service_dirs:
            service_path = project_root / service_dir
            if not service_path.exists():
                continue
                
            for py_file in service_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for Redis validation patterns
                    matches = self._find_redis_patterns_in_content(content, search_patterns)
                    
                    if matches:
                        rel_path = str(py_file.relative_to(project_root))
                        implementations[f"{service_dir}_{py_file.stem}"] = {
                            "file_path": rel_path,
                            "service": service_dir,
                            "matches": matches,
                            "line_count": len(content.splitlines())
                        }
                        
                except Exception as e:
                    logger.warning(f"Failed to scan {py_file}: {e}")
        
        return implementations
    
    def _find_redis_patterns_in_content(self, content: str, patterns: List[str]) -> List[Dict[str, Any]]:
        """Find Redis validation patterns in file content."""
        matches = []
        lines = content.splitlines()
        
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            for pattern in patterns:
                if pattern.lower() in line_lower:
                    matches.append({
                        "pattern": pattern,
                        "line_number": i,
                        "line_content": line.strip(),
                        "context": "redis_validation"
                    })
        
        return matches
    
    def _analyze_redis_validation_interfaces(self) -> Dict[str, Dict[str, Any]]:
        """
        Analyze Redis validation method interfaces across services.
        
        Returns:
            Dictionary of interface details for each implementation
        """
        implementations = {}
        project_root = Path(__file__).parent.parent.parent
        
        # Known Redis validation files
        validation_files = [
            "netra_backend/app/core/health_checkers.py",
            "auth_service/services/health_check_service.py",
            "analytics_service/analytics_core/database/connection.py"
        ]
        
        for file_path in validation_files:
            full_path = project_root / file_path
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST to extract method signatures
                tree = ast.parse(content)
                interface_info = self._extract_interface_from_ast(tree, file_path)
                
                if interface_info:
                    implementations[file_path] = interface_info
                    
            except Exception as e:
                logger.warning(f"Failed to analyze interface in {file_path}: {e}")
        
        return implementations
    
    def _extract_interface_from_ast(self, tree: ast.AST, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract Redis validation interface from AST."""
        interface_info = {
            "file_path": file_path,
            "methods": [],
            "classes": [],
            "return_types": [],
            "parameters": []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if "redis" in node.name.lower() and "health" in node.name.lower():
                    method_info = {
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "decorators": [d.id if hasattr(d, 'id') else str(d) for d in node.decorator_list],
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "line_number": node.lineno
                    }
                    interface_info["methods"].append(method_info)
            
            elif isinstance(node, ast.ClassDef):
                if "redis" in node.name.lower() and "health" in node.name.lower():
                    class_info = {
                        "name": node.name,
                        "bases": [base.id if hasattr(base, 'id') else str(base) for base in node.bases],
                        "methods": [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))],
                        "line_number": node.lineno
                    }
                    interface_info["classes"].append(class_info)
        
        return interface_info if (interface_info["methods"] or interface_info["classes"]) else None
    
    def _compare_validation_interfaces(self, implementations: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compare interfaces between Redis validation implementations."""
        mismatches = []
        
        if len(implementations) < 2:
            return mismatches
        
        impl_list = list(implementations.items())
        
        for i in range(len(impl_list)):
            for j in range(i + 1, len(impl_list)):
                file1, interface1 = impl_list[i]
                file2, interface2 = impl_list[j]
                
                # Compare method signatures
                methods1 = {m["name"]: m for m in interface1.get("methods", [])}
                methods2 = {m["name"]: m for m in interface2.get("methods", [])}
                
                # Find methods with same name but different signatures
                common_methods = set(methods1.keys()) & set(methods2.keys())
                
                for method_name in common_methods:
                    m1, m2 = methods1[method_name], methods2[method_name]
                    
                    if m1["args"] != m2["args"] or m1["is_async"] != m2["is_async"]:
                        mismatches.append({
                            "type": "method_signature_mismatch",
                            "method": method_name,
                            "file1": file1,
                            "file2": file2,
                            "signature1": m1,
                            "signature2": m2
                        })
                
                # Compare class interfaces
                classes1 = {c["name"]: c for c in interface1.get("classes", [])}
                classes2 = {c["name"]: c for c in interface2.get("classes", [])}
                
                common_classes = set(classes1.keys()) & set(classes2.keys())
                
                for class_name in common_classes:
                    c1, c2 = classes1[class_name], classes2[class_name]
                    
                    if set(c1["methods"]) != set(c2["methods"]):
                        mismatches.append({
                            "type": "class_method_mismatch",
                            "class": class_name,
                            "file1": file1,
                            "file2": file2,
                            "methods1": c1["methods"],
                            "methods2": c2["methods"]
                        })
        
        return mismatches
    
    def _extract_redis_validation_behaviors(self) -> Dict[str, Dict[str, Any]]:
        """Extract Redis validation behavior patterns from implementations."""
        behaviors = {}
        project_root = Path(__file__).parent.parent.parent
        
        # Analyze known implementations
        validation_files = [
            "netra_backend/app/core/health_checkers.py",
            "auth_service/services/health_check_service.py", 
            "analytics_service/analytics_core/database/connection.py"
        ]
        
        for file_path in validation_files:
            full_path = project_root / file_path
            if not full_path.exists():
                continue
                
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                behavior_info = self._analyze_validation_behavior(content, file_path)
                
                if behavior_info:
                    behaviors[file_path] = behavior_info
                    
            except Exception as e:
                logger.warning(f"Failed to analyze behavior in {file_path}: {e}")
        
        return behaviors
    
    def _analyze_validation_behavior(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze Redis validation behavior patterns in content."""
        behavior_info = {
            "file_path": file_path,
            "timeout_values": [],
            "error_handling_patterns": [],
            "return_formats": [],
            "connection_patterns": []
        }
        
        lines = content.splitlines()
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Find timeout values
            if "timeout" in line_lower and any(op in line_lower for op in ["=", ":"]):
                behavior_info["timeout_values"].append(line.strip())
            
            # Find error handling patterns
            if any(pattern in line_lower for pattern in ["except", "try:", "raise", "error"]):
                if "redis" in line_lower or "connection" in line_lower:
                    behavior_info["error_handling_patterns"].append(line.strip())
            
            # Find return format patterns
            if "return" in line_lower and any(pattern in line_lower for pattern in ["{", "dict", "result"]):
                behavior_info["return_formats"].append(line.strip())
            
            # Find connection patterns
            if any(pattern in line_lower for pattern in ["redis", "connection", "client", "ping"]):
                if any(op in line_lower for op in ["=", "await", "get_", "connect"]):
                    behavior_info["connection_patterns"].append(line.strip())
        
        return behavior_info
    
    def _compare_validation_behaviors(self, implementations: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compare behaviors between Redis validation implementations."""
        differences = []
        
        if len(implementations) < 2:
            return differences
        
        impl_list = list(implementations.items())
        
        # Compare timeout handling
        timeout_patterns = {}
        for file_path, behavior in implementations.items():
            timeout_patterns[file_path] = set(behavior.get("timeout_values", []))
        
        # Find timeout differences
        if len(set(len(timeouts) for timeouts in timeout_patterns.values())) > 1:
            differences.append({
                "type": "timeout_pattern_difference",
                "details": timeout_patterns
            })
        
        # Compare error handling
        error_patterns = {}
        for file_path, behavior in implementations.items():
            error_patterns[file_path] = set(behavior.get("error_handling_patterns", []))
        
        # Find error handling differences  
        all_error_patterns = set()
        for patterns in error_patterns.values():
            all_error_patterns.update(patterns)
        
        for file_path, patterns in error_patterns.items():
            missing_patterns = all_error_patterns - patterns
            if missing_patterns:
                differences.append({
                    "type": "error_handling_difference",
                    "file": file_path,
                    "missing_patterns": list(missing_patterns)
                })
        
        # Compare return formats
        return_patterns = {}
        for file_path, behavior in implementations.items():
            return_patterns[file_path] = set(behavior.get("return_formats", []))
        
        # Find return format differences
        if len(set(len(returns) for returns in return_patterns.values())) > 1:
            differences.append({
                "type": "return_format_difference", 
                "details": return_patterns
            })
        
        return differences
    
    def _check_service_redis_imports(self) -> Dict[str, Dict[str, Any]]:
        """Check how services import and use Redis validation."""
        service_imports = {}
        project_root = Path(__file__).parent.parent.parent
        
        services = ["netra_backend", "auth_service", "analytics_service"]
        
        for service in services:
            service_path = project_root / service
            if not service_path.exists():
                continue
            
            import_info = {
                "service": service,
                "uses_ssot": False,
                "has_local_impl": False,
                "import_patterns": [],
                "local_implementations": []
            }
            
            # Scan for imports and implementations
            for py_file in service_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for SSOT imports
                    if any(pattern in content.lower() for pattern in [
                        "from shared.redis_validation", 
                        "import shared.redis_validation",
                        "from shared.validation.redis",
                        "from shared.health.redis"
                    ]):
                        import_info["uses_ssot"] = True
                        import_info["import_patterns"].append(str(py_file.relative_to(service_path)))
                    
                    # Check for local Redis implementations
                    if any(pattern in content.lower() for pattern in [
                        "def check_redis_health",
                        "def _check_redis_health", 
                        "class RedisHealthChecker",
                        "redis.*ping",
                        "async def.*redis.*health"
                    ]):
                        import_info["has_local_impl"] = True
                        import_info["local_implementations"].append(str(py_file.relative_to(service_path)))
                
                except Exception as e:
                    logger.warning(f"Failed to scan {py_file}: {e}")
            
            service_imports[service] = import_info
        
        return service_imports
    
    def tearDown(self):
        """Clean up test and record final metrics."""
        self.metrics.end_timing()
        
        # Log test results
        violations = self.metrics.get_custom("violations_detected", 0)
        logger.info(f" ALERT:  Redis Validation SSOT Test Complete: {violations} violations detected")
        
        if violations > 1:
            logger.error(f"SSOT VIOLATION: {violations} Redis validation implementations found. "
                        f"This is a DEPLOYMENT BLOCKER until consolidated.")
        else:
            logger.info(" PASS:  Redis validation appears to be SSOT compliant")
        
        super().tearDown()


if __name__ == "__main__":
    # Run as standalone test
    pytest.main([__file__, "-v", "--tb=short"])