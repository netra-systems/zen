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
        // Show message updates from sub-agents
        if (payload?.state?.messages && payload.state.messages.length > 0) {
          const message = payload.state.messages[0];
          const agentMessage: Message = {
            id: generateMessageId(),
            role: 'assistant',
            content: message.content || '',
            timestamp: new Date().toISOString(),
            subAgentName: payload.sub_agent_name,
            displayed_to_user: true,
            metadata: { type: 'status_update' }
          };
          addMessage(agentMessage);
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
        const payload = wsMessage.payload as any;
        const errorMessage: Message = {
          id: generateMessageId(),
          role: 'assistant',
          content: `❌ Error: ${payload?.error || 'An error occurred'}`,
          timestamp: new Date().toISOString(),
          subAgentName: payload?.sub_agent_name || 'System',
          displayed_to_user: true,
          error: true
        };
        addMessage(errorMessage);
      } else if (wsMessage.type === 'agent_log') {
        const payload = wsMessage.payload as any;
        const logPrefix = payload.level === 'error' ? '❌' : 
                         payload.level === 'warning' ? '⚠️' : 'ℹ️';
        const logMessage: Message = {
          id: generateMessageId(),
          role: 'assistant',
          content: `${logPrefix} ${payload.message}`,
          timestamp: new Date().toISOString(),
          subAgentName: payload.sub_agent_name || 'System',
          displayed_to_user: true,
          metadata: { type: 'log', level: payload.level }
        };
        addMessage(logMessage);
      } else if (wsMessage.type === 'tool_call') {
        const payload = wsMessage.payload as any;
        const toolMessage: Message = {
          id: generateMessageId(),
          role: 'assistant',
          content: `🔧 Calling tool: ${payload.tool_name}`,
          timestamp: new Date().toISOString(),
          subAgentName: payload.sub_agent_name || 'System',
          displayed_to_user: true,
          metadata: { type: 'tool_call', tool_name: payload.tool_name, tool_args: payload.tool_args }
        };
        addMessage(toolMessage);
      } else if (wsMessage.type === 'tool_result') {
        const payload = wsMessage.payload as any;
        const resultMessage: Message = {
          id: generateMessageId(),
          role: 'assistant',
          content: `✅ Tool result from ${payload.tool_name}: ${JSON.stringify(payload.result).substring(0, 200)}...`,
          timestamp: new Date().toISOString(),
          subAgentName: payload.sub_agent_name || 'System',
          displayed_to_user: true,
          metadata: { type: 'tool_result', tool_name: payload.tool_name, result: payload.result }
        };
        addMessage(resultMessage);
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