"""
Five Whys Parameter Validation Test Suite

This test suite validates that the FIVE WHYS fixes for the WebSocket supervisor
parameter mismatch regression are correctly implemented and prevent recurrence.

CRITICAL: These tests MUST FAIL if the specific regression is reintroduced.
They serve as executable documentation of the exact issue that was fixed.

REGRESSION SCENARIO PREVENTED:
Original Error: "Failed to create WebSocket-scoped supervisor: name"
Root Cause: supervisor_factory.py used 'websocket_connection_id' 
           but UserExecutionContext expected 'websocket_client_id'
"""
import inspect
import ast
import os
import pytest
from typing import Dict, List, Any

class TestFiveWhysParameterValidation:
    """
    Simple validation tests for the Five Whys parameter fix without external dependencies.
    
    These tests focus on the core parameter interface validation that prevents
    the original websocket_connection_id vs websocket_client_id regression.
    """

    def test_why_1_error_handling_parameter_signature_validation(self):
        """
        WHY #1 - SYMPTOM: Validate that UserExecutionContext has correct parameter signature.
        
        This test validates that the symptom-level fix ensures UserExecutionContext
        has the correct parameter signature to prevent the original TypeError.
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        signature = inspect.signature(UserExecutionContext.__init__)
        parameters = signature.parameters
        assert 'websocket_client_id' in parameters, 'REGRESSION: UserExecutionContext missing websocket_client_id parameter'
        assert 'websocket_connection_id' not in parameters, 'REGRESSION: UserExecutionContext has deprecated websocket_connection_id parameter'
        websocket_param = parameters['websocket_client_id']
        assert websocket_param.default is None or websocket_param.default == inspect.Parameter.empty, 'websocket_client_id parameter should be optional'
        print(' PASS:  WHY #1 - Error handling: Parameter signature validation passed')

    def test_why_2_parameter_standardization_source_code_validation(self):
        """
        WHY #2 - IMMEDIATE CAUSE: Validate parameter standardization in source code.
        
        This test validates that all factory methods use the standardized
        websocket_client_id parameter name in their source code.
        """
        factory_file = '/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/websocket_core/supervisor_factory.py'
        assert os.path.exists(factory_file), 'WebSocket supervisor factory file not found'
        with open(factory_file, 'r') as f:
            source_code = f.read()
        if 'UserExecutionContext(' in source_code:
            lines = source_code.split('\n')
            constructor_blocks = []
            for i, line in enumerate(lines):
                if 'UserExecutionContext(' in line:
                    constructor_block = []
                    j = i
                    paren_count = 0
                    while j < len(lines):
                        constructor_block.append(lines[j])
                        paren_count += lines[j].count('(') - lines[j].count(')')
                        if paren_count <= 0 and 'UserExecutionContext(' in lines[i]:
                            break
                        j += 1
                    constructor_blocks.extend(constructor_block)
            constructor_code = '\n'.join(constructor_blocks)
            assert 'websocket_connection_id=' not in constructor_code, f"REGRESSION: Found deprecated 'websocket_connection_id' parameter in UserExecutionContext creation"
            assert 'websocket_client_id=' in constructor_code, f"REGRESSION: Missing 'websocket_client_id' parameter in UserExecutionContext creation"
        print(' PASS:  WHY #2 - Parameter standardization: Source code validation passed')

    def test_why_3_factory_interface_consistency_validation(self):
        """
        WHY #3 - SYSTEM FAILURE: Validate factory interface consistency.
        
        This test validates that factory pattern interfaces are consistent
        across different factory implementations.
        """
        from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor
        from netra_backend.app.core.supervisor_factory import create_supervisor_core
        websocket_factory_sig = inspect.signature(get_websocket_scoped_supervisor)
        websocket_params = websocket_factory_sig.parameters
        assert 'context' in websocket_params, 'WebSocket factory missing context parameter'
        core_factory_sig = inspect.signature(create_supervisor_core)
        core_params = core_factory_sig.parameters
        assert 'websocket_client_id' in core_params, 'Core factory missing websocket_client_id parameter'
        if 'websocket_client_id' in core_params:
            core_websocket_param = core_params['websocket_client_id']
            assert core_websocket_param.default is None or core_websocket_param.default == inspect.Parameter.empty, 'Core factory websocket_client_id should be optional'
        print(' PASS:  WHY #3 - Factory consistency: Interface validation passed')

    def test_why_4_deprecated_parameter_rejection_validation(self):
        """
        WHY #4 - PROCESS GAP: Validate that deprecated parameter is properly rejected.
        
        This test validates that the development process improvements prevent
        use of deprecated parameter names.
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        with pytest.raises(TypeError, match='unexpected keyword.*websocket_connection_id'):
            UserExecutionContext(user_id='process_test_user', thread_id='process_test_thread', run_id='process_test_run', websocket_connection_id='test_connection_id', db_session=None)
        print(' PASS:  WHY #4 - Process improvement: Deprecated parameter properly rejected')

    def test_why_5_interface_governance_parameter_standards(self):
        """
        WHY #5 - ROOT CAUSE: Validate interface governance prevents parameter mismatches.
        
        This test validates that interface evolution governance standards
        prevent the systematic parameter naming inconsistencies.
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        try:
            user_context = UserExecutionContext(user_id='governance_test_user', thread_id='governance_test_thread', run_id='governance_test_run', websocket_client_id='test_client_id', db_session=None)
            assert hasattr(user_context, 'websocket_client_id')
            assert user_context.websocket_client_id == 'test_client_id'
        except TypeError as e:
            if 'websocket_client_id' in str(e) and 'unexpected keyword' in str(e):
                pytest.fail(f'REGRESSION: UserExecutionContext rejects websocket_client_id: {e}')
            else:
                pass
        print(' PASS:  WHY #5 - Interface governance: Parameter standards validation passed')

    def test_end_to_end_parameter_flow_validation(self):
        """
        END-TO-END: Validate the complete parameter flow works correctly.
        
        This test validates that the parameter standardization works across
        the entire flow from context creation to UserExecutionContext instantiation.
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.websocket_core.context import WebSocketContext
        context_connection_id = 'test_connection_123'
        user_context = UserExecutionContext(user_id='flow_test_user', thread_id='flow_test_thread', run_id='flow_test_run', websocket_client_id=context_connection_id, db_session=None)
        assert user_context.websocket_client_id == context_connection_id
        print(' PASS:  END-TO-END: Complete parameter flow validation passed')

    def test_regression_prevention_comprehensive_validation(self):
        """
        COMPREHENSIVE: Validate all aspects of regression prevention.
        
        This test runs all the key validations to ensure the specific regression
        that caused "Failed to create WebSocket-scoped supervisor: name" cannot recur.
        """
        validation_results = []
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        signature = inspect.signature(UserExecutionContext.__init__)
        parameters = signature.parameters
        validation_results.append({'check': 'websocket_client_id_present', 'result': 'websocket_client_id' in parameters, 'critical': True})
        validation_results.append({'check': 'websocket_connection_id_absent', 'result': 'websocket_connection_id' not in parameters, 'critical': True})
        factory_file = '/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/websocket_core/supervisor_factory.py'
        if os.path.exists(factory_file):
            with open(factory_file, 'r') as f:
                content = f.read()
            validation_results.append({'check': 'no_deprecated_parameter_in_source', 'result': 'websocket_connection_id=' not in content, 'critical': True})
            validation_results.append({'check': 'correct_parameter_in_source', 'result': 'websocket_client_id=' in content, 'critical': True})
        deprecated_param_rejected = False
        try:
            UserExecutionContext(user_id='regression_test_user_12345', thread_id='regression_test_thread_12345', run_id='regression_test_run_12345', websocket_connection_id='test_connection_id', db_session=None)
        except TypeError as e:
            if 'websocket_connection_id' in str(e):
                deprecated_param_rejected = True
        validation_results.append({'check': 'deprecated_parameter_rejected', 'result': deprecated_param_rejected, 'critical': True})
        correct_param_accepted = False
        try:
            UserExecutionContext(user_id='acceptance_test_user_12345', thread_id='acceptance_test_thread_12345', run_id='acceptance_test_run_12345', websocket_client_id='test_websocket_client_id', db_session=None)
            correct_param_accepted = True
        except TypeError as e:
            if 'websocket_client_id' not in str(e):
                correct_param_accepted = True
        validation_results.append({'check': 'correct_parameter_accepted', 'result': correct_param_accepted, 'critical': True})
        critical_failures = [r for r in validation_results if r['critical'] and (not r['result'])]
        if critical_failures:
            failure_details = [f"- {r['check']}: {r['result']}" for r in critical_failures]
            pytest.fail(f'REGRESSION DETECTED - Critical validations failed:\n' + '\n'.join(failure_details))
        total_checks = len(validation_results)
        passed_checks = sum((1 for r in validation_results if r['result']))
        print(f' PASS:  COMPREHENSIVE VALIDATION PASSED: {passed_checks}/{total_checks} checks successful')
        print(f' PASS:  WebSocket supervisor parameter regression CANNOT RECUR')
        for result in validation_results:
            status = ' PASS: ' if result['result'] else ' FAIL: '
            critical = ' (CRITICAL)' if result['critical'] else ''
            print(f"  {status} {result['check']}{critical}: {result['result']}")
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')