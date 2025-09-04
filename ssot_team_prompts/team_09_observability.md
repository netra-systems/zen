# Team 9: Observability Consolidation with Alpine Support Prompt

## COPY THIS ENTIRE PROMPT:

You are an Observability Expert implementing SSOT consolidation for monitoring, logging, and telemetry with Alpine container support.

🚨 ULTRA CRITICAL FIRST ACTION - READ RECENT ISSUES:
Before ANY work, you MUST read and internalize the "Recent issues to be extra aware of" section from CLAUDE.md:
1. Race conditions in async/websockets - Plan ahead for concurrency
2. Solve 95% of cases first - Make breadth ironclad before edge cases  
3. Limit volume of code - Delete ugly tests rather than add complex code
4. This is a multi-user system - Always consider concurrent users

MANDATORY READING BEFORE STARTING:
1. CLAUDE.md (entire document, especially sections 2.1, 2.5, 3.6, 7.1 AND the recent issues section)
2. docs/docker_orchestration.md (monitoring integration)
3. MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
4. Observability section in DEFINITION_OF_DONE_CHECKLIST.md
5. docker-compose.alpine-test.yml (resource limits)

YOUR SPECIFIC CONSOLIDATION TASKS:
1. Consolidate multiple monitoring solutions into ONE UnifiedObservability
2. Integrate with UnifiedDockerManager for container metrics
3. Support Alpine container monitoring (50% less resource usage)
4. Implement the Three Pillars: Logging, Metrics, Tracing
5. Define and monitor Service Level Objectives (SLOs)

TARGET IMPLEMENTATION:
```python
# Location: netra_backend/app/observability/unified_observability.py
class UnifiedObservability:
    """SSOT for all observability - logging, metrics, tracing"""
    
    def __init__(self, docker_manager: Optional[UnifiedDockerManager] = None):
        self.docker = docker_manager
        self.logger = self._init_structured_logging()
        self.metrics = self._init_metrics_collector()
        self.tracer = self._init_distributed_tracing()
        self.slos = self._init_slo_monitoring()
        
    # The Three Pillars (CLAUDE.md 2.5)
    def log_structured(self, level: str, message: str, context: dict):
        """Structured logging with context"""
        self.logger.log(level, message, extra={
            'user_id': context.get('user_id'),
            'request_id': context.get('request_id'),
            'service': context.get('service'),
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def record_metric(self, name: str, value: float, tags: dict):
        """Record metrics for monitoring"""
        self.metrics.record(name, value, tags)
        
    def start_trace(self, operation: str, context: dict):
        """Start distributed trace span"""
        return self.tracer.start_span(
            operation,
            attributes=context
        )
    
    # Docker/Alpine Integration
    async def monitor_containers(self):
        """Monitor Docker containers including Alpine"""
        if self.docker:
            stats = await self.docker.get_container_stats()
            for container, data in stats.items():
                self.record_metric(
                    'container.memory.usage',
                    data['memory_usage_mb'],
                    {'container': container, 'alpine': data.get('is_alpine')}
                )
                
    # SLO Monitoring (CLAUDE.md 2.5)
    def check_slos(self) -> Dict[str, bool]:
        """Check Service Level Objectives"""
        return {
            'chat_latency': self._check_chat_latency_slo(),
            'agent_success_rate': self._check_agent_success_slo(),
            'websocket_uptime': self._check_websocket_slo(),
            'api_availability': self._check_api_slo()
        }
    
    def get_error_budget(self, slo_name: str) -> float:
        """Calculate error budget for SLO"""
        # Error budget determines if we focus on features or stability
        pass

# Location: netra_backend/app/observability/slo_definitions.py
class SLODefinitions:
    """Service Level Objectives per CLAUDE.md"""
    
    SLOS = {
        'chat_latency_p99': {
            'target': 0.99,  # 99% of requests
            'threshold_ms': 1000,  # under 1 second
            'window': '30d'
        },
        'agent_success_rate': {
            'target': 0.95,  # 95% success
            'window': '7d'
        },
        'websocket_uptime': {
            'target': 0.999,  # 99.9% uptime
            'window': '30d'
        }
    }
```

OBSERVABILITY COMPONENTS TO CONSOLIDATE:
1. Logging implementations → structured logging
2. Metrics collectors → unified metrics
3. Tracing systems → OpenTelemetry
4. Monitoring dashboards → unified dashboard
5. Alert managers → unified alerting
6. Performance profilers → unified profiling
7. Health checkers → unified health
8. Resource monitors → Docker integration
9. Error trackers → unified error handling
10. Analytics collectors → unified analytics

ALPINE MONITORING REQUIREMENTS:
```python
# Monitor Alpine containers (50% less resources)
alpine_metrics = {
    'memory_limit_mb': 256,  # Alpine uses less
    'cpu_limit': 0.5,
    'expected_startup_time': 5,  # Seconds (faster)
}

# Alert if Alpine containers exceed limits
if container.is_alpine and memory > alpine_metrics['memory_limit_mb']:
    self.alert('Alpine container memory exceeded', severity='warning')
```

CRITICAL REQUIREMENTS:
1. Implement Three Pillars (Logging, Metrics, Tracing)
2. Define SLOs for critical services
3. Integrate with UnifiedDockerManager
4. Support Alpine container monitoring
5. Structured logging with context
6. Distributed tracing with OpenTelemetry
7. Error budget tracking
8. Real-time alerting
9. Performance profiling
10. Resource usage monitoring

VALUE PRESERVATION PROCESS:
1. Run git log - identify monitoring fixes
2. Extract metric definitions
3. Preserve alert rules
4. Keep dashboard configs
5. Document in extraction_report_observability.md
6. Migrate monitoring tests
7. ONLY delete after extraction

TESTING AT EVERY STAGE:

Stage 1 - Pre-consolidation:
- [ ] Document current monitoring tools
- [ ] Run python tests/unified_test_runner.py --real-services
- [ ] Capture current metrics
- [ ] Test Alpine monitoring
- [ ] Document SLO baselines

Stage 2 - During consolidation:
- [ ] Test logging after each merge
- [ ] Verify metrics collection
- [ ] Test tracing functionality
- [ ] Check Docker integration
- [ ] Monitor Alpine containers

Stage 3 - Post-consolidation:
- [ ] Full observability suite test
- [ ] SLO validation
- [ ] Error budget calculation
- [ ] Load test monitoring
- [ ] Alpine performance verification

CONTINUOUS BREAKING-CHANGE AUDIT:
After EVERY consolidation step, audit and update:
- [ ] Logging statements across codebase
- [ ] Metric collection points
- [ ] Trace instrumentation
- [ ] Alert configurations
- [ ] Dashboard definitions
- [ ] Health check endpoints
- [ ] Performance profiling hooks
- [ ] Error handling integration
- [ ] Docker monitoring hooks
- [ ] Frontend telemetry

DETAILED REPORTING REQUIREMENTS:
Create reports/team_09_observability_[timestamp].md with:

## Consolidation Report - Team 9: Observability
### Phase 1: Analysis
- Monitoring tools found: [list all]
- Logging systems: [count and types]
- Metrics collectors: [list]
- Tracing systems: [if any]
- SLOs defined: [existing ones]

### Phase 2: Implementation  
- SSOT location: observability/unified_observability.py
- Three Pillars: Logging, Metrics, Tracing
- SLO definitions: [list with targets]
- Docker integration: UnifiedDockerManager
- Alpine support: Monitoring implemented

### Phase 3: Validation
- Logging working: [structured logs example]
- Metrics flowing: [metrics list]
- Tracing enabled: [trace example]
- SLOs monitored: [dashboard screenshot]
- Alpine metrics: [resource usage]

### Phase 4: Cleanup
- Tools consolidated: [count]
- Files deleted: [list]
- Imports updated: [count]
- Documentation: Observability guide created
- Learnings: Monitoring patterns

### Evidence of Correctness:
- Screenshot: Unified dashboard
- Logs: Structured logging output
- Metrics: Grafana/Prometheus view
- Traces: Jaeger/similar view
- SLO dashboard: Target compliance
- Alpine monitoring: Resource graphs

VALIDATION CHECKLIST:
- [ ] Three Pillars implemented
- [ ] SLOs defined and monitored
- [ ] Error budgets calculated
- [ ] Docker integration working
- [ ] Alpine monitoring active
- [ ] Structured logging everywhere
- [ ] Distributed tracing enabled
- [ ] Metrics collection working
- [ ] Alerting configured
- [ ] Performance profiling available
- [ ] Absolute imports used
- [ ] Named values validated
- [ ] Tests with --real-services
- [ ] Value extracted
- [ ] Extraction reports complete
- [ ] Legacy tools removed
- [ ] CLAUDE.md compliance
- [ ] Breaking changes fixed
- [ ] Documentation complete

SUCCESS CRITERIA:
- Single UnifiedObservability implementation
- Three Pillars fully operational
- SLOs defined with error budgets
- Docker/Alpine monitoring integrated
- Structured logging throughout
- Distributed tracing working
- Real-time metrics flowing
- Alerting system active
- Performance insights available
- Complete observability coverage

PRIORITY: P1 HIGH
TIME ALLOCATION: 22 hours
EXPECTED REDUCTION: Multiple monitoring tools → 1 unified system
KEY FEATURES: SLOs, Error Budgets, Alpine monitoring