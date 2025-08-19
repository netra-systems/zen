import { useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { ThreadService } from '@/services/threadService';
import { ThreadRenameService } from '@/services/threadRenameService';
import { generateUniqueId } from '@/lib/utils';
import { ChatMessage, MessageSendingParams, MESSAGE_INPUT_CONSTANTS } from '../types';
import { optimisticMessageManager } from '@/services/optimistic-updates';
import { logger } from '@/utils/debug-logger';

const { CHAR_LIMIT } = MESSAGE_INPUT_CONSTANTS;

export const useMessageSending = () => {
  const [isSending, setIsSending] = useState(false);
  const { sendMessage } = useWebSocket();
  const { 
    addMessage, 
    setActiveThread, 
    setProcessing, 
    addOptimisticMessage,
    updateOptimisticMessage,
    messages 
  } = useUnifiedChatStore();
  const { setCurrentThread, addThread } = useThreadStore();

  const validateMessage = (params: MessageSendingParams): boolean => {
    const { message, isAuthenticated } = params;
    const trimmed = message.trim();
    return isAuthenticated && !!trimmed && !isSending && trimmed.length <= CHAR_LIMIT;
  };

  const createThreadTitle = (message: string): string => {
    const maxLength = 50;
    return message.length > maxLength 
      ? message.substring(0, maxLength) + '...' 
      : message;
  };

  const createNewThread = async (message: string): Promise<string> => {
    const title = createThreadTitle(message);
    const newThread = await ThreadService.createThread(title);
    addThread(newThread);
    setCurrentThread(newThread.id);
    setActiveThread(newThread.id);
    return newThread.id;
  };

  const getOrCreateThreadId = async (
    activeThreadId: string | null,
    currentThreadId: string | null,
    message: string
  ): Promise<string> => {
    const threadId = activeThreadId || currentThreadId;
    return threadId || await createNewThread(message);
  };

  const createUserMessage = (message: string): ChatMessage => {
    return {
      id: generateUniqueId('msg'),
      role: 'user' as const,
      content: message,
      timestamp: Date.now()
    };
  };

  const sendWebSocketMessage = (message: string, threadId: string): void => {
    // For the first message in a thread or new conversation, use start_agent
    // For subsequent messages, use user_message
    // This ensures proper agent initialization and context setup
    
    // Check if this is the first message (new thread or no messages in current thread)
    const isFirstMessage = !threadId || checkIfFirstMessage(threadId);
    
    if (isFirstMessage) {
      // Use start_agent for initial message - properly initializes agent context
      sendMessage({ 
        type: 'start_agent', 
        payload: { 
          user_request: message,
          thread_id: threadId || null,
          context: {},
          settings: {}
        } 
      });
    } else {
      // Use user_message for subsequent messages in an existing conversation
      sendMessage({ 
        type: 'user_message', 
        payload: { 
          content: message, 
          references: [],
          thread_id: threadId 
        } 
      });
    }
  };

  const handleThreadRename = async (threadId: string, message: string): Promise<void> => {
    const thread = await ThreadService.getThread(threadId);
    const shouldRename = thread && (!thread.metadata?.renamed || thread.metadata?.title === 'New Chat');
    if (shouldRename) {
      ThreadRenameService.autoRenameThread(threadId, message);
    }
  };

  const handleSend = async (params: MessageSendingParams): Promise<void> => {
    if (!validateMessage(params)) return;
    
    const trimmedMessage = params.message.trim();
    setIsSending(true);
    
    try {
      const threadId = await getOrCreateThreadId(
        params.activeThreadId, 
        params.currentThreadId, 
        trimmedMessage
      );
      
      await handleOptimisticSend(trimmedMessage, threadId);
      await handleThreadRename(threadId, trimmedMessage);
      setProcessing(true);
    } catch (error) {
      logger.error('Failed to send message:', error);
      await handleSendFailure(error);
    } finally {
      setIsSending(false);
    }
  };

  // ========================================================================
  // Optimistic Update Helpers (8-line functions)
  // ========================================================================

  const handleOptimisticSend = async (message: string, threadId: string): Promise<void> => {
    const optimisticUser = optimisticMessageManager.addOptimisticUserMessage(message, threadId);
    const optimisticAi = optimisticMessageManager.addOptimisticAiMessage(threadId);
    
    addOptimisticMessage(optimisticUser);
    addOptimisticMessage(optimisticAi);
    sendWebSocketMessage(message, threadId);
  };

  const handleSendFailure = async (error: unknown): Promise<void> => {
    const failedMessages = optimisticMessageManager.getFailedMessages();
    
    failedMessages.forEach(msg => {
      updateOptimisticMessage(msg.localId, { status: 'failed', retry: createRetryHandler(msg) });
    });
  };

  const createRetryHandler = (message: any) => async (): Promise<void> => {
    try {
      await optimisticMessageManager.retryMessage(message.localId);
      updateOptimisticMessage(message.localId, { status: 'pending' });
    } catch (retryError) {
      logger.error('Retry failed:', retryError);
      updateOptimisticMessage(message.localId, { status: 'failed' });
    }
  };

  return {
    isSending,
    handleSend,
  };
};