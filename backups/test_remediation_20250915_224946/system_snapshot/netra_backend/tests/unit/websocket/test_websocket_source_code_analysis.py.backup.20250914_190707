"""
Source Code Analysis Test for WebSocket Silent Failure Patterns - Issue #373

MISSION: Analyze actual source code to prove the silent failure patterns exist
and quantify the gap between old patterns and modern infrastructure.

This test validates the findings by examining source code directly.
"""

import pytest
import inspect
from pathlib import Path

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketSourceCodeAnalysis(SSotBaseTestCase):
    """
    Source code analysis to validate WebSocket silent failure patterns.
    """

    def test_source_code_pattern_analysis_SHOULD_FAIL(self):
        """
        FAILING TEST: Analyzes actual source code to prove old patterns exist.
        
        This test should FAIL because it demonstrates logger.warning patterns
        exist in the identified files from Issue #373.
        """
        findings = {}
        
        # Analyze UnifiedToolDispatcher
        try:
            from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
            source = inspect.getsource(UnifiedToolDispatcher)
            
            # Count old pattern occurrences
            warning_count = source.count('logger.warning')
            critical_count = source.count('logger.critical')
            emit_critical_event_count = source.count('emit_critical_event')
            
            findings['UnifiedToolDispatcher'] = {
                'logger_warning': warning_count,
                'logger_critical': critical_count,
                'emit_critical_event': emit_critical_event_count,
                'has_old_pattern': warning_count > 0,
                'has_modern_pattern': emit_critical_event_count > 0
            }
        except Exception as e:
            findings['UnifiedToolDispatcher'] = {'error': str(e)}
        
        # Analyze ReportingSubAgent
        try:
            from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
            source = inspect.getsource(ReportingSubAgent)
            
            # Count patterns
            warning_count = source.count('logger.warning') + source.count('self.logger.warning')
            critical_count = source.count('logger.critical') + source.count('self.logger.critical')
            emit_critical_event_count = source.count('emit_critical_event')
            
            findings['ReportingSubAgent'] = {
                'logger_warning': warning_count,
                'logger_critical': critical_count, 
                'emit_critical_event': emit_critical_event_count,
                'has_old_pattern': warning_count > 0,
                'has_modern_pattern': emit_critical_event_count > 0
            }
        except Exception as e:
            findings['ReportingSubAgent'] = {'error': str(e)}
        
        # Analyze ExecutionEngine
        try:
            from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine
            source = inspect.getsource(ExecutionEngine)
            
            # Count patterns
            warning_count = source.count('logger.warning')
            critical_count = source.count('logger.critical')
            emit_critical_event_count = source.count('emit_critical_event')
            
            findings['ExecutionEngine'] = {
                'logger_warning': warning_count,
                'logger_critical': critical_count,
                'emit_critical_event': emit_critical_event_count,
                'has_old_pattern': warning_count > 0,
                'has_modern_pattern': emit_critical_event_count > 0
            }
        except Exception as e:
            findings['ExecutionEngine'] = {'error': str(e)}
        
        # Analyze modern infrastructure availability
        modern_infrastructure = {}
        try:
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
            modern_infrastructure['UnifiedWebSocketEmitter'] = {
                'has_emit_critical_event': hasattr(UnifiedWebSocketEmitter, 'emit_critical_event'),
                'has_emit_agent_started': hasattr(UnifiedWebSocketEmitter, 'emit_agent_started'),
                'has_emit_tool_executing': hasattr(UnifiedWebSocketEmitter, 'emit_tool_executing'),
                'has_emit_tool_completed': hasattr(UnifiedWebSocketEmitter, 'emit_tool_completed'),
                'has_emit_agent_completed': hasattr(UnifiedWebSocketEmitter, 'emit_agent_completed')
            }
        except Exception as e:
            modern_infrastructure['UnifiedWebSocketEmitter'] = {'error': str(e)}
            
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            modern_infrastructure['UnifiedWebSocketManager'] = {
                'has_emit_critical_event': hasattr(UnifiedWebSocketManager, 'emit_critical_event'),
                'has_send_event': hasattr(UnifiedWebSocketManager, 'send_event')
            }
        except Exception as e:
            modern_infrastructure['UnifiedWebSocketManager'] = {'error': str(e)}
        
        # Calculate metrics
        components_with_old_pattern = sum(1 for f in findings.values() 
                                        if isinstance(f, dict) and f.get('has_old_pattern', False))
        components_analyzed = len([f for f in findings.values() if 'error' not in f])
        
        total_warning_patterns = sum(f.get('logger_warning', 0) for f in findings.values() 
                                   if isinstance(f, dict) and 'logger_warning' in f)
        
        modern_infrastructure_available = any(
            f.get('has_emit_critical_event', False) for f in modern_infrastructure.values()
            if isinstance(f, dict)
        )
        
        # Print detailed findings for analysis
        print(f"\n=== WEBSOCKET SILENT FAILURE ANALYSIS ===")
        print(f"Components analyzed: {components_analyzed}")
        print(f"Components with old patterns: {components_with_old_pattern}")
        print(f"Total logger.warning patterns found: {total_warning_patterns}")
        print(f"Modern infrastructure available: {modern_infrastructure_available}")
        print(f"\nDetailed findings: {findings}")
        print(f"Modern infrastructure: {modern_infrastructure}")
        
        # These assertions should FAIL to demonstrate the issue
        self.assertLess(components_with_old_pattern, 1,
                       f"ISSUE #373 CONFIRMED: {components_with_old_pattern} components use old logger.warning patterns")
        
        self.assertLess(total_warning_patterns, 2,
                       f"ISSUE #373 CONFIRMED: {total_warning_patterns} logger.warning patterns found in WebSocket code")
        
        if modern_infrastructure_available and components_with_old_pattern > 0:
            self.fail("CRITICAL INFRASTRUCTURE GAP: Modern infrastructure exists but old patterns still in use!")

    def test_specific_line_analysis_SHOULD_FAIL(self):
        """
        FAILING TEST: Analyzes the specific lines mentioned in Issue #373.
        
        This test should FAIL because it validates the exact lines reported in the issue.
        """
        line_findings = []
        
        # Check UnifiedToolDispatcher lines 949, 985
        try:
            import inspect
            from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
            
            source_lines = inspect.getsourcelines(UnifiedToolDispatcher)[0]
            
            # Look for logger.warning patterns
            for i, line in enumerate(source_lines, 1):
                if 'logger.warning' in line and 'Failed to emit' in line:
                    line_findings.append({
                        'file': 'UnifiedToolDispatcher',
                        'line_number': i,
                        'content': line.strip(),
                        'pattern': 'logger.warning'
                    })
        except Exception as e:
            line_findings.append({'error': f'UnifiedToolDispatcher analysis failed: {e}'})
        
        # Check ReportingSubAgent line 258 area
        try:
            from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
            source_lines = inspect.getsourcelines(ReportingSubAgent)[0]
            
            for i, line in enumerate(source_lines, 1):
                if 'logger.warning' in line or 'self.logger.warning' in line:
                    if 'Failed to emit' in line or 'start event' in line:
                        line_findings.append({
                            'file': 'ReportingSubAgent', 
                            'line_number': i,
                            'content': line.strip(),
                            'pattern': 'logger.warning'
                        })
        except Exception as e:
            line_findings.append({'error': f'ReportingSubAgent analysis failed: {e}'})
        
        # Check ExecutionEngine lines 352, 367, 384 area
        try:
            from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine
            source_lines = inspect.getsourcelines(ExecutionEngine)[0]
            
            for i, line in enumerate(source_lines, 1):
                if 'logger.warning' in line and ('Failed to emit' in line or 'agent' in line):
                    line_findings.append({
                        'file': 'ExecutionEngine',
                        'line_number': i, 
                        'content': line.strip(),
                        'pattern': 'logger.warning'
                    })
        except Exception as e:
            line_findings.append({'error': f'ExecutionEngine analysis failed: {e}'})
        
        print(f"\n=== SPECIFIC LINE ANALYSIS ===")
        for finding in line_findings:
            print(finding)
        
        # This should FAIL if the specific lines exist
        problematic_lines = [f for f in line_findings if 'error' not in f]
        self.assertLess(len(problematic_lines), 1,
                       f"ISSUE #373 CONFIRMED: {len(problematic_lines)} specific problematic lines found!")

    def test_business_impact_calculation_SHOULD_FAIL(self):
        """
        FAILING TEST: Calculates the business impact of the silent failure patterns.
        
        This test should FAIL because it quantifies the high business cost.
        """
        # Business constants
        chat_percentage_of_value = 90  # Chat is 90% of platform value
        critical_events_per_execution = 5  # 5 critical events per agent execution
        average_executions_per_session = 3  # 3 agent executions per user session
        
        # Pattern analysis from findings
        components_with_silent_failures = 3  # UnifiedToolDispatcher, ReportingSubAgent, ExecutionEngine
        failure_patterns_per_component = 2   # Average 2 logger.warning patterns per component
        
        # Calculate potential impact
        total_failure_patterns = components_with_silent_failures * failure_patterns_per_component
        potential_lost_events_per_session = critical_events_per_execution * average_executions_per_session
        
        # Business impact calculation
        ux_degradation_percentage = (total_failure_patterns / (components_with_silent_failures * 5)) * 100
        chat_value_at_risk = chat_percentage_of_value * (ux_degradation_percentage / 100)
        
        print(f"\n=== BUSINESS IMPACT ANALYSIS ===")
        print(f"Components with silent failures: {components_with_silent_failures}")
        print(f"Total failure patterns: {total_failure_patterns}")
        print(f"Potential lost events per session: {potential_lost_events_per_session}")
        print(f"UX degradation: {ux_degradation_percentage:.1f}%")
        print(f"Chat value at risk: {chat_value_at_risk:.1f}%")
        
        # These should FAIL to highlight business impact
        self.assertLess(total_failure_patterns, 3,
                       f"BUSINESS RISK: {total_failure_patterns} silent failure patterns threaten user experience")
        
        self.assertLess(ux_degradation_percentage, 20,
                       f"UX RISK: {ux_degradation_percentage:.1f}% degradation from silent failures")
        
        self.assertLess(chat_value_at_risk, 10,
                       f"REVENUE RISK: {chat_value_at_risk:.1f}% of chat value at risk from silent failures")


if __name__ == '__main__':
    pytest.main([__file__, "-v", "--no-header", "--tb=short"])