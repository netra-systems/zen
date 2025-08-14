import { messageService } from './messageService';
import { logger } from '@/lib/logger';

export const chatService = {
  // Wrap messageService methods for backward compatibility
  sendMessage: messageService.saveMessage.bind(messageService),
  getMessages: messageService.getThreadMessages.bind(messageService),
  saveMessage: messageService.saveMessage.bind(messageService),
  getThreadMessages: messageService.getThreadMessages.bind(messageService),
  
  // Additional chat-specific methods
  getChatHistory: async (threadId: string) => {
    return messageService.getThreadMessages(threadId);
  },
  
  clearChat: async (threadId: string) => {
    // Implementation would clear all messages in a thread
    logger.warn('clearChat method not implemented', {
      component: 'chatService',
      action: 'clear_chat_not_implemented',
      metadata: { threadId }
    });
    return { success: true };
  }
};