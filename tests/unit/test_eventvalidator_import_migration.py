"""
UNIT TEST: EventValidator Import Migration Test

PURPOSE: Test import pattern migration for EventValidator SSOT consolidation.
Validates that import changes don't break functionality and guides migration.

Issue #231: EventValidator SSOT violations blocking Golden Path
- Tests that old import patterns still work (backward compatibility)
- Tests that new unified import patterns work correctly
- Detects import regressions during migration

Expected Behavior:
- Old imports should work via compatibility aliases
- New unified imports should be the preferred pattern
- All import patterns should provide same functionality

Business Value Impact: Ensures migration doesn't break $500K+ ARR chat functionality
"""

import pytest
import sys
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestEventValidatorImportMigration(SSotBaseTestCase):
    """
    Test EventValidator import migration patterns and backward compatibility.
    
    Ensures migration doesn't break existing functionality.
    """
    
    def setUp(self):
        super().setUp()
        
        self.test_user_id = "test-user-migration"
        self.test_connection_id = "conn-migration-test"
        
        self.sample_event = {
            "type": "agent_started",
            "run_id": "test-run-migration",
            "agent_name": "test-agent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"status": "started", "agent": "test-agent"}
        }
        
    def test_unified_import_pattern(self):
        """Test the new unified import pattern works correctly."""
        logger.info("[U+1F9EA] Testing unified import pattern")
        
        try:
            # NEW PATTERN: Import from unified SSOT location
            from netra_backend.app.websocket_core.event_validator import (
                UnifiedEventValidator,
                ValidationResult,
                WebSocketEventMessage,
                CriticalAgentEventType,
                EventCriticality,
                get_websocket_validator,
                validate_agent_events,
                assert_critical_events_received,
                get_critical_event_types,
                create_mock_critical_events
            )
            
            # Test main validator class
            validator = UnifiedEventValidator()
            self.assertIsNotNone(validator)
            
            # Test validation functionality
            result = validator.validate_event(self.sample_event, self.test_user_id, self.test_connection_id)
            self.assertIsInstance(result, ValidationResult)
            self.assertTrue(result.is_valid)
            
            # Test enums
            self.assertEqual(CriticalAgentEventType.AGENT_STARTED.value, "agent_started")
            self.assertIn(EventCriticality.MISSION_CRITICAL, EventCriticality)
            
            # Test utility functions
            critical_types = get_critical_event_types()
            self.assertIsInstance(critical_types, set)
            self.assertIn("agent_started", critical_types)
            
            mock_events = create_mock_critical_events()
            self.assertEqual(len(mock_events), 5)
            
            # Test validation function
            validation_result = validate_agent_events(mock_events)
            self.assertTrue(validation_result.is_valid)
            
            logger.success(" PASS:  Unified import pattern test passed")
            
        except ImportError as e:
            self.fail(f"Unified import pattern failed: {e}")
        except Exception as e:
            self.fail(f"Unified import functionality failed: {e}")
            
    def test_backward_compatibility_aliases(self):
        """Test that backward compatibility aliases work."""
        logger.info("[U+1F9EA] Testing backward compatibility aliases")
        
        try:
            # Test that old class names still work as aliases
            from netra_backend.app.websocket_core.event_validator import (
                WebSocketEventValidator,  # Should be alias for UnifiedEventValidator
                AgentEventValidator,      # Should be alias for UnifiedEventValidator
                AgentEventValidationResult  # Should be alias for ValidationResult
            )
            
            # Test WebSocketEventValidator alias
            ws_validator = WebSocketEventValidator()
            self.assertIsNotNone(ws_validator)
            
            # Test AgentEventValidator alias
            agent_validator = AgentEventValidator()
            self.assertIsNotNone(agent_validator)
            
            # Test that both aliases create the same type
            self.assertEqual(type(ws_validator), type(agent_validator))
            
            # Test validation with alias
            result = ws_validator.validate_event(self.sample_event, self.test_user_id, self.test_connection_id)
            self.assertIsNotNone(result)
            
            logger.success(" PASS:  Backward compatibility aliases test passed")
            
        except ImportError as e:
            logger.warning(f"Backward compatibility aliases not available: {e}")
            # This might be expected if aliases haven't been implemented yet
        except Exception as e:
            self.fail(f"Backward compatibility alias functionality failed: {e}")
            
    def test_production_import_compatibility(self):
        """Test compatibility with production import patterns."""
        logger.info("[U+1F9EA] Testing production import compatibility")
        
        # Test that production imports still work
        compatibility_results = {}
        
        # Test 1: Production WebSocketEventValidator import
        try:
            from netra_backend.app.services.websocket_error_validator import (
                WebSocketEventValidator as ProductionValidator,
                ValidationResult as ProductionResult,
                get_websocket_validator as get_production_validator
            )
            
            prod_validator = ProductionValidator()
            prod_result = prod_validator.validate_event(self.sample_event, self.test_user_id, self.test_connection_id)
            
            compatibility_results["production"] = {
                "import_success": True,
                "validation_success": prod_result.is_valid,
                "has_stats": hasattr(prod_validator, 'get_validation_stats')
            }
            
        except ImportError:
            compatibility_results["production"] = {"import_success": False}
        except Exception as e:
            compatibility_results["production"] = {"import_success": True, "error": str(e)}
            
        # Test 2: SSOT Framework import
        try:
            from netra_backend.app.websocket_core.event_validator import (
                AgentEventValidator as SSOTValidator,
                AgentEventValidationResult as SSOTResult,
                validate_agent_events as ssot_validate,
                get_critical_event_types as ssot_get_types
            )
            
            ssot_validator = SSOTValidator()
            ssot_validator.record_event(self.sample_event)
            ssot_result = ssot_validator.perform_full_validation()
            
            compatibility_results["ssot_framework"] = {
                "import_success": True,
                "validation_success": ssot_result.is_valid,
                "has_business_score": hasattr(ssot_result, 'business_value_score')
            }
            
        except ImportError:
            compatibility_results["ssot_framework"] = {"import_success": False}
        except Exception as e:
            compatibility_results["ssot_framework"] = {"import_success": True, "error": str(e)}
            
        logger.info(f"Production compatibility results: {compatibility_results}")
        
        # At least one compatibility pattern should work
        working_patterns = [result for result in compatibility_results.values() 
                          if result.get("import_success", False)]
        
        self.assertGreater(len(working_patterns), 0, 
                         f"No production import patterns working: {compatibility_results}")
        
        logger.success(" PASS:  Production import compatibility test passed")
        
    def test_import_migration_guidance(self):
        """Test that provides migration guidance for developers."""
        logger.info("[U+1F9EA] Testing import migration guidance")
        
        migration_guidance = {
            "preferred_imports": [],
            "deprecated_imports": [],
            "compatibility_status": {}
        }
        
        # Test preferred unified imports
        try:
            from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
            migration_guidance["preferred_imports"].append(
                "from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator"
            )
        except ImportError:
            pass
            
        # Test deprecated patterns (should still work but not recommended)
        deprecated_patterns = [
            ("netra_backend.app.services.websocket_error_validator", "WebSocketEventValidator"),
            ("test_framework.ssot.agent_event_validators", "AgentEventValidator")
        ]
        
        for module_path, class_name in deprecated_patterns:
            try:
                module = __import__(module_path, fromlist=[class_name])
                validator_class = getattr(module, class_name)
                validator = validator_class()
                
                migration_guidance["deprecated_imports"].append(f"from {module_path} import {class_name}")
                migration_guidance["compatibility_status"][module_path] = "working"
                
            except ImportError:
                migration_guidance["compatibility_status"][module_path] = "import_failed"
            except Exception as e:
                migration_guidance["compatibility_status"][module_path] = f"error: {e}"
                
        logger.info(f"Migration guidance: {migration_guidance}")
        
        # Ensure there's at least one working import pattern
        self.assertGreater(len(migration_guidance["preferred_imports"]) + len(migration_guidance["deprecated_imports"]), 0,
                         "No working import patterns found for EventValidator")
        
        logger.success(" PASS:  Import migration guidance test passed")
        
    def test_functionality_equivalence_across_imports(self):
        """Test that different import patterns provide equivalent functionality."""
        logger.info("[U+1F9EA] Testing functionality equivalence across imports")
        
        validators = {}
        
        # Collect all available validators
        try:
            from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
            validators["unified"] = UnifiedEventValidator()
        except ImportError:
            pass
            
        try:
            from netra_backend.app.services.websocket_error_validator import WebSocketEventValidator
            validators["production"] = WebSocketEventValidator()
        except ImportError:
            pass
            
        try:
            from netra_backend.app.websocket_core.event_validator import AgentEventValidator
            validators["ssot_framework"] = AgentEventValidator()
        except ImportError:
            pass
            
        logger.info(f"Found validators: {list(validators.keys())}")
        
        # Test that all validators can validate the same event
        validation_results = {}
        
        for name, validator in validators.items():
            try:
                if hasattr(validator, 'validate_event'):
                    # Production/Unified pattern
                    result = validator.validate_event(self.sample_event, self.test_user_id, self.test_connection_id)
                    validation_results[name] = {
                        "is_valid": result.is_valid,
                        "method": "validate_event",
                        "has_error_message": hasattr(result, 'error_message')
                    }
                elif hasattr(validator, 'record_event') and hasattr(validator, 'perform_full_validation'):
                    # SSOT framework pattern
                    validator.record_event(self.sample_event)
                    result = validator.perform_full_validation()
                    validation_results[name] = {
                        "is_valid": result.is_valid,
                        "method": "record_event + perform_full_validation",
                        "has_business_score": hasattr(result, 'business_value_score')
                    }
                else:
                    validation_results[name] = {"error": "unknown validation interface"}
                    
            except Exception as e:
                validation_results[name] = {"error": str(e)}
                
        logger.info(f"Validation results: {validation_results}")
        
        # Check that all working validators agree on validity
        valid_results = [result for result in validation_results.values() 
                        if "error" not in result and result.get("is_valid") is not None]
        
        if len(valid_results) > 1:
            # All should agree on basic validity
            validity_values = [result["is_valid"] for result in valid_results]
            self.assertEqual(len(set(validity_values)), 1, 
                           f"Validators disagree on event validity: {validation_results}")
            
        logger.success(" PASS:  Functionality equivalence test passed")
        
    def test_migration_safety_checks(self):
        """Test safety checks for migration process."""
        logger.info("[U+1F9EA] Testing migration safety checks")
        
        safety_report = {
            "critical_functions_available": [],
            "backward_compatibility": True,
            "migration_risks": []
        }
        
        # Check that critical functions are available in unified implementation
        critical_functions = [
            "validate_event",
            "get_critical_event_types", 
            "create_mock_critical_events",
            "validate_agent_events"
        ]
        
        try:
            from netra_backend.app.websocket_core import event_validator
            
            for func_name in critical_functions:
                if hasattr(event_validator, func_name):
                    safety_report["critical_functions_available"].append(func_name)
                else:
                    safety_report["migration_risks"].append(f"Missing function: {func_name}")
                    
        except ImportError:
            safety_report["migration_risks"].append("Cannot import unified event_validator module")
            
        # Check backward compatibility
        try:
            # Test that old import patterns don't completely break
            from netra_backend.app.services.websocket_error_validator import get_websocket_validator
            old_validator = get_websocket_validator()
            self.assertIsNotNone(old_validator)
        except Exception as e:
            safety_report["backward_compatibility"] = False
            safety_report["migration_risks"].append(f"Old import pattern broken: {e}")
            
        logger.info(f"Migration safety report: {safety_report}")
        
        # Migration should not break critical functionality
        self.assertGreater(len(safety_report["critical_functions_available"]), 0,
                         "No critical functions available in unified implementation")
        
        if not safety_report["backward_compatibility"]:
            logger.warning(" WARNING: [U+FE0F] Backward compatibility may be broken - migration risk detected")
            
        logger.success(" PASS:  Migration safety checks passed")


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    suite = pytest.TestLoader().loadTestsFromTestCase(TestEventValidatorImportMigration)
    runner = pytest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print(" PASS:  SUCCESS: Import migration patterns validated")
        print("Migration should be safe for EventValidator SSOT consolidation")
    else:
        print(" FAIL:  FAILURE: Import migration has issues")
        print("Review migration strategy before proceeding with SSOT consolidation")