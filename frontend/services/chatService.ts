import { messageService } from './messageService';

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
    console.warn('clearChat not implemented');
    return { success: true };
  }
};