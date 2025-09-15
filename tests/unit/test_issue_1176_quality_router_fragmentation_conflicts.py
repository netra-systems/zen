"""
Quality MessageRouter Fragmentation Conflict Tests - Issue #1176

Focused tests for the specific fragmentation between MessageRouter and QualityMessageRouter.
These tests target the documented dependency chain failures and import conflicts.

Priority: P0 BLOCKER  
Business Impact: $500K+ ARR protection - quality routing infrastructure
"""

import unittest
import importlib
import sys
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestQualityMessageRouterFragmentation(SSotBaseTestCase):
    """Test specific fragmentation issues with QualityMessageRouter vs MessageRouter."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.core_router_class = None
        self.quality_router_class = None
        self.dependency_failures = []

    def test_quality_router_import_dependency_chain_failure(self):
        """
        Test that QualityMessageRouter import chain is broken as documented.
        
        Expected Failure: UnifiedWebSocketManager dependency issue prevents import.
        This reproduces the documented Issue #1181 dependency chain failure.
        """
        logger.info("Testing QualityMessageRouter import dependency chain...")
        
        # Test 1: Core MessageRouter should import successfully
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            self.core_router_class = MessageRouter
            logger.info("✅ Core MessageRouter import: SUCCESS")
        except Exception as e:
            self.fail(f"Core MessageRouter import failed: {e}")
        
        # Test 2: QualityMessageRouter import should fail due to dependency issues
        quality_import_success = False
        quality_import_error = None
        
        try:
            # Try direct import of QualityMessageRouter
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            self.quality_router_class = QualityMessageRouter
            quality_import_success = True
            logger.info("✅ QualityMessageRouter import: SUCCESS")
        except ImportError as e:
            quality_import_error = str(e)
            if "UnifiedWebSocketManager" in str(e):
                logger.info(f"❌ QualityMessageRouter import: EXPECTED FAILURE - {e}")
                self.dependency_failures.append(("UnifiedWebSocketManager", str(e)))
            else:
                logger.warning(f"❌ QualityMessageRouter import: UNEXPECTED FAILURE - {e}")
                self.dependency_failures.append(("Unexpected", str(e)))
        except Exception as e:
            quality_import_error = str(e)
            logger.error(f"❌ QualityMessageRouter import: CRITICAL FAILURE - {e}")
            self.dependency_failures.append(("Critical", str(e)))
        
        # Test 3: Verify fragmentation pattern
        if quality_import_success and self.core_router_class and self.quality_router_class:
            # If both imported successfully, check for interface conflicts
            self._validate_router_interface_conflicts()
        elif not quality_import_success:
            # This is the expected fragmentation issue documented in Issue #1181
            logger.info("FRAGMENTATION CONFIRMED: QualityMessageRouter import chain broken")
            
            # This test is designed to fail to highlight the dependency chain issue
            error_details = f"QualityMessageRouter import failed: {quality_import_error}"
            if "UnifiedWebSocketManager" in quality_import_error:
                self.fail(f"DEPENDENCY CHAIN FRAGMENTATION: {error_details}")
            else:
                self.fail(f"UNEXPECTED IMPORT FRAGMENTATION: {error_details}")

    def _validate_router_interface_conflicts(self):
        """Helper to validate interface conflicts if both routers are available."""
        logger.info("Validating router interface conflicts...")
        
        # Create instances for interface comparison
        core_router = self.core_router_class()
        
        # Mock QualityMessageRouter dependencies
        mock_supervisor = Mock()
        mock_db_session_factory = Mock()
        mock_quality_gate_service = Mock()
        mock_monitoring_service = Mock()
        
        quality_router = self.quality_router_class(
            supervisor=mock_supervisor,
            db_session_factory=mock_db_session_factory,
            quality_gate_service=mock_quality_gate_service,
            monitoring_service=mock_monitoring_service
        )
        
        # Compare handling mechanisms
        core_handlers = getattr(core_router, 'handlers', [])
        quality_handlers = getattr(quality_router, 'handlers', {})
        
        logger.info(f"Core router handlers: {len(core_handlers)} items")
        logger.info(f"Quality router handlers: {len(quality_handlers)} items")
        
        # Check for overlapping message type handling
        overlapping_types = []
        
        if hasattr(core_router, 'handlers') and hasattr(quality_router, 'handlers'):
            # Get supported message types from core router
            core_message_types = set()
            for handler in core_router.handlers:
                if hasattr(handler, 'supported_types'):
                    core_message_types.update(handler.supported_types)
            
            # Check if quality router handles any of the same types
            for handler_name, handler in quality_router.handlers.items():
                if hasattr(handler, 'supported_types'):
                    quality_types = set(handler.supported_types)
                    overlap = core_message_types.intersection(quality_types)
                    if overlap:
                        overlapping_types.extend(list(overlap))
        
        if overlapping_types:
            overlap_details = ", ".join(set(overlapping_types))
            self.fail(f"ROUTER INTERFACE CONFLICTS: Overlapping message types - {overlap_details}")

    def test_quality_router_dependency_resolution_failures(self):
        """
        Test specific dependency resolution failures that cause QualityMessageRouter issues.
        
        Expected Failure: Dependencies cannot be resolved, causing routing fragmentation.
        """
        logger.info("Testing QualityMessageRouter dependency resolution...")
        
        # List of dependencies QualityMessageRouter needs
        required_dependencies = [
            'netra_backend.app.dependencies.get_user_execution_context',
            'netra_backend.app.quality_enhanced_start_handler.QualityEnhancedStartAgentHandler',
            'netra_backend.app.services.quality_gate_service.QualityGateService',
            'netra_backend.app.services.quality_monitoring_service.QualityMonitoringService',
            'netra_backend.app.services.websocket.quality_alert_handler.QualityAlertHandler',
            'netra_backend.app.services.websocket.quality_metrics_handler.QualityMetricsHandler',
            'netra_backend.app.services.websocket.quality_report_handler.QualityReportHandler',
            'netra_backend.app.services.websocket.quality_validation_handler.QualityValidationHandler',
            'netra_backend.app.services.user_execution_context.UserExecutionContext',
        ]
        
        dependency_results = []
        
        for dependency_path in required_dependencies:
            try:
                # Split into module and class/function
                if '.' in dependency_path:
                    module_path, item_name = dependency_path.rsplit('.', 1)
                else:
                    module_path, item_name = dependency_path, None
                
                # Try to import the module
                module = importlib.import_module(module_path)
                
                if item_name:
                    # Try to get the specific item from the module
                    item = getattr(module, item_name)
                    dependency_results.append((dependency_path, True, None))
                    logger.debug(f"✅ Dependency resolved: {dependency_path}")
                else:
                    dependency_results.append((dependency_path, True, None))
                    logger.debug(f"✅ Module resolved: {dependency_path}")
                    
            except ImportError as e:
                dependency_results.append((dependency_path, False, f"ImportError: {e}"))
                logger.warning(f"❌ Dependency failed: {dependency_path} - {e}")
            except AttributeError as e:
                dependency_results.append((dependency_path, False, f"AttributeError: {e}"))
                logger.warning(f"❌ Dependency failed: {dependency_path} - {e}")
            except Exception as e:
                dependency_results.append((dependency_path, False, f"Error: {e}"))
                logger.error(f"❌ Dependency failed: {dependency_path} - {e}")
        
        # Analyze dependency resolution results
        successful_deps = [r for r in dependency_results if r[1]]
        failed_deps = [r for r in dependency_results if not r[1]]
        
        logger.info(f"Dependency resolution results:")
        logger.info(f"  Successful: {len(successful_deps)}/{len(required_dependencies)}")
        logger.info(f"  Failed: {len(failed_deps)}/{len(required_dependencies)}")
        
        for dep_path, success, error in failed_deps:
            logger.info(f"  FAILED: {dep_path} - {error}")
        
        # If dependencies fail, it explains QualityMessageRouter fragmentation
        if failed_deps:
            failure_summary = "; ".join([f"{r[0]}: {r[2]}" for r in failed_deps])
            self.fail(f"DEPENDENCY RESOLUTION FRAGMENTATION: {len(failed_deps)} dependencies failed - {failure_summary}")

    def test_router_instantiation_conflicts(self):
        """
        Test that router instantiation patterns create conflicts.
        
        Expected Failure: Different instantiation requirements prevent unified usage.
        """
        logger.info("Testing router instantiation conflicts...")
        
        instantiation_results = []
        
        # Test 1: Core MessageRouter instantiation (should be simple)
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            core_router = MessageRouter()
            instantiation_results.append(('core', True, len(core_router.handlers), None))
            logger.info(f"✅ Core MessageRouter instantiation: SUCCESS - {len(core_router.handlers)} handlers")
        except Exception as e:
            instantiation_results.append(('core', False, 0, str(e)))
            logger.error(f"❌ Core MessageRouter instantiation: FAILED - {e}")
        
        # Test 2: QualityMessageRouter instantiation (requires dependencies)
        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            
            # Create mock dependencies - this reveals the complexity fragmentation
            mock_supervisor = Mock()
            mock_db_session_factory = Mock()
            mock_quality_gate_service = Mock()
            mock_monitoring_service = Mock()
            
            quality_router = QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )
            
            handler_count = len(quality_router.handlers) if hasattr(quality_router, 'handlers') else 0
            instantiation_results.append(('quality', True, handler_count, None))
            logger.info(f"✅ QualityMessageRouter instantiation: SUCCESS - {handler_count} handlers")
            
        except ImportError as e:
            instantiation_results.append(('quality', False, 0, f"ImportError: {e}"))
            logger.warning(f"❌ QualityMessageRouter instantiation: IMPORT FAILED - {e}")
        except Exception as e:
            instantiation_results.append(('quality', False, 0, str(e)))
            logger.error(f"❌ QualityMessageRouter instantiation: FAILED - {e}")
        
        # Analyze instantiation complexity difference
        successful_instantiations = [r for r in instantiation_results if r[1]]
        failed_instantiations = [r for r in instantiation_results if not r[1]]
        
        logger.info(f"Instantiation analysis:")
        for name, success, handler_count, error in instantiation_results:
            if success:
                logger.info(f"  {name}: SUCCESS - {handler_count} handlers")
            else:
                logger.info(f"  {name}: FAILED - {error}")
        
        # Check for instantiation complexity fragmentation
        if len(successful_instantiations) == 2:
            # Both routers can be instantiated - check complexity difference
            core_result = next(r for r in successful_instantiations if r[0] == 'core')
            quality_result = next(r for r in successful_instantiations if r[0] == 'quality')
            
            # Core router requires 0 dependencies, Quality router requires 4 dependencies
            # This is a fragmentation in instantiation patterns
            self.fail("INSTANTIATION FRAGMENTATION: Core router needs 0 deps, Quality router needs 4 deps")
        
        elif failed_instantiations:
            # Some routers failed to instantiate - clear fragmentation
            failure_details = "; ".join([f"{r[0]}: {r[3]}" for r in failed_instantiations])
            self.fail(f"INSTANTIATION FRAGMENTATION: {failure_details}")

    def test_message_handling_pattern_fragmentation(self):
        """
        Test that message handling patterns differ between routers causing fragmentation.
        
        Expected Failure: Inconsistent message handling patterns.
        """
        logger.info("Testing message handling pattern fragmentation...")
        
        handling_patterns = {}
        
        # Analyze Core MessageRouter pattern
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            core_router = MessageRouter()
            
            handling_patterns['core'] = {
                'handler_storage': 'list' if isinstance(core_router.handlers, list) else 'other',
                'handler_count': len(core_router.handlers),
                'has_custom_handlers': hasattr(core_router, 'custom_handlers'),
                'has_builtin_handlers': hasattr(core_router, 'builtin_handlers'),
                'has_fallback': hasattr(core_router, 'fallback_handler'),
                'has_stats': hasattr(core_router, 'routing_stats'),
                'initialization_params': 0  # No params needed
            }
            
        except Exception as e:
            handling_patterns['core'] = {'error': str(e)}
        
        # Analyze QualityMessageRouter pattern (if available)
        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            
            # Count required initialization parameters
            import inspect
            sig = inspect.signature(QualityMessageRouter.__init__)
            param_count = len([p for p in sig.parameters.values() if p.name != 'self'])
            
            handling_patterns['quality'] = {
                'handler_storage': 'unknown',  # Can't instantiate without dependencies
                'handler_count': 'unknown',
                'initialization_params': param_count,
                'requires_dependencies': True
            }
            
        except ImportError as e:
            handling_patterns['quality'] = {'import_error': str(e)}
        except Exception as e:
            handling_patterns['quality'] = {'error': str(e)}
        
        # Compare patterns
        logger.info("Message handling pattern analysis:")
        for router_name, pattern in handling_patterns.items():
            logger.info(f"  {router_name}: {pattern}")
        
        # Check for pattern fragmentation
        fragmentation_issues = []
        
        if 'core' in handling_patterns and 'quality' in handling_patterns:
            core_pattern = handling_patterns['core']
            quality_pattern = handling_patterns['quality']
            
            # Check for initialization parameter differences
            if 'initialization_params' in core_pattern and 'initialization_params' in quality_pattern:
                if core_pattern['initialization_params'] != quality_pattern['initialization_params']:
                    fragmentation_issues.append(
                        f"Init params: core={core_pattern['initialization_params']}, "
                        f"quality={quality_pattern['initialization_params']}"
                    )
            
            # Check for structural differences
            if 'error' in core_pattern or 'error' in quality_pattern:
                fragmentation_issues.append("Router instantiation errors indicate structural fragmentation")
            
            if 'import_error' in quality_pattern:
                fragmentation_issues.append(f"Quality router import fragmentation: {quality_pattern['import_error']}")
        
        if fragmentation_issues:
            issues_summary = "; ".join(fragmentation_issues)
            self.fail(f"MESSAGE HANDLING PATTERN FRAGMENTATION: {issues_summary}")


if __name__ == '__main__':
    unittest.main()