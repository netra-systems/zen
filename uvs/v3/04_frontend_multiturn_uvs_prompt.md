# Multi-Agent Team: UVS Frontend Multiturn Conversation Support

## Required Reading Before Starting

### Primary Sources of Truth (READ IN ORDER)
1. **[`../../UVS_REQUIREMENTS.md`](../../UVS_REQUIREMENTS.md)** - Authoritative UVS specification
2. **[`../../CLAUDE.md`](../../CLAUDE.md)** - Core directives and SSOT principles  
3. **[`../../docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md`](../../docs/AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** - Agent architecture clarity
4. **[`../../SPEC/learnings/websocket_agent_integration_critical.xml`](../../SPEC/learnings/websocket_agent_integration_critical.xml)** - WebSocket SSOT patterns

## Team Mission
Enhance frontend to support multiturn conversations leveraging UVS, ensuring:
- **CHAT IS KING**: Always deliver substantive value (per CLAUDE.md §1.1)
- **Zero Silent Failures**: All errors are loud and visible
- **User Isolation**: Factory pattern for multi-user safety
- **Business Value**: Time-to-value < 2 minutes for new users

## Team Composition & Roles

### 1. Principal Engineer (Coordinator + SSOT Guardian)
- **Primary Responsibilities**:
  - Enforce SSOT principles from CLAUDE.md
  - Implement factory pattern for frontend isolation
  - Ensure WebSocket bridge pattern compliance
  - Coordinate with AgentWebSocketBridge backend
- **Critical Tasks**:
  - Validate against `MISSION_CRITICAL_NAMED_VALUES_INDEX.xml`
  - Implement race condition prevention
  - Create comprehensive MRO analysis for component inheritance

### 2. Product Manager Agent (Business Value Driver)
- **Responsibilities**:
  - Map user journeys with BVJ (Business Value Justification)
  - Define conversion metrics (Free → Paid)
  - Ensure "Chat delivers COMPLETE value" (CLAUDE.md §1.1)
  - Create fallback UX for all failure modes

### 3. Implementation Agent (Execution with Resilience)
- **Responsibilities**:
  - Implement with circuit breakers and retry logic
  - Use factory pattern for component instantiation
  - Add comprehensive error boundaries
  - Follow `SPEC/type_safety.xml` strictly

### 4. QA/Security Agent (Mission Critical Testing)
- **Responsibilities**:
  - Test against `tests/mission_critical/test_websocket_agent_events_suite.py`
  - Verify multi-user isolation (10+ concurrent users)
  - Test all 4 UVS report types + edge cases
  - Validate WebSocket event ordering

## Critical Architecture Patterns

### 1. Frontend Factory Pattern
```typescript
// SSOT: Frontend component factory for user isolation
class FrontendComponentFactory {
  private static instances = new Map<string, ConversationManager>();
  
  static getConversationManager(userId: string): ConversationManager {
    const key = `conv_${userId}`;
    if (!this.instances.has(key)) {
      // Create isolated instance per user
      this.instances.set(key, new ConversationManager(userId));
    }
    return this.instances.get(key)!;
  }
  
  static cleanup(userId: string): void {
    const key = `conv_${userId}`;
    const instance = this.instances.get(key);
    if (instance) {
      instance.dispose();
      this.instances.delete(key);
    }
  }
}
```

### 2. WebSocket Bridge Integration
```typescript
// Must integrate with backend AgentWebSocketBridge pattern
class WebSocketBridgeClient {
  private bridge: AgentWebSocketBridge;
  private retryPolicy = new ExponentialBackoff();
  private circuitBreaker = new CircuitBreaker();
  
  async ensureIntegration(): Promise<void> {
    // Idempotent initialization (per websocket_agent_integration_critical.xml)
    if (this.isIntegrated()) return;
    
    await this.circuitBreaker.call(async () => {
      await this.bridge.ensure_integration();
      await this.validateEventFlow();
    });
  }
  
  private async validateEventFlow(): Promise<void> {
    // Verify all 5 critical events from CLAUDE.md §6
    const requiredEvents = [
      'agent_started',
      'agent_thinking', 
      'tool_executing',
      'tool_completed',
      'agent_completed'
    ];
    
    for (const event of requiredEvents) {
      if (!this.bridge.supportsEvent(event)) {
        throw new Error(`Missing critical event: ${event}`);
      }
    }
  }
}
```

### 3. Race Condition Prevention
```typescript
// CLAUDE.md: "Avoid architectural overkill" - Use simple, proven patterns

// Pattern 1: Simple queue with processing flag
class ConversationManager {
  private messageQueue: Message[] = [];
  private isProcessing = false;
  
  async sendMessage(message: string): Promise<void> {
    // Queue the message
    this.messageQueue.push({ text: message, timestamp: Date.now() });
    
    // Process if not already processing
    if (!this.isProcessing) {
      await this.processMessageQueue();
    }
  }
  
  private async processMessageQueue(): Promise<void> {
    this.isProcessing = true;
    
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()!;
      try {
        await this.websocket.send('user_message', message);
        await this.waitForResponse();
      } catch (error) {
        console.error('🚨 Message send failed:', error);
        this.messageQueue.unshift(message); // Re-queue for retry
        break;
      }
    }
    
    this.isProcessing = false;
  }
}

// Pattern 2: Use React's built-in state batching
function useMessageQueue() {
  const [sending, setSending] = useState(false);
  const [queue, setQueue] = useState<Message[]>([]);
  
  const sendMessage = useCallback(async (text: string) => {
    if (sending) {
      // React batches state updates - no race condition
      setQueue(prev => [...prev, { text }]);
      return;
    }
    
    setSending(true);
    try {
      await api.sendMessage(text);
    } finally {
      setSending(false);
      // Process next in queue if any
      setQueue(prev => {
        const [next, ...rest] = prev;
        if (next) sendMessage(next.text);
        return rest;
      });
    }
  }, [sending]);
  
  return { sendMessage, sending, queueLength: queue.length };
}

// Pattern 3: AbortController for cancellable requests (Web Standard)
class RequestManager {
  private currentRequest?: AbortController;
  
  async sendMessage(message: string): Promise<void> {
    // Cancel in-flight request
    this.currentRequest?.abort();
    
    this.currentRequest = new AbortController();
    
    try {
      await fetch('/api/message', {
        method: 'POST',
        body: JSON.stringify({ message }),
        signal: this.currentRequest.signal
      });
    } catch (error) {
      if (error.name !== 'AbortError') throw error;
    }
  }
}
```

### 4. Error Boundaries with Loud Failures
```tsx
// CLAUDE.md: "Make all errors loud. Protect against silent errors."
class UVSErrorBoundary extends React.Component<Props, State> {
  componentDidCatch(error: Error, info: ErrorInfo) {
    // LOUD error logging
    console.error('🚨 UVS ERROR:', error);
    console.error('Component Stack:', info.componentStack);
    
    // Send to monitoring
    this.sendToMonitoring({
      error: error.message,
      stack: error.stack,
      component: info.componentStack,
      userId: this.props.userId,
      timestamp: Date.now()
    });
    
    // Update UI to show error state
    this.setState({
      hasError: true,
      errorType: this.categorizeError(error),
      fallbackAction: this.determineFallback(error)
    });
  }
  
  render() {
    if (this.state.hasError) {
      return (
        <FallbackUI
          errorType={this.state.errorType}
          action={this.state.fallbackAction}
          onRetry={() => this.setState({ hasError: false })}
        />
      );
    }
    return this.props.children;
  }
}
```

## Edge Cases and Failure Modes

### Critical Edge Cases to Handle

#### 1. WebSocket Disconnection During Multi-turn
```typescript
class WebSocketReconnectionHandler {
  private messageBuffer: QueuedMessage[] = [];
  private reconnectAttempts = 0;
  
  async handleDisconnection(): Promise<void> {
    // Buffer messages during disconnection
    this.startBuffering();
    
    // Attempt reconnection with backoff
    while (this.reconnectAttempts < 5) {
      try {
        await this.reconnect();
        await this.flushBuffer();
        break;
      } catch (e) {
        this.reconnectAttempts++;
        await this.exponentialBackoff();
      }
    }
    
    if (this.reconnectAttempts >= 5) {
      // Switch to polling fallback
      await this.switchToPollingMode();
    }
  }
}
```

#### 2. Concurrent User Message Race Conditions
```typescript
interface MessageQueue {
  userId: string;
  queue: UserMessage[];
  processing: boolean;
}

class ConcurrentMessageHandler {
  private queues = new Map<string, MessageQueue>();
  
  async processMessage(userId: string, message: UserMessage): Promise<void> {
    const queue = this.getOrCreateQueue(userId);
    queue.queue.push(message);
    
    if (!queue.processing) {
      queue.processing = true;
      await this.processQueue(queue);
    }
  }
  
  private async processQueue(queue: MessageQueue): Promise<void> {
    while (queue.queue.length > 0) {
      const message = queue.queue.shift()!;
      await this.sendWithRetry(message);
    }
    queue.processing = false;
  }
}
```

#### 3. State Corruption Recovery
```typescript
class StateRecoveryManager {
  private lastKnownGoodState: ConversationState;
  private stateValidator = new StateValidator();
  
  async validateAndRecover(state: ConversationState): Promise<ConversationState> {
    if (!this.stateValidator.isValid(state)) {
      console.error('🚨 State corruption detected');
      
      // Attempt recovery strategies
      const recovered = await this.tryRecoveryStrategies([
        () => this.recoverFromLocalStorage(),
        () => this.recoverFromServer(),
        () => this.useLastKnownGood(),
        () => this.createFreshState()
      ]);
      
      return recovered;
    }
    
    // State is valid, update last known good
    this.lastKnownGoodState = structuredClone(state);
    return state;
  }
}
```

## SSOT Compliance Checklist

### Pre-Implementation Verification
- [ ] Read `MISSION_CRITICAL_NAMED_VALUES_INDEX.xml`
- [ ] Verify all string literals with `scripts/query_string_literals.py`
- [ ] Check `SPEC/mega_class_exceptions.xml` for allowed large classes
- [ ] Review `SPEC/learnings/websocket_agent_integration_critical.xml`
- [ ] Validate against `DEFINITION_OF_DONE_CHECKLIST.md`

### Implementation Requirements
- [ ] Use factory pattern for ALL component creation
- [ ] Implement idempotent initialization
- [ ] Add circuit breakers to external calls
- [ ] Include retry with exponential backoff
- [ ] Create comprehensive error boundaries
- [ ] Log all errors loudly (no silent failures)
- [ ] Test with 10+ concurrent users

### Testing Requirements
- [ ] Run `python tests/mission_critical/test_websocket_agent_events_suite.py`
- [ ] Test all 4 UVS report types
- [ ] Verify WebSocket event ordering
- [ ] Test disconnection recovery
- [ ] Validate race condition prevention
- [ ] Test state corruption recovery
- [ ] Verify memory cleanup

## Performance Requirements

### Critical Metrics
- **First Meaningful Response**: < 500ms
- **Complete Report Rendering**: < 100ms  
- **WebSocket Latency**: < 200ms
- **Context Save/Load**: < 50ms
- **Memory Per User**: < 10MB
- **Concurrent Users**: 10+ without degradation

### Optimization Strategies
```typescript
// Use React.memo for expensive components
const ExpensiveReport = React.memo(({ report }: Props) => {
  // Component implementation
}, (prevProps, nextProps) => {
  // Custom comparison for re-render optimization
  return prevProps.report.id === nextProps.report.id &&
         prevProps.report.version === nextProps.report.version;
});

// Use virtual scrolling for long lists
const VirtualizedMessageList = ({ messages }: { messages: Message[] }) => {
  return (
    <VirtualList
      height={600}
      itemCount={messages.length}
      itemSize={80}
      overscanCount={5}
    >
      {({ index, style }) => (
        <div style={style}>
          <MessageComponent message={messages[index]} />
        </div>
      )}
    </VirtualList>
  );
};
```

## Deployment Validation

### Pre-Deployment Checklist
1. **Run unified test runner with real services**:
   ```bash
   python tests/unified_test_runner.py --real-services --categories unit integration e2e
   ```

2. **Verify WebSocket events**:
   ```bash
   python tests/mission_critical/test_websocket_agent_events_suite.py
   ```

3. **Check architecture compliance**:
   ```bash
   python scripts/check_architecture_compliance.py
   ```

4. **Update string literals index**:
   ```bash
   python scripts/scan_string_literals.py
   ```

### Rollback Triggers
- Error rate > 1% in production
- WebSocket connection failures > 5%
- Response time > 1s for any UVS report type
- Memory usage > 100MB per user
- Any SSOT violation detected

## Business Value Justification (BVJ)

### Segment: All (Free → Enterprise)
### Business Goal: Conversion & Retention
### Value Impact:
- **Free → Paid Conversion**: +15% through better UX
- **User Engagement**: +60% multi-turn conversation rate
- **Time to Value**: -50% (from 4 min to 2 min)
- **Support Tickets**: -30% due to better guidance

### Strategic Impact:
- Foundation for AI-powered customer success
- Enables data-driven optimization insights
- Reduces onboarding friction significantly
- Creates stickiness through conversation context

## Team Execution Flow

1. **Principal** reviews SSOT compliance and architecture
2. **Principal** performs MRO analysis on existing components
3. **PM** validates BVJ and conversion metrics
4. **Implementation** creates factory pattern infrastructure
5. **Implementation** builds race condition guards
6. **QA** creates edge case test suite
7. **Implementation** adds error boundaries
8. **Implementation** integrates WebSocket bridge
9. **QA** runs mission-critical test suite
10. **Principal** validates SSOT compliance
11. **Full team** monitors rollout metrics

## Final Critical Reminders

### From CLAUDE.md:
- "ULTRA THINK DEEPLY ALWAYS. Our lives DEPEND on you SUCCEEDING."
- "CHAT IS KING - SUBSTANTIVE VALUE"
- "Make all errors loud"
- "Protect against silent errors"
- "COMPLETE YOUR TASKS FULLY"

### From Learnings:
- "ALL initialization methods must be idempotent"
- "Business-critical integrations require proactive health monitoring"
- "Always provide graceful degradation paths"
- "Coordination concerns must be separated from domain concerns"