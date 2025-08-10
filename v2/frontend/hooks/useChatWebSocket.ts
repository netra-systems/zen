'use client';

import { useEffect, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { useChatStore } from '@/store/chat';
import { Message } from '@/types/chat';

// Counter to ensure unique message IDs
let messageIdCounter = 0;

const generateMessageId = () => {
  return `msg_${Date.now()}_${++messageIdCounter}`;
};

export const useChatWebSocket = () => {
  const { messages } = useWebSocket();
  const { 
    addMessage, 
    setSubAgentName, 
    setSubAgentStatus, 
    setProcessing 
  } = useChatStore();
  
  // Track the last processed message index to avoid reprocessing
  const lastProcessedIndex = useRef(0);

  useEffect(() => {
    // Only process new messages
    const newMessages = messages.slice(lastProcessedIndex.current);
    
    newMessages.forEach((wsMessage) => {
      // Handle different message types
      if (wsMessage.type === 'sub_agent_update') {
        const payload = wsMessage.payload as any;
        if (payload?.sub_agent_name) {
          try {
            setSubAgentName(payload.sub_agent_name);
          } catch (error) {
            console.error('Failed to set sub-agent name:', error);
          }
        }
        if (payload?.state) {
          try {
            setSubAgentStatus({
              status: payload.state.lifecycle || 'idle',
              tools: payload.state.tools || []
            });
          } catch (error) {
            console.error('Failed to set sub-agent status:', error);
          }
        }
      } else if (wsMessage.type === 'agent_started') {
        setProcessing(true);
      } else if (wsMessage.type === 'agent_finished' || wsMessage.type === 'agent_completed') {
        setProcessing(false);
        // Add a completion message
        const completionMessage: Message = {
          id: generateMessageId(),
          role: 'assistant',
          content: 'Task completed successfully.',
          timestamp: new Date().toISOString(),
          subAgentName: useChatStore.getState().subAgentName,
          displayed_to_user: true
        };
        addMessage(completionMessage);
      } else if (wsMessage.type === 'error') {
        setProcessing(false);
        const errorMessage: Message = {
          id: generateMessageId(),
          role: 'assistant',
          content: `Error: ${(wsMessage.payload as any)?.error || 'An error occurred'}`,
          timestamp: new Date().toISOString(),
          subAgentName: 'System',
          displayed_to_user: true,
          error: true
        };
        addMessage(errorMessage);
      } else if (wsMessage.type === 'message_received') {
        // Acknowledgment that message was received - don't add duplicate
        // User messages are already added immediately when sent
      } else if (wsMessage.type === 'agent_stopped') {
        setProcessing(false);
        const stoppedMessage: Message = {
          id: generateMessageId(),
          role: 'assistant',
          content: 'Processing stopped.',
          timestamp: new Date().toISOString(),
          subAgentName: 'System',
          displayed_to_user: true
        };
        addMessage(stoppedMessage);
      }
      
      // Handle any message with displayed_to_user flag
      if ((wsMessage as any).displayed_to_user) {
        const chatMessage: Message = {
          id: `msg_${Date.now()}`,
          role: (wsMessage as any).role || 'assistant',
          content: (wsMessage as any).content || JSON.stringify(wsMessage.payload),
          timestamp: new Date().toISOString(),
          subAgentName: (wsMessage as any).subAgentName || useChatStore.getState().subAgentName,
          displayed_to_user: true,
          metadata: wsMessage.payload
        };
        addMessage(chatMessage);
      }
    });
    
    // Update the last processed index
    lastProcessedIndex.current = messages.length;
  }, [messages, addMessage, setSubAgentName, setSubAgentStatus, setProcessing]);
};