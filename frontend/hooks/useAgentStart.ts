import { useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';

interface StartAgentOptions {
  userRequest: string;
  threadId?: string;
  context?: Record<string, any>;
  settings?: Record<string, any>;
}

/**
 * Hook for explicitly starting agent processing
 * Use this when you need to start an agent without a user message in the chat
 * (e.g., for optimization workflows, background tasks, etc.)
 */
export const useAgentStart = () => {
  const { sendMessage, status } = useWebSocket();
  const { setProcessing, setActiveThread } = useUnifiedChatStore();
  const { currentThreadId } = useThreadStore();

  const startAgent = useCallback((options: StartAgentOptions) => {
    if (status !== 'OPEN') {
      console.error('WebSocket is not connected');
      return false;
    }

    const { userRequest, threadId, context, settings } = options;
    const actualThreadId = threadId || currentThreadId;

    // Set the active thread if provided
    if (actualThreadId) {
      setActiveThread(actualThreadId);
    }

    // Send start_agent message to backend
    sendMessage({
      type: 'start_agent',
      payload: {
        user_request: userRequest,
        thread_id: actualThreadId || null,
        context: context || {},
        settings: settings || {}
      }
    });

    // Set processing state
    setProcessing(true);

    return true;
  }, [status, sendMessage, setProcessing, setActiveThread, currentThreadId]);

  const startOptimizationAgent = useCallback((
    prompt: string,
    optimizationSettings?: Record<string, any>
  ) => {
    return startAgent({
      userRequest: prompt,
      context: { type: 'optimization' },
      settings: optimizationSettings || { 
        mode: 'comprehensive',
        include_recommendations: true 
      }
    });
  }, [startAgent]);

  const startAnalysisAgent = useCallback((
    prompt: string,
    analysisContext?: Record<string, any>
  ) => {
    return startAgent({
      userRequest: prompt,
      context: { 
        type: 'analysis',
        ...analysisContext 
      }
    });
  }, [startAgent]);

  return {
    startAgent,
    startOptimizationAgent,
    startAnalysisAgent,
    isConnected: status === 'OPEN'
  };
};