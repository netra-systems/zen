import { messageService } from './messageService';

export const chatService = {
  // Wrap messageService methods for backward compatibility
  sendMessage: messageService.sendMessage.bind(messageService),
  getMessages: messageService.getMessages.bind(messageService),
  updateMessage: messageService.updateMessage.bind(messageService),
  deleteMessage: messageService.deleteMessage.bind(messageService),
  
  // Additional chat-specific methods
  getChatHistory: async (threadId: string) => {
    return messageService.getMessages(threadId);
  },
  
  clearChat: async (threadId: string) => {
    // Implementation would clear all messages in a thread
    console.warn('clearChat not implemented');
    return { success: true };
  }
};