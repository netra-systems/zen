import { useWebSocket } from '@/hooks/useWebSocket';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useThreadStore } from '@/store/threadStore';
import { useAuthStore } from '@/store/authStore';
import { Message } from '@/types/unified';
import { ThreadService } from '@/services/threadService';
import { generateUniqueId } from '@/lib/utils';
import { MESSAGE_INPUT_CONSTANTS } from '../constants';
import { logger } from '@/utils/debug-logger';

const { CHAR_LIMIT } = MESSAGE_INPUT_CONSTANTS;

export const useMessageSender = () => {
  const { sendMessage } = useWebSocket();
  const { setProcessing, addMessage } = useUnifiedChatStore();
  const { currentThreadId, setCurrentThread, addThread } = useThreadStore();
  const { isAuthenticated, isDeveloperOrHigher } = useAuthStore();
  
  const isAdmin = isDeveloperOrHigher();

  const createThread = async (title: string) => {
    try {
      const newThread = await ThreadService.createThread(title);
      addThread(newThread);
      setCurrentThread(newThread.id);
      return newThread.id;
    } catch (error) {
      logger.error('Failed to create thread:', error);
      throw error;
    }
  };

  const createUserMessage = (content: string): Message => {
    return {
      id: generateUniqueId('msg'),
      type: 'user',
      content,
      created_at: new Date().toISOString(),
      displayed_to_user: true
    };
  };

  const prepareThreadId = async (message: string) => {
    let threadId = currentThreadId;
    
    if (!threadId) {
      const title = message.substring(0, 50) + (message.length > 50 ? '...' : '');
      threadId = await createThread(title);
    }
    
    return threadId;
  };

  const sendWebSocketMessage = (text: string, threadId: string) => {
    sendMessage({ 
      type: 'user_message', 
      payload: { 
        text, 
        references: [],
        thread_id: threadId,
        admin_context: isAdmin && text.startsWith('/') ? true : undefined
      } 
    });
  };

  const handleSend = async (
    message: string, 
    isSending: boolean,
    onSendingChange: (sending: boolean) => void,
    onMessageHistory: (message: string) => void,
    onClear: () => void,
    onHideOverlays: () => void
  ) => {
    if (!isAuthenticated) {
      logger.error('User must be authenticated to send messages');
      return;
    }
    
    const trimmedMessage = message.trim();
    if (!trimmedMessage || isSending || trimmedMessage.length > CHAR_LIMIT) {
      return;
    }

    onSendingChange(true);
    onMessageHistory(trimmedMessage);
    
    try {
      const threadId = await prepareThreadId(trimmedMessage);
      const userMessage = createUserMessage(trimmedMessage);
      
      addMessage(userMessage);
      sendWebSocketMessage(trimmedMessage, threadId);
      setProcessing(true);
      
      onClear();
      onHideOverlays();
      
      setTimeout(() => onSendingChange(false), 100);
    } catch (error) {
      logger.error('Failed to send message:', error);
      onSendingChange(false);
    }
  };

  return {
    handleSend,
    isAuthenticated,
    isAdmin
  };
};