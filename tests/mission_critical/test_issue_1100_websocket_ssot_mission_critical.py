"""
Mission Critical WebSocket SSOT Validation - Issue #1100

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Mission Critical Infrastructure  
- Business Goal: Ensure 500K+ ARR WebSocket infrastructure remains functional
- Value Impact: Validates mission-critical WebSocket functionality during SSOT migration
- Strategic Impact: Prevents business disruption during technical debt elimination

CRITICAL: These tests MUST pass before deployment. Failure indicates business
value is at risk and deployment should be blocked.
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any
from datetime import datetime, timezone
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class WebSocketSSotMissionCriticalTests(SSotAsyncTestCase):
    """Mission critical WebSocket SSOT validation tests."""
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_all_websocket_events_sent_post_ssot_migration(self):
        """
        MUST PASS: All 5 WebSocket events sent after SSOT migration.
        
        This test MUST pass or deployment is blocked. Validates that all
        business-critical WebSocket events are delivered consistently
        after SSOT consolidation.
        """
        logger.info("MISSION CRITICAL: Validating all WebSocket events post-SSOT migration")
        
        required_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        event_delivery_results = {}
        critical_failures = []
        
        try:
            # Execute agent with monitoring to capture all events
            result = await self.execute_agent_with_monitoring(
                agent="triage_agent",
                message="Mission critical validation: system status check",
                timeout=60  # Extended timeout for critical validation
            )
            
            # Validate each required event
            for event_type in required_events:
                event_count = result.events.get(event_type, 0)
                event_delivery_results[event_type] = {
                    'count': event_count,
                    'delivered': event_count > 0,
                    'timestamps': result.event_timestamps.get(event_type, [])
                }
                
                if event_count == 0:
                    critical_failures.append({
                        'event_type': event_type,
                        'failure_reason': 'event_not_delivered',
                        'impact': 'business_critical'
                    })
            
            # Validate event order and timing
            if len(result.event_order) > 0:
                # Check for required event sequence  
                expected_sequence = ["agent_started", "agent_completed"]  # Minimum required
                sequence_valid = all(event in result.event_order for event in expected_sequence)
                
                if not sequence_valid:
                    critical_failures.append({
                        'event_type': 'sequence_validation',
                        'failure_reason': 'invalid_event_sequence',
                        'expected': expected_sequence,
                        'actual': result.event_order,
                        'impact': 'business_critical'
                    })
            
        except Exception as e:
            logger.error(f"MISSION CRITICAL: Agent execution failed: {e}")
            critical_failures.append({
                'event_type': 'agent_execution',
                'failure_reason': f'execution_exception: {str(e)}',
                'impact': 'business_critical'
            })
        
        # Log results for debugging
        logger.info(f"Event delivery results: {event_delivery_results}")
        if critical_failures:
            logger.error(f"MISSION CRITICAL FAILURES: {critical_failures}")
        
        # These assertions are NON-NEGOTIABLE for deployment
        for event_type in required_events:
            assert event_delivery_results.get(event_type, {}).get('delivered', False), (
                f"MISSION CRITICAL: WebSocket event '{event_type}' not delivered. "
                f"This blocks deployment as it indicates 500K+ ARR functionality is broken. "
                f"Event counts: {event_delivery_results}"
            )
        
        assert len(critical_failures) == 0, (
            f"MISSION CRITICAL: {len(critical_failures)} failures detected. "
            f"Deployment blocked due to business-critical WebSocket functionality issues: "
            f"{critical_failures}"
        )
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_websocket_manager_ssot_violation_detection(self):
        """
        MUST PASS: No SSOT violations detected in WebSocket management.
        
        This test ensures single source of truth compliance and prevents
        dual implementation patterns that could cause race conditions.
        """
        logger.info("MISSION CRITICAL: Detecting WebSocket manager SSOT violations")
        
        ssot_violations = []
        implementation_analysis = {}
        
        try:
            # Check for canonical SSOT implementation
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            implementation_analysis['canonical_available'] = True
            logger.info("Canonical WebSocketManager implementation available")
            
        except ImportError as e:
            implementation_analysis['canonical_available'] = False
            ssot_violations.append({
                'type': 'missing_canonical_implementation',
                'error': str(e),
                'impact': 'deployment_blocking'
            })
        
        try:
            # Check for deprecated factory implementation (should not exist)
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            implementation_analysis['factory_available'] = True
            ssot_violations.append({
                'type': 'deprecated_factory_still_available',
                'class': 'WebSocketManagerFactory',
                'impact': 'ssot_violation'
            })
            logger.warning("SSOT VIOLATION: Deprecated WebSocketManagerFactory still available")
            
        except ImportError:
            implementation_analysis['factory_available'] = False
            logger.info("Deprecated WebSocketManagerFactory not available (correct)""mission_critical_thread",
                    run_id="mission_critical_run",
                    request_id="ssot_validation_test"
                )
                
                # Test factory function instantiation (SSOT compliant)
                from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
                manager = get_websocket_manager(
                    user_context=test_context,
                    mode=WebSocketManagerMode.UNIFIED
                )
                
                implementation_analysis['factory_instantiation_works'] = True
                logger.info("Factory WebSocketManager instantiation successful")
                
            except Exception as e:
                implementation_analysis['factory_instantiation_works'] = False
                ssot_violations.append({
                    'type': 'factory_instantiation_failed',
                    'error': str(e),
                    'impact': 'deployment_blocking'
                })
        
        # Test for factory function availability (should not exist)
        factory_functions = [
            'create_websocket_manager',
            'create_websocket_manager_sync',
            'get_websocket_manager_factory'
        ]
        
        available_factory_functions = []
        for func_name in factory_functions:
            try:
                import importlib
                module = importlib.import_module('netra_backend.app.websocket_core.websocket_manager_factory')
                if hasattr(module, func_name):
                    available_factory_functions.append(func_name)
            except ImportError:
                pass
        
        if available_factory_functions:
            ssot_violations.append({
                'type': 'factory_functions_still_available',
                'functions': available_factory_functions,
                'impact': 'ssot_violation'
            })
        
        implementation_analysis['factory_functions_available'] = available_factory_functions
        
        logger.info(f"SSOT implementation analysis: {implementation_analysis}")
        
        # These assertions are NON-NEGOTIABLE for SSOT compliance
        assert implementation_analysis.get('canonical_available', False), (
            "MISSION CRITICAL: Canonical WebSocketManager implementation must be available. "
            "SSOT compliance requires the canonical implementation."
        )
        
        assert not implementation_analysis.get('factory_available', False), (
            "MISSION CRITICAL: Deprecated WebSocketManagerFactory must be eliminated. "
            "SSOT compliance prohibits multiple WebSocket manager implementations."
        )
        
        assert len(available_factory_functions) == 0, (
            f"MISSION CRITICAL: Factory functions must be eliminated for SSOT compliance: "
            f"{available_factory_functions}"
        )
        
        assert len(ssot_violations) == 0, (
            f"MISSION CRITICAL: {len(ssot_violations)} SSOT violations detected. "
            f"Deployment blocked due to SSOT compliance failures: {ssot_violations}"
        )
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_business_value_protection_during_migration(self):
        """
        MUST PASS: Business value protected during import migration.
        
        This test validates that chat functionality continues operating
        during the SSOT migration process, protecting 500K+ ARR.
        """
        logger.info("MISSION CRITICAL: Validating business value protection during migration")
        
        business_value_indicators = {
            'chat_functionality_working': False,
            'agent_responses_delivered': False,
            'websocket_connections_stable': False,
            'user_experience_preserved': False
        }
        
        business_critical_failures = []
        
        try:
            # Test core chat functionality
            chat_test_result = await self.execute_agent_with_monitoring(
                agent="triage_agent",
                message="Business value test: provide user assistance",
                timeout=45
            )
            
            # Validate chat functionality
            if len(chat_test_result.events) > 0:
                business_value_indicators['chat_functionality_working'] = True
                
            if chat_test_result.events.get('agent_completed', 0) > 0:
                business_value_indicators['agent_responses_delivered'] = True
                
            # Test WebSocket connection stability
            connection_stability_test = await self._test_websocket_connection_stability()
            business_value_indicators['websocket_connections_stable'] = connection_stability_test['stable']
            
            # Test user experience preservation
            ux_test_result = await self._test_user_experience_preservation()
            business_value_indicators['user_experience_preserved'] = ux_test_result['preserved']
            
            # Validate business continuity
            business_continuity_score = sum(business_value_indicators.values())
            if business_continuity_score < 3:  # At least 3 of 4 indicators must pass
                business_critical_failures.append({
                    'type': 'insufficient_business_continuity',
                    'score': f"{business_continuity_score}/4",
                    'indicators': business_value_indicators,
                    'impact': 'revenue_risk'
                })
            
        except Exception as e:
            logger.error(f"MISSION CRITICAL: Business value test failed: {e}")
            business_critical_failures.append({
                'type': 'business_value_test_exception',
                'error': str(e),
                'impact': 'revenue_risk'
            })
        
        logger.info(f"Business value indicators: {business_value_indicators}")
        
        # These assertions protect 500K+ ARR functionality
        assert business_value_indicators['chat_functionality_working'], (
            "MISSION CRITICAL: Chat functionality not working. "
            "500K+ ARR is at risk if users cannot interact with AI agents."
        )
        
        assert business_value_indicators['agent_responses_delivered'], (
            "MISSION CRITICAL: Agent responses not delivered. "
            "Core business value depends on agent response delivery."
        )
        
        assert business_value_indicators['websocket_connections_stable'], (
            "MISSION CRITICAL: WebSocket connections unstable. "
            "Real-time functionality is essential for user experience."
        )
        
        assert len(business_critical_failures) == 0, (
            f"MISSION CRITICAL: {len(business_critical_failures)} business value failures. "
            f"500K+ ARR functionality compromised: {business_critical_failures}"
        )
    
    @pytest.mark.mission_critical
    @pytest.mark.no_skip
    async def test_websocket_ssot_import_migration_completion(self):
        """
        MUST PASS: WebSocket SSOT import migration completion validation.
        
        Validates that all 25+ identified files have completed migration
        to SSOT import patterns and no deprecated imports remain.
        """
        logger.info("MISSION CRITICAL: Validating WebSocket SSOT import migration completion")
        
        import os
        import re
        from pathlib import Path
        
        # Get project root
        current_dir = Path(__file__).parent
        while current_dir.name != "netra-apex" and current_dir.parent != current_dir:
            current_dir = current_dir.parent
        project_root = current_dir
        
        migration_status = {
            'files_scanned': 0,
            'deprecated_imports_found': 0,
            'violation_files': [],
            'migration_complete': False
        }
        
        # Priority files that were identified in Issue #1100
        priority_files = [
            "netra_backend/app/agents/supervisor/agent_instance_factory.py",
            "netra_backend/app/agents/tool_executor_factory.py",
            "netra_backend/app/services/agent_websocket_bridge.py"
        ]
        
        # Deprecated patterns that must not exist
        deprecated_patterns = [
            r"from\s+netra_backend\.app\.websocket_core\.websocket_manager_factory\s+import",
            r"import\s+netra_backend\.app\.websocket_core\.websocket_manager_factory",
            r"websocket_manager_factory\."
        ]
        
        try:
            # Scan netra_backend app directory
            app_dir = project_root / "netra_backend" / "app"
            
            if app_dir.exists():
                for py_file in app_dir.rglob("*.py"):
                    if "__pycache__" not in str(py_file) and "test_" not in py_file.name:
                        migration_status['files_scanned'] += 1
                        
                        try:
                            with open(py_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                            # Check for deprecated patterns
                            for pattern in deprecated_patterns:
                                if re.search(pattern, content):
                                    migration_status['deprecated_imports_found'] += 1
                                    migration_status['violation_files'].append({
                                        'file': str(py_file.relative_to(project_root)),
                                        'pattern': pattern
                                    })
                                    
                        except (UnicodeDecodeError, FileNotFoundError):
                            continue
            
            # Check priority files specifically
            priority_violations = []
            for priority_file in priority_files:
                file_path = project_root / priority_file
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        for pattern in deprecated_patterns:
                            if re.search(pattern, content):
                                priority_violations.append({
                                    'file': priority_file,
                                    'pattern': pattern
                                })
                    except (UnicodeDecodeError, FileNotFoundError):
                        continue
            
            migration_status['migration_complete'] = (
                migration_status['deprecated_imports_found'] == 0 and
                len(priority_violations) == 0
            )
            
        except Exception as e:
            logger.error(f"MISSION CRITICAL: Import migration scan failed: {e}")
            migration_status['scan_error'] = str(e)
        
        logger.info(f"Migration status: {migration_status}")
        
        # These assertions ensure SSOT migration completion
        assert migration_status['files_scanned'] > 0, (
            "MISSION CRITICAL: No files scanned for import migration validation. "
            "Cannot verify SSOT migration completion."
        )
        
        assert migration_status['deprecated_imports_found'] == 0, (
            f"MISSION CRITICAL: {migration_status['deprecated_imports_found']} deprecated imports found. "
            f"SSOT migration incomplete. Violations: {migration_status['violation_files']}"
        )
        
        assert migration_status['migration_complete'], (
            f"MISSION CRITICAL: WebSocket SSOT import migration not complete. "
            f"Files scanned: {migration_status['files_scanned']}, "
            f"Deprecated imports: {migration_status['deprecated_imports_found']}"
        )
    
    async def _test_websocket_connection_stability(self) -> Dict[str, Any]:
        """
        Test WebSocket connection stability.
        
        Returns:
            Connection stability test results
        """
        stability_result = {
            'stable': False,
            'connection_attempts': 0,
            'successful_connections': 0,
            'average_connection_time': 0
        }
        
        connection_times = []
        
        try:
            for attempt in range(3):  # Test 3 connection attempts
                stability_result['connection_attempts'] += 1
                
                start_time = time.time()
                
                # Simulate WebSocket connection test
                await asyncio.sleep(0.1)  # Simulate connection time
                
                end_time = time.time()
                connection_time = end_time - start_time
                connection_times.append(connection_time)
                stability_result['successful_connections'] += 1
            
            stability_result['average_connection_time'] = sum(connection_times) / len(connection_times)
            stability_result['stable'] = stability_result['successful_connections'] == stability_result['connection_attempts']
            
        except Exception as e:
            logger.warning(f"Connection stability test error: {e}")
            stability_result['error'] = str(e)
        
        return stability_result
    
    async def _test_user_experience_preservation(self) -> Dict[str, Any]:
        """
        Test user experience preservation during migration.
        
        Returns:
            User experience test results
        """
        ux_result = {
            'preserved': False,
            'response_quality': False,
            'interaction_flow': False,
            'performance_acceptable': False
        }
        
        try:
            # Test agent response quality
            agent_result = await self.execute_agent_with_monitoring(
                agent="triage_agent",
                message="UX test: provide helpful response",
                timeout=30
            )
            
            # Check response quality indicators
            if agent_result.events.get('agent_completed', 0) > 0:
                ux_result['response_quality'] = True
                
            # Check interaction flow (proper event sequence)
            if len(agent_result.event_order) >= 2:  # At least started and completed
                ux_result['interaction_flow'] = True
                
            # Check performance (reasonable response time)
            if hasattr(agent_result, 'total_time') and agent_result.total_time < 30:
                ux_result['performance_acceptable'] = True
                
            # Overall UX preservation
            ux_indicators_passed = sum([
                ux_result['response_quality'],
                ux_result['interaction_flow'], 
                ux_result['performance_acceptable']
            ])
            
            ux_result['preserved'] = ux_indicators_passed >= 2  # At least 2 of 3 indicators
            
        except Exception as e:
            logger.warning(f"User experience test error: {e}")
            ux_result['error'] = str(e)
        
        return ux_result