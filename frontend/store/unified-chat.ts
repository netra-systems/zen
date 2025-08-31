// Unified Chat Store - Modular architecture
// Version 5.0 - Clean separation using focused stores

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { unstable_batchedUpdates } from 'react-dom';
import { WebSocketEventBuffer } from '@/lib/circular-buffer';
import { handleWebSocketEvent } from './websocket-event-handlers';
import { mergeMediumLayerContent, mergeSlowLayerAgents, createUpdatedFastLayerData } from './layer-merge-utils';
import type { UnifiedChatState, UnifiedWebSocketEvent } from '@/types/store-types';
import type { AgentExecution } from '@/types/store-types';
import type { OptimisticMessage } from '@/services/optimistic-updates';

// ============================================
// Initial State Configuration
// ============================================

const createInitialState = () => ({
  // Layer data
  fastLayerData: null,
  mediumLayerData: null,
  slowLayerData: null,
  
  // Processing state
  isProcessing: false,
  currentRunId: null,
  
  // Thread management
  activeThreadId: null,
  threads: new Map(),
  isThreadLoading: false,
  threadLoadingState: null,
  messages: [],
  
  // WebSocket connection
  isConnected: false,
  connectionError: null,
  
  // Initialization state
  initialized: false,
  
  // Agent tracking
  executedAgents: new Map<string, AgentExecution>(),
  agentIterations: new Map<string, number>(),
  
  // Optimistic updates
  optimisticMessages: new Map<string, OptimisticMessage>(),
  pendingUserMessage: null as OptimisticMessage | null,
  pendingAiMessage: null as OptimisticMessage | null,
  
  // Debug and performance
  wsEventBuffer: new WebSocketEventBuffer(1000),
  wsEventBufferVersion: 0,
  performanceMetrics: createInitialPerformanceMetrics(),
  
  // Legacy compatibility
  subAgentName: null,
  subAgentStatus: null,
  subAgentTools: [],
  subAgentProgress: null,
  subAgentError: null,
  subAgentDescription: null,
  subAgentExecutionTime: null,
  queuedSubAgents: []
});

const createInitialPerformanceMetrics = () => ({
  renderCount: 0,
  lastRenderTime: 0,
  averageResponseTime: 0,
  memoryUsage: 0
});

// ============================================
// Unified Chat Store
// ============================================

export const useUnifiedChatStore = create<UnifiedChatState>()(
  devtools(
    (set, get) => ({
      ...createInitialState(),
      
      // Layer update actions with modular merging and batched updates
      updateFastLayer: (data) => {
        unstable_batchedUpdates(() => {
          updateFastLayerData(data, set, get);
        });
      },
      
      updateMediumLayer: (data) => {
        unstable_batchedUpdates(() => {
          updateMediumLayerData(data, set, get);
        });
      },
      
      updateSlowLayer: (data) => {
        unstable_batchedUpdates(() => {
          updateSlowLayerData(data, set, get);
        });
      },
      
      // Modular WebSocket event handling with batched updates
      handleWebSocketEvent: (event: UnifiedWebSocketEvent) => {
        unstable_batchedUpdates(() => {
          handleWebSocketEvent(event, get(), set, get);
        });
      },
      
      // Additional actions
      resetLayers: () => resetAllLayers(set),
      addMessage: (message) => addMessageToHistory(message, set),
      setProcessing: (isProcessing) => setProcessingState(isProcessing, set),
      setConnectionStatus: (isConnected, error) => updateConnectionStatus(isConnected, error, set),
      
      // Thread management actions
      setActiveThread: (threadId) => setActiveThreadId(threadId, set),
      setThreadLoading: (isLoading) => setThreadLoadingState(isLoading, set),
      startThreadLoading: (threadId) => startThreadLoadingProcess(threadId, set),
      completeThreadLoading: (threadId, messages) => completeThreadLoadingProcess(threadId, messages, set),
      clearMessages: () => clearMessageHistory(set),
      loadMessages: (messages) => loadMessageHistory(messages, set),
      
      // Legacy sub-agent compatibility
      setSubAgentName: (name) => setSubAgentNameWithSync(name, set, get),
      setSubAgentStatus: (statusData) => updateSubAgentStatus(statusData, set),
      
      // Agent tracking actions
      updateExecutedAgent: (agentId, execution) => updateExecutedAgentAction(agentId, execution, set),
      incrementAgentIteration: (agentId) => incrementAgentIterationAction(agentId, set, get),
      resetAgentTracking: () => resetAgentTrackingAction(set),
      
      // Optimistic update actions
      addOptimisticMessage: (message) => addOptimisticMessageAction(message, set),
      updateOptimisticMessage: (localId, updates) => updateOptimisticMessageAction(localId, updates, set),
      removeOptimisticMessage: (localId) => removeOptimisticMessageAction(localId, set),
      clearOptimisticMessages: () => clearOptimisticMessagesAction(set),
      
      // Comprehensive reset for logout
      resetStore: () => resetEntireStore(set),
    }),
    { name: 'unified-chat-store' }
  )
);

// ============================================
// Layer Update Functions
// ============================================

const updateFastLayerData = (
  data: any,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const state = get();
  const fastLayerData = state.fastLayerData 
    ? { ...state.fastLayerData, ...data }
    : data;
  set({ fastLayerData });
};

const updateMediumLayerData = (
  data: any,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const state = get();
  const mediumLayerData = mergeMediumLayerContent(state.mediumLayerData, data);
  set({ mediumLayerData });
};

// Layer merge utilities moved to separate module

const updateSlowLayerData = (
  data: any,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const state = get();
  const slowLayerData = mergeSlowLayerAgents(state.slowLayerData, data);
  set({ slowLayerData });
};

// Slow layer merge utilities moved to separate module

// ============================================
// Action Helper Functions (8 lines max)
// ============================================

const resetAllLayers = (set: (partial: Partial<UnifiedChatState>) => void): void => {
  set({
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null,
    currentRunId: null,
    isProcessing: false,
    messages: []
  });
};

const addMessageToHistory = (
  message: any,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set((state) => ({ messages: [...state.messages, message] }));
};

const setProcessingState = (
  isProcessing: boolean,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set({ isProcessing });
};

const updateConnectionStatus = (
  isConnected: boolean,
  error: string | undefined,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set({ isConnected, connectionError: error || null });
};

const setActiveThreadId = (
  threadId: string | null,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set({ activeThreadId: threadId });
};

const setThreadLoadingState = (
  isLoading: boolean,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set({ isThreadLoading: isLoading });
};

const startThreadLoadingProcess = (
  threadId: string,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set({ activeThreadId: threadId, isThreadLoading: true, messages: [] });
};

const completeThreadLoadingProcess = (
  threadId: string,
  messages: any[],
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set({ activeThreadId: threadId, isThreadLoading: false, messages });
};

const clearMessageHistory = (set: (partial: Partial<UnifiedChatState>) => void): void => {
  set({ messages: [] });
};

const loadMessageHistory = (
  messages: any[],
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set({ messages, isThreadLoading: false });
};

const setSubAgentNameWithSync = (
  name: string | null,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const state = get();
  const fastLayerData = createUpdatedFastLayerData(state.fastLayerData, name);
  set({ subAgentName: name, fastLayerData });
};

const updateSubAgentStatus = (
  statusData: any,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set({
    subAgentStatus: statusData?.status || null,
    subAgentTools: statusData?.tools || [],
    subAgentProgress: statusData?.progress || null,
    subAgentError: statusData?.error || null
  });
};

// ============================================
// Agent Tracking Action Functions (8 lines max)
// ============================================

const updateExecutedAgentAction = (
  agentId: string,
  execution: AgentExecution,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set((state) => {
    const executedAgents = new Map(state.executedAgents);
    executedAgents.set(agentId, execution);
    return { executedAgents };
  });
};

const incrementAgentIterationAction = (
  agentId: string,
  set: (partial: Partial<UnifiedChatState>) => void,
  get: () => UnifiedChatState
): void => {
  const state = get();
  const agentIterations = new Map(state.agentIterations);
  const currentIteration = agentIterations.get(agentId) || 0;
  agentIterations.set(agentId, currentIteration + 1);
  set({ agentIterations });
};

const resetAgentTrackingAction = (set: (partial: Partial<UnifiedChatState>) => void): void => {
  set({
    executedAgents: new Map<string, AgentExecution>(),
    agentIterations: new Map<string, number>()
  });
};

// ============================================
// Optimistic Update Action Functions (8 lines max)
// ============================================

const addOptimisticMessageAction = (
  message: OptimisticMessage,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set((state) => ({
    optimisticMessages: new Map(state.optimisticMessages).set(message.localId, message),
    pendingUserMessage: message.role === 'user' ? message : state.pendingUserMessage,
    pendingAiMessage: message.role === 'assistant' ? message : state.pendingAiMessage
  }));
};

const updateOptimisticMessageAction = (
  localId: string,
  updates: Partial<OptimisticMessage>,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set((state) => {
    const optimisticMessages = new Map(state.optimisticMessages);
    const existing = optimisticMessages.get(localId);
    if (!existing) return state;
    const updated = { ...existing, ...updates };
    optimisticMessages.set(localId, updated);
    return { optimisticMessages };
  });
};

const removeOptimisticMessageAction = (
  localId: string,
  set: (partial: Partial<UnifiedChatState>) => void
): void => {
  set((state) => {
    const optimisticMessages = new Map(state.optimisticMessages);
    optimisticMessages.delete(localId);
    const pendingUserMessage = state.pendingUserMessage?.localId === localId ? null : state.pendingUserMessage;
    const pendingAiMessage = state.pendingAiMessage?.localId === localId ? null : state.pendingAiMessage;
    return { optimisticMessages, pendingUserMessage, pendingAiMessage };
  });
};

const clearOptimisticMessagesAction = (set: (partial: Partial<UnifiedChatState>) => void): void => {
  set({
    optimisticMessages: new Map(),
    pendingUserMessage: null,
    pendingAiMessage: null
  });
};

// Comprehensive store reset for logout
const resetEntireStore = (set: (partial: Partial<UnifiedChatState>) => void): void => {
  set({
    // Reset all layer data
    fastLayerData: null,
    mediumLayerData: null,
    slowLayerData: null,
    
    // Reset processing state
    isProcessing: false,
    currentRunId: null,
    
    // Reset thread management
    activeThreadId: null,
    threads: new Map(),
    isThreadLoading: false,
    threadLoadingState: null,
    messages: [],
    
    // Reset WebSocket connection
    isConnected: false,
    connectionError: null,
    
    // Reset initialization state
    initialized: false,
    
    // Reset agent tracking
    executedAgents: new Map(),
    agentIterations: new Map(),
    
    // Reset optimistic updates
    optimisticMessages: new Map(),
    pendingUserMessage: null,
    pendingAiMessage: null,
    
    // Reset debug and performance
    wsEventBuffer: new WebSocketEventBuffer(1000),
    wsEventBufferVersion: 0,
    performanceMetrics: createInitialPerformanceMetrics(),
    
    // Reset legacy compatibility
    subAgentName: null,
    subAgentStatus: null,
    subAgentTools: [],
    subAgentProgress: null,
    subAgentError: null,
    subAgentDescription: null,
    subAgentExecutionTime: null,
    queuedSubAgents: []
  });
};
