/**
 * Event handlers for ChatSidebar component
 * All functions are ≤8 lines for compliance with architecture requirements
 */

import { ThreadService } from '@/services/threadService';
import { useUnifiedChatStore } from '@/store/unified-chat';

interface WebSocketMessage {
  type: string;
  payload: any;
}

interface WebSocketSender {
  sendMessage: (message: WebSocketMessage) => void;
}

const clearChatState = () => {
  const { clearMessages, resetLayers } = useUnifiedChatStore.getState();
  clearMessages?.();
  resetLayers?.();
};

const setActiveThreadInStore = (threadId: string) => {
  const { setActiveThread } = useUnifiedChatStore.getState();
  setActiveThread?.(threadId);
};

const dispatchWebSocketEvent = (eventType: string, threadId: string | null) => {
  const event = new CustomEvent(eventType, { detail: { threadId } });
  window.dispatchEvent(event);
};

const disconnectFromCurrentThread = (activeThreadId: string | null) => {
  dispatchWebSocketEvent('disconnectWebSocket', activeThreadId);
};

const connectToNewThread = (threadId: string) => {
  dispatchWebSocketEvent('connectWebSocket', threadId);
};

const sendThreadSwitchMessage = (sender: WebSocketSender, threadId: string) => {
  sender.sendMessage({
    type: 'switch_thread',
    payload: { thread_id: threadId }
  });
};

const setThreadLoadingState = (loading: boolean) => {
  const { setThreadLoading } = useUnifiedChatStore.getState();
  setThreadLoading(loading);
};

const convertThreadMessages = (response: any) => {
  return response.messages.map((msg: any) => ({
    id: msg.id,
    role: msg.role as 'user' | 'assistant' | 'system',
    content: msg.content,
    timestamp: msg.created_at * 1000,
    threadId: response.thread_id,
    metadata: msg.metadata ? { ...msg.metadata } : undefined
  }));
};

const loadMessagesIntoStore = (convertedMessages: any[]) => {
  const { loadMessages } = useUnifiedChatStore.getState();
  loadMessages(convertedMessages);
};

export const createNewChatHandler = (
  setIsCreatingThread: (creating: boolean) => void,
  loadThreads: () => Promise<void>
) => {
  return async () => {
    setIsCreatingThread(true);
    try {
      const newThread = await ThreadService.createThread();
      clearChatState();
      setActiveThreadInStore(newThread.id);
      await loadThreads();
    } catch (error) {
      console.error('Failed to create thread:', error);
    } finally {
      setIsCreatingThread(false);
    }
  };
};

export const createThreadClickHandler = (
  activeThreadId: string | null,
  isProcessing: boolean,
  webSocketSender: WebSocketSender
) => {
  return async (threadId: string) => {
    if (threadId === activeThreadId || isProcessing) return;
    
    try {
      clearChatState();
      disconnectFromCurrentThread(activeThreadId);
      setActiveThreadInStore(threadId);
      sendThreadSwitchMessage(webSocketSender, threadId);
      setThreadLoadingState(true);
      
      const response = await ThreadService.getThreadMessages(threadId);
      const convertedMessages = convertThreadMessages(response);
      loadMessagesIntoStore(convertedMessages);
      
      connectToNewThread(threadId);
      console.log('Switched to thread:', threadId, 'with', convertedMessages.length, 'messages');
    } catch (error) {
      console.error('Failed to switch thread:', error);
      setThreadLoadingState(false);
    }
  };
};