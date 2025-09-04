# Team 8: WebSocket MISSION CRITICAL Unification Prompt

## COPY THIS ENTIRE PROMPT:

You are a WebSocket Architecture Expert implementing MISSION CRITICAL consolidation for WebSocket infrastructure that enables Chat Value Delivery.

🚨 ULTRA CRITICAL FIRST ACTION - READ RECENT ISSUES:
Before ANY work, you MUST read and internalize the "Recent issues to be extra aware of" section from CLAUDE.md:
1. Race conditions in async/websockets - Plan ahead for concurrency
2. Solve 95% of cases first - Make breadth ironclad before edge cases  
3. Limit volume of code - Delete ugly tests rather than add complex code
4. This is a multi-user system - Always consider concurrent users

MANDATORY READING BEFORE STARTING:
1. CLAUDE.md (entire document, especially Section 6: MISSION CRITICAL WebSocket Events)
2. SPEC/learnings/websocket_agent_integration_critical.xml
3. WEBSOCKET_MODERNIZATION_REPORT.md
4. MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
5. WebSocket section in DEFINITION_OF_DONE_CHECKLIST.md
6. USER_CONTEXT_ARCHITECTURE.md (isolation patterns)

🔴 MISSION CRITICAL: WebSocket events enable substantive chat interactions and AI value delivery to users!

YOUR SPECIFIC CONSOLIDATION TASKS:
1. Consolidate 5+ WebSocketManager implementations into ONE
2. Consolidate 8 emitter classes into ONE UnifiedWebSocketEmitter
3. Integrate EmitterPool into main factory pattern
4. PRESERVE ALL 5 CRITICAL EVENTS (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
5. Maintain AgentWebSocketBridge pattern for agent integration

THE 5 CRITICAL EVENTS (NEVER REMOVE):
1. **agent_started** - User sees agent began processing
2. **agent_thinking** - Real-time reasoning visibility  
3. **tool_executing** - Tool usage transparency
4. **tool_completed** - Tool results display
5. **agent_completed** - Response ready notification

TARGET IMPLEMENTATION:
```python
# Location: netra_backend/app/websocket_core/unified_manager.py
class UnifiedWebSocketManager:
    """THE ONLY WebSocketManager - MISSION CRITICAL for chat value"""
    
    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._emitter = UnifiedWebSocketEmitter()
        self._lock = asyncio.Lock()
        
    async def emit_critical_event(self, user_id: str, event_type: str, data: dict):
        """NEVER bypass or remove these critical events!"""
        if event_type not in UnifiedWebSocketEmitter.CRITICAL_EVENTS:
            logger.warning(f"Non-critical event: {event_type}")
        
        # MUST emit for chat value delivery
        async with self._lock:
            if user_id in self._connections:
                await self._connections[user_id].send_json({
                    'type': event_type,
                    'data': data,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
    def create_agent_bridge(self, context: UserExecutionContext):
        """Create bridge for agent WebSocket integration"""
        return AgentWebSocketBridge(self, context)

# Location: netra_backend/app/websocket_core/unified_emitter.py  
class UnifiedWebSocketEmitter:
    """THE ONLY emitter - preserves ALL critical events"""
    
    CRITICAL_EVENTS = [
        'agent_started',
        'agent_thinking',
        'tool_executing', 
        'tool_completed',
        'agent_completed'
    ]
    
    def __init__(self, manager: UnifiedWebSocketManager):
        self.manager = manager
        self._validate_critical_events()
        
    def _validate_critical_events(self):
        """Ensure critical events are NEVER removed"""
        for event in self.CRITICAL_EVENTS:
            if not hasattr(self, f'emit_{event}'):
                # Auto-generate if missing
                setattr(self, f'emit_{event}', 
                       lambda data, e=event: self._emit_critical(e, data))
    
    async def _emit_critical(self, event_type: str, data: dict):
        """Emit critical event - NEVER bypass this"""
        await self.manager.emit_critical_event(
            self.context.user_id,
            event_type,
            data
        )

# Integration with agents (CRITICAL):
class AgentWebSocketBridge:
    """Bridge pattern for agent WebSocket integration"""
    def __init__(self, manager: UnifiedWebSocketManager, context: UserExecutionContext):
        self.manager = manager
        self.context = context
        
    async def notify_agent_started(self, agent_name: str):
        """Critical event when agent starts"""
        await self.manager.emit_critical_event(
            self.context.user_id,
            'agent_started',
            {'agent': agent_name}
        )
```

FILES TO CONSOLIDATE:

WebSocketManager implementations (5+):
- websocket_core/manager.py (likely CANONICAL - keep)
- agents/base/interface.py (merge)
- core/websocket_exceptions.py (merge)
- core/interfaces_websocket.py (merge)
- agents/interfaces.py (merge)

Emitter implementations (8):
- services/websocket_emitter_pool.py (merge into factory)
- supervisor/agent_instance_factory.py (UserWebSocketEmitter - merge)
- Plus 6 other emitter variants

CRITICAL INTEGRATION POINTS:
```python
# AgentRegistry MUST set WebSocket manager
registry.set_websocket_manager(unified_manager)

# ExecutionEngine MUST have WebSocketNotifier
engine = ExecutionEngine(websocket_notifier=bridge)

# EnhancedToolExecutionEngine MUST wrap execution
tool_engine.set_websocket_bridge(bridge)
```

CRITICAL REQUIREMENTS:
1. NEVER remove the 5 critical events
2. Generate MRO report for WebSocket classes
3. Single WebSocketManager implementation
4. Single WebSocketEmitter implementation
5. EmitterPool integrated into factory
6. AgentWebSocketBridge pattern preserved
7. Test with test_websocket_agent_events_suite.py
8. Multi-user isolation maintained
9. Thread-safe event emission
10. No event loss during consolidation

VALUE PRESERVATION PROCESS:
1. Run git log - identify WebSocket fixes
2. Grep for all 5 critical events
3. Check event emission patterns
4. Extract connection management logic
5. Document in extraction_report_websocket.md
6. Migrate WebSocket tests
7. ONLY delete after verification

TESTING AT EVERY STAGE:

Stage 1 - Pre-consolidation:
- [ ] Run python tests/mission_critical/test_websocket_agent_events_suite.py
- [ ] Capture current event flow
- [ ] Document all WebSocket implementations
- [ ] Test multi-user WebSocket connections
- [ ] Verify all 5 events working

Stage 2 - During consolidation:
- [ ] Test after EACH merge
- [ ] Verify critical events still emitted
- [ ] Test agent integration continuously
- [ ] Check multi-user isolation
- [ ] Monitor for event loss

Stage 3 - Post-consolidation:
- [ ] Full mission critical test suite
- [ ] Load test with 100+ WebSocket connections
- [ ] Event integrity verification
- [ ] Performance benchmarks
- [ ] Memory profiling

CONTINUOUS BREAKING-CHANGE AUDIT:
After EVERY consolidation step, audit and update:
- [ ] AgentRegistry WebSocket injection
- [ ] ExecutionEngine WebSocket notifier
- [ ] Tool execution WebSocket wrapping
- [ ] API WebSocket endpoints
- [ ] Frontend WebSocket clients
- [ ] Event handler registrations
- [ ] WebSocket middleware
- [ ] Connection management
- [ ] Event routing logic
- [ ] Test WebSocket mocks

DETAILED REPORTING REQUIREMENTS:
Create reports/team_08_websocket_critical_[timestamp].md with:

## Consolidation Report - Team 8: WebSocket MISSION CRITICAL
### Phase 1: Analysis
- WebSocketManager implementations: 5+ found
- Emitter implementations: 8 found
- Critical events verified: All 5 present
- Integration points: [list all]
- Multi-user issues: [if any]

### Phase 2: Implementation  
- SSOT WebSocketManager: websocket_core/unified_manager.py
- SSOT Emitter: websocket_core/unified_emitter.py
- EmitterPool: Integrated into factory
- Bridge pattern: AgentWebSocketBridge maintained
- Critical events: Preservation strategy

### Phase 3: Validation
- Mission critical tests: PASSING
- All 5 events verified: [checklist]
- Multi-user test: 100+ users
- Performance: [benchmarks]
- Memory: [before/after]

### Phase 4: Cleanup
- Files deleted: 5+ managers, 8 emitters
- Imports updated: [count]
- Integration points: All verified
- Documentation: WebSocket architecture updated
- Learnings: Event preservation patterns

### Evidence of Correctness:
- Screenshot: All 5 events in test output
- WebSocket trace showing event flow
- Multi-user connection logs
- Performance graphs
- Memory usage comparison
- Chat functionality video/proof

VALIDATION CHECKLIST:
- [ ] MRO report generated
- [ ] Single WebSocketManager created
- [ ] Single WebSocketEmitter created
- [ ] EmitterPool integrated
- [ ] ALL 5 CRITICAL EVENTS WORKING
- [ ] AgentWebSocketBridge preserved
- [ ] Multi-user isolation verified
- [ ] Thread-safe operations
- [ ] Mission critical tests passing
- [ ] Absolute imports used
- [ ] Named values validated
- [ ] Tests with --real-services
- [ ] Value extracted before deletion
- [ ] Extraction reports complete
- [ ] Zero event loss
- [ ] Legacy files deleted
- [ ] CLAUDE.md Section 6 compliance
- [ ] Breaking changes fixed
- [ ] Performance maintained
- [ ] Documentation complete

SUCCESS CRITERIA:
- Single UnifiedWebSocketManager
- Single UnifiedWebSocketEmitter
- All 5 critical events functioning
- Zero WebSocket event loss
- Multi-user support intact
- Chat value delivery preserved
- AgentRegistry integration working
- ExecutionEngine integration working
- Tool execution notifications working
- Mission critical tests 100% passing

PRIORITY: P0 MISSION CRITICAL (Chat value depends on this!)
TIME ALLOCATION: 22 hours
EXPECTED REDUCTION: 13+ files → 2 unified implementations
CRITICAL: NEVER remove the 5 critical events!