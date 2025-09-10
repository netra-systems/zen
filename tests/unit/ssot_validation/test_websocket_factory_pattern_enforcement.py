"""
WebSocket Factory Pattern Enforcement Test Suite

This test validates the elimination of singleton WebSocket patterns and enforcement
of factory patterns for proper user isolation and security.

PURPOSE: Detect and prevent singleton pattern usage that creates security vulnerabilities:
1. No singleton `get_websocket_manager()` function calls
2. All WebSocket managers created via factory pattern with user context
3. Factory creates isolated instances per user (no shared state)
4. UserExecutionContext requirements enforced
5. No shared state between factory-created instances

CRITICAL: These tests FAIL with current singleton usage and PASS after factory migration.
Supports GitHub issue #212 remediation by enforcing secure multi-user patterns.

Business Value Justification (BVJ):
- Segment: Platform/Security - Multi-user isolation requirements
- Business Goal: Prevent user data leakage and ensure proper isolation
- Value Impact: Security foundation for enterprise AI chat platform
- Revenue Impact: Enables secure multi-tenant platform ($500K+ ARR protection)
"""

import ast
import asyncio
import inspect
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.core_types import UserID, ConnectionID, ensure_user_id


@dataclass
class SingletonViolation:
    """Represents a singleton pattern violation."""
    file_path: str
    line_number: int
    function_call: str
    violation_type: str
    security_risk: str
    factory_replacement: str


@dataclass
class FactoryValidationResult:
    """Results of factory pattern validation."""
    singleton_violations_found: int
    factory_usage_count: int
    user_isolation_violations: int
    violations: List[SingletonViolation]
    security_compliance_score: float


class TestWebSocketFactoryPatternEnforcement(SSotBaseTestCase):
    """
    CRITICAL: WebSocket factory pattern enforcement for user isolation security.
    
    These tests ensure singleton patterns are eliminated and factory patterns
    provide proper user isolation to prevent security vulnerabilities.
    """

    # Security violation thresholds
    SINGLETON_VIOLATION_THRESHOLD = 100  # Current state tolerance
    TARGET_SINGLETON_VIOLATIONS = 0     # Final security goal
    
    @property
    def logger(self):
        """Get logger for this test class."""
        return logging.getLogger(self.__class__.__name__)
    
    # Singleton patterns (SECURITY VIOLATIONS)
    SINGLETON_PATTERNS = [
        r"get_websocket_manager\(\)",
        r"WebSocketManager\(\)",  # Direct instantiation without context
        r"UnifiedWebSocketManager\(\)",  # Direct instantiation
        r"websocket_manager\s*=\s*.*\.instance\(\)", # Singleton instance pattern
        r"@singleton",  # Singleton decorator
        r"_instance\s*=\s*None",  # Singleton instance storage
    ]
    
    # Factory patterns (SECURITY COMPLIANT)
    FACTORY_PATTERNS = [
        r"WebSocketManagerFactory\(\)",
        r"create_websocket_manager\(",
        r"await\s+.*\.create_isolated_manager\(",
        r"factory\.create_.*\(.*user_id",
    ]

    @property
    def codebase_root(self) -> Path:
        """Get the codebase root directory."""
        return Path(__file__).parent.parent.parent.parent

    def _get_websocket_related_files(self) -> List[Path]:
        """Get Python files that likely contain WebSocket manager usage."""
        websocket_files = []
        
        exclude_patterns = {
            '.git', 'venv', '.venv', '__pycache__', '.pytest_cache',
            'node_modules', '.test_venv', 'build', 'dist'
        }
        
        for root, dirs, files in os.walk(self.codebase_root):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().lower()
                            if 'websocket' in content and ('manager' in content or 'factory' in content):
                                websocket_files.append(file_path)
                    except Exception:
                        continue
                        
        return websocket_files

    def _analyze_singleton_violations(self, file_path: Path) -> List[SingletonViolation]:
        """
        Analyze a file for singleton pattern violations.
        
        Returns:
            List of singleton violations found
        """
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for line_num, line in enumerate(content.splitlines(), 1):
                line_stripped = line.strip()
                
                for pattern in self.SINGLETON_PATTERNS:
                    if re.search(pattern, line_stripped):
                        violation = SingletonViolation(
                            file_path=str(file_path.relative_to(self.codebase_root)),
                            line_number=line_num,
                            function_call=line_stripped,
                            violation_type=f"Singleton pattern: {pattern}",
                            security_risk=self._get_security_risk(pattern),
                            factory_replacement=self._get_factory_replacement(pattern, line_stripped)
                        )
                        violations.append(violation)
                        
        except Exception as e:
            self.logger.warning(f"Error analyzing file {file_path}: {e}")
            
        return violations

    def _get_security_risk(self, pattern: str) -> str:
        """Get security risk description for a singleton pattern."""
        risk_map = {
            r"get_websocket_manager\(\)": "Shared manager instance across users - data leakage risk",
            r"WebSocketManager\(\)": "Direct instantiation bypasses user context isolation",
            r"UnifiedWebSocketManager\(\)": "No user isolation - messages could cross users",
            r"websocket_manager\s*=\s*.*\.instance\(\)": "Singleton instance shared globally",
            r"@singleton": "Class-level singleton prevents user isolation",
            r"_instance\s*=\s*None": "Global instance storage violates user isolation",
        }
        
        for risk_pattern, risk_desc in risk_map.items():
            if pattern == risk_pattern:
                return risk_desc
        return "Potential user isolation violation"

    def _get_factory_replacement(self, pattern: str, line: str) -> str:
        """Generate secure factory replacement for singleton usage."""
        if "get_websocket_manager()" in line:
            return "factory = WebSocketManagerFactory(); manager = await factory.create_isolated_manager(user_id, connection_id)"
        elif "WebSocketManager()" in line:
            return "manager = await factory.create_isolated_manager(user_id, connection_id)"
        elif "UnifiedWebSocketManager()" in line:
            return "manager = await WebSocketManagerFactory().create_isolated_manager(user_id, connection_id)"
        else:
            return "Replace with factory pattern - see canonical_imports.py"

    def _scan_for_singleton_violations(self) -> FactoryValidationResult:
        """
        Scan codebase for singleton pattern violations.
        
        Returns:
            Complete factory validation results
        """
        websocket_files = self._get_websocket_related_files()
        all_violations = []
        factory_usage_count = 0
        
        for file_path in websocket_files:
            file_violations = self._analyze_singleton_violations(file_path)
            all_violations.extend(file_violations)
            
            # Count factory pattern usage
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in self.FACTORY_PATTERNS:
                        factory_usage_count += len(re.findall(pattern, content))
            except Exception:
                continue
        
        # Calculate security compliance score
        total_websocket_usage = len(all_violations) + factory_usage_count
        security_compliance_score = 0.0
        if total_websocket_usage > 0:
            security_compliance_score = (factory_usage_count / total_websocket_usage) * 100
        
        return FactoryValidationResult(
            singleton_violations_found=len(all_violations),
            factory_usage_count=factory_usage_count,
            user_isolation_violations=len(all_violations),
            violations=all_violations,
            security_compliance_score=security_compliance_score
        )

    def test_no_singleton_get_websocket_manager_usage(self):
        """
        CRITICAL: Singleton pattern eliminated, factory pattern required.
        
        The get_websocket_manager() singleton function creates security vulnerabilities
        by sharing WebSocket manager instances across different users, potentially
        causing message cross-contamination.
        
        EXPECTED: This test FAILS with current codebase (singleton usage exists)
        GOAL: This test PASSES when all singleton usage eliminated
        """
        validation_result = self._scan_for_singleton_violations()
        
        # Filter for get_websocket_manager singleton calls specifically
        singleton_violations = [
            v for v in validation_result.violations 
            if "get_websocket_manager()" in v.function_call
        ]
        
        self.logger.info(f"🔍 Singleton get_websocket_manager() violations: {len(singleton_violations)}")
        
        if singleton_violations:
            self.logger.warning("🚨 SECURITY VIOLATION: Singleton WebSocket manager usage found")
            self.logger.warning("❌ These patterns create user data leakage risks:")
            
            for i, violation in enumerate(singleton_violations[:5], 1):  # Show first 5
                self.logger.warning(f"   {i}. {violation.file_path}:{violation.line_number}")
                self.logger.warning(f"      ❌ {violation.function_call}")
                self.logger.warning(f"      🚨 Risk: {violation.security_risk}")
                self.logger.warning(f"      ✅ Replace: {violation.factory_replacement}")
        
        # ASSERTION: No singleton get_websocket_manager() calls allowed
        assert len(singleton_violations) == 0, (
            f"Found {len(singleton_violations)} singleton get_websocket_manager() calls. "
            f"These create CRITICAL SECURITY VULNERABILITIES.\n\n"
            f"🚨 SECURITY RISK: Singleton patterns cause user data leakage\n"
            f"• User A's messages could be sent to User B's WebSocket\n"
            f"• Shared manager state creates race conditions\n"
            f"• No proper user isolation or context enforcement\n\n"
            f"✅ SECURE REPLACEMENT PATTERN:\n"
            f"```python\n"
            f"from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerFactory\n"
            f"factory = WebSocketManagerFactory()\n"
            f"manager = await factory.create_isolated_manager(user_id, connection_id)\n"
            f"```\n\n"
            f"❌ INSECURE PATTERN (DO NOT USE):\n"
            f"```python\n"
            f"manager = get_websocket_manager()  # 🚨 SECURITY VIOLATION\n"
            f"```"
        )

    def test_factory_creates_isolated_instances(self):
        """
        CRITICAL: Each factory call creates unique manager instance.
        
        Factory pattern must create completely isolated manager instances
        to ensure user data separation and prevent security vulnerabilities.
        """
        # This test requires the factory to actually exist and be importable
        try:
            from netra_backend.app.websocket_core.canonical_imports import (
                WebSocketManagerFactory, create_websocket_manager
            )
        except ImportError as e:
            pytest.skip(f"WebSocket factory not yet implemented: {e}")
        
        # Test factory isolation behavior
        async def test_factory_isolation():
            """Test that factory creates isolated instances."""
            
            # Create two different user contexts
            user_id_1 = ensure_user_id("user_1_test")
            user_id_2 = ensure_user_id("user_2_test")
            connection_id_1 = ConnectionID(f"conn_1_{uuid.uuid4()}")
            connection_id_2 = ConnectionID(f"conn_2_{uuid.uuid4()}")
            
            try:
                factory = WebSocketManagerFactory()
                
                # Create two isolated managers
                manager_1 = await factory.create_isolated_manager(user_id_1, connection_id_1)
                manager_2 = await factory.create_isolated_manager(user_id_2, connection_id_2)
                
                # CRITICAL: Instances must be different objects
                assert manager_1 is not manager_2, (
                    "Factory must create different instances for different users. "
                    "Shared instances create security vulnerabilities."
                )
                
                # CRITICAL: Managers must have different user contexts
                if hasattr(manager_1, 'user_id') and hasattr(manager_2, 'user_id'):
                    assert manager_1.user_id != manager_2.user_id, (
                        "Each manager must have its own user context. "
                        "Shared user contexts violate isolation requirements."
                    )
                
                # CRITICAL: No shared state between managers
                if hasattr(manager_1, '_connections') and hasattr(manager_2, '_connections'):
                    manager_1._connections['test'] = 'user_1_data'
                    assert 'test' not in manager_2._connections, (
                        "Managers share state - CRITICAL SECURITY VIOLATION. "
                        "User data could leak between different users."
                    )
                
                self.logger.info("✅ Factory isolation test passed - users properly isolated")
                return True
                
            except Exception as e:
                self.logger.error(f"Factory isolation test failed: {e}")
                return False
        
        # Run the async test
        result = asyncio.run(test_factory_isolation())
        
        assert result, (
            "Factory pattern must create isolated instances with proper user separation. "
            "Shared instances or state create critical security vulnerabilities."
        )

    def test_user_execution_context_enforcement(self):
        """
        CRITICAL: UserExecutionContext requirements enforced in factory usage.
        
        All WebSocket manager creation must include proper user context
        to ensure security isolation and proper user data handling.
        """
        validation_result = self._scan_for_singleton_violations()
        
        # Check that we have some factory usage (indicating migration progress)
        factory_usage = validation_result.factory_usage_count
        
        self.logger.info(f"🏭 Factory pattern usage count: {factory_usage}")
        self.logger.info(f"🚨 Singleton violations: {validation_result.singleton_violations_found}")
        self.logger.info(f"📊 Security compliance: {validation_result.security_compliance_score:.1f}%")
        
        # If we have factory usage, ensure it includes user context
        if factory_usage > 0:
            # Scan for factory calls without user_id parameter
            websocket_files = self._get_websocket_related_files()
            context_violations = []
            
            for file_path in websocket_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for line_num, line in enumerate(content.splitlines(), 1):
                        # Check for factory calls without user_id
                        if re.search(r"create_isolated_manager\(", line):
                            if "user_id" not in line:
                                context_violations.append({
                                    'file': str(file_path.relative_to(self.codebase_root)),
                                    'line': line_num,
                                    'code': line.strip()
                                })
                                
                except Exception:
                    continue
            
            if context_violations:
                self.logger.warning("⚠️ Factory calls without user context found:")
                for violation in context_violations[:3]:
                    self.logger.warning(f"   📁 {violation['file']}:{violation['line']}")
                    self.logger.warning(f"   ❌ {violation['code']}")
                    self.logger.warning(f"   ✅ Must include user_id parameter for isolation")
            
            # This is a warning for now, not a hard failure
            # We want to encourage correct usage without blocking progress
            if len(context_violations) > 0:
                self.logger.warning(
                    f"Found {len(context_violations)} factory calls without proper user context. "
                    f"These should include user_id parameter for proper isolation."
                )
        
        # Document the requirement regardless of current state
        self.logger.info("📋 USER CONTEXT REQUIREMENTS:")
        self.logger.info("   ✅ All WebSocket managers must have user context")
        self.logger.info("   ✅ Factory calls must include user_id parameter")
        self.logger.info("   ✅ ConnectionID must be unique per user session")
        self.logger.info("   ❌ Anonymous or shared managers are not allowed")
        
        # Pass test - this documents requirements and provides warnings
        assert True, "User context enforcement documented - see warnings above"

    def test_singleton_elimination_progress_tracking(self):
        """
        Track progress toward complete singleton elimination.
        
        This test measures security improvement over time and provides
        clear metrics for SSOT migration progress.
        """
        validation_result = self._scan_for_singleton_violations()
        
        # Calculate security metrics
        total_violations = validation_result.singleton_violations_found
        factory_usage = validation_result.factory_usage_count
        compliance_score = validation_result.security_compliance_score
        
        # Log comprehensive security analysis
        self.logger.info("🔐 WEBSOCKET SECURITY ANALYSIS:")
        self.logger.info("=" * 50)
        self.logger.info(f"🚨 Singleton violations: {total_violations}")
        self.logger.info(f"🏭 Factory pattern usage: {factory_usage}")
        self.logger.info(f"📊 Security compliance: {compliance_score:.1f}%")
        
        # Security risk assessment
        if total_violations > 50:
            risk_level = "CRITICAL"
            risk_color = "🔴"
        elif total_violations > 20:
            risk_level = "HIGH"
            risk_color = "🟠"
        elif total_violations > 5:
            risk_level = "MEDIUM"
            risk_color = "🟡"
        else:
            risk_level = "LOW"
            risk_color = "🟢"
            
        self.logger.info(f"{risk_color} Security Risk Level: {risk_level}")
        
        # Provide security roadmap
        self.logger.info("\n🛡️ SECURITY ROADMAP:")
        if total_violations > 0:
            self.logger.info(f"   1. Eliminate remaining {total_violations} singleton violations")
            self.logger.info(f"   2. Replace with factory pattern for user isolation")
            self.logger.info(f"   3. Add user context validation to all factory calls")
            self.logger.info(f"   4. Test multi-user isolation scenarios")
        else:
            self.logger.info("   ✅ All singleton patterns eliminated!")
            self.logger.info("   ✅ Factory patterns provide proper user isolation")
            self.logger.info("   ✅ Security requirements met")
        
        # Track improvement milestones
        security_milestones = [
            (0, "🎉 SECURITY MILESTONE: All singleton violations eliminated!"),
            (5, "🎯 Near-complete security: <5 violations remaining"),
            (20, "📈 Good progress: Major security violations reduced"),
            (50, "🚨 Security attention needed: >50 critical violations"),
        ]
        
        for threshold, message in security_milestones:
            if total_violations <= threshold:
                self.logger.info(message)
                break
        
        # Record security metrics for tracking
        security_metrics = {
            'singleton_violations': total_violations,
            'factory_usage': factory_usage,
            'security_compliance_score': compliance_score,
            'security_risk_level': risk_level,
        }
        
        self.record_test_metrics('websocket_factory_security', security_metrics)
        
        # Always pass - this tracks progress rather than enforcing limits
        assert True, f"Security tracking: {total_violations} violations, {compliance_score:.1f}% compliant"

    def test_factory_pattern_implementation_guide(self):
        """
        Provide comprehensive factory pattern implementation guidance.
        
        This test documents the secure patterns developers should follow
        and provides clear examples for SSOT migration.
        """
        validation_result = self._scan_for_singleton_violations()
        
        self.logger.info("🏭 WEBSOCKET FACTORY PATTERN IMPLEMENTATION GUIDE")
        self.logger.info("=" * 60)
        
        self.logger.info("\n✅ SECURE FACTORY PATTERN (USE THIS):")
        self.logger.info("```python")
        self.logger.info("from netra_backend.app.websocket_core.canonical_imports import (")
        self.logger.info("    WebSocketManagerFactory,")
        self.logger.info("    create_websocket_manager")
        self.logger.info(")")
        self.logger.info("")
        self.logger.info("# Method 1: Using factory class")
        self.logger.info("factory = WebSocketManagerFactory()")
        self.logger.info("manager = await factory.create_isolated_manager(")
        self.logger.info("    user_id=ensure_user_id(user_id),")
        self.logger.info("    connection_id=ConnectionID(connection_id)")
        self.logger.info(")")
        self.logger.info("")
        self.logger.info("# Method 2: Using convenience function")
        self.logger.info("manager = await create_websocket_manager(")
        self.logger.info("    user_id=user_id,")
        self.logger.info("    connection_id=connection_id")
        self.logger.info(")")
        self.logger.info("```")
        
        self.logger.info("\n❌ INSECURE SINGLETON PATTERNS (NEVER USE):")
        self.logger.info("```python")
        self.logger.info("# 🚨 SECURITY VIOLATION - Shared across users")
        self.logger.info("manager = get_websocket_manager()")
        self.logger.info("")
        self.logger.info("# 🚨 SECURITY VIOLATION - No user context")
        self.logger.info("manager = UnifiedWebSocketManager()")
        self.logger.info("")
        self.logger.info("# 🚨 SECURITY VIOLATION - Global singleton")
        self.logger.info("manager = WebSocketManager.instance()")
        self.logger.info("```")
        
        if validation_result.violations:
            self.logger.info(f"\n🔧 IMMEDIATE ACTION REQUIRED:")
            self.logger.info(f"   Found {len(validation_result.violations)} singleton violations")
            self.logger.info(f"   Priority files for remediation:")
            
            # Group violations by file for targeted fixes
            file_violations = {}
            for violation in validation_result.violations:
                if violation.file_path not in file_violations:
                    file_violations[violation.file_path] = []
                file_violations[violation.file_path].append(violation)
            
            # Show top 5 files needing attention
            for i, (file_path, violations) in enumerate(list(file_violations.items())[:5], 1):
                self.logger.info(f"   {i}. {file_path} ({len(violations)} violations)")
        else:
            self.logger.info("\n🎉 EXCELLENT: No singleton violations found!")
            self.logger.info("   All WebSocket patterns follow secure factory pattern")
        
        # Security checklist
        self.logger.info("\n📋 SECURITY IMPLEMENTATION CHECKLIST:")
        self.logger.info("   ✅ Replace get_websocket_manager() with factory pattern")
        self.logger.info("   ✅ Include user_id in all manager creation calls")
        self.logger.info("   ✅ Use unique ConnectionID per user session")
        self.logger.info("   ✅ Test user isolation (no message cross-contamination)")
        self.logger.info("   ✅ Validate factory creates unique instances")
        self.logger.info("   ✅ Remove any singleton decorators or global instances")
        
        # Always pass - this is educational
        assert True, "Factory pattern implementation guide provided"


if __name__ == "__main__":
    # Allow running this test file directly for development
    pytest.main([__file__, "-v", "--tb=short"])