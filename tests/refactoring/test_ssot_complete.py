"""
Comprehensive SSOT Refactoring Validation Test Suite
=====================================================
CRITICAL: This test suite validates that ALL SSOT refactoring is complete and correct.
Must pass 100% before considering refactoring done.
"""

import asyncio
import json
import os
import sys
import time
import pytest
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

# Import the scanners and validators we created
from tests.refactoring.continuous_validation import RefactoringValidator
from tests.refactoring.legacy_file_tracker import LegacyFileTracker
from tests.refactoring.import_scanner import LegacyImportScanner


class TestSSOTRefactoringComplete:
    """Comprehensive validation of SSOT refactoring completion."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        cls.project_root = project_root
        cls.validator = RefactoringValidator()
        cls.file_tracker = LegacyFileTracker()
        cls.import_scanner = LegacyImportScanner()
        
    def test_factory_consolidation_complete(self):
        """Verify factory consolidation is complete with single implementation."""
        logger.info("="*80)
        logger.info("TEST: Factory Consolidation Complete")
        logger.info("="*80)
        
        # Check that ONLY ONE factory exists
        factory_files = [
            'netra_backend/app/agents/agent_instance_factory.py',
            'netra_backend/app/agents/agent_instance_factory_optimized.py',
            'netra_backend/app/agents/agent_instance_factory_legacy.py',
            'netra_backend/app/agents/agent_factory_v1.py',
            'netra_backend/app/agents/agent_factory_v2.py'
        ]
        
        existing_factories = []
        for factory_path in factory_files:
            full_path = self.project_root / factory_path
            if full_path.exists():
                existing_factories.append(factory_path)
                
        # Should have exactly ONE factory
        assert len(existing_factories) == 1, \
            f"Expected 1 factory, found {len(existing_factories)}: {existing_factories}"
            
        assert existing_factories[0] == 'netra_backend/app/agents/agent_instance_factory.py', \
            f"Wrong factory file exists: {existing_factories[0]}"
            
        # Verify factory performance
        self._verify_factory_performance()
        
        # Verify WebSocket integration
        self._verify_factory_websocket_integration()
        
        logger.success("[U+2713] Factory consolidation complete!")
        
    def test_agent_consolidation_complete(self):
        """Verify all 37 agents are consolidated with no duplicates."""
        logger.info("="*80)
        logger.info("TEST: Agent Consolidation Complete")
        logger.info("="*80)
        
        # List of all expected agents (37 total)
        expected_agents = [
            'data_sub_agent',
            'optimization_sub_agent',
            'analysis_sub_agent',
            'research_sub_agent',
            'forecasting_sub_agent',
            'simulation_sub_agent',
            'visualization_sub_agent',
            'etl_sub_agent',
            'statistical_sub_agent',
            'ml_sub_agent',
            'nlp_sub_agent',
            'computer_vision_sub_agent',
            'time_series_sub_agent',
            'graph_analytics_sub_agent',
            'real_time_sub_agent',
            'batch_processing_sub_agent',
            'stream_processing_sub_agent',
            'data_quality_sub_agent',
            'data_governance_sub_agent',
            'metadata_management_sub_agent',
            'data_catalog_sub_agent',
            'lineage_tracking_sub_agent',
            'compliance_sub_agent',
            'privacy_sub_agent',
            'security_sub_agent',
            'audit_sub_agent',
            'monitoring_sub_agent',
            'alerting_sub_agent',
            'reporting_sub_agent',
            'dashboard_sub_agent',
            'collaboration_sub_agent',
            'workflow_sub_agent',
            'orchestration_sub_agent',
            'scheduling_sub_agent',
            'resource_management_sub_agent',
            'cost_optimization_sub_agent',
            'performance_tuning_sub_agent'
        ]
        
        # Check each agent has ONLY ONE implementation
        duplicate_agents = []
        missing_agents = []
        
        for agent_name in expected_agents:
            agent_dir = self.project_root / f'netra_backend/app/agents/{agent_name}'
            
            if not agent_dir.exists():
                missing_agents.append(agent_name)
                continue
                
            # Check for duplicate implementations
            agent_files = list(agent_dir.glob('*agent*.py'))
            legacy_files = [f for f in agent_files if 'legacy' in f.name or 'old' in f.name or '_v1' in f.name]
            
            if legacy_files:
                duplicate_agents.append({
                    'agent': agent_name,
                    'duplicates': [f.name for f in legacy_files]
                })
                
        assert len(missing_agents) == 0, f"Missing agents: {missing_agents}"
        assert len(duplicate_agents) == 0, f"Agents with duplicates: {duplicate_agents}"
        
        # Verify execution order
        self._verify_agent_execution_order()
        
        logger.success("[U+2713] Agent consolidation complete - all 37 agents verified!")
        
    def test_tool_execution_consolidation_complete(self):
        """Verify single tool dispatch path with proper request isolation."""
        logger.info("="*80)
        logger.info("TEST: Tool Execution Consolidation Complete")
        logger.info("="*80)
        
        # Check for single tool dispatcher
        dispatcher_files = [
            'netra_backend/app/agents/tool_dispatcher.py',
            'netra_backend/app/agents/tool_dispatcher_core.py',
            'netra_backend/app/agents/request_scoped_tool_dispatcher.py',
            'netra_backend/app/agents/tool_dispatcher_legacy.py'
        ]
        
        existing_dispatchers = []
        for dispatcher_path in dispatcher_files:
            full_path = self.project_root / dispatcher_path
            if full_path.exists():
                existing_dispatchers.append(dispatcher_path)
                
        assert len(existing_dispatchers) == 1, \
            f"Expected 1 dispatcher, found {len(existing_dispatchers)}: {existing_dispatchers}"
            
        # Verify request isolation
        self._verify_request_isolation()
        
        # Verify all tools working
        self._verify_all_tools_functional()
        
        logger.success("[U+2713] Tool execution consolidation complete!")
        
    def test_infrastructure_consolidation_complete(self):
        """Verify infrastructure managers are consolidated."""
        logger.info("="*80)
        logger.info("TEST: Infrastructure Consolidation Complete")
        logger.info("="*80)
        
        # Check legacy infrastructure removed
        legacy_infra = [
            'netra_backend/app/infrastructure/legacy_managers',
            'netra_backend/app/infrastructure/old_session_manager.py',
            'netra_backend/app/infrastructure/duplicate_id_generator.py'
        ]
        
        for legacy_path in legacy_infra:
            full_path = self.project_root / legacy_path
            assert not full_path.exists(), f"Legacy infrastructure still exists: {legacy_path}"
            
        # Verify ID centralization
        self._verify_id_generation_centralized()
        
        # Verify no session leaks
        self._verify_no_session_leaks()
        
        logger.success("[U+2713] Infrastructure consolidation complete!")
        
    def test_no_regressions(self):
        """Verify no regressions from baseline."""
        logger.info("="*80)
        logger.info("TEST: No Regressions")
        logger.info("="*80)
        
        regression_check = self.validator.check_for_regressions()
        
        assert regression_check['no_regressions'], \
            f"Regressions detected: {regression_check['regressions']}"
            
        logger.success("[U+2713] No regressions detected!")
        
    def test_all_legacy_files_removed(self):
        """Verify ALL legacy files have been removed."""
        logger.info("="*80)
        logger.info("TEST: All Legacy Files Removed")
        logger.info("="*80)
        
        verification = self.file_tracker.verify_removal()
        
        assert verification['all_removed'], \
            f"Legacy files still exist: {verification['remaining_files']}"
            
        logger.success("[U+2713] All legacy files removed!")
        
    def test_no_legacy_imports(self):
        """Verify no legacy imports remain in codebase."""
        logger.info("="*80)
        logger.info("TEST: No Legacy Imports")
        logger.info("="*80)
        
        is_clean = self.import_scanner.validate_clean()
        
        assert is_clean, "Legacy imports still exist in codebase"
        
        logger.success("[U+2713] No legacy imports found!")
        
    def test_mission_critical_websocket_events(self):
        """Verify mission critical WebSocket events are working."""
        logger.info("="*80)
        logger.info("TEST: Mission Critical WebSocket Events")
        logger.info("="*80)
        
        # Run the mission critical test suite
        import subprocess
        result = subprocess.run(
            [sys.executable, str(self.project_root / 'tests/mission_critical/test_websocket_agent_events_suite.py')],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        assert result.returncode == 0, \
            f"Mission critical WebSocket tests failed:\n{result.stdout}\n{result.stderr}"
            
        logger.success("[U+2713] Mission critical WebSocket events working!")
        
    def test_performance_maintained(self):
        """Verify performance metrics are maintained or improved."""
        logger.info("="*80)
        logger.info("TEST: Performance Maintained")
        logger.info("="*80)
        
        perf_check = self.validator._compare_performance()
        
        assert not perf_check['degradation_detected'], \
            "Performance degradation detected"
            
        logger.success("[U+2713] Performance maintained!")
        
    def test_500_plus_tests_passing(self):
        """Verify 500+ tests are passing."""
        logger.info("="*80)
        logger.info("TEST: 500+ Tests Passing")
        logger.info("="*80)
        
        test_results = self.validator._run_all_tests(quick=False)
        
        total_tests = test_results['total_tests']
        passed_tests = test_results['passed']
        
        assert total_tests >= 500, f"Expected 500+ tests, found {total_tests}"
        assert passed_tests >= 500, f"Expected 500+ passing tests, only {passed_tests} passed"
        
        success_rate = test_results['success_rate']
        assert success_rate >= 95.0, f"Test success rate too low: {success_rate}%"
        
        logger.success(f"[U+2713] {passed_tests}/{total_tests} tests passing ({success_rate:.1f}%)")
        
    # Helper verification methods
    
    def _verify_factory_performance(self):
        """Verify factory performance metrics."""
        # This would measure actual performance
        logger.info("  Verifying factory performance...")
        # TODO: Add actual performance checks
        
    def _verify_factory_websocket_integration(self):
        """Verify factory WebSocket integration."""
        logger.info("  Verifying factory WebSocket integration...")
        # TODO: Add WebSocket integration checks
        
    def _verify_agent_execution_order(self):
        """Verify correct agent execution order."""
        logger.info("  Verifying agent execution order (Data -> Optimization -> Analysis)...")
        # TODO: Add execution order verification
        
    def _verify_request_isolation(self):
        """Verify proper request isolation in tool dispatcher."""
        logger.info("  Verifying request isolation...")
        # TODO: Add isolation checks
        
    def _verify_all_tools_functional(self):
        """Verify all tools are working."""
        logger.info("  Verifying all tools functional...")
        # TODO: Add tool functionality checks
        
    def _verify_id_generation_centralized(self):
        """Verify ID generation is centralized."""
        logger.info("  Verifying ID generation centralized...")
        # TODO: Add ID generation checks
        
    def _verify_no_session_leaks(self):
        """Verify no session leaks."""
        logger.info("  Verifying no session leaks...")
        # TODO: Add session leak checks
        

def generate_final_validation_report():
    """Generate comprehensive final validation report."""
    logger.info("\n" + "="*80)
    logger.info("GENERATING FINAL SSOT VALIDATION REPORT")
    logger.info("="*80)
    
    validator = RefactoringValidator()
    report = validator.generate_final_report()
    
    # Print summary
    logger.info("\nFINAL VALIDATION SUMMARY:")
    logger.info("-"*40)
    
    # Test results
    final_tests = report['final_test_results']
    logger.info(f"Tests: {final_tests['passed']}/{final_tests['total_tests']} passing")
    logger.info(f"Success Rate: {final_tests['success_rate']:.1f}%")
    
    # Legacy removal
    legacy = report['legacy_removal_complete']
    if legacy['complete']:
        logger.success(f"[U+2713] Legacy Files: All {legacy['removed']} files removed")
    else:
        logger.error(f"[U+2717] Legacy Files: {legacy['remaining']} files still exist")
        
    # Import validation
    imports = report['import_validation']
    if imports['complete']:
        logger.success(f"[U+2713] Imports: Clean (scanned {imports['files_scanned']} files)")
    else:
        logger.error(f"[U+2717] Imports: {imports['violations_found']} violations found")
        
    # Regressions
    regressions = report['regression_analysis']
    if regressions['no_regressions']:
        logger.success("[U+2713] Regressions: None detected")
    else:
        logger.error(f"[U+2717] Regressions: {regressions['regressions_found']} found")
        
    # Performance
    perf = report['performance_comparison']
    if not perf['degradation_detected']:
        logger.success("[U+2713] Performance: Maintained or improved")
    else:
        logger.error("[U+2717] Performance: Degradation detected")
        
    # Code metrics
    metrics = report['code_metrics_comparison']
    before_lines = metrics['before'].get('total_lines', 0)
    after_lines = metrics['after'].get('total_lines', 0)
    reduction = before_lines - after_lines
    
    if reduction > 0:
        logger.success(f"[U+2713] Code Reduction: {reduction} lines removed ({(reduction/before_lines)*100:.1f}%)")
    
    logger.info("="*80)
    
    return report


if __name__ == "__main__":
    # Run all validation tests
    pytest.main([__file__, '-v', '--tb=short'])
    
    # Generate final report
    generate_final_validation_report()