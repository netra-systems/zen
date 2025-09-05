# Multi-Agent Team: UVS Frontend Multiturn Conversation Support v3

## 📚 CRITICAL: Required Reading Before Starting

### Primary Source of Truth
**MUST READ FIRST**: [`../../UVS_REQUIREMENTS.md`](../../UVS_REQUIREMENTS.md) - This is the authoritative specification for UVS implementation.

### Coordination with Backend Teams
**For backend implementation details**, read the backend agent prompts:
- `01_action_plan_enhancement_prompt.md` - ActionPlanBuilder resilience
- `02_reporting_resilience_prompt.md` - ReportingSubAgent UVS
- `03_supervisor_orchestration_prompt.md` - Simplified orchestration

This prompt focuses on frontend implementation to enable seamless multiturn conversations with UVS.

## Team Mission
Enhance the frontend to support multiturn conversations that leverage the UVS system, ensuring users can iteratively refine their optimization requests and always receive value, even with incomplete data.

## Team Composition & Roles

### 1. Principal Engineer (Coordinator)
- **Role**: Frontend architecture and WebSocket integration
- **Responsibilities**:
  - Design conversation state management
  - Implement WebSocket event handling for UVS flows
  - Coordinate between UI components and backend
  - Ensure seamless user experience

### 2. Product Manager Agent
- **Role**: User experience and conversation flows
- **Responsibilities**:
  - Map multiturn conversation journeys
  - Define UI feedback patterns for UVS states
  - Create success metrics for engagement
  - Validate "CHAT IS KING" in UI/UX

### 3. Implementation Agent
- **Role**: Execute frontend enhancements
- **Responsibilities**:
  - Implement conversation context persistence
  - Add UI components for progressive data collection
  - Create visual indicators for UVS report types
  - Build interactive guidance elements

### 4. QA/Security Agent
- **Role**: Frontend testing and validation
- **Responsibilities**:
  - Test multiturn conversation flows
  - Verify state management across sessions
  - Validate WebSocket resilience
  - Test progressive enhancement scenarios

## Context & Requirements

### Core UVS Frontend Principles
```typescript
// Frontend must support these UVS modes
enum ReportType {
  FULL_ANALYSIS = 'full_analysis',     // Complete data available
  PARTIAL_ANALYSIS = 'partial_analysis', // Some data available
  GUIDANCE = 'guidance',                // No data - help user get started
  FALLBACK = 'fallback'                 // Error recovery mode
}

// Conversation must maintain context
interface ConversationContext {
  sessionId: string;
  turnCount: number;
  dataCollected: DataSufficiency;
  previousResponses: ChatMessage[];
  currentWorkflow: WorkflowType;
  nextSteps: string[];
}
```

### Multiturn Conversation Features

#### 1. Progressive Data Collection
```typescript
interface ProgressiveDataUI {
  // Show what data we have
  dataCompleteness: {
    usage_data: boolean;
    cost_data: boolean;
    performance_data: boolean;
  };
  
  // Guide user to provide missing pieces
  missingDataPrompts: string[];
  
  // Allow incremental uploads
  uploadHandlers: {
    csv: (file: File) => void;
    json: (file: File) => void;
    text: (description: string) => void;
  };
}
```

#### 2. Dynamic UI Based on Report Type
```tsx
function ReportDisplay({ report }: { report: UVSReport }) {
  switch (report.report_type) {
    case 'full_analysis':
      return <FullAnalysisView 
        data={report.data_insights}
        optimizations={report.optimizations}
        savings={report.savings_potential}
        charts={report.visualizations}
      />;
      
    case 'partial_analysis':
      return <PartialAnalysisView
        availableData={report.available_sections}
        insights={report.data_insights}
        missingDataGuide={report.missing_data_guidance}
        nextSteps={report.next_steps}
      />;
      
    case 'guidance':
      return <GuidanceView
        questions={report.exploration_questions}
        dataGuide={report.data_collection_guide}
        examples={report.example_optimizations}
        nextSteps={report.next_steps}
      />;
      
    case 'fallback':
      return <FallbackView
        message={report.message}
        alternatives={report.conversation_starters}
        capabilities={report.capabilities}
      />;
  }
}
```

#### 3. Interactive Next Steps
```tsx
interface NextStepsComponent {
  steps: NextStep[];
  onStepClick: (step: NextStep) => void;
}

function NextSteps({ steps, onStepClick }: NextStepsComponent) {
  return (
    <div className="next-steps-container">
      <h3>What would you like to do next?</h3>
      {steps.map((step, index) => (
        <button
          key={index}
          onClick={() => onStepClick(step)}
          className="next-step-action"
        >
          {step.icon && <Icon name={step.icon} />}
          {step.label}
        </button>
      ))}
    </div>
  );
}
```

## Implementation Requirements

### 1. Conversation State Management

```typescript
class ConversationManager {
  private context: ConversationContext;
  private websocket: WebSocketManager;
  
  constructor(sessionId: string) {
    this.context = {
      sessionId,
      turnCount: 0,
      dataCollected: DataSufficiency.NONE,
      previousResponses: [],
      currentWorkflow: null,
      nextSteps: []
    };
  }
  
  async sendMessage(message: string, attachments?: File[]) {
    this.context.turnCount++;
    
    // Include context in request
    const request = {
      message,
      attachments,
      context: {
        turn_count: this.context.turnCount,
        data_collected: this.context.dataCollected,
        previous_summary: this.summarizePrevious()
      }
    };
    
    await this.websocket.send('user_message', request);
  }
  
  handleUVSResponse(response: UVSReport) {
    // Update context based on response
    this.updateDataSufficiency(response);
    this.context.previousResponses.push(response);
    this.context.nextSteps = response.next_steps || [];
    
    // Update UI to show appropriate view
    this.renderResponse(response);
  }
  
  private updateDataSufficiency(response: UVSReport) {
    if (response.report_type === 'full_analysis') {
      this.context.dataCollected = DataSufficiency.SUFFICIENT;
    } else if (response.report_type === 'partial_analysis') {
      this.context.dataCollected = DataSufficiency.PARTIAL;
    }
  }
}
```

### 2. WebSocket Event Handling for UVS

```typescript
class UVSWebSocketHandler {
  private socket: WebSocket;
  private ui: UIManager;
  
  setupEventHandlers() {
    // Workflow type indication
    this.socket.on('workflow_started', (data) => {
      this.ui.showWorkflowIndicator(data.workflow_type);
      
      if (data.workflow_type === 'guidance') {
        this.ui.showMessage('I\'ll help you get started with optimization');
      } else if (data.workflow_type === 'partial_analysis') {
        this.ui.showMessage('Analyzing available data...');
      }
    });
    
    // Agent progress
    this.socket.on('agent_started', (data) => {
      if (data.agent === 'data_helper') {
        this.ui.showHelper('Preparing data collection guidance...');
      }
    });
    
    // Handle different report types
    this.socket.on('agent_completed', (data) => {
      if (data.agent === 'reporting') {
        this.handleReportingComplete(data);
      }
    });
  }
  
  private handleReportingComplete(data: any) {
    // Determine UI based on report type
    switch (data.report_type) {
      case 'guidance':
        this.ui.showGuidanceMode();
        this.ui.enableDataUpload();
        break;
      case 'partial_analysis':
        this.ui.showPartialResults();
        this.ui.highlightMissingData();
        break;
      case 'full_analysis':
        this.ui.showFullAnalysis();
        break;
    }
  }
}
```

### 3. Progressive Enhancement UI Components

```tsx
// Data Collection Helper Component
function DataCollectionHelper({ missingData }: { missingData: string[] }) {
  const [uploadProgress, setUploadProgress] = useState({});
  
  return (
    <div className="data-collection-helper">
      <h3>Help us analyze your AI usage better</h3>
      
      {missingData.includes('usage_data') && (
        <div className="data-request">
          <Icon name="chart" />
          <div>
            <h4>Usage Data</h4>
            <p>Upload your AI service usage logs or metrics</p>
            <FileUpload 
              accept=".csv,.json"
              onUpload={(file) => handleDataUpload('usage', file)}
            />
          </div>
        </div>
      )}
      
      {missingData.includes('cost_data') && (
        <div className="data-request">
          <Icon name="dollar" />
          <div>
            <h4>Cost Data</h4>
            <p>Share your billing or cost reports</p>
            <FileUpload 
              accept=".csv,.pdf"
              onUpload={(file) => handleDataUpload('cost', file)}
            />
          </div>
        </div>
      )}
      
      <div className="alternative-input">
        <p>Or describe your setup:</p>
        <textarea 
          placeholder="E.g., We use GPT-4 for customer support, processing about 10k requests daily..."
          onBlur={(e) => handleTextDescription(e.target.value)}
        />
      </div>
    </div>
  );
}

// Adaptive Report Display
function AdaptiveReport({ report, onNextStep }: AdaptiveReportProps) {
  const [expanded, setExpanded] = useState({});
  
  return (
    <div className={`report-container report-${report.report_type}`}>
      {/* Visual indicator of report completeness */}
      <DataCompletenessIndicator 
        level={report.data_completeness || 0}
      />
      
      {/* Dynamic content based on report type */}
      {report.report_type === 'guidance' ? (
        <GuidanceContent 
          questions={report.exploration_questions}
          onQuestionAnswer={(q, a) => handleQuestionResponse(q, a)}
        />
      ) : report.report_type === 'partial_analysis' ? (
        <PartialAnalysisContent
          available={report.available_sections}
          missing={report.missing_data_guidance}
          onProvideData={() => showDataHelper()}
        />
      ) : (
        <FullAnalysisContent 
          insights={report.data_insights}
          optimizations={report.optimizations}
        />
      )}
      
      {/* Always show next steps */}
      <NextStepsSection 
        steps={report.next_steps}
        onSelectStep={onNextStep}
      />
    </div>
  );
}
```

### 4. Conversation Context Persistence

```typescript
class ConversationPersistence {
  private storage = window.localStorage;
  private sessionKey: string;
  
  saveContext(context: ConversationContext) {
    this.storage.setItem(
      this.sessionKey,
      JSON.stringify({
        ...context,
        timestamp: Date.now()
      })
    );
  }
  
  loadContext(): ConversationContext | null {
    const saved = this.storage.getItem(this.sessionKey);
    if (!saved) return null;
    
    const parsed = JSON.parse(saved);
    
    // Check if context is still valid (e.g., not older than 1 hour)
    if (Date.now() - parsed.timestamp > 3600000) {
      this.storage.removeItem(this.sessionKey);
      return null;
    }
    
    return parsed;
  }
  
  appendToConversation(message: ChatMessage) {
    const context = this.loadContext() || this.createNewContext();
    context.previousResponses.push(message);
    context.turnCount++;
    this.saveContext(context);
  }
}
```

## UI/UX Patterns for UVS

### Visual Feedback States

```css
/* Different visual states for report types */
.report-guidance {
  border-left: 4px solid #3498db; /* Blue - informational */
}

.report-partial_analysis {
  border-left: 4px solid #f39c12; /* Orange - incomplete */
}

.report-full_analysis {
  border-left: 4px solid #27ae60; /* Green - complete */
}

.report-fallback {
  border-left: 4px solid #95a5a6; /* Gray - recovery */
}

/* Progress indicators */
.data-completeness-bar {
  height: 8px;
  background: linear-gradient(
    to right,
    #27ae60 var(--completeness),
    #ecf0f1 var(--completeness)
  );
}

/* Interactive elements for next steps */
.next-step-action {
  transition: all 0.2s;
  cursor: pointer;
}

.next-step-action:hover {
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
```

### Conversation Flow Animations

```typescript
// Smooth transitions between report states
function animateReportTransition(
  fromType: ReportType,
  toType: ReportType
) {
  const container = document.querySelector('.report-container');
  
  container.style.animation = 'fadeOut 0.3s';
  
  setTimeout(() => {
    // Update content
    updateReportContent(toType);
    
    // Animate in with appropriate effect
    if (toType === 'full_analysis' && fromType === 'partial_analysis') {
      container.style.animation = 'slideUpFadeIn 0.5s';
    } else {
      container.style.animation = 'fadeIn 0.3s';
    }
  }, 300);
}
```

## Testing Scenarios

### Scenario 1: No Data to Full Analysis Journey
```typescript
async function test_progressive_data_collection() {
  // Start with no data
  const conversation = new ConversationManager('test-session');
  await conversation.sendMessage('Help me optimize my AI costs');
  
  // Should receive guidance report
  expect(ui.getCurrentReportType()).toBe('guidance');
  expect(ui.hasDataUploadPrompts()).toBe(true);
  
  // Upload partial data
  await conversation.uploadFile(mockUsageData);
  
  // Should receive partial analysis
  expect(ui.getCurrentReportType()).toBe('partial_analysis');
  expect(ui.hasMissingDataIndicators()).toBe(true);
  
  // Upload remaining data
  await conversation.uploadFile(mockCostData);
  
  // Should receive full analysis
  expect(ui.getCurrentReportType()).toBe('full_analysis');
  expect(ui.hasCompleteOptimizations()).toBe(true);
}
```

### Scenario 2: Conversation Context Retention
```typescript
async function test_context_persistence() {
  // First turn
  const conv1 = new ConversationManager('session-1');
  await conv1.sendMessage('I use GPT-4 for customer service');
  
  // Simulate page refresh
  window.location.reload();
  
  // Resume conversation
  const conv2 = new ConversationManager('session-1');
  await conv2.sendMessage('How can I reduce costs?');
  
  // Should remember previous context
  expect(conv2.context.turnCount).toBe(2);
  expect(conv2.context.previousResponses).toHaveLength(1);
}
```

### Scenario 3: Fallback UI Handling
```typescript
async function test_fallback_ui() {
  // Simulate backend error
  mockWebSocket.simulateError('reporting_failed');
  
  await conversation.sendMessage('Analyze my usage');
  
  // UI should show fallback gracefully
  expect(ui.getCurrentReportType()).toBe('fallback');
  expect(ui.hasAlternativeActions()).toBe(true);
  expect(ui.hasErrorMessages()).toBe(false); // Don't show technical errors
}
```

## Performance Optimizations

```typescript
// Debounced text input for descriptions
const handleTextDescription = debounce((text: string) => {
  if (text.length > 50) {
    conversation.addContext({ 
      type: 'user_description',
      content: text 
    });
  }
}, 500);

// Lazy load heavy visualizations
const ChartComponent = lazy(() => import('./Charts'));

// Cache report components
const reportCache = new Map<string, ReactElement>();

function getCachedReport(reportId: string, report: UVSReport) {
  if (!reportCache.has(reportId)) {
    reportCache.set(reportId, <AdaptiveReport report={report} />);
  }
  return reportCache.get(reportId);
}
```

## Success Metrics

### Week 1 Must-Haves
✅ Conversation context persists across turns  
✅ UI adapts to all 4 report types  
✅ Data upload UI appears for guidance/partial reports  
✅ Next steps are interactive and actionable  
✅ WebSocket events update UI appropriately  
✅ No UI crashes on any report type  

### User Engagement Metrics
- Time to first data upload (target: < 2 minutes)
- Conversion from guidance to data provision (target: > 40%)
- Multi-turn conversation rate (target: > 60%)
- Next step click-through rate (target: > 30%)

## Key Files to Modify

### Frontend Components
- `frontend/src/components/Chat/ChatInterface.tsx` - Main conversation UI
- `frontend/src/components/Reports/AdaptiveReport.tsx` - Dynamic report display
- `frontend/src/components/DataCollection/DataHelper.tsx` - Progressive data UI

### State Management
- `frontend/src/store/conversationSlice.ts` - Conversation context
- `frontend/src/store/reportSlice.ts` - Report state handling

### WebSocket Integration
- `frontend/src/services/websocket.ts` - WebSocket event handlers
- `frontend/src/services/uvs-handler.ts` - UVS-specific events

### New Files to Create
- `frontend/src/components/UVS/GuidanceView.tsx` - Guidance report UI
- `frontend/src/components/UVS/ProgressIndicator.tsx` - Data completeness
- `frontend/src/hooks/useConversationContext.ts` - Context management
- `frontend/src/utils/reportTypeAdapter.ts` - Report type handling

## Integration with Backend UVS

### Request Format
```typescript
interface UVSRequest {
  message: string;
  session_id: string;
  turn_count: number;
  context: {
    data_sufficiency: DataSufficiency;
    previous_report_type?: ReportType;
    collected_data_types: string[];
  };
  attachments?: {
    type: 'csv' | 'json' | 'text';
    content: string | File;
  }[];
}
```

### Response Handling
```typescript
interface UVSResponse {
  report_type: ReportType;
  content: any; // Varies by report type
  next_steps: NextStep[];
  data_completeness?: number; // 0-100
  workflow_type: 'guidance' | 'partial_analysis' | 'full_analysis';
  session_context?: {
    can_continue: boolean;
    suggested_actions: string[];
  };
}
```

## Critical Constraints

### MUST Maintain
- WebSocket connection stability
- Message ordering guarantees
- User authentication state
- Existing API contracts
- Browser compatibility (Chrome, Safari, Firefox, Edge)

### Performance Requirements
- Report rendering: < 100ms
- Context save/load: < 50ms
- WebSocket latency: < 200ms
- Smooth animations: 60fps

## Team Execution Flow

1. **Principal** analyzes current frontend architecture
2. **PM** designs optimal multiturn conversation flows
3. **Principal** architects state management solution
4. **Implementation** builds conversation context system
5. **Implementation** creates adaptive UI components
6. **QA** tests all conversation scenarios
7. **Implementation** adds progressive enhancement
8. **QA** validates cross-browser compatibility
9. **Principal** integrates with backend WebSocket
10. **Full team** monitors user engagement metrics

## Deployment Strategy

1. **Feature Flag Implementation**
   ```typescript
   if (features.uvsMultiturn) {
     return <UVSConversationInterface />;
   } else {
     return <LegacyChatInterface />;
   }
   ```

2. **A/B Testing**
   - 10% initial rollout
   - Monitor engagement metrics
   - Gradual increase to 100%

3. **Rollback Plan**
   - Feature flag for instant disable
   - Fallback to simple chat
   - No data migration needed

## Remember the Goal

The frontend should make the UVS system feel magical to users:

1. **Always Helpful** - Never leave user stuck
2. **Progressive** - Build understanding over time
3. **Responsive** - Immediate feedback for all actions
4. **Intelligent** - Remember context and adapt
5. **Delightful** - Smooth, intuitive interactions

This is about creating a conversation, not just a Q&A. The UI should guide users naturally from "I need help" to "Here's my optimized AI strategy" regardless of how much data they start with.