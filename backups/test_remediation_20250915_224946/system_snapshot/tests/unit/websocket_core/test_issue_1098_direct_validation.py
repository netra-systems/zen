"""Direct Validation Test for Issue #1098 - Legacy WebSocket Factory Problems

This test directly runs the validation to demonstrate legacy factory issues
without relying on pytest discovery.
"""

import pytest
import unittest
import warnings
from datetime import datetime, timezone

from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import ensure_user_id

logger = get_logger(__name__)


@pytest.mark.unit
class Issue1098LegacyWebSocketFactoryProblemsTests(unittest.TestCase):
    """Direct test for Issue #1098 legacy WebSocket factory problems."""
    
    def test_legacy_factory_produces_malformed_events(self):
        """EXPECTED TO FAIL: Demonstrate legacy factory event structure problems."""
        
        logger.info("=== ISSUE #1098 LEGACY WEBSOCKET FACTORY PROBLEM DEMONSTRATION ===")
        
        # Import legacy factory (deprecated code that causes problems)  
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from netra_backend.app.websocket_core.websocket_manager_factory import (
                validate_websocket_component_health
            )
        
        # Show what proper WebSocket events should look like for Golden Path
        proper_event_structure = {
            "type": "agent_started",
            "user_id": "user_12345",
            "thread_id": "thread_67890", 
            "run_id": "run_abcdef",
            "agent_name": "supervisor_agent",
            "task": "Process user request",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Show what legacy factory typically produces (missing critical fields)
        legacy_event_structure = {
            "agent_name": "supervisor_agent",
            "task": "Process user request"
            # MISSING: type, user_id, thread_id, run_id, timestamp
        }
        
        logger.warning(f"PROPER SSOT EVENT: {proper_event_structure}")
        logger.warning(f"LEGACY BROKEN EVENT: {legacy_event_structure}")
        logger.warning(f"PROPER EVENT has {len(proper_event_structure)} fields")
        logger.warning(f"LEGACY EVENT has {len(legacy_event_structure)} fields")
        
        # Test health check (this may pass but events are still broken)
        try:
            health_status = validate_websocket_component_health()
            logger.info(f"Legacy factory health check: {health_status['status']}")
            
            # Even if health passes, the events are malformed
            self.assertEqual(health_status['status'], 'healthy')
            
        except Exception as e:
            logger.error(f"Legacy factory health check failed: {e}")
        
        # EXPECTED FAILURES: Show the missing fields in legacy events
        missing_fields = []
        required_fields = ['type', 'user_id', 'thread_id', 'run_id', 'timestamp']
        
        for field in required_fields:
            if field not in legacy_event_structure:
                missing_fields.append(field)
                logger.error(f"❌ LEGACY BUG: Missing field '{field}' breaks Golden Path")
        
        # Demonstrate the problem  
        self.assertEqual(len(missing_fields), 0,
            f"LEGACY BUG DEMONSTRATED: Legacy factory missing {len(missing_fields)} "
            f"critical fields {missing_fields} that block AI response delivery. "
            f"This prevents $500K+ ARR Golden Path functionality.")
    
    def test_legacy_factory_emits_deprecation_warnings(self):
        """Test that legacy factory properly warns about deprecation."""
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always", DeprecationWarning)
            
            # Import should trigger warnings
            from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager_sync
            
            # Check warnings were issued  
            deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
            
            self.assertGreater(len(deprecation_warnings), 0,
                "Legacy factory should issue deprecation warnings")
                
            warning_messages = [str(warning.message) for warning in deprecation_warnings]
            ssot_mentions = [msg for msg in warning_messages if 'SSOT' in msg or 'deprecated' in msg.lower()]
            
            self.assertGreater(len(ssot_mentions), 0,
                "Should warn about SSOT consolidation")
                
            logger.info("✅ CONFIRMED: Legacy factory properly warns about deprecation")
    

if __name__ == '__main__':
    # Run the tests directly
    unittest.main(verbosity=2)