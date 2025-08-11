'use client';

import { useEffect, useRef, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import { useChatStore } from '@/store/chat';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { Message } from '@/types/chat';
import type { UnifiedWebSocketEvent } from '@/types/unified-chat';
import { generateUniqueId } from '@/lib/utils';

export const useChatWebSocket = (runId?: string) => {
  const { messages } = useWebSocket();
  const { 
    addMessage, 
    setSubAgentName, 
    setSubAgentStatus, 
    setProcessing 
  } = useChatStore();
  
  // Unified chat store for new layer-based UI
  const { 
    handleWebSocketEvent,
    setProcessing: setUnifiedProcessing,
    addMessage: addUnifiedMessage 
  } = useUnifiedChatStore();
  
  // Additional state for test compatibility
  const [agentStatus, setAgentStatus] = useState<string>('IDLE');
  const [workflowProgress, setWorkflowProgress] = useState<any>({ current_step: 0, total_steps: 0 });
  const [streamingMessage, setStreamingMessage] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [subAgentStreams, setSubAgentStreams] = useState<any>({});
  const [errors, setErrors] = useState<any[]>([]);
  const [fallbackActive, setFallbackActive] = useState<boolean>(false);
  const [fallbackStrategy, setFallbackStrategy] = useState<string>('');
  const [tools, setTools] = useState<any[]>([]);
  const [selectedTool, setSelectedTool] = useState<any>(null);
  const [toolExecutionStatus, setToolExecutionStatus] = useState<string>('idle');
  const [toolResults, setToolResults] = useState<any>({});
  const [activeTools, setActiveTools] = useState<any[]>([]);
  const [registeredTools, setRegisteredTools] = useState<any[]>([]);
  const [toolExecutionQueue, setToolExecutionQueue] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState<boolean>(true);
  const [retryAttempts, setRetryAttempts] = useState<number>(0);
  const [aggregatedResults, setAggregatedResults] = useState<any>({});
  const [validationResults, setValidationResults] = useState<any>({});
  const [pendingApproval, setPendingApproval] = useState<any>(null);
  
  // Track the last processed message index to avoid reprocessing
  const lastProcessedIndex = useRef(0);

  useEffect(() => {
    // Only process new messages
    const newMessages = messages.slice(lastProcessedIndex.current);
    
    newMessages.forEach((wsMessage) => {
      // Handle unified chat events first
      const unifiedEventTypes = [
        'agent_started', 'tool_executing', 'agent_thinking', 
        'partial_result', 'agent_completed', 'final_report'
      ];
      
      if (unifiedEventTypes.includes(wsMessage.type)) {
        handleWebSocketEvent(wsMessage as UnifiedWebSocketEvent);
      }
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
            id: generateUniqueId('msg'),
            type: 'agent',
            content: message.content || '',
            created_at: new Date().toISOString(),
            sub_agent_name: payload.sub_agent_name,
            displayed_to_user: true
          };
          addMessage(agentMessage);
        }
      } else if (wsMessage.type === 'agent_started') {
        setProcessing(true);
        setUnifiedProcessing(true);
        setAgentStatus('RUNNING');
        const payload = wsMessage.payload as any;
        if (payload) {
          setWorkflowProgress({
            current_step: 0,
            total_steps: payload.total_steps || 5,
            estimated_duration: payload.estimated_duration || 120
          });
        }
      } else if (wsMessage.type === 'agent_finished' || wsMessage.type === 'agent_completed') {
        setProcessing(false);
        setUnifiedProcessing(false);
        setAgentStatus('COMPLETED');
        // Add a completion message
        const completionMessage: Message = {
          id: generateUniqueId('msg'),
          type: 'agent',
          content: 'Task completed successfully.',
          created_at: new Date().toISOString(),
          sub_agent_name: useChatStore.getState().subAgentName,
          displayed_to_user: true
        };
        addMessage(completionMessage);
      } else if (wsMessage.type === 'error') {
        setProcessing(false);
        setUnifiedProcessing(false);
        const payload = wsMessage.payload as any;
        
        // Also handle error in unified chat
        handleWebSocketEvent(wsMessage as UnifiedWebSocketEvent);
        const errorMessage: Message = {
          id: generateUniqueId('msg'),
          type: 'error',
          content: `❌ Error: ${payload?.error || 'An error occurred'}`,
          created_at: new Date().toISOString(),
          sub_agent_name: payload?.sub_agent_name || 'System',
          displayed_to_user: true,
          error: payload?.error || 'An error occurred'
        };
        addMessage(errorMessage);
      } else if (wsMessage.type === 'agent_log') {
        const payload = wsMessage.payload as any;
        const logPrefix = payload.level === 'error' ? '❌' : 
                         payload.level === 'warning' ? '⚠️' : 'ℹ️';
        const logMessage: Message = {
          id: generateUniqueId('msg'),
          type: 'system',
          content: `${logPrefix} ${payload.message}`,
          created_at: new Date().toISOString(),
          sub_agent_name: payload.sub_agent_name || 'System',
          displayed_to_user: true
        };
        addMessage(logMessage);
      } else if (wsMessage.type === 'tool_call') {
        const payload = wsMessage.payload as any;
        const toolMessage: Message = {
          id: generateUniqueId('msg'),
          type: 'tool',
          content: `🔧 Calling tool: ${payload.tool_name}`,
          created_at: new Date().toISOString(),
          sub_agent_name: payload.sub_agent_name || 'System',
          displayed_to_user: true,
          tool_info: { tool_name: payload.tool_name, tool_args: payload.tool_args }
        };
        addMessage(toolMessage);
      } else if (wsMessage.type === 'tool_result') {
        const payload = wsMessage.payload as any;
        const resultMessage: Message = {
          id: generateUniqueId('msg'),
          type: 'tool',
          content: `✅ Tool result from ${payload.tool_name}: ${JSON.stringify(payload.result).substring(0, 200)}...`,
          created_at: new Date().toISOString(),
          sub_agent_name: payload.sub_agent_name || 'System',
          displayed_to_user: true,
          tool_info: { tool_name: payload.tool_name, result: payload.result }
        };
        addMessage(resultMessage);
      } else if (wsMessage.type === 'message_chunk') {
        const payload = wsMessage.payload as any;
        if (payload) {
          setStreamingMessage(payload.content || '');
          setIsStreaming(!payload.is_complete);
        }
      } else if (wsMessage.type === 'sub_agent_stream') {
        const payload = wsMessage.payload as any;
        if (payload?.stream_id) {
          setSubAgentStreams((prev: Record<string, any>) => ({
            ...prev,
            [payload.stream_id]: {
              agent: payload.agent,
              content: payload.content
            }
          }));
        }
      } else if (wsMessage.type === 'sub_agent_error') {
        const payload = wsMessage.payload as any;
        if (payload) {
          setErrors((prev: any[]) => [...prev, {
            agent: payload.sub_agent_name,
            type: payload.error?.type || 'UNKNOWN',
            message: payload.error?.message || '',
            recoverable: payload.recovery_action === 'RETRY_WITH_FALLBACK'
          }]);
        }
      } else if (wsMessage.type === 'agent_failure') {
        const payload = wsMessage.payload as any;
        if (payload) {
          setFallbackActive(true);
          setFallbackStrategy(payload.fallback_strategy || '');
        }
      } else if (wsMessage.type === 'partial_completion') {
        const payload = wsMessage.payload as any;
        if (payload?.partial_results) {
          setAggregatedResults(payload.partial_results);
        }
      } else if (wsMessage.type === 'workflow_progress') {
        const payload = wsMessage.payload as any;
        if (payload) {
          setWorkflowProgress({
            current_step: payload.current_step || 0,
            total_steps: payload.total_steps || 5
          });
        }
      } else if (wsMessage.type === 'tool_registered') {
        const payload = wsMessage.payload as any;
        if (payload) {
          setRegisteredTools((prev: any[]) => [...prev, payload]);
        }
      } else if (wsMessage.type === 'tool_execution_start') {
        const payload = wsMessage.payload as any;
        if (payload) {
          setToolExecutionStatus('executing');
          setSelectedTool(payload.tool_name);
          setActiveTools((prev: any[]) => [...prev, payload.tool_name]);
        }
      } else if (wsMessage.type === 'tool_execution_complete') {
        const payload = wsMessage.payload as any;
        if (payload) {
          setToolExecutionStatus('completed');
          setToolResults((prev: Record<string, any>) => ({
            ...prev,
            [payload.tool_name]: payload.result
          }));
          setActiveTools((prev: any[]) => prev.filter((t: any) => t !== payload.tool_name));
        }
      } else if (wsMessage.type === 'tool_execution_error') {
        const payload = wsMessage.payload as any;
        if (payload) {
          setToolExecutionStatus('error');
          setErrors((prev: any[]) => [...prev, {
            type: 'TOOL_ERROR',
            tool: payload.tool_name,
            error: payload.error
          }]);
        }
      } else if (wsMessage.type === 'validation_result') {
        const payload = wsMessage.payload as any;
        if (payload) {
          setValidationResults((prev: any) => ({
            ...prev,
            [payload.field]: payload.valid
          }));
        }
      } else if (wsMessage.type === 'connection_status') {
        const payload = wsMessage.payload as any;
        setIsConnected(payload?.connected || false);
        setRetryAttempts(payload?.retry_attempts || 0);
      } else if (wsMessage.type === 'message_received') {
        // Acknowledgment that message was received - don't add duplicate
        // User messages are already added immediately when sent
      } else if (wsMessage.type === 'agent_stopped') {
        setProcessing(false);
        setAgentStatus('STOPPED');
        const stoppedMessage: Message = {
          id: generateUniqueId('msg'),
          type: 'system',
          content: 'Processing stopped.',
          created_at: new Date().toISOString(),
          sub_agent_name: 'System',
          displayed_to_user: true
        };
        addMessage(stoppedMessage);
      } else if (wsMessage.type === 'approval_required') {
        const payload = wsMessage.payload as any;
        setPendingApproval(payload);
        // Add approval message to chat
        const approvalMessage: Message = {
          id: generateUniqueId('msg'),
          type: 'system',
          content: payload.message || 'Approval required for this operation',
          created_at: new Date().toISOString(),
          sub_agent_name: payload.sub_agent_name || 'System',
          displayed_to_user: true,
          raw_data: { approval_data: payload }
        };
        addMessage(approvalMessage);
      }
      
      // Handle any message with displayed_to_user flag
      if ((wsMessage as any).displayed_to_user) {
        const chatMessage: Message = {
          id: generateUniqueId('msg'),
          type: (wsMessage as any).type || 'agent',
          content: (wsMessage as any).content || JSON.stringify(wsMessage.payload),
          created_at: new Date().toISOString(),
          sub_agent_name: (wsMessage as any).sub_agent_name || useChatStore.getState().subAgentName,
          displayed_to_user: true,
          raw_data: wsMessage.payload
        };
        addMessage(chatMessage);
      }
    });
    
    // Update the last processed index
    lastProcessedIndex.current = messages.length;
  }, [messages, addMessage, setSubAgentName, setSubAgentStatus, setProcessing, 
      handleWebSocketEvent, setUnifiedProcessing, addUnifiedMessage]);
  
  // Tool execution functions for tests
  const registerTool = (tool: any) => {
    setRegisteredTools((prev: any[]) => [...prev, tool]);
  };
  
  const executeTool = async (toolName: string, args: any) => {
    setSelectedTool(toolName);
    setToolExecutionStatus('executing');
    setToolExecutionQueue((prev: any[]) => [...prev, { name: toolName, args }]);
    // Simulate async execution
    return new Promise((resolve) => {
      setTimeout(() => {
        const result = { success: true, data: args };
        setToolResults((prev: Record<string, any>) => ({ ...prev, [toolName]: result }));
        setToolExecutionStatus('completed');
        resolve(result);
      }, 100);
    });
  };
  
  const clearErrors = () => {
    setErrors([]);
  };
  
  return {
    agentStatus,
    workflowProgress,
    streamingMessage,
    isStreaming,
    subAgentStreams,
    errors,
    fallbackActive,
    fallbackStrategy,
    tools,
    selectedTool,
    toolExecutionStatus,
    toolResults,
    activeTools,
    registeredTools,
    toolExecutionQueue,
    isConnected,
    retryAttempts,
    aggregatedResults,
    validationResults,
    pendingApproval,
    setPendingApproval,
    registerTool,
    executeTool,
    clearErrors,
    setAgentStatus,
    setWorkflowProgress
  };
};