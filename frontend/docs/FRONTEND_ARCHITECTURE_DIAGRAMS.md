# Frontend Architecture Diagrams

## Key Components Architecture

```mermaid
graph TB
    subgraph "Entry Points"
        App[App Router<br/>Next.js 14]
        Pages[Pages<br/>chat, settings, etc.]
    end

    subgraph "Authentication Layer"
        AuthProvider[AuthProvider<br/>Context + Token Management]
        AuthGuard[AuthGuard<br/>Route Protection]
        AuthService[UnifiedAuthService<br/>Token Refresh + Storage]
    end

    subgraph "WebSocket Layer"
        WSProvider[WebSocketProvider<br/>Connection Management]
        WSService[WebSocketService<br/>Message Handling]
        EventProcessor[EventProcessor<br/>Event Stream Processing]
        Reconciliation[ReconciliationService<br/>Optimistic Updates]
    end

    subgraph "State Management"
        UnifiedChat[UnifiedChatStore<br/>Chat State]
        AuthStore[AuthStore<br/>Auth State]
        ChatPersistence[ChatStatePersistence<br/>Local Storage]
    end

    subgraph "UI Components"
        MainChat[MainChat<br/>Core Chat Interface]
        MessageList[MessageList<br/>Message Display]
        MessageInput[MessageInput<br/>User Input]
        ResponseCard[PersistentResponseCard<br/>Agent Response]
        AgentStatus[AgentStatusIndicator<br/>Processing Status]
        ChatSidebar[ChatSidebar<br/>Thread Navigation]
    end

    subgraph "Hooks Layer"
        useInit[useInitializationCoordinator]
        useLoading[useLoadingState]
        useWebSocket[useWebSocket]
        useAuth[useAuth]
        useThreadNav[useThreadNavigation]
    end

    subgraph "Services"
        API[API Service<br/>Backend Communication]
        Logger[Logger Service<br/>Structured Logging]
        GTM[GTM Events<br/>Analytics]
    end

    App --> Pages
    Pages --> AuthGuard
    AuthGuard --> AuthProvider
    AuthProvider --> AuthService
    
    Pages --> MainChat
    MainChat --> useInit
    MainChat --> useLoading
    MainChat --> MessageList
    MainChat --> MessageInput
    MainChat --> ResponseCard
    
    useInit --> useAuth
    useInit --> useWebSocket
    useInit --> UnifiedChat
    
    WSProvider --> WSService
    WSService --> EventProcessor
    WSService --> Reconciliation
    EventProcessor --> UnifiedChat
    
    UnifiedChat --> ChatPersistence
    AuthProvider --> AuthStore
    
    MessageInput --> UnifiedChat
    MessageList --> UnifiedChat
    ResponseCard --> AgentStatus
    
    ChatSidebar --> useThreadNav
    useThreadNav --> UnifiedChat
    
    WSService --> Logger
    AuthService --> API
    MainChat --> GTM

    style App fill:#e1f5fe
    style AuthProvider fill:#fff3e0
    style WSProvider fill:#f3e5f5
    style UnifiedChat fill:#e8f5e9
    style MainChat fill:#fce4ec
```

## Loading Flow State Machine

```mermaid
stateDiagram-v2
    [*] --> INITIALIZING: Page Load
    
    INITIALIZING --> AUTH_CHECK: Start Auth
    
    AUTH_CHECK --> WEBSOCKET_CONNECT: Token Valid
    AUTH_CHECK --> LOGIN_REDIRECT: No Token
    
    WEBSOCKET_CONNECT --> STORE_INIT: WS Connected
    WEBSOCKET_CONNECT --> CONNECTION_FAILED: WS Failed
    
    STORE_INIT --> READY: Store Initialized
    STORE_INIT --> READY: Timeout (500ms)
    
    READY --> THREAD_LOADING: Thread Selected
    READY --> SHOW_EMPTY: No Thread
    
    THREAD_LOADING --> THREAD_READY: Messages Loaded
    THREAD_LOADING --> THREAD_READY: Timeout (15s)
    
    THREAD_READY --> PROCESSING: User Message
    THREAD_READY --> SHOW_PROMPTS: No Messages
    
    PROCESSING --> THREAD_READY: Agent Complete
    
    CONNECTION_FAILED --> WEBSOCKET_CONNECT: Retry
    CONNECTION_FAILED --> ERROR: Max Retries
    
    ERROR --> INITIALIZING: User Retry
    LOGIN_REDIRECT --> [*]: Navigate Away
    
    note right of INITIALIZING: Progress: 0-33%
    note right of WEBSOCKET_CONNECT: Progress: 33-66%
    note right of STORE_INIT: Progress: 66-100%
    note right of READY: Progress: 100%
```

## Initialization Coordinator Flow

```mermaid
sequenceDiagram
    participant User
    participant Page
    participant AuthGuard
    participant InitCoordinator
    participant AuthContext
    participant WebSocket
    participant Store
    participant MainChat
    
    User->>Page: Navigate to /chat
    Page->>AuthGuard: Render with children
    AuthGuard->>AuthContext: Check auth state
    
    alt No Token
        AuthContext-->>AuthGuard: Not authenticated
        AuthGuard->>User: Redirect to /login
    else Token exists
        AuthContext-->>AuthGuard: Authenticated
        AuthGuard->>MainChat: Render
        MainChat->>InitCoordinator: useInitializationCoordinator()
        
        Note over InitCoordinator: Phase: 'auth' (0-33%)
        InitCoordinator->>AuthContext: Check initialized
        AuthContext-->>InitCoordinator: Auth ready
        
        Note over InitCoordinator: Phase: 'websocket' (33-66%)
        InitCoordinator->>WebSocket: Connect
        WebSocket-->>InitCoordinator: Connected
        
        Note over InitCoordinator: Phase: 'store' (66-100%)
        InitCoordinator->>Store: Initialize
        Store-->>InitCoordinator: Ready
        
        Note over InitCoordinator: Phase: 'ready' (100%)
        InitCoordinator-->>MainChat: isInitialized: true
        MainChat->>User: Show Chat Interface
    end
```

## Component Communication Flow

```mermaid
graph LR
    subgraph "User Actions"
        UserInput[User Types Message]
        ThreadSelect[User Selects Thread]
        Login[User Logs In]
    end
    
    subgraph "Event Flow"
        UserInput --> MessageInput
        MessageInput --> UnifiedChatStore
        UnifiedChatStore --> WebSocketService
        WebSocketService --> Backend[Backend API]
        
        Backend --> WSEvents[WS Events]
        WSEvents --> EventProcessor
        EventProcessor --> StoreUpdate[Store Updates]
        StoreUpdate --> UIUpdate[UI Re-render]
        
        ThreadSelect --> ChatSidebar
        ChatSidebar --> ThreadNav[useThreadNavigation]
        ThreadNav --> UnifiedChatStore
        
        Login --> AuthService
        AuthService --> TokenStorage[Token Storage]
        TokenStorage --> AuthContext
        AuthContext --> RouteAccess[Route Access]
    end
    
    style UserInput fill:#ffeb3b
    style ThreadSelect fill:#ffeb3b
    style Login fill:#ffeb3b
    style UIUpdate fill:#4caf50
```

## WebSocket Event Processing

```mermaid
flowchart TB
    WSMessage[WebSocket Message]
    
    WSMessage --> ParseJSON{Parse JSON}
    ParseJSON -->|Valid| EventType{Event Type?}
    ParseJSON -->|Invalid| LogError[Log Error]
    
    EventType -->|agent_started| AgentEvents[Agent Events]
    EventType -->|user_message| MessageEvents[Message Events]
    EventType -->|thread_created| ThreadEvents[Thread Events]
    EventType -->|tool_executing| ToolEvents[Tool Events]
    
    AgentEvents --> UpdateFastLayer[Update Fast Layer]
    AgentEvents --> UpdateStatus[Update Status]
    
    MessageEvents --> AddMessage[Add to Messages]
    MessageEvents --> Reconcile[Reconciliation Check]
    
    ThreadEvents --> UpdateThread[Update Active Thread]
    ThreadEvents --> LoadMessages[Load Thread Messages]
    
    ToolEvents --> UpdateMedium[Update Medium Layer]
    ToolEvents --> ShowProgress[Show Progress]
    
    UpdateFastLayer --> StoreUpdate[Unified Chat Store]
    UpdateStatus --> StoreUpdate
    AddMessage --> StoreUpdate
    UpdateThread --> StoreUpdate
    UpdateMedium --> StoreUpdate
    
    StoreUpdate --> TriggerRerender[Trigger Component Re-render]
    TriggerRerender --> UpdateUI[UI Updates]
    
    Reconcile --> OptimisticUpdate{Optimistic Update?}
    OptimisticUpdate -->|Yes| MarkConfirmed[Mark Confirmed]
    OptimisticUpdate -->|No| SkipDuplicate[Skip Duplicate]
```

## Authentication Flow with Token Refresh

```mermaid
sequenceDiagram
    participant Browser
    participant AuthContext
    participant AuthService
    participant LocalStorage
    participant Backend
    
    Browser->>AuthContext: Initialize
    AuthContext->>LocalStorage: Check jwt_token
    
    alt Token exists
        LocalStorage-->>AuthContext: Return token
        AuthContext->>AuthService: Validate token
        
        alt Token expired
            AuthService->>LocalStorage: Get refresh_token
            LocalStorage-->>AuthService: Return refresh
            AuthService->>Backend: POST /auth/refresh
            Backend-->>AuthService: New tokens
            AuthService->>LocalStorage: Store new tokens
            AuthService-->>AuthContext: Update user
        else Token valid
            AuthService-->>AuthContext: Decode user
        end
        
        AuthContext->>Browser: User authenticated
        
        Note over AuthContext: Schedule refresh check
        loop Every 2 minutes
            AuthContext->>AuthService: needsRefresh()?
            alt Needs refresh
                AuthService->>Backend: Refresh token
                Backend-->>AuthService: New token
                AuthService->>AuthContext: Update
            end
        end
        
    else No token
        LocalStorage-->>AuthContext: null
        AuthContext->>Browser: Not authenticated
        Browser->>Browser: Redirect to /login
    end
```

## Loading State Transitions

```mermaid
graph TB
    subgraph "Initialization States"
        Init[INITIALIZING<br/>0-33%]
        Connect[CONNECTING<br/>33-66%]
        Store[STORE_INIT<br/>66-100%]
    end
    
    subgraph "Ready States"
        Ready[READY<br/>100%]
        ThreadReady[THREAD_READY]
        Processing[PROCESSING]
    end
    
    subgraph "Error States"
        ConnFailed[CONNECTION_FAILED]
        Error[ERROR]
    end
    
    subgraph "UI Display"
        LoadingScreen[InitializationProgress<br/>Component]
        EmptyState[Show Example Prompts]
        ChatInterface[Main Chat UI]
        ThreadLoading[Loading Thread...]
        AgentWorking[Agent Processing...]
    end
    
    Init --> LoadingScreen
    Connect --> LoadingScreen
    Store --> LoadingScreen
    
    Ready --> EmptyState
    ThreadReady --> ChatInterface
    Processing --> AgentWorking
    
    ConnFailed --> LoadingScreen
    Error --> LoadingScreen
    
    Init -->|Auth Complete| Connect
    Connect -->|WS Open| Store
    Store -->|Initialized| Ready
    
    Ready -->|Thread Selected| ThreadLoading
    ThreadLoading -->|Messages Loaded| ThreadReady
    ThreadReady -->|User Message| Processing
    Processing -->|Complete| ThreadReady
    
    Connect -->|Failed| ConnFailed
    ConnFailed -->|Retry| Connect
    ConnFailed -->|Max Retries| Error
    
    style LoadingScreen fill:#ffecb3
    style EmptyState fill:#c8e6c9
    style ChatInterface fill:#b3e5fc
    style Error fill:#ffcdd2
```

## Store Relationships

```mermaid
erDiagram
    UnifiedChatStore ||--o{ Message : contains
    UnifiedChatStore ||--|| ActiveThread : manages
    UnifiedChatStore ||--o{ FastLayerData : updates
    UnifiedChatStore ||--o{ MediumLayerData : updates
    UnifiedChatStore ||--o{ SlowLayerData : updates
    
    AuthStore ||--|| User : contains
    AuthStore ||--|| Token : stores
    
    WebSocketService ||--|| Connection : maintains
    WebSocketService ||--o{ WebSocketMessage : processes
    
    ChatStatePersistence ||--o{ ThreadHistory : stores
    ChatStatePersistence ||--o{ MessageCache : caches
    
    ReconciliationService ||--o{ OptimisticMessage : tracks
    ReconciliationService ||--o{ Confirmation : processes
    
    Message {
        string id
        string content
        string role
        timestamp created
    }
    
    ActiveThread {
        string threadId
        boolean isLoading
        array messages
    }
    
    User {
        string id
        string email
        string full_name
    }
    
    Token {
        string access_token
        string refresh_token
        number expiry
    }
    
    WebSocketMessage {
        string type
        object payload
        string message_id
    }
```

## Fix for 100% Loading Issue

```mermaid
flowchart TB
    Start[User Loads Chat Page]
    
    Start --> InitCoord[useInitializationCoordinator]
    InitCoord --> CheckPhase{Check Phase}
    
    CheckPhase -->|auth| ShowLoading1[Show Loading 0-33%]
    CheckPhase -->|websocket| ShowLoading2[Show Loading 33-66%]
    CheckPhase -->|store| ShowLoading3[Show Loading 66-100%]
    CheckPhase -->|ready| CheckInit{isInitialized?}
    
    CheckInit -->|No| ShowLoading4[Show Loading]
    CheckInit -->|Yes| OldLogic{OLD: shouldShowLoading?}
    
    OldLogic -->|Yes| StuckAt100[❌ STUCK at 100%]
    OldLogic -->|No| ShowChat1[Show Chat]
    
    CheckInit -->|Yes| NewLogic{NEW: phase !== 'ready'?}
    NewLogic -->|Yes| ShowLoading5[Show Loading]
    NewLogic -->|No| ShowChat2[✅ Show Chat]
    
    style StuckAt100 fill:#ffcdd2
    style ShowChat2 fill:#c8e6c9
    style OldLogic fill:#ffebee
    style NewLogic fill:#e8f5e9
```

## Key Insights

1. **Component Hierarchy**: AuthGuard wraps all protected pages, MainChat is the core interface component
2. **State Management**: UnifiedChatStore is the SSOT for chat state, AuthStore for auth state
3. **Loading Flow**: Three-phase initialization (auth → websocket → store) ensures proper setup
4. **WebSocket Integration**: Event processor handles all real-time updates through a centralized pipeline
5. **Fix Applied**: Changed loading condition from `(!isInitialized || shouldShowLoading)` to `(!isInitialized || phase !== 'ready')` to prevent stuck state at 100%