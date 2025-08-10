'use client';

import { useEffect, useRef, useState } from 'react';
import { useWebSocket } from './useWebSocket';
import { useChatStore } from '@/store/chat';
import { Message } from '@/types/chat';

// Counter to ensure unique message IDs
let messageIdCounter = 0;

const generateMessageId = () => {
  return `msg_${Date.now()}_${++messageIdCounter}`;
};

interface AgentMetrics {
  currentAgent: string | null;
  previousAgent: string | null;
  agentStartTime: number;
  totalStartTime: number;
  stepCount: number;
  agentTimings: Map<string, number>;
  toolCallCount: Map<string, number>;
}

export const useEnhancedChatWebSocket = () => {
  const { messages } = useWebSocket();
  const { 
    addMessage, 
    updateMessage,
    setSubAgentName, 
    setSubAgentStatus, 
    setProcessing 
  } = useChatStore();
  
  // Track the last processed message index to avoid reprocessing
  const lastProcessedIndex = useRef(0);
  
  // Track agent metrics and timing
  const [metrics, setMetrics] = useState<AgentMetrics>({
    currentAgent: null,
    previousAgent: null,
    agentStartTime: Date.now(),
    totalStartTime: Date.now(),
    stepCount: 0,
    agentTimings: new Map(),
    toolCallCount: new Map()
  });

  // Track final report data
  const [finalReportData, setFinalReportData] = useState<any>(null);

  useEffect(() => {
    // Only process new messages
    const newMessages = messages.slice(lastProcessedIndex.current);
    
    newMessages.forEach((wsMessage) => {
      const now = Date.now();
      
      // Handle different message types
      if (wsMessage.type === 'sub_agent_update') {
        const payload = wsMessage.payload as any;
        
        // Detect agent transitions
        const newAgentName = payload?.sub_agent_name;
        if (newAgentName && newAgentName !== metrics.currentAgent) {
          // Record timing for previous agent
          if (metrics.currentAgent) {
            const duration = now - metrics.agentStartTime;
            metrics.agentTimings.set(
              metrics.currentAgent, 
              (metrics.agentTimings.get(metrics.currentAgent) || 0) + duration
            );
            
            // Add transition message
            const transitionMessage: Message & any = {
              id: generateMessageId(),
              type: 'system',
              content: `Transitioning from ${metrics.currentAgent} to ${newAgentName}`,
              created_at: new Date().toISOString(),
              sub_agent_name: 'System',
              displayed_to_user: true,
              agent_transition: {
                from: metrics.currentAgent,
                to: newAgentName,
                timestamp: new Date().toISOString()
              }
            };
            addMessage(transitionMessage);
          }
          
          // Update metrics
          setMetrics(prev => ({
            ...prev,
            previousAgent: prev.currentAgent,
            currentAgent: newAgentName,
            agentStartTime: now,
            stepCount: prev.stepCount + 1
          }));
          
          try {
            setSubAgentName(newAgentName);
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
          
          // Check for final report data
          if (payload.state.data_result || payload.state.optimizations_result || 
              payload.state.action_plan_result || payload.state.final_report) {
            setFinalReportData({
              data_result: payload.state.data_result,
              optimizations_result: payload.state.optimizations_result,
              action_plan_result: payload.state.action_plan_result,
              report_result: payload.state.report_result,
              final_report: payload.state.final_report,
              execution_metrics: {
                total_duration: now - metrics.totalStartTime,
                agent_timings: Array.from(metrics.agentTimings.entries()).map(([name, duration]) => ({
                  agent_name: name,
                  duration,
                  start_time: new Date(metrics.totalStartTime).toISOString(),
                  end_time: new Date(now).toISOString()
                })),
                tool_calls: Array.from(metrics.toolCallCount.entries()).map(([name, count]) => ({
                  tool_name: name,
                  count,
                  avg_duration: 0 // Would need to track individual tool durations for this
                }))
              }
            });
          }
        }
        
        // Show message updates from sub-agents with timing
        if (payload?.state?.messages && payload.state.messages.length > 0) {
          const message = payload.state.messages[0];
          const agentMessage: Message & any = {
            id: generateMessageId(),
            type: 'agent',
            content: message.content || '',
            created_at: new Date().toISOString(),
            sub_agent_name: payload.sub_agent_name,
            displayed_to_user: true,
            step_timing: {
              start: new Date().toISOString(),
              end: null,
              duration: null
            },
            step_number: metrics.stepCount,
            total_steps: null // We don't know total steps ahead of time
          };
          addMessage(agentMessage);
        }
      } else if (wsMessage.type === 'agent_started') {
        setProcessing(true);
        setMetrics(prev => ({
          ...prev,
          totalStartTime: now,
          stepCount: 0,
          agentTimings: new Map(),
          toolCallCount: new Map()
        }));
      } else if (wsMessage.type === 'agent_finished' || wsMessage.type === 'agent_completed') {
        setProcessing(false);
        
        // Record final timing for current agent
        if (metrics.currentAgent) {
          const duration = now - metrics.agentStartTime;
          metrics.agentTimings.set(
            metrics.currentAgent, 
            (metrics.agentTimings.get(metrics.currentAgent) || 0) + duration
          );
        }
        
        // Add a completion message with final metrics
        const completionMessage: Message & any = {
          id: generateMessageId(),
          type: 'agent',
          content: 'Task completed successfully. View the detailed report for insights.',
          created_at: new Date().toISOString(),
          sub_agent_name: useChatStore.getState().subAgentName,
          displayed_to_user: true,
          step_timing: {
            start: new Date(metrics.totalStartTime).toISOString(),
            end: new Date().toISOString(),
            duration: now - metrics.totalStartTime
          }
        };
        addMessage(completionMessage);
      } else if (wsMessage.type === 'error') {
        setProcessing(false);
        const payload = wsMessage.payload as any;
        const errorMessage: Message & any = {
          id: generateMessageId(),
          type: 'error',
          content: `Error: ${payload?.error || 'An error occurred'}`,
          created_at: new Date().toISOString(),
          sub_agent_name: payload?.sub_agent_name || 'System',
          displayed_to_user: true,
          error: payload?.error || 'An error occurred',
          step_timing: {
            start: new Date().toISOString(),
            end: new Date().toISOString(),
            duration: 0
          }
        };
        addMessage(errorMessage);
      } else if (wsMessage.type === 'agent_log') {
        const payload = wsMessage.payload as any;
        const logMessage: Message & any = {
          id: generateMessageId(),
          type: 'system',
          content: payload.message,
          created_at: new Date().toISOString(),
          sub_agent_name: payload.sub_agent_name || 'System',
          displayed_to_user: true
        };
        addMessage(logMessage);
      } else if (wsMessage.type === 'tool_call') {
        const payload = wsMessage.payload as any;
        const toolName = payload.tool_name || 'Unknown';
        
        // Track tool call count
        setMetrics(prev => {
          const newCount = new Map(prev.toolCallCount);
          newCount.set(toolName, (newCount.get(toolName) || 0) + 1);
          return { ...prev, toolCallCount: newCount };
        });
        
        const toolMessage: Message & any = {
          id: generateMessageId(),
          type: 'tool',
          content: `Executing tool: ${toolName}`,
          created_at: new Date().toISOString(),
          sub_agent_name: payload.sub_agent_name || 'System',
          displayed_to_user: true,
          tool_info: { tool_name: toolName, tool_args: payload.tool_args },
          step_timing: {
            start: new Date().toISOString(),
            end: null,
            duration: null
          }
        };
        const msgId = toolMessage.id;
        addMessage(toolMessage);
        
        // Store the message ID to update it when we get the result
        (window as any).__pendingToolCalls = (window as any).__pendingToolCalls || {};
        (window as any).__pendingToolCalls[toolName] = msgId;
      } else if (wsMessage.type === 'tool_result') {
        const payload = wsMessage.payload as any;
        const toolName = payload.tool_name || 'Unknown';
        
        // Update the original tool call message with timing
        const pendingMsgId = (window as any).__pendingToolCalls?.[toolName];
        if (pendingMsgId) {
          updateMessage(pendingMsgId, {
            step_timing: {
              start: new Date().toISOString(),
              end: new Date().toISOString(),
              duration: 100 // Would need to track actual duration
            }
          });
          delete (window as any).__pendingToolCalls[toolName];
        }
        
        const resultMessage: Message & any = {
          id: generateMessageId(),
          type: 'tool',
          content: `Tool result from ${toolName}: ${JSON.stringify(payload.result).substring(0, 200)}...`,
          created_at: new Date().toISOString(),
          sub_agent_name: payload.sub_agent_name || 'System',
          displayed_to_user: true,
          tool_info: { tool_name: toolName, result: payload.result }
        };
        addMessage(resultMessage);
      } else if (wsMessage.type === 'message_received') {
        // Acknowledgment that message was received - don't add duplicate
      } else if (wsMessage.type === 'agent_stopped') {
        setProcessing(false);
        const stoppedMessage: Message = {
          id: generateMessageId(),
          type: 'system',
          content: 'Processing stopped.',
          created_at: new Date().toISOString(),
          sub_agent_name: 'System',
          displayed_to_user: true
        };
        addMessage(stoppedMessage);
      }
      
      // Handle any message with displayed_to_user flag
      if ((wsMessage as any).displayed_to_user && !['tool_call', 'tool_result', 'sub_agent_update'].includes(wsMessage.type)) {
        const chatMessage: Message = {
          id: generateMessageId(),
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
  }, [messages, addMessage, updateMessage, setSubAgentName, setSubAgentStatus, setProcessing, metrics]);

  return {
    metrics,
    finalReportData,
    currentAgent: metrics.currentAgent,
    totalDuration: Date.now() - metrics.totalStartTime,
    stepCount: metrics.stepCount
  };
};