# Data Helper Agent - Iterative Loop and Interaction Diagrams

## 1. Data Helper Agent Iterative Loop with User Interactions

This diagram shows how the Data Helper Agent can perform an iterative loop based on user interactions, particularly when users don't have access to requested data or need clarification.

```mermaid
stateDiagram-v2
    [*] --> UserRequest: User makes initial request
    
    UserRequest --> TriageAgent: Process request
    
    TriageAgent --> EvaluateDataSufficiency: Analyze available data
    
    state EvaluateDataSufficiency {
        [*] --> CheckData
        CheckData --> Sufficient: Has all needed data
        CheckData --> Partial: Has some data
        CheckData --> Insufficient: No/minimal data
    }
    
    Sufficient --> FullWorkflow: Execute complete workflow
    Partial --> DataHelperActivated: Activate Data Helper
    Insufficient --> DataHelperActivated: Activate Data Helper
    
    state DataHelperActivated {
        [*] --> AnalyzeGaps
        AnalyzeGaps --> GenerateRequest: Create data request
        GenerateRequest --> StructureItems: Structure data points
        StructureItems --> SendToUser: Send request to user
    }
    
    state UserInteractionLoop {
        SendToUser --> UserResponse
        
        UserResponse --> HasData: User provides data
        UserResponse --> NoAccess: "I don't have access"
        UserResponse --> NeedsClarification: "What do you mean?"
        UserResponse --> PartialData: Provides some data
        UserResponse --> Abandon: User abandons
        
        NoAccess --> AdaptRequest: Modify request
        NeedsClarification --> ClarifyRequest: Provide examples
        PartialData --> UpdateContext: Store partial data
        
        AdaptRequest --> AlternativeData: Request alternatives
        ClarifyRequest --> SimplifiedRequest: Simplify language
        UpdateContext --> ReEvaluate: Check if sufficient
        
        AlternativeData --> SendToUser: Send new request
        SimplifiedRequest --> SendToUser: Send clarified request
        
        ReEvaluate --> StillInsufficient: Need more data
        ReEvaluate --> NowSufficient: Can proceed
        
        StillInsufficient --> GenerateFollowUp: Create follow-up request
        GenerateFollowUp --> SendToUser
        
        NowSufficient --> ProceedWithWorkflow
    }
    
    HasData --> ValidateData: Validate provided data
    ValidateData --> StoreInState: Update agent state
    StoreInState --> ProceedWithWorkflow: Continue workflow
    
    ProceedWithWorkflow --> DataAgent: Process available data
    DataAgent --> OptimizationAgent: Generate strategies
    OptimizationAgent --> ActionAgent: Create action plan
    ActionAgent --> ReportingAgent: Generate report
    
    FullWorkflow --> DataAgent
    
    Abandon --> GenerateFallback: Provide general guidance
    GenerateFallback --> [*]
    
    ReportingAgent --> [*]

    note right of UserInteractionLoop
        Iterative Loop:
        - Adapts to user constraints
        - Clarifies requirements
        - Accepts partial data
        - Provides alternatives
    end note
    
    note right of DataHelperActivated
        Data Helper Features:
        - Analyzes data gaps
        - Generates structured requests
        - Provides justifications
        - Handles edge cases
    end note
```

## 2. Data Helper Agent Interactions with Other Agent Processes

This diagram illustrates how the Data Helper Agent interacts with other agents in the system, showing data flow and decision points.

```mermaid
graph TB
    subgraph "User Interface Layer"
        User[User Input]
        WebSocket[WebSocket Manager]
        Response[User Response]
    end
    
    subgraph "Workflow Orchestrator"
        WO[Workflow Orchestrator]
        WO --> |1. Initial Request| Triage
        WO --> |Monitors| ExecutionState[Execution State]
    end
    
    subgraph "Triage Phase"
        Triage[Triage Agent]
        Triage --> |Analyzes| DataSufficiency{Data Sufficiency?}
        DataSufficiency -->|Sufficient| SkipDataHelper[Skip Data Helper]
        DataSufficiency -->|Partial| ActivateDataHelper[Activate Data Helper]
        DataSufficiency -->|Insufficient| OnlyDataHelper[Only Data Helper]
    end
    
    subgraph "Data Helper Process"
        DH[Data Helper Agent]
        DHT[Data Helper Tool]
        DH --> |Uses| DHT
        DHT --> |Generates| DataRequest[Data Request]
        
        DataRequest --> |Contains| UserInstructions[User Instructions]
        DataRequest --> |Contains| StructuredItems[Structured Items]
        DataRequest --> |Contains| Categories[Data Categories]
        
        DH --> |Updates| StateTracking[State.context_tracking]
        DH --> |Emits| WSEvents[WebSocket Events]
    end
    
    subgraph "Agent State Management"
        State[DeepAgentState]
        State --> |Stores| TriageResult[triage_result]
        State --> |Stores| DataHelperResult[data_helper_result]
        State --> |Stores| PreviousResults[previous_results]
        State --> |Stores| UserData[user_provided_data]
    end
    
    subgraph "Other Agents"
        DataAgent[Data Agent]
        OptAgent[Optimization Agent]
        ActionAgent[Action Agent]
        ReportAgent[Reporting Agent]
        
        DataAgent --> |Reads| UserData
        DataAgent --> |Reads| DataHelperResult
        DataAgent --> |Generates| DataInsights[Data Insights]
        
        OptAgent --> |Uses| DataInsights
        OptAgent --> |Considers| DataGaps[Identified Gaps]
        OptAgent --> |Generates| Strategies[Optimization Strategies]
        
        ActionAgent --> |Implements| Strategies
        ActionAgent --> |Notes| MissingData[Missing Data Points]
        
        ReportAgent --> |Summarizes| AllResults[All Agent Results]
        ReportAgent --> |Includes| DataRequestSummary[Data Request Summary]
    end
    
    subgraph "Iterative Feedback Loop"
        UserFeedback[User Provides Data]
        UserFeedback --> |Updates| State
        State --> |Triggers| Reprocessing{Reprocess?}
        Reprocessing -->|Yes| WO
        Reprocessing -->|No| Continue[Continue with current data]
    end
    
    %% Main Flow
    User --> WebSocket
    WebSocket --> WO
    
    SkipDataHelper --> DataAgent
    ActivateDataHelper --> DH
    OnlyDataHelper --> DH
    
    DH --> Response
    Response --> UserFeedback
    
    WSEvents --> |agent_thinking| WebSocket
    WSEvents --> |tool_executing| WebSocket
    WSEvents --> |tool_completed| WebSocket
    
    DataAgent --> OptAgent
    OptAgent --> ActionAgent
    ActionAgent --> ReportAgent
    ReportAgent --> WebSocket
    
    %% State interactions
    Triage -.-> State
    DH -.-> State
    DataAgent -.-> State
    OptAgent -.-> State
    ActionAgent -.-> State
    ReportAgent -.-> State
    
    style DH fill:#f9f,stroke:#333,stroke-width:4px
    style DataRequest fill:#bbf,stroke:#333,stroke-width:2px
    style UserFeedback fill:#bfb,stroke:#333,stroke-width:2px
    style State fill:#ffd,stroke:#333,stroke-width:2px
```

## 3. Detailed Data Helper Iterative Decision Flow

This diagram shows the detailed decision-making process within the Data Helper's iterative loop:

```mermaid
flowchart TD
    Start([User Request Received]) --> Analyze[Analyze Request Context]
    
    Analyze --> Extract[Extract Key Requirements]
    
    Extract --> Check{Check Available Data}
    
    Check -->|Has Data| Validate[Validate Data Quality]
    Check -->|No Data| Generate[Generate Initial Request]
    
    Validate -->|Quality OK| Proceed[Proceed to Next Agent]
    Validate -->|Quality Issues| RequestBetter[Request Better Data]
    
    Generate --> Format[Format Request]
    
    Format --> Present[Present to User]
    
    Present --> Wait[Wait for Response]
    
    Wait --> Received{Response Type?}
    
    Received -->|Complete Data| Store[Store in State]
    Received -->|Partial Data| Assess[Assess Completeness]
    Received -->|No Access| Alternative[Find Alternatives]
    Received -->|Clarification| Explain[Provide Examples]
    Received -->|Timeout| Fallback[Use Defaults]
    
    Store --> Validate
    
    Assess -->|Sufficient| Store
    Assess -->|Insufficient| SupplementRequest[Create Supplemental Request]
    
    SupplementRequest --> Present
    
    Alternative --> SuggestProxy[Suggest Proxy Data]
    
    SuggestProxy --> Present
    
    Explain --> Simplify[Simplify Language]
    
    Simplify --> Examples[Add Examples]
    
    Examples --> Present
    
    Fallback --> UseGeneric[Use Generic Recommendations]
    
    UseGeneric --> Proceed
    
    RequestBetter --> SpecifyFormat[Specify Format Requirements]
    
    SpecifyFormat --> Present
    
    Proceed --> UpdateTracking[Update context_tracking]
    
    UpdateTracking --> EmitEvents[Emit WebSocket Events]
    
    EmitEvents --> End([Continue Workflow])
    
    style Generate fill:#f9f,stroke:#333,stroke-width:2px
    style Present fill:#bbf,stroke:#333,stroke-width:2px
    style Store fill:#bfb,stroke:#333,stroke-width:2px
    style Alternative fill:#ffb,stroke:#333,stroke-width:2px
```

## Key Features of the Data Helper Agent's Iterative Loop

### 1. **Adaptive Request Generation**
- Analyzes triage results and previous agent outputs
- Identifies specific data gaps
- Generates contextual data requests

### 2. **User Interaction Handling**
- **No Access Scenario**: Suggests alternative data sources or proxy metrics
- **Clarification Needed**: Provides examples and simplified explanations
- **Partial Data**: Accepts what's available and adapts recommendations
- **Timeout/Abandon**: Falls back to generic guidance

### 3. **State Management**
- Stores all interactions in `state.context_tracking`
- Maintains data request history
- Tracks user-provided data for downstream agents

### 4. **Integration Points**
- **Triage Agent**: Receives data sufficiency assessment
- **Data Agent**: Provides collected data for analysis
- **Optimization Agent**: Considers data gaps in strategy generation
- **Reporting Agent**: Includes data request summary in final report

### 5. **WebSocket Events**
The Data Helper emits real-time events for transparency:
- `agent_thinking`: Shows reasoning process
- `tool_executing`: Indicates data request generation
- `tool_completed`: Confirms request creation
- `agent_completed`: Signals readiness for user interaction

### 6. **Iterative Refinement**
The system can loop through multiple iterations:
1. Initial data request
2. User provides partial data or indicates constraints
3. Data Helper adapts request
4. Process repeats until sufficient data or user abandons
5. Workflow continues with available data

This iterative approach ensures the system remains helpful even when users have limited data access, providing value through adaptive recommendations based on available information.