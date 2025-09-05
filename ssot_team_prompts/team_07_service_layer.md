# Team 7: Service Layer Consolidation with Docker Integration Prompt

## COPY THIS ENTIRE PROMPT:

You are a Service Architecture Expert implementing SSOT consolidation for the service layer with Docker/Alpine integration.

🚨 ULTRA CRITICAL FIRST ACTION - READ RECENT ISSUES:
Before ANY work, you MUST read and internalize the "Recent issues to be extra aware of" section from CLAUDE.md:
1. Race conditions in async/websockets - Plan ahead for concurrency
2. Solve 95% of cases first - Make breadth ironclad before edge cases  
3. Limit volume of code - Delete ugly tests rather than add complex code
4. This is a multi-user system - Always consider concurrent users

MANDATORY READING BEFORE STARTING:
1. CLAUDE.md (entire document, especially sections 2.1, 3.6, 6, 7.1 AND the recent issues section)
2. docs/docker_orchestration.md (UnifiedDockerManager architecture)
3. MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
4. SPEC/independent_services.xml (service independence rules)
5. Service section in DEFINITION_OF_DONE_CHECKLIST.md
6. docker-compose.alpine-test.yml (Alpine configurations)

YOUR SPECIFIC CONSOLIDATION TASKS:
1. Consolidate 40+ service folders into 15 logical services
2. Ensure all Docker operations use UnifiedDockerManager
3. Maintain Alpine container support (50% performance gain)
4. Preserve service independence per SPEC/independent_services.xml
5. Consolidate service initialization and health checks

TARGET SERVICE STRUCTURE:
```
netra_backend/app/services/
├── core/                    # Core infrastructure services
│   ├── unified_docker.py    # UnifiedDockerManager (EXISTS)
│   ├── unified_websocket.py # WebSocket service
│   └── unified_cache.py     # Caching service
├── data/                    # Data processing services
│   ├── unified_processor.py
│   └── unified_pipeline.py
├── agent/                   # Agent execution services
│   ├── unified_executor.py
│   └── unified_orchestrator.py
├── admin/                   # Admin services
│   ├── unified_admin.py
│   └── unified_monitoring.py
└── integration/            # External integrations
    ├── unified_llm.py
    └── unified_storage.py
```

SERVICE CONSOLIDATION PATTERNS:
```python
# Pattern 1: Service with Docker awareness
class UnifiedDataService:
    """Data service with Docker integration"""
    def __init__(self, docker_manager: Optional[UnifiedDockerManager] = None):
        self.docker = docker_manager or UnifiedDockerManager()
        self.config = self._load_config()
    
    async def process_with_docker(self, data):
        """Process data using Docker containers if available"""
        if self.docker.is_available():
            # Use Docker for processing
            container = await self.docker.run_alpine_container(
                'data-processor',
                data=data
            )
            return await container.get_result()
        else:
            # Fallback to local processing
            return self._process_local(data)

# Pattern 2: Service independence
class UnifiedCacheService:
    """Cache service maintaining independence"""
    def __init__(self):
        # Service is 100% independent
        # No imports from other services
        self.cache = self._init_cache()
    
    def get(self, key: str):
        """Independent cache operation"""
        return self.cache.get(key)
```

DOCKER INTEGRATION REQUIREMENTS:
```python
# All Docker operations MUST go through UnifiedDockerManager
from netra_backend.app.services.core.unified_docker import UnifiedDockerManager

docker = UnifiedDockerManager()

# Alpine support for 50% performance gain
await docker.start_services(use_alpine=True)

# Health checks
health = await docker.check_health(comprehensive=True)

# Resource monitoring
stats = await docker.get_container_stats()
```

SERVICES TO CONSOLIDATE (40+ → 15):
1. Docker-related services → unified_docker.py (EXISTS)
2. WebSocket services → unified_websocket.py
3. Cache services → unified_cache.py
4. Data services → unified_processor.py + unified_pipeline.py
5. Agent services → unified_executor.py + unified_orchestrator.py
6. Admin services → unified_admin.py + unified_monitoring.py
7. LLM services → unified_llm.py
8. Storage services → unified_storage.py
9. Auth services → Keep separate (independent service)
10. Frontend services → Keep separate (independent service)

CRITICAL REQUIREMENTS:
1. Maintain service independence (SPEC/independent_services.xml)
2. All Docker via UnifiedDockerManager
3. Support Alpine containers (50% faster)
4. Preserve health check mechanisms
5. Consolidate duplicate service logic
6. Validate against MISSION_CRITICAL index
7. Test with real services and Docker
8. Extract value before deletion
9. Maintain async/await patterns
10. Support both Docker and non-Docker modes

VALUE PRESERVATION PROCESS (Per Service):
1. Run git log - identify service-specific fixes
2. Grep for Docker operations
3. Check for Alpine optimizations
4. Extract service initialization logic
5. Document in extraction_report_[service].md
6. Migrate service tests
7. ONLY delete after extraction

TESTING AT EVERY STAGE:

Stage 1 - Pre-consolidation:
- [ ] Map all 40+ services
- [ ] Run python tests/unified_test_runner.py --real-services
- [ ] Test with Alpine containers: --alpine flag
- [ ] Document service dependencies
- [ ] Check Docker integration points

Stage 2 - During consolidation:
- [ ] Test each service consolidation
- [ ] Verify Docker operations work
- [ ] Test Alpine container support
- [ ] Check service independence
- [ ] Monitor performance

Stage 3 - Post-consolidation:
- [ ] Full regression with Docker
- [ ] Alpine performance benchmarks
- [ ] Service health checks
- [ ] Load test with 15 services
- [ ] Memory usage comparison

CONTINUOUS BREAKING-CHANGE AUDIT:
After EVERY consolidation step, audit and update:
- [ ] Service imports across codebase
- [ ] Docker-compose files (both regular and Alpine)
- [ ] Service initialization in main.py
- [ ] Health check endpoints
- [ ] Service discovery mechanisms
- [ ] API endpoints using services
- [ ] Background tasks
- [ ] Test fixtures
- [ ] Environment configurations
- [ ] Deployment scripts

DETAILED REPORTING REQUIREMENTS:
Create reports/team_07_service_layer_[timestamp].md with:

## Consolidation Report - Team 7: Service Layer
### Phase 1: Analysis
- Services analyzed: 40+
- Docker integration points: [list]
- Alpine optimizations found: [list]
- Service dependencies: [matrix]
- Independence violations: [if any]

### Phase 2: Implementation  
- Target structure: 15 services achieved
- Docker integration: All via UnifiedDockerManager
- Alpine support: Maintained/enhanced
- Service groupings: [consolidation map]
- Health checks: [consolidated approach]

### Phase 3: Validation
- Service count: 40+ → 15
- Tests passing: [percentage]
- Alpine performance: [50% improvement verified]
- Docker integration: [working]
- Service independence: [verified]

### Phase 4: Cleanup
- Services deleted: [count]
- Files removed: [list]
- Imports updated: [count]
- Docker configs updated: [regular + Alpine]
- Documentation: Service architecture updated

### Evidence of Correctness:
- Service structure (15 services proof)
- Docker integration tests
- Alpine performance benchmarks
- Health check results
- Service independence verification
- Memory/resource usage

VALIDATION CHECKLIST:
- [ ] Service audit complete (40+ → 15)
- [ ] Docker via UnifiedDockerManager
- [ ] Alpine support maintained
- [ ] Service independence verified
- [ ] Health checks consolidated
- [ ] Absolute imports used
- [ ] Named values validated
- [ ] Tests with --real-services
- [ ] Tests with --alpine flag
- [ ] Value extracted from services
- [ ] Extraction reports complete
- [ ] Async patterns preserved
- [ ] Legacy services deleted
- [ ] CLAUDE.md compliance
- [ ] Breaking changes fixed
- [ ] Performance improved (Alpine)
- [ ] Documentation complete

SUCCESS CRITERIA:
- Service count: 40+ reduced to 15
- All Docker via UnifiedDockerManager
- Alpine containers working (50% faster)
- Service independence maintained
- Zero functionality loss
- Health checks operational
- Performance improved with Alpine
- Both Docker and non-Docker modes work
- Clean service architecture
- Complete consolidation

PRIORITY: P1 HIGH
TIME ALLOCATION: 24 hours
EXPECTED REDUCTION: 40+ service folders → 15 services
KEY BENEFIT: 50% performance gain with Alpine