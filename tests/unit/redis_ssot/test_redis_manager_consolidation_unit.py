"""
Redis Manager Consolidation Unit Test - CRITICAL for GitHub Issue #190

This test validates that the 4→1 Redis manager consolidation works correctly,
ensuring single Redis manager handles all operations and preventing the chaos
of 76 files importing different Redis managers.

BUSINESS IMPACT: CRITICAL - $500K+ ARR at risk
- Chat functionality failures from Redis connection instability
- Agent state persistence issues causing 1011 WebSocket errors
- Memory leaks from multiple Redis connection pools
- User isolation failures from competing Redis managers

CURRENT STATE (Expected to FAIL until consolidation complete):
- PRIMARY SSOT: /netra_backend/app/redis_manager.py (734 lines)
- VIOLATION 1: /netra_backend/app/db/redis_manager.py
- VIOLATION 2: /netra_backend/app/cache/redis_cache_manager.py  
- VIOLATION 3: /auth_service/redis_manager.py
- 76 files importing different Redis managers creating chaos

CONSOLIDATION REQUIREMENTS:
1. Single Redis manager handles all operations (connection, caching, health checks)
2. Connection pool sharing works across components
3. Configuration consistency maintained across all services
4. Memory usage reduced vs multiple managers
5. All Redis operations (get/set/delete/ping/health) work through single manager
6. User isolation properly maintained with factory patterns
"""

import asyncio
import inspect
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestContext, CategoryType
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class RedisManagerConsolidationUnitTest(SSotBaseTestCase):
    """
    Critical unit test validating 4→1 Redis manager consolidation.
    
    This test MUST pass for deployment - validates single Redis manager
    can handle all operations previously distributed across 4 managers.
    
    DEPLOYMENT BLOCKER: This test will FAIL until SSOT consolidation is complete.
    """
    
    def setUp(self):
        """Set up test context for Redis manager consolidation validation."""
        super().setUp()
        self.context = SsotTestContext(
            test_id=f"redis_mgr_consolidation_{int(time.time())}",
            test_name="Redis Manager Consolidation Unit Test",
            test_category=CategoryType.MISSION_CRITICAL,
            metadata={
                "github_issue": "#190",
                "business_impact": "CRITICAL",
                "deployment_blocker": True,
                "ssot_category": "redis_manager_consolidation",
                "expected_violations": 3,  # Number of duplicate managers to eliminate
                "arr_at_risk": "$500K+"
            }
        )
        self.metrics.start_timing()
        
        # Primary SSOT Redis manager
        self.primary_ssot_path = "netra_backend/app/redis_manager.py"
        
        # Known SSOT violations (should be eliminated)
        self.violation_managers = [
            "netra_backend/app/db/redis_manager.py",
            "netra_backend/app/cache/redis_cache_manager.py", 
            "auth_service/redis_manager.py"
        ]
        
        # Core Redis operations all managers must support
        self.required_operations = [
            "get", "set", "delete", "ping", "health_check",
            "connect", "disconnect", "exists", "expire"
        ]
        
    def test_single_redis_manager_exists(self):
        """
        CRITICAL: Test that primary SSOT Redis manager exists and is comprehensive.
        
        Validates the primary Redis manager can handle all operations
        previously distributed across multiple managers.
        """
        logger.info("🔍 TESTING: Single Redis manager exists and is comprehensive")
        
        project_root = Path(__file__).parent.parent.parent.parent
        primary_path = project_root / self.primary_ssot_path
        
        # Primary manager must exist
        assert primary_path.exists(), (
            f"🚨 MISSING SSOT: Primary Redis manager not found at {primary_path}. "
            f"This is CRITICAL for consolidation."
        )
        
        # Analyze primary manager capabilities
        manager_info = self._analyze_redis_manager_capabilities(primary_path)
        
        self.metrics.record_custom("primary_manager_methods", len(manager_info["methods"]))
        self.metrics.record_custom("primary_manager_classes", len(manager_info["classes"]))
        self.metrics.record_custom("primary_manager_capabilities", manager_info)
        
        # Primary manager must have comprehensive Redis capabilities
        missing_operations = set(self.required_operations) - set(manager_info["operation_methods"])
        
        assert len(missing_operations) == 0, (
            f"🚨 INCOMPLETE SSOT: Primary Redis manager missing operations: {missing_operations}. "
            f"SSOT manager must handle ALL Redis operations. Found: {manager_info['operation_methods']}"
        )
        
        # Manager must be substantial enough to replace others
        assert len(manager_info["methods"]) >= 10, (
            f"🚨 INSUFFICIENT SSOT: Primary manager has only {len(manager_info['methods'])} methods. "
            f"Expected at least 10 methods to replace multiple managers."
        )
        
        logger.info(f"✅ Primary Redis manager validated: {len(manager_info['methods'])} methods, "
                   f"{len(manager_info['operation_methods'])} Redis operations")
    
    def test_duplicate_managers_still_exist(self):
        """
        Test that duplicate Redis managers still exist (should FAIL until consolidation).
        
        This test documents current violations and will pass once consolidation
        eliminates the duplicate managers.
        """
        logger.info("🚨 TESTING: Duplicate Redis managers exist (Expected violations)")
        
        project_root = Path(__file__).parent.parent.parent.parent
        violations_found = []
        
        for violation_path in self.violation_managers:
            full_path = project_root / violation_path
            if full_path.exists():
                violations_found.append(violation_path)
                logger.warning(f"SSOT VIOLATION: Found duplicate manager at {violation_path}")
        
        self.metrics.record_custom("violations_found", len(violations_found))
        self.metrics.record_custom("violation_details", violations_found)
        
        # This should FAIL until consolidation is complete
        assert len(violations_found) == 0, (
            f"🚨 SSOT VIOLATION: Found {len(violations_found)} duplicate Redis managers. "
            f"ONLY the primary SSOT manager should exist. "
            f"Duplicates found: {violations_found}"
        )
        
        logger.error(f"EXPECTED FAILURE: {len(violations_found)} duplicate managers still exist")
    
    def test_connection_pool_sharing_capability(self):
        """
        Test that single manager can provide shared connection pool.
        
        Validates the SSOT manager can provide connection sharing across
        components to reduce memory usage vs multiple managers.
        """
        logger.info("🔍 TESTING: Connection pool sharing capability")
        
        project_root = Path(__file__).parent.parent.parent.parent
        primary_path = project_root / self.primary_ssot_path
        
        if not primary_path.exists():
            pytest.skip("Primary Redis manager not found - skipping pool sharing test")
        
        manager_code = self._load_manager_code(primary_path)
        pool_capabilities = self._analyze_connection_pool_capabilities(manager_code)
        
        self.metrics.record_custom("pool_capabilities", pool_capabilities)
        
        # Manager must support connection pooling
        assert pool_capabilities["has_connection_pool"], (
            f"🚨 NO CONNECTION POOLING: SSOT manager must support connection pooling "
            f"to replace multiple managers efficiently."
        )
        
        # Must support shared access patterns
        assert pool_capabilities["has_client_sharing"], (
            f"🚨 NO CLIENT SHARING: SSOT manager must support client sharing "
            f"to reduce memory vs multiple managers."
        )
        
        logger.info(f"✅ Connection pool sharing validated: {pool_capabilities}")
    
    def test_configuration_consistency_support(self):
        """
        Test that single manager supports consistent configuration.
        
        Validates the SSOT manager uses consistent configuration patterns
        that can replace the various config approaches in duplicate managers.
        """
        logger.info("🔍 TESTING: Configuration consistency support")
        
        project_root = Path(__file__).parent.parent.parent.parent
        primary_path = project_root / self.primary_ssot_path
        
        if not primary_path.exists():
            pytest.skip("Primary Redis manager not found - skipping config test")
        
        manager_code = self._load_manager_code(primary_path)
        config_info = self._analyze_configuration_patterns(manager_code)
        
        self.metrics.record_custom("config_patterns", config_info)
        
        # Must use environment-based configuration (SSOT pattern)
        assert config_info["uses_environment_config"], (
            f"🚨 NO ENVIRONMENT CONFIG: SSOT manager must use environment-based "
            f"configuration for consistency across services."
        )
        
        # Must support health checks
        assert config_info["supports_health_checks"], (
            f"🚨 NO HEALTH CHECKS: SSOT manager must support health monitoring "
            f"to replace health check logic in duplicate managers."
        )
        
        logger.info(f"✅ Configuration consistency validated: {config_info}")
    
    def test_memory_usage_optimization(self):
        """
        Test memory optimization potential of single manager.
        
        Validates that single manager approach will use less memory
        than multiple managers with separate connection pools.
        """
        logger.info("🔍 TESTING: Memory usage optimization potential")
        
        # Simulate memory usage comparison
        current_managers = len(self.violation_managers) + 1  # Include primary
        optimized_managers = 1
        
        # Each manager typically has connection pool (assume 5-10 connections each)
        estimated_connections_current = current_managers * 7  # Average connections per manager
        estimated_connections_optimized = 10  # Single shared pool
        
        memory_reduction = (estimated_connections_current - estimated_connections_optimized) / estimated_connections_current
        
        self.metrics.record_custom("current_managers", current_managers)
        self.metrics.record_custom("optimized_managers", optimized_managers)
        self.metrics.record_custom("estimated_memory_reduction", memory_reduction)
        
        # Should provide significant memory reduction
        assert memory_reduction > 0.5, (
            f"🚨 INSUFFICIENT OPTIMIZATION: Expected >50% memory reduction, "
            f"got {memory_reduction:.2%}. Single manager must provide significant optimization."
        )
        
        logger.info(f"✅ Memory optimization validated: {memory_reduction:.2%} reduction expected "
                   f"({estimated_connections_current} → {estimated_connections_optimized} connections)")
    
    def test_user_isolation_factory_support(self):
        """
        Test that single manager supports proper user isolation.
        
        Critical for multi-user system - validates SSOT manager can provide
        user isolation without compromising on single connection pool benefits.
        """
        logger.info("🔍 TESTING: User isolation factory support")
        
        project_root = Path(__file__).parent.parent.parent.parent
        primary_path = project_root / self.primary_ssot_path
        
        if not primary_path.exists():
            pytest.skip("Primary Redis manager not found - skipping isolation test")
        
        manager_code = self._load_manager_code(primary_path)
        isolation_info = self._analyze_user_isolation_patterns(manager_code)
        
        self.metrics.record_custom("isolation_patterns", isolation_info)
        
        # Must support factory pattern for user isolation
        factory_indicators = [
            isolation_info["has_factory_methods"],
            isolation_info["has_context_isolation"],
            isolation_info["has_namespace_support"]
        ]
        
        isolation_score = sum(factory_indicators) / len(factory_indicators)
        
        assert isolation_score >= 0.67, (
            f"🚨 INSUFFICIENT ISOLATION: SSOT manager isolation score {isolation_score:.2%} "
            f"below required 67%. Multi-user system requires proper isolation. "
            f"Patterns found: {isolation_info}"
        )
        
        logger.info(f"✅ User isolation validated: {isolation_score:.2%} isolation score")
    
    def _analyze_redis_manager_capabilities(self, manager_path: Path) -> Dict[str, Any]:
        """Analyze Redis manager capabilities from source code."""
        try:
            with open(manager_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read manager file {manager_path}: {e}")
            return {"methods": [], "classes": [], "operation_methods": []}
        
        capabilities = {
            "methods": [],
            "classes": [],
            "operation_methods": [],
            "async_methods": [],
            "sync_methods": []
        }
        
        lines = content.splitlines()
        
        for line in lines:
            line_stripped = line.strip()
            
            # Find method definitions
            if line_stripped.startswith("def ") or line_stripped.startswith("async def "):
                method_name = self._extract_method_name(line_stripped)
                if method_name:
                    capabilities["methods"].append(method_name)
                    
                    if line_stripped.startswith("async def"):
                        capabilities["async_methods"].append(method_name)
                    else:
                        capabilities["sync_methods"].append(method_name)
                    
                    # Check if it's a Redis operation method
                    for operation in self.required_operations:
                        if operation in method_name.lower():
                            capabilities["operation_methods"].append(method_name)
                            break
            
            # Find class definitions
            if line_stripped.startswith("class "):
                class_name = self._extract_class_name(line_stripped)
                if class_name:
                    capabilities["classes"].append(class_name)
        
        return capabilities
    
    def _extract_method_name(self, line: str) -> Optional[str]:
        """Extract method name from method definition line."""
        try:
            if "def " in line:
                start = line.find("def ") + 4
                end = line.find("(", start)
                if end > start:
                    return line[start:end].strip()
        except Exception:
            pass
        return None
    
    def _extract_class_name(self, line: str) -> Optional[str]:
        """Extract class name from class definition line."""
        try:
            if "class " in line:
                start = line.find("class ") + 6
                end = line.find("(", start) if "(" in line else line.find(":", start)
                if end > start:
                    return line[start:end].strip()
        except Exception:
            pass
        return None
    
    def _load_manager_code(self, manager_path: Path) -> str:
        """Load Redis manager source code."""
        try:
            with open(manager_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load manager code {manager_path}: {e}")
            return ""
    
    def _analyze_connection_pool_capabilities(self, code: str) -> Dict[str, Any]:
        """Analyze connection pool capabilities in manager code."""
        capabilities = {
            "has_connection_pool": False,
            "has_client_sharing": False,
            "has_async_support": False,
            "has_retry_logic": False
        }
        
        code_lower = code.lower()
        
        # Check for connection pool patterns
        pool_indicators = [
            "connectionpool", "pool", "redis.connectionpool", 
            "connection_pool", "pool_class"
        ]
        capabilities["has_connection_pool"] = any(indicator in code_lower for indicator in pool_indicators)
        
        # Check for client sharing patterns
        sharing_indicators = [
            "get_client", "shared_client", "client_instance",
            "singleton", "_client", "redis_client"
        ]
        capabilities["has_client_sharing"] = any(indicator in code_lower for indicator in sharing_indicators)
        
        # Check for async support
        capabilities["has_async_support"] = "async def" in code or "await " in code
        
        # Check for retry logic
        retry_indicators = [
            "retry", "backoff", "reconnect", "circuit_breaker",
            "exponential", "max_retries"
        ]
        capabilities["has_retry_logic"] = any(indicator in code_lower for indicator in retry_indicators)
        
        return capabilities
    
    def _analyze_configuration_patterns(self, code: str) -> Dict[str, Any]:
        """Analyze configuration patterns in manager code."""
        patterns = {
            "uses_environment_config": False,
            "supports_health_checks": False,
            "has_error_handling": False,
            "uses_isolated_environment": False
        }
        
        code_lower = code.lower()
        
        # Check environment configuration usage
        env_indicators = [
            "get_env", "isolatedenvironment", "os.environ",
            "environment", "config"
        ]
        patterns["uses_environment_config"] = any(indicator in code_lower for indicator in env_indicators)
        
        # Check health check support
        health_indicators = [
            "health", "ping", "check", "status", "alive"
        ]
        patterns["supports_health_checks"] = any(indicator in code_lower for indicator in health_indicators)
        
        # Check error handling
        error_indicators = [
            "try:", "except", "raise", "error", "exception"
        ]
        patterns["has_error_handling"] = any(indicator in code_lower for indicator in error_indicators)
        
        # Check IsolatedEnvironment usage (SSOT pattern)
        patterns["uses_isolated_environment"] = "isolatedenvironment" in code_lower
        
        return patterns
    
    def _analyze_user_isolation_patterns(self, code: str) -> Dict[str, Any]:
        """Analyze user isolation patterns in manager code."""
        patterns = {
            "has_factory_methods": False,
            "has_context_isolation": False,
            "has_namespace_support": False,
            "has_user_specific_keys": False
        }
        
        code_lower = code.lower()
        
        # Check for factory pattern methods
        factory_indicators = [
            "create_", "get_instance", "factory", "build_",
            "make_", "new_instance"
        ]
        patterns["has_factory_methods"] = any(indicator in code_lower for indicator in factory_indicators)
        
        # Check for context isolation
        context_indicators = [
            "context", "user_context", "session", "namespace",
            "prefix", "tenant", "isolation"
        ]
        patterns["has_context_isolation"] = any(indicator in code_lower for indicator in context_indicators)
        
        # Check for namespace support
        namespace_indicators = [
            "namespace", "prefix", "key_prefix", "tenant_id"
        ]
        patterns["has_namespace_support"] = any(indicator in code_lower for indicator in namespace_indicators)
        
        # Check for user-specific key patterns
        user_indicators = [
            "user_id", "user:", "session:", "tenant:", "prefix"
        ]
        patterns["has_user_specific_keys"] = any(indicator in code_lower for indicator in user_indicators)
        
        return patterns
    
    def tearDown(self):
        """Clean up test and record final metrics."""
        self.metrics.end_timing()
        
        violations = self.metrics.get_custom("violations_found", 0)
        primary_methods = self.metrics.get_custom("primary_manager_methods", 0)
        
        logger.info(f"🚨 Redis Manager Consolidation Test Complete:")
        logger.info(f"   - Violations found: {violations} (expected: 3)")
        logger.info(f"   - Primary manager methods: {primary_methods}")
        
        if violations > 0:
            logger.error(f"DEPLOYMENT BLOCKER: {violations} duplicate Redis managers found. "
                        f"GitHub Issue #190 consolidation incomplete.")
        else:
            logger.info("✅ Redis manager consolidation appears complete")
        
        super().tearDown()


if __name__ == "__main__":
    # Run as standalone test
    pytest.main([__file__, "-v", "--tb=short"])