'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { generateUniqueId } from '@/lib/utils';
import { useWebSocketContext } from './WebSocketProvider';
import { useChatStore } from '@/store/chatStore';
import type {
  AgentContextType, Message, OptimizationResults, AgentError,
  WebSocketMessage, SubAgentState, Thread, ThreadHistory,
  AgentConfig, AgentContext
} from '@/types/unified';

// Using typed interface from @/types/agent

const AgentContext = createContext<AgentContextType | null>(null);

export const useAgentContext = () => {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgentContext must be used within AgentProvider');
  }
  return context;
};

interface AgentProviderProps {
  children: React.ReactNode;
  config?: AgentConfig;
  context?: Partial<AgentContext>;
}

export const AgentProvider: React.FC<AgentProviderProps> = ({ 
  children, 
  config,
  context: initialContext 
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<AgentError | null>(null);
  const [optimizationResults, setOptimizationResults] = useState<OptimizationResults | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [showThinking, setShowThinking] = useState(false);
  const [context, setContext] = useState<AgentContext>({
    ...initialContext,
    preferences: { ...config, ...initialContext?.preferences }
  });
  
  // Only use WebSocketContext if it exists
  let wsContext: any = null;
  try {
    wsContext = useWebSocketContext();
  } catch {
    // WebSocketContext not available
  }
  
  const { sendMessage: wsSendMessage, messages: wsMessages, status } = wsContext || {
    sendMessage: () => {},
    messages: [],
    status: 'CLOSED'
  };
  
  const chatStore = useChatStore();

  // Handle incoming WebSocket messages with proper typing
  useEffect(() => {
    const lastMessage = wsMessages?.[wsMessages.length - 1] as WebSocketMessage;
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case 'agent_started':
        setIsProcessing(true);
        setError(null);
        break;
        
      case 'agent_completed':
        setIsProcessing(false);
        if (lastMessage.data?.report) {
          const message: Message = {
            id: generateUniqueId('msg'),
            content: lastMessage.data.report,
            role: 'assistant',
            type: 'ai',
            thread_id: lastMessage.data.thread_id || null,
            created_at: new Date().toISOString(),
            displayed_to_user: true,
            metadata: {
              sub_agent: lastMessage.data.sub_agent,
              execution_time_ms: lastMessage.data.execution_time_ms,
              model_used: lastMessage.data.model_used
            }
          };
          chatStore.addMessage(message);
        }
        break;
        
      case 'agent_error':
        setIsProcessing(false);
        const agentError: AgentError = {
          id: generateUniqueId('error'),
          type: lastMessage.data?.error?.type || 'execution',
          message: lastMessage.data?.error?.message || 'Agent error occurred',
          details: lastMessage.data?.error?.details,
          sub_agent: lastMessage.data?.sub_agent,
          timestamp: new Date().toISOString(),
          is_recoverable: lastMessage.data?.error?.is_recoverable || false
        };
        setError(agentError);
        break;
        
      case 'optimization_complete':
        const optimizationData: OptimizationResults = {
          id: lastMessage.data?.id || generateUniqueId('opt'),
          status: 'completed',
          created_at: new Date().toISOString(),
          analysis: lastMessage.data?.analysis || {
            summary: '',
            key_findings: [],
            bottlenecks_identified: [],
            root_causes: [],
            confidence_score: 0,
            analysis_timestamp: new Date().toISOString()
          },
          metrics: lastMessage.data?.metrics || [],
          recommendations: lastMessage.data?.recommendations || []
        };
        setOptimizationResults(optimizationData);
        break;
        
      case 'sub_agent_update':
        const subAgentUpdate: SubAgentState = {
          name: lastMessage.data?.name || 'Unknown Agent',
          status: lastMessage.data?.status || 'running',
          description: lastMessage.data?.description,
          tools: lastMessage.data?.tools || [],
          progress: lastMessage.data?.progress,
          error: lastMessage.data?.error,
          execution_time: lastMessage.data?.execution_time
        };
        chatStore.setSubAgentStatus(subAgentUpdate);
        break;
        
      case 'stream_chunk':
        // Handle streaming responses
        if (lastMessage.data?.content) {
          // Update streaming message or create new one
          const streamingMessage: Message = {
            id: lastMessage.data.message_id || generateUniqueId('stream'),
            content: lastMessage.data.content,
            role: 'assistant',
            type: 'ai',
            created_at: new Date().toISOString(),
            displayed_to_user: true,
            metadata: {
              is_streaming: true,
              chunk_index: lastMessage.data.chunk_index
            }
          };
          
          if (lastMessage.data.is_final) {
            streamingMessage.metadata!.is_streaming = false;
          }
          
          // Update or add message
          if (lastMessage.data.message_id) {
            chatStore.updateMessage(lastMessage.data.message_id, {
              content: lastMessage.data.content,
              metadata: streamingMessage.metadata
            });
          } else {
            chatStore.addMessage(streamingMessage);
          }
        }
        break;
        
      case 'stream_complete':
        // Handle stream completion
        setIsProcessing(false);
        break;
    }
  }, [wsMessages, chatStore]);

  const sendMessage = useCallback((message: string) => {
    if (status !== 'OPEN' && wsContext) {
      setError(new Error('WebSocket is not connected'));
      return;
    }

    // Add user message to chat
    chatStore.addMessage({
      id: generateUniqueId('msg'),
      content: message,
      role: 'user',
      thread_id: null,
      created_at: new Date().toISOString()
    });

    // Send message via WebSocket
    wsSendMessage({
      type: 'chat_message',
      data: { content: message }
    });

    setIsProcessing(true);
    setError(null);
  }, [status, wsSendMessage, chatStore, wsContext]);

  const stopProcessing = useCallback(() => {
    wsSendMessage({
      type: 'stop_processing',
      data: {}
    });
    setIsProcessing(false);
  }, [wsSendMessage]);

  const sendWsMessage = useCallback((message: any) => {
    wsSendMessage(message);
  }, [wsSendMessage]);

  const startAgent = useCallback((
    userRequest: string,
    threadId?: string,
    context?: Record<string, any>,
    settings?: Record<string, any>
  ) => {
    if (status !== 'OPEN' && wsContext) {
      setError(new Error('WebSocket is not connected'));
      return;
    }

    // Send start_agent message to backend
    wsSendMessage({
      type: 'start_agent',
      payload: {
        user_request: userRequest,
        thread_id: threadId || null,
        context: context || {},
        settings: settings || {}
      }
    });

    setIsProcessing(true);
    setError(null);
  }, [status, wsSendMessage, wsContext]);

  const value: AgentContextType = {
    isProcessing,
    sendMessage,
    stopProcessing,
    error,
    optimizationResults,
    messages,
    showThinking,
    sendWsMessage,
    startAgent
  };

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
};
