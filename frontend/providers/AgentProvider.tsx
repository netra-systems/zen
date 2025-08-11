'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { generateUniqueId } from '@/lib/utils';
import { useWebSocketContext } from './WebSocketProvider';
import { useChatStore } from '@/store/chatStore';

interface AgentContextType {
  isProcessing: boolean;
  sendMessage: (message: string) => void;
  stopProcessing: () => void;
  error: Error | null;
  optimizationResults: any;
  messages: any[];
  showThinking: boolean;
  sendWsMessage: (message: any) => void;
}

const AgentContext = createContext<AgentContextType | null>(null);

export const useAgentContext = () => {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgentContext must be used within AgentProvider');
  }
  return context;
};

export const AgentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [optimizationResults, setOptimizationResults] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [showThinking, setShowThinking] = useState(false);
  
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

  // Handle incoming WebSocket messages
  useEffect(() => {
    const lastMessage = wsMessages?.[wsMessages.length - 1];
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case 'agent_started':
        setIsProcessing(true);
        setError(null);
        break;
      case 'agent_completed':
        setIsProcessing(false);
        if (lastMessage.data?.report) {
          chatStore.addMessage({
            id: generateUniqueId('msg'),
            content: lastMessage.data.report,
            role: 'assistant',
            thread_id: lastMessage.data.thread_id || null,
            created_at: new Date().toISOString()
          });
        }
        break;
      case 'agent_error':
        setIsProcessing(false);
        setError(new Error(lastMessage.data?.error?.message || 'Agent error occurred'));
        break;
      case 'optimization_complete':
        setOptimizationResults(lastMessage.data);
        break;
      case 'sub_agent_update':
        // Handle sub-agent updates if needed
        break;
      case 'stream_chunk':
        // Handle streaming responses
        break;
      case 'stream_complete':
        // Handle stream completion
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

  const value: AgentContextType = {
    isProcessing,
    sendMessage,
    stopProcessing,
    error,
    optimizationResults,
    messages,
    showThinking,
    sendWsMessage
  };

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
};
