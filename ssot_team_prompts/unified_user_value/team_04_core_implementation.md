# Team D: Implementation Agent - ReportingSubAgent Core Resilience

## COPY THIS ENTIRE PROMPT:

You are an Implementation Engineer enhancing the EXISTING ReportingSubAgent with resilience features while maintaining it as the SINGLE SOURCE OF TRUTH.

CRITICAL: You are MODIFYING the existing class at `netra_backend/app/agents/reporting_sub_agent.py`, NOT creating a new one.

## MANDATORY FIRST ACTIONS:

1. READ `netra_backend/app/agents/reporting_sub_agent.py` - Current code
2. READ `reporting_crash_audit_and_plan.md` - Implementation requirements  
3. READ `CLAUDE.md` Section 2.1 - SSOT principles
4. READ `netra_backend/app/agents/base_agent.py` - Available base methods
5. GREP for ALL references to ReportingSubAgent across codebase

## YOUR IMPLEMENTATION TASK:

### 1. Core Resilience Enhancements

**MODIFY existing ReportingSubAgent class:**
```python
# Location: netra_backend/app/agents/reporting_sub_agent.py

class ReportingSubAgent(BaseAgent):
    """SSOT ReportingSubAgent - Enhanced with resilience
    
    Business Value: Zero crashes, 100% output guarantee
    """
    
    # ADD: Report level definitions
    REPORT_LEVELS = {
        'FULL': ['action_plan_result', 'optimizations_result', 'data_result', 'triage_result'],
        'STANDARD': ['optimizations_result', 'data_result', 'triage_result'],
        'BASIC': ['data_result', 'triage_result'],
        'MINIMAL': ['triage_result'],
        'FALLBACK': []
    }
    
    def __init__(self, context: Optional[UserExecutionContext] = None):
        # KEEP existing initialization
        super().__init__(...)
        
        # ADD: Resilience components
        self._retry_policy = ExponentialBackoffPolicy(
            max_retries=3,
            base_delay=1.0,
            max_delay=10.0
        )
        self._checkpoint_manager = None  # Lazy init
        self._report_level = None
        
    # MODIFY: Make validation non-fatal
    def _validate_analysis_results(self, context: UserExecutionContext) -> str:
        """Validate and determine report level (non-fatal)"""
        metadata = context.metadata
        
        # Determine highest achievable report level
        for level, required in self.REPORT_LEVELS.items():
            if all(metadata.get(field) for field in required):
                self.logger.info(f"Report level determined: {level}")
                return level
        
        self.logger.warning(f"Insufficient data for standard report, using FALLBACK")
        return 'FALLBACK'
    
    # MODIFY: Main execute method with recovery
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute with automatic recovery and graceful degradation"""
        
        # KEEP: Context validation
        if not isinstance(context, UserExecutionContext):
            raise AgentValidationError(f"Invalid context type: {type(context)}")
        
        # KEEP: WebSocket events
        if stream_updates:
            await self.emit_agent_started("Starting resilient report generation...")
            
        try:
            # NEW: Determine report level (non-fatal)
            self._report_level = self._validate_analysis_results(context)
            
            # NEW: Try with progressive degradation
            result = await self._execute_with_recovery(context, stream_updates)
            
            # KEEP: Success emission
            if stream_updates:
                await self.emit_agent_completed(result)
                
            return result
            
        except Exception as e:
            # NEW: Ultimate fallback (never fails)
            return await self._create_guaranteed_output(context, e, stream_updates)
    
    # ADD: New recovery method
    async def _execute_with_recovery(self, context: UserExecutionContext, 
                                    stream_updates: bool) -> Dict[str, Any]:
        """Execute with retry and progressive degradation"""
        
        strategies = [
            self._try_full_generation,
            self._try_partial_generation,
            self._try_minimal_generation,
            self._create_fallback_report
        ]
        
        last_error = None
        for strategy in strategies:
            try:
                if stream_updates:
                    await self.emit_thinking(f"Attempting {strategy.__name__}...")
                    
                return await strategy(context)
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"{strategy.__name__} failed: {e}, trying next strategy")
                continue
        
        # Should never reach here, but guarantee output
        return self._create_guaranteed_output(context, last_error, stream_updates)
    
    # ADD: Progressive generation methods
    async def _try_full_generation(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Try to generate full report with all data"""
        if self._report_level not in ['FULL', 'STANDARD']:
            raise ValueError(f"Insufficient data for full generation")
            
        prompt = self._build_reporting_prompt(context)
        response = await self._execute_with_retry(
            lambda: self._execute_reporting_llm_with_observability(prompt, ...)
        )
        
        return {
            'success': True,
            'level': self._report_level,
            'report': self._extract_and_validate_report(response, context.run_id),
            'recovery_performed': False
        }
    
    async def _try_partial_generation(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Generate report with available data only"""
        available_data = self._get_available_data(context)
        
        if not available_data:
            raise ValueError("No data available for partial generation")
        
        sections = []
        for section_name, section_data in available_data.items():
            section_content = await self._generate_section(section_name, section_data)
            sections.append(section_content)
        
        return {
            'success': True,
            'level': 'PARTIAL',
            'report': self._combine_sections(sections),
            'missing_data': self._get_missing_fields(context),
            'recovery_performed': True
        }
    
    async def _try_minimal_generation(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Generate minimal report with triage data only"""
        triage_data = context.metadata.get('triage_result')
        
        if not triage_data:
            raise ValueError("No triage data for minimal generation")
        
        return {
            'success': True,
            'level': 'MINIMAL',
            'report': self._create_minimal_report_from_triage(triage_data),
            'missing_data': self._get_missing_fields(context),
            'recovery_performed': True,
            'data_helper_suggested': True
        }
    
    # ADD: Retry wrapper
    async def _execute_with_retry(self, func, max_retries=3):
        """Execute with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                return await func()
            except (TimeoutError, ConnectionError, LLMError) as e:
                if attempt < max_retries - 1:
                    delay = self._retry_policy.get_delay(attempt)
                    self.logger.info(f"Retry {attempt + 1}/{max_retries} after {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise
    
    # ADD: Guaranteed output method
    def _create_guaranteed_output(self, context: UserExecutionContext, 
                                 error: Exception, stream_updates: bool) -> Dict[str, Any]:
        """Always return meaningful output, never fail"""
        
        # Log error for monitoring
        self.logger.error(f"All strategies failed for {context.run_id}: {error}")
        
        # Create meaningful fallback
        return {
            'success': True,  # We always succeed in providing output
            'level': 'FALLBACK',
            'report': {
                'summary': 'Report generation encountered limitations',
                'request': context.metadata.get('user_request', 'No request available'),
                'available_data': list(self._get_available_data(context).keys()),
                'recommendation': 'Please provide additional data for comprehensive analysis',
                'error_context': str(error)[:200]  # Limited error info
            },
            'recovery_performed': True,
            'trigger_data_helper': True,
            'metadata': {
                'fallback_reason': type(error).__name__,
                'timestamp': time.time()
            }
        }
    
    # ADD: Helper methods
    def _get_available_data(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Get all available data from context"""
        available = {}
        for field in ['triage_result', 'data_result', 'optimizations_result', 'action_plan_result']:
            if context.metadata.get(field):
                available[field] = context.metadata[field]
        return available
    
    def _get_missing_fields(self, context: UserExecutionContext) -> List[str]:
        """Identify missing required fields"""
        all_fields = self.REPORT_LEVELS['FULL']
        return [f for f in all_fields if not context.metadata.get(f)]
    
    # MODIFY: Existing fallback method to be more comprehensive
    def _create_fallback_report(self, context: UserExecutionContext) -> Dict[str, Any]:
        """Enhanced fallback report with all available data"""
        metadata = context.metadata
        available_data = self._get_available_data(context)
        
        report = {
            'status': 'Analysis completed with available data',
            'level': self._report_level,
            'sections': {}
        }
        
        # Add whatever sections we can create
        if 'triage_result' in available_data:
            report['sections']['classification'] = self._format_triage_section(available_data['triage_result'])
        
        if 'data_result' in available_data:
            report['sections']['data_analysis'] = self._format_data_section(available_data['data_result'])
            
        if 'optimizations_result' in available_data:
            report['sections']['recommendations'] = self._format_optimization_section(available_data['optimizations_result'])
            
        if 'action_plan_result' in available_data:
            report['sections']['action_plan'] = self._format_action_section(available_data['action_plan_result'])
        
        # Always add next steps
        report['sections']['next_steps'] = self._generate_next_steps(available_data, self._get_missing_fields(context))
        
        return {
            'success': True,
            'level': self._report_level,
            'report': report,
            'missing_data': self._get_missing_fields(context),
            'recovery_performed': True
        }
```

### 2. Update ALL References

**Find and update all imports:**
```bash
# Find all files that import ReportingSubAgent
grep -r "from.*reporting.*import\|import.*reporting" --include="*.py"

# Update patterns:
# OLD: from some.path import SomeReportingClass
# NEW: from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
```

**Update workflow orchestrator:**
```python
# Location: workflow_orchestrator.py

# ADD: Failure handling for reporting
async def _execute_workflow_step(self, context: ExecutionContext, 
                                step: PipelineStep) -> ExecutionResult:
    """Execute with reporting failure handling"""
    
    # Existing code...
    
    if step.agent_name == 'reporting':
        # Special handling for reporting
        result = await self._execute_with_fallback(step_context, context.state)
        
        # Check if data_helper is needed
        if result.result.get('trigger_data_helper'):
            await self._trigger_data_helper_collection(context, result)
            
    return result

async def _trigger_data_helper_collection(self, context, report_result):
    """Trigger data helper when reporting needs more data"""
    missing_data = report_result.result.get('missing_data', [])
    
    data_helper_step = self._create_pipeline_step(
        'data_helper', 'data_request', 99, dependencies=[]
    )
    
    # Execute data helper
    await self._execute_workflow_step(context, data_helper_step)
```

### 3. Remove Legacy Code

**Files/patterns to remove:**
```python
# REMOVE: Any duplicate reporting implementations
# REMOVE: Old error handlers that cause crashes
# REMOVE: Unused reporting utilities

# Files to check and clean:
# - netra_backend/app/agents/demo_service/reporting.py (if duplicate)
# - Any test-only reporting implementations
# - Deprecated report formats
```

### 4. Add Monitoring

```python
# ADD to ReportingSubAgent:

def _emit_metrics(self, level: str, recovery: bool, duration: float):
    """Emit metrics for monitoring"""
    metrics = {
        'report_level': level,
        'recovery_performed': recovery,
        'generation_time_ms': duration * 1000,
        'timestamp': time.time()
    }
    
    # Log for observability
    self.logger.info(f"Report metrics: {metrics}")
    
    # Could also send to monitoring service
    # await self.metrics_client.record('reporting', metrics)
```

## DELIVERABLES:

1. **Updated reporting_sub_agent.py** - Enhanced with all resilience features
2. **migration_script.py** - Update all references across codebase
3. **removed_files.txt** - List of deleted legacy files
4. **test_validation.py** - Verify all changes work

## VALIDATION CHECKLIST:

- [ ] ReportingSubAgent remains single class
- [ ] No new reporting classes created
- [ ] All crash scenarios handled
- [ ] Progressive degradation implemented
- [ ] Retry logic added
- [ ] Guaranteed output always returned
- [ ] All references updated
- [ ] Legacy code removed
- [ ] Tests updated and passing
- [ ] WebSocket events preserved
- [ ] Factory pattern compatible
- [ ] Performance targets met

Remember: You are ENHANCING the existing ReportingSubAgent, NOT creating a new class. This remains the SINGLE SOURCE OF TRUTH for all reporting.