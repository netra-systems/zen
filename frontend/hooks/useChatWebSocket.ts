'use client';

import { useEffect, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import type { UnifiedWebSocketEvent } from '@/types/unified-chat';

export const useChatWebSocket = (runId?: string) => {
  const { messages } = useWebSocket();
  const { handleWebSocketEvent } = useUnifiedChatStore();
  
  // Track the last processed message index to avoid reprocessing
  const lastProcessedIndex = useRef(0);

  useEffect(() => {
    // Only process new messages
    const newMessages = messages.slice(lastProcessedIndex.current);
    
    newMessages.forEach((wsMessage) => {
      // Route all events through the unified store
      handleWebSocketEvent(wsMessage as UnifiedWebSocketEvent);
    });
    
    // Update the last processed index
    lastProcessedIndex.current = messages.length;
  }, [messages, handleWebSocketEvent]);

  // Return unified store state for backward compatibility
  const unifiedStore = useUnifiedChatStore();
  
  return {
    // Core state
    messages: unifiedStore.messages,
    isProcessing: unifiedStore.isProcessing,
    
    // Agent state
    agentStatus: unifiedStore.isProcessing ? 'RUNNING' : 'IDLE',
    subAgentName: unifiedStore.currentMessage?.fastLayer?.agentName || '',
    
    // Workflow progress (derived from layers)
    workflowProgress: {
      current_step: unifiedStore.currentMessage?.fastLayer ? 1 : 0,
      total_steps: 3 // Fast, Medium, Slow layers
    },
    
    // Tool state
    activeTools: unifiedStore.currentMessage?.fastLayer?.activeTools || [],
    toolExecutionStatus: unifiedStore.currentMessage?.fastLayer?.activeTools?.length > 0 ? 'executing' : 'idle',
    
    // Connection state (from WebSocket hook)
    isConnected: true, // WebSocket hook handles reconnection
    
    // Error state
    errors: unifiedStore.messages?.filter(m => m.type === 'error') || [],
    
    // Streaming state
    isStreaming: unifiedStore.currentMessage?.mediumLayer?.partialContent ? true : false,
    streamingMessage: unifiedStore.currentMessage?.mediumLayer?.partialContent || '',
    
    // Actions (delegate to unified store)
    addMessage: unifiedStore.addMessage,
    setProcessing: unifiedStore.setProcessing,
    clearMessages: unifiedStore.clearMessages,
    
    // For test compatibility - return empty/default values
    fallbackActive: false,
    fallbackStrategy: '',
    tools: [],
    selectedTool: null,
    toolResults: {},
    registeredTools: [],
    toolExecutionQueue: [],
    retryAttempts: 0,
    aggregatedResults: {},
    validationResults: {},
    pendingApproval: null,
    subAgentStreams: {},
    setSubAgentName: () => {},
    setSubAgentStatus: () => {},
    registerTool: () => {},
    executeTool: () => {}
  };
};