# PROMPT 6: UVS Workflow Integration & Migration Engineer

## COPY THIS ENTIRE PROMPT INTO A NEW CLAUDE INSTANCE:

You are implementing the workflow integration and migration strategy for the Unified User Value System (UVS). This ensures UVS works seamlessly with existing systems and all references are updated.

## CRITICAL CONTEXT - READ FIRST:

The UVS must integrate with:
- **WorkflowOrchestrator** - Adapt workflow based on loop type
- **UnifiedTriageAgent** - Initial classification
- **UnifiedDataAgent** - Data processing
- **DataHelperAgent** - Data collection guidance
- **UnifiedWebSocketManager** - Real-time updates
- **AgentRegistry** - Agent management
- **ExecutionEngine** - Agent execution (with fallback removal noted)

ALL references to reporting across the codebase must use the enhanced ReportingSubAgent.

## YOUR IMPLEMENTATION TASK:

Integrate UVS with existing systems and migrate all references.

### 1. WorkflowOrchestrator Integration

```python
# Location: netra_backend/app/agents/supervisor/workflow_orchestrator.py

from typing import Dict, Any, List
from netra_backend.app.agents.supervisor.execution_context import PipelineStep
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WorkflowOrchestrator:
    """Orchestrates workflow with UVS loop adaptation"""
    
    def __init__(self, agent_registry, execution_engine, websocket_manager):
        self.agent_registry = agent_registry
        self.execution_engine = execution_engine
        self.websocket_manager = websocket_manager
    
    def _define_workflow_based_on_triage(self, triage_result: Dict[str, Any]) -> List[PipelineStep]:
        """Define adaptive workflow based on triage and UVS loop detection
        
        Enhanced to support UVS iterative loops and progressive value delivery.
        """
        
        # Check for UVS loop indicators
        loop_indicators = self._detect_uvs_loop_indicators(triage_result)
        
        if loop_indicators.get('is_iteration'):
            # User is in an iterative loop
            return self._create_uvs_loop_workflow(loop_indicators, triage_result)
        
        # Standard workflow with UVS enhancements
        data_sufficiency = triage_result.get("data_sufficiency", "unknown")
        
        if data_sufficiency == "sufficient":
            # Full workflow for complete analysis
            return [
                self._create_pipeline_step("triage", "classification", 1, dependencies=[]),
                self._create_pipeline_step("data", "insights", 2, dependencies=["triage"]),
                self._create_pipeline_step("optimization", "strategies", 3, dependencies=["data"]),
                self._create_pipeline_step("actions", "implementation", 4, dependencies=["optimization"]),
                self._create_pipeline_step("reporting", "uvs_full_value", 5, dependencies=["actions"])
            ]
        
        elif data_sufficiency == "partial":
            # Partial workflow with progressive value
            return [
                self._create_pipeline_step("triage", "classification", 1, dependencies=[]),
                self._create_pipeline_step("data", "partial_insights", 2, dependencies=["triage"]),
                self._create_pipeline_step("reporting", "uvs_progressive_value", 3, dependencies=["data"]),
                self._create_pipeline_step("data_helper", "collection_guidance", 4, dependencies=["reporting"])
            ]
        
        elif data_sufficiency == "insufficient":
            # Imagination mode - guide user to data
            return [
                self._create_pipeline_step("triage", "problem_analysis", 1, dependencies=[]),
                self._create_pipeline_step("reporting", "uvs_imagination_mode", 2, dependencies=["triage"]),
                self._create_pipeline_step("data_helper", "comprehensive_guidance", 3, dependencies=["reporting"])
            ]
        
        else:
            # Default UVS workflow
            logger.warning(f"Unknown data sufficiency: {data_sufficiency}, using UVS default")
            return [
                self._create_pipeline_step("triage", "classification", 1, dependencies=[]),
                self._create_pipeline_step("reporting", "uvs_adaptive", 2, dependencies=["triage"])
            ]
    
    def _detect_uvs_loop_indicators(self, triage_result: Dict) -> Dict:
        """Detect if user is in a UVS iterative loop"""
        
        metadata = triage_result.get('metadata', {})
        request = triage_result.get('user_request', '')
        
        indicators = {
            'is_iteration': False,
            'loop_type': None,
            'iteration_number': 0
        }
        
        # Check for iteration markers
        if 'iteration' in metadata or 'previous_report_id' in metadata:
            indicators['is_iteration'] = True
            indicators['iteration_number'] = metadata.get('iteration', 2)
        
        # Detect loop type from request patterns
        if any(phrase in request.lower() for phrase in ['what about', 'how about', 'but what if']):
            indicators['loop_type'] = 'refinement'
            indicators['is_iteration'] = True
        
        elif any(phrase in request.lower() for phrase in ['here is', 'i have', 'i got']):
            indicators['loop_type'] = 'data_discovery'
            indicators['is_iteration'] = True
        
        elif any(phrase in request.lower() for phrase in ['help', 'where do i start', 'what data']):
            indicators['loop_type'] = 'imagination'
        
        return indicators
    
    def _create_uvs_loop_workflow(self, loop_indicators: Dict, 
                                 triage_result: Dict) -> List[PipelineStep]:
        """Create workflow for UVS iterative loops"""
        
        loop_type = loop_indicators.get('loop_type', 'unknown')
        
        if loop_type == 'refinement':
            # User refining previous analysis
            return [
                self._create_pipeline_step("reporting", "uvs_refinement", 1, 
                                         dependencies=[], 
                                         metadata={'preserve_context': True})
            ]
        
        elif loop_type == 'data_discovery':
            # User providing more data
            return [
                self._create_pipeline_step("data", "incremental_processing", 1, dependencies=[]),
                self._create_pipeline_step("reporting", "uvs_progressive_update", 2, dependencies=["data"])
            ]
        
        elif loop_type == 'imagination':
            # User needs guidance
            return [
                self._create_pipeline_step("reporting", "uvs_imagination_guidance", 1, dependencies=[]),
                self._create_pipeline_step("data_helper", "detailed_instructions", 2, dependencies=["reporting"])
            ]
        
        else:
            # Default iterative workflow
            return [
                self._create_pipeline_step("triage", "reanalysis", 1, dependencies=[]),
                self._create_pipeline_step("reporting", "uvs_adaptive", 2, dependencies=["triage"])
            ]
    
    async def handle_reporting_failure(self, error: Exception, 
                                      context: ExecutionContext) -> ExecutionResult:
        """Handle reporting failures with UVS guarantee
        
        UVS GUARANTEE: ReportingSubAgent NEVER fails to deliver value
        """
        
        logger.error(f"Reporting encountered issue: {error}")
        
        # UVS handles its own failures internally
        # This is a safety net that should rarely be used
        
        # Check if data collection would help
        if 'missing' in str(error).lower() or 'insufficient' in str(error).lower():
            logger.info("Triggering data_helper fallback for missing data")
            
            # Create data_helper step
            data_helper_step = self._create_pipeline_step(
                'data_helper',
                'emergency_data_request',
                99,
                dependencies=[],
                metadata={'triggered_by': 'reporting_failure'}
            )
            
            # Execute data_helper
            result = await self._execute_workflow_step(context, data_helper_step)
            
            # Create UVS result
            reporting_result = ExecutionResult(
                success=True,  # UVS always succeeds
                agent_name='reporting',
                result={
                    'type': 'uvs_recovery',
                    'report': {
                        'type': 'data_collection_needed',
                        'guidance': result.result,
                        'message': 'I need more information to provide complete analysis'
                    }
                },
                execution_time_ms=100,
                status=ExecutionStatus.PARTIAL
            )
            
            return reporting_result
        
        # For other errors, UVS provides educational content
        return ExecutionResult(
            success=True,  # UVS always succeeds
            agent_name='reporting',
            result={
                'type': 'uvs_educational',
                'report': self._generate_educational_fallback()
            },
            execution_time_ms=50,
            status=ExecutionStatus.COMPLETED
        )
    
    def _generate_educational_fallback(self) -> Dict:
        """Generate educational content as ultimate fallback"""
        
        return {
            'type': 'educational_guidance',
            'title': 'AI Optimization Quick Start',
            'sections': {
                'getting_started': {
                    'title': 'Where to Begin',
                    'steps': [
                        'Collect any AI/LLM invoices or usage reports',
                        'Export API usage data from your provider',
                        'Document your main AI use cases'
                    ]
                },
                'common_optimizations': {
                    'title': 'Quick Wins',
                    'items': [
                        'Caching repeated queries (30-50% savings)',
                        'Using smaller models for simple tasks (60% reduction)',
                        'Batching similar requests (40% efficiency)'
                    ]
                },
                'next_steps': {
                    'title': 'Your Next Step',
                    'action': 'Start with any data you have and we\'ll guide you from there'
                }
            }
        }
```

### 2. Agent Registry Updates

```python
# Location: netra_backend/app/agents/supervisor/agent_registry.py

class AgentRegistry:
    """Registry with UVS-enhanced reporting"""
    
    def _register_default_agents(self):
        """Register default agents with UVS enhancements"""
        
        # Register enhanced ReportingSubAgent
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        self.register_agent(
            'reporting',
            ReportingSubAgent,
            metadata={
                'description': 'UVS-enhanced reporting with guaranteed value delivery',
                'supports_loops': True,
                'supports_checkpoints': True,
                'never_fails': True,
                'progressive_value': True
            }
        )
        
        # Register other agents...
    
    def get_agent_for_loop(self, loop_type: str) -> str:
        """Get appropriate agent for UVS loop type"""
        
        loop_agent_map = {
            'imagination': 'reporting',  # ReportingSubAgent handles imagination
            'data_discovery': 'data',
            'refinement': 'reporting',
            'context': 'reporting',
            'completion': 'reporting'
        }
        
        return loop_agent_map.get(loop_type, 'reporting')
```

### 3. Migration Script for References

```python
# Location: scripts/migrate_to_uvs.py

import os
import re
from typing import List, Tuple
from pathlib import Path

def find_reporting_references(root_dir: str) -> List[Tuple[str, int, str]]:
    """Find all references to reporting in codebase"""
    
    references = []
    patterns = [
        r'from.*reporting.*import',
        r'import.*reporting',
        r'ReportingAgent',
        r'reporting_agent',
        r'report_generator',
        r'generate_report',
        r'create_report'
    ]
    
    for root, dirs, files in os.walk(root_dir):
        # Skip test and migration directories
        if any(skip in root for skip in ['.git', '__pycache__', 'migrations']):
            continue
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            for pattern in patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    references.append((filepath, i+1, line.strip()))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    return references

def update_imports(filepath: str):
    """Update imports to use UVS-enhanced ReportingSubAgent"""
    
    replacements = {
        # Old import patterns -> New UVS import
        r'from netra_backend\.app\.agents\.reporting import.*': 
            'from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent',
        
        r'from.*reporting_agent import ReportingAgent':
            'from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent',
        
        r'ReportingAgent\(': 'ReportingSubAgent(',
        
        r'reporting_agent = ': 'reporting_sub_agent = ',
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated: {filepath}")
            return True
    
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
    
    return False

def remove_legacy_reporting_files(root_dir: str):
    """Remove legacy reporting implementations"""
    
    legacy_files = [
        'netra_backend/app/agents/reporting_agent.py',
        'netra_backend/app/agents/report_generator.py',
        'netra_backend/app/agents/basic_reporting.py',
        # Add other legacy files
    ]
    
    removed = []
    for filepath in legacy_files:
        full_path = os.path.join(root_dir, filepath)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                removed.append(filepath)
                print(f"Removed legacy file: {filepath}")
            except Exception as e:
                print(f"Error removing {filepath}: {e}")
    
    return removed

def validate_uvs_integration():
    """Validate UVS integration is complete"""
    
    checks = []
    
    # Check ReportingSubAgent exists and has UVS features
    try:
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        # Check for UVS attributes
        agent = ReportingSubAgent()
        checks.append(('ReportingSubAgent exists', True))
        checks.append(('Has UVS_LEVELS', hasattr(agent, 'UVS_LEVELS')))
        checks.append(('Has loop_detector', hasattr(agent, '_loop_detector')))
        checks.append(('Has checkpoint_manager', hasattr(agent, '_checkpoint_manager')))
        
    except ImportError as e:
        checks.append(('ReportingSubAgent exists', False))
    
    # Check WorkflowOrchestrator integration
    try:
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(None, None, None)
        checks.append(('WorkflowOrchestrator updated', 
                      hasattr(orchestrator, '_detect_uvs_loop_indicators')))
    
    except Exception as e:
        checks.append(('WorkflowOrchestrator updated', False))
    
    return checks

def main():
    """Main migration script"""
    
    print("="*50)
    print("UVS Migration Script")
    print("="*50)
    
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Step 1: Find all references
    print("\n1. Finding reporting references...")
    references = find_reporting_references(root_dir)
    print(f"Found {len(references)} references")
    
    # Step 2: Update imports
    print("\n2. Updating imports...")
    updated_files = set()
    for filepath, _, _ in references:
        if filepath not in updated_files:
            if update_imports(filepath):
                updated_files.add(filepath)
    
    print(f"Updated {len(updated_files)} files")
    
    # Step 3: Remove legacy files
    print("\n3. Removing legacy files...")
    removed = remove_legacy_reporting_files(root_dir)
    print(f"Removed {len(removed)} legacy files")
    
    # Step 4: Validate integration
    print("\n4. Validating UVS integration...")
    checks = validate_uvs_integration()
    
    all_passed = True
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False
    
    # Final report
    print("\n" + "="*50)
    if all_passed:
        print("✓ UVS Migration Complete!")
        print("ReportingSubAgent is now the SINGLE SOURCE OF TRUTH")
    else:
        print("⚠ Migration partially complete - review failed checks")
    print("="*50)

if __name__ == "__main__":
    main()
```

### 4. WebSocket Integration

```python
# Location: netra_backend/app/services/agent_websocket_bridge.py

class AgentWebSocketBridge:
    """WebSocket bridge with UVS loop support"""
    
    async def notify_uvs_loop(self, run_id: str, loop_type: str, 
                             iteration: int, progress: float):
        """Notify about UVS loop progress"""
        
        await self.send_event({
            'type': 'uvs_loop_update',
            'run_id': run_id,
            'loop_type': loop_type,
            'iteration': iteration,
            'progress': progress,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def notify_value_level(self, run_id: str, level: str,
                                completeness: float):
        """Notify about UVS value level"""
        
        await self.send_event({
            'type': 'uvs_value_level',
            'run_id': run_id,
            'level': level,
            'data_completeness': completeness,
            'message': self._get_level_message(level)
        })
    
    def _get_level_message(self, level: str) -> str:
        """Get user-friendly message for value level"""
        
        messages = {
            'full': 'Complete analysis ready',
            'standard': 'Comprehensive insights available',
            'basic': 'Initial analysis complete',
            'minimal': 'Preliminary findings ready',
            'fallback_imagination': 'Let\'s explore optimization options'
        }
        
        return messages.get(level, 'Processing...')
```

### 5. Test Updates

```python
# Location: tests/mission_critical/test_uvs_integration.py

import pytest
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent

class TestUVSIntegration:
    """Test UVS integration across systems"""
    
    @pytest.mark.critical
    async def test_reporting_is_singleton(self):
        """Verify ReportingSubAgent is the only reporting implementation"""
        
        # Search for any other reporting classes
        import netra_backend.app.agents as agents_module
        
        reporting_classes = []
        for name in dir(agents_module):
            if 'report' in name.lower():
                obj = getattr(agents_module, name)
                if isinstance(obj, type):
                    reporting_classes.append(name)
        
        # Should only find ReportingSubAgent
        assert len(reporting_classes) <= 1
        if reporting_classes:
            assert reporting_classes[0] == 'ReportingSubAgent'
    
    @pytest.mark.critical
    async def test_workflow_uvs_integration(self):
        """Test WorkflowOrchestrator handles UVS loops"""
        
        from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(None, None, None)
        
        # Test loop detection
        triage_result = {
            'metadata': {'iteration': 2},
            'user_request': 'What about latency?'
        }
        
        indicators = orchestrator._detect_uvs_loop_indicators(triage_result)
        
        assert indicators['is_iteration'] == True
        assert indicators['loop_type'] == 'refinement'
    
    @pytest.mark.critical  
    async def test_never_fails_guarantee(self):
        """Test UVS never fails to deliver value"""
        
        # Test with various failure scenarios
        bad_contexts = [
            {},  # Empty context
            {'user_request': None},  # Null request
            {'data_result': float('inf')},  # Invalid data
            {'circular_ref': ...},  # Circular reference
        ]
        
        for context_data in bad_contexts:
            context = create_test_context(metadata=context_data)
            agent = ReportingSubAgent(context)
            
            # Should never raise exception
            result = await agent.execute(context, stream_updates=True)
            
            assert result['success'] == True
            assert 'report' in result
            assert result['report'] is not None
```

## CRITICAL MIGRATION NOTES:

1. **Run migration script first** - Update all imports
2. **Remove ALL legacy reporting code** - No duplicates
3. **Test thoroughly** - Ensure no breaks
4. **Update documentation** - Reference UVS features
5. **Monitor performance** - Ensure no degradation

## INTEGRATION CHECKLIST:

- [ ] WorkflowOrchestrator detects UVS loops
- [ ] AgentRegistry updated with UVS metadata  
- [ ] All imports migrated to ReportingSubAgent
- [ ] Legacy reporting files removed
- [ ] WebSocket events for UVS added
- [ ] Tests updated for UVS features
- [ ] Documentation updated
- [ ] Performance benchmarks pass
- [ ] No duplicate reporting logic remains
- [ ] Migration script runs successfully

## FINAL VALIDATION:

Run these commands to validate:

```bash
# Run migration script
python scripts/migrate_to_uvs.py

# Search for any remaining old references
grep -r "ReportingAgent" --include="*.py" .
grep -r "report_generator" --include="*.py" .

# Run UVS integration tests
python tests/mission_critical/test_uvs_integration.py

# Run full test suite
python tests/unified_test_runner.py --real-services
```

Remember: After migration, ReportingSubAgent is the SINGLE SOURCE OF TRUTH for all user value delivery. No other reporting implementation should exist in the codebase.