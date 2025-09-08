"""
WebSocket Manager Protocol Validator - Five Whys Prevention Tool

This module provides validation utilities to ensure WebSocket manager implementations
comply with the WebSocketManagerProtocol, preventing the root cause identified in
the Five Whys analysis.

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all user tiers)  
- Business Goal: Prevent system failures from interface drift
- Value Impact: Ensures reliable WebSocket communication across all implementations
- Revenue Impact: Prevents critical errors that cause user experience failures

Root Cause Prevention:
This tool directly addresses WHY #5 from Five Whys analysis by providing runtime
validation that formal interface contracts are maintained during migrations.
"""

import asyncio
import inspect
from typing import Any, Dict, List, Optional
from datetime import datetime

from netra_backend.app.websocket_core.protocols import (
    WebSocketManagerProtocol, 
    WebSocketManagerProtocolValidator
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def validate_websocket_manager_on_startup(manager: Any, context: str = "Startup") -> bool:
    """
    Validate WebSocket manager protocol compliance during system startup.
    
    This function ensures that WebSocket managers are protocol compliant before
    they are used in production, preventing the Five Whys root cause.
    
    Args:
        manager: WebSocket manager to validate
        context: Context string for logging and error messages
        
    Returns:
        True if validation passes, False otherwise
        
    Raises:
        RuntimeError: If validation fails and strict mode is enabled
    """
    try:
        logger.info(f"🔍 Validating WebSocket Manager Protocol compliance for {context}...")
        
        validation_result = WebSocketManagerProtocolValidator.validate_manager_protocol(manager)
        
        if validation_result['compliant']:
            logger.info(
                f"✅ PROTOCOL VALIDATION PASSED: {context} WebSocket manager "
                f"({validation_result['manager_type']}) is fully compliant with WebSocketManagerProtocol. "
                f"Compliance: {validation_result['summary']['compliance_percentage']}%"
            )
            return True
        else:
            logger.error(
                f"❌ PROTOCOL VALIDATION FAILED: {context} WebSocket manager "
                f"({validation_result['manager_type']}) is NOT compliant with WebSocketManagerProtocol. "
                f"Compliance: {validation_result['summary']['compliance_percentage']}%. "
                f"Missing methods: {validation_result['missing_methods']}. "
                f"Invalid signatures: {validation_result['invalid_signatures']}"
            )
            
            # Log detailed failure information for debugging
            for method_name, details in validation_result['method_check_details'].items():
                if not (details['exists'] and details['callable'] and details['async_correct']):
                    logger.error(
                        f"  ❌ Method '{method_name}': exists={details['exists']}, "
                        f"callable={details['callable']}, async_correct={details['async_correct']}"
                    )
            
            return False
            
    except Exception as e:
        logger.error(f"Protocol validation failed with exception for {context}: {e}")
        return False


def create_protocol_compliance_report(manager: Any) -> Dict[str, Any]:
    """
    Create a comprehensive protocol compliance report for documentation.
    
    This function generates detailed compliance reports that can be used for
    auditing and ensuring long-term protocol adherence.
    
    Args:
        manager: WebSocket manager to analyze
        
    Returns:
        Detailed compliance report dictionary
    """
    try:
        validation_result = WebSocketManagerProtocolValidator.validate_manager_protocol(manager)
        
        # Enhance with additional analysis
        enhanced_report = {
            **validation_result,
            'report_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'report_version': '1.0.0',
                'purpose': 'Five Whys Root Cause Prevention',
                'root_cause': 'lack of formal interface contracts causing implementation drift'
            },
            'five_whys_critical_methods': {
                'get_connection_id_by_websocket': validation_result['method_check_details'].get('get_connection_id_by_websocket', {}),
                'update_connection_thread': validation_result['method_check_details'].get('update_connection_thread', {})
            },
            'recommendations': []
        }
        
        # Generate specific recommendations
        if not validation_result['compliant']:
            if validation_result['missing_methods']:
                enhanced_report['recommendations'].append({
                    'priority': 'HIGH',
                    'category': 'Missing Methods',
                    'description': f"Implement missing methods: {', '.join(validation_result['missing_methods'])}",
                    'root_cause_prevention': True
                })
            
            if validation_result['invalid_signatures']:
                enhanced_report['recommendations'].append({
                    'priority': 'HIGH', 
                    'category': 'Invalid Signatures',
                    'description': f"Fix method signatures: {', '.join(validation_result['invalid_signatures'])}",
                    'root_cause_prevention': True
                })
        
        # Check for Five Whys critical methods specifically
        five_whys_methods = ['get_connection_id_by_websocket', 'update_connection_thread']
        for method in five_whys_methods:
            if method in validation_result['missing_methods']:
                enhanced_report['recommendations'].append({
                    'priority': 'CRITICAL',
                    'category': 'Five Whys Prevention',
                    'description': f"URGENT: Implement {method} to prevent AttributeError during agent execution",
                    'root_cause_prevention': True,
                    'five_whys_critical': True
                })
        
        if validation_result['compliant']:
            enhanced_report['recommendations'].append({
                'priority': 'LOW',
                'category': 'Maintenance',
                'description': 'Continue monitoring protocol compliance during future migrations',
                'root_cause_prevention': True
            })
        
        return enhanced_report
        
    except Exception as e:
        logger.error(f"Failed to create compliance report: {e}")
        return {
            'compliant': False,
            'error': str(e),
            'report_metadata': {
                'generated_at': datetime.utcnow().isoformat(),
                'error_occurred': True
            }
        }


async def test_critical_method_functionality(manager: Any) -> Dict[str, Any]:
    """
    Test the functionality of Five Whys critical methods.
    
    This function performs runtime testing of the critical methods that were
    missing in the original Five Whys analysis, ensuring they work correctly.
    
    Args:
        manager: WebSocket manager to test
        
    Returns:
        Test results dictionary
    """
    test_results = {
        'overall_success': False,
        'tests_run': 0,
        'tests_passed': 0,
        'test_details': {},
        'errors': []
    }
    
    try:
        # Test 1: get_connection_id_by_websocket with None input
        test_results['tests_run'] += 1
        test_name = 'get_connection_id_by_websocket_none'
        try:
            result = manager.get_connection_id_by_websocket(None)
            test_results['test_details'][test_name] = {
                'passed': result is None,
                'result': str(result),
                'description': 'Should return None for None websocket input'
            }
            if result is None:
                test_results['tests_passed'] += 1
        except Exception as e:
            test_results['test_details'][test_name] = {
                'passed': False,
                'error': str(e),
                'description': 'Should handle None input gracefully'
            }
            test_results['errors'].append(f"{test_name}: {e}")
        
        # Test 2: update_connection_thread with non-existent connection
        test_results['tests_run'] += 1
        test_name = 'update_connection_thread_missing'
        try:
            result = manager.update_connection_thread("non-existent-id", "test-thread")
            test_results['test_details'][test_name] = {
                'passed': result is False,
                'result': str(result),
                'description': 'Should return False for non-existent connection'
            }
            if result is False:
                test_results['tests_passed'] += 1
        except Exception as e:
            test_results['test_details'][test_name] = {
                'passed': False,
                'error': str(e),
                'description': 'Should handle missing connection gracefully'
            }
            test_results['errors'].append(f"{test_name}: {e}")
        
        # Test 3: send_to_thread functionality
        if hasattr(manager, 'send_to_thread'):
            test_results['tests_run'] += 1
            test_name = 'send_to_thread_basic'
            try:
                # This should return False for non-existent thread without throwing
                result = await manager.send_to_thread("non-existent-thread", {"test": "message"})
                test_results['test_details'][test_name] = {
                    'passed': isinstance(result, bool),
                    'result': str(result),
                    'description': 'Should return boolean for thread message sending'
                }
                if isinstance(result, bool):
                    test_results['tests_passed'] += 1
            except Exception as e:
                test_results['test_details'][test_name] = {
                    'passed': False,
                    'error': str(e),
                    'description': 'Should handle thread messaging gracefully'
                }
                test_results['errors'].append(f"{test_name}: {e}")
        
        # Test 4: get_connection_health functionality
        if hasattr(manager, 'get_connection_health'):
            test_results['tests_run'] += 1
            test_name = 'get_connection_health_basic'
            try:
                result = manager.get_connection_health("test-user")
                test_results['test_details'][test_name] = {
                    'passed': isinstance(result, dict),
                    'result': str(type(result)),
                    'description': 'Should return dict for connection health'
                }
                if isinstance(result, dict):
                    test_results['tests_passed'] += 1
            except Exception as e:
                test_results['test_details'][test_name] = {
                    'passed': False,
                    'error': str(e),
                    'description': 'Should return health information as dict'
                }
                test_results['errors'].append(f"{test_name}: {e}")
        
        # Calculate overall success
        test_results['overall_success'] = (
            test_results['tests_run'] > 0 and 
            test_results['tests_passed'] == test_results['tests_run'] and
            len(test_results['errors']) == 0
        )
        
        test_results['success_rate'] = (
            test_results['tests_passed'] / test_results['tests_run'] * 100
            if test_results['tests_run'] > 0 else 0
        )
        
        if test_results['overall_success']:
            logger.info(
                f"✅ Five Whys Critical Method Testing PASSED: "
                f"{test_results['tests_passed']}/{test_results['tests_run']} tests passed"
            )
        else:
            logger.warning(
                f"⚠️  Five Whys Critical Method Testing ISSUES: "
                f"{test_results['tests_passed']}/{test_results['tests_run']} tests passed. "
                f"Errors: {len(test_results['errors'])}"
            )
        
        return test_results
        
    except Exception as e:
        logger.error(f"Critical method functionality testing failed: {e}")
        test_results['errors'].append(f"Testing framework error: {e}")
        return test_results


def log_protocol_compliance_summary(managers: List[tuple]) -> None:
    """
    Log a summary of protocol compliance across multiple managers.
    
    Args:
        managers: List of (manager, context_name) tuples to validate
    """
    logger.info("🔍 WebSocket Manager Protocol Compliance Summary")
    logger.info("=" * 60)
    
    total_managers = len(managers)
    compliant_managers = 0
    
    for manager, context in managers:
        is_compliant = validate_websocket_manager_on_startup(manager, context)
        if is_compliant:
            compliant_managers += 1
    
    compliance_rate = (compliant_managers / total_managers * 100) if total_managers > 0 else 0
    
    logger.info(
        f"📊 PROTOCOL COMPLIANCE SUMMARY: {compliant_managers}/{total_managers} managers compliant "
        f"({compliance_rate:.1f}%)"
    )
    
    if compliance_rate == 100:
        logger.info("✅ ALL WebSocket managers are protocol compliant! Five Whys root cause is prevented.")
    elif compliance_rate >= 80:
        logger.warning("⚠️  Most managers are compliant, but some need attention.")
    else:
        logger.error("❌ CRITICAL: Multiple managers are not protocol compliant. Five Whys root cause risk is HIGH.")
    
    logger.info("=" * 60)


__all__ = [
    'validate_websocket_manager_on_startup',
    'create_protocol_compliance_report', 
    'test_critical_method_functionality',
    'log_protocol_compliance_summary'
]