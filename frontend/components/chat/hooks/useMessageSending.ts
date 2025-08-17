import { useState } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { ThreadService } from '@/services/threadService';
import { ThreadRenameService } from '@/services/threadRenameService';
import { generateUniqueId } from '@/lib/utils';
import { ChatMessage, MessageSendingParams, MESSAGE_INPUT_CONSTANTS } from '../types';

const { CHAR_LIMIT } = MESSAGE_INPUT_CONSTANTS;

export const useMessageSending = () => {
  const [isSending, setIsSending] = useState(false);
  const { sendMessage } = useWebSocket();
  const { addMessage, setActiveThread, setProcessing } = useUnifiedChatStore();
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
    sendMessage({ 
      type: 'user_message', 
      payload: { 
        content: message, 
        references: [],
        thread_id: threadId 
      } 
    });
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
      
      const userMessage = createUserMessage(trimmedMessage);
      addMessage(userMessage);
      
      sendWebSocketMessage(trimmedMessage, threadId);
      await handleThreadRename(threadId, trimmedMessage);
      
      setProcessing(true);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsSending(false);
    }
  };

  return {
    isSending,
    handleSend,
  };
};