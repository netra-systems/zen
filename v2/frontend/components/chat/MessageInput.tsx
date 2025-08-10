import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useChatStore } from '@/store/chat';
import { useThreadStore } from '@/store/threadStore';
import { Send } from 'lucide-react';
import { Message } from '@/types/chat';
import { ThreadService } from '@/services/threadService';

export const MessageInput: React.FC = () => {
  const [message, setMessage] = useState('');
  const { sendMessage } = useWebSocket();
  const { setProcessing, isProcessing, addMessage } = useChatStore();
  const { currentThreadId, setCurrentThread, addThread } = useThreadStore();

  const handleSend = async () => {
    if (message.trim()) {
      let threadId = currentThreadId;
      
      // Create a new thread if none exists
      if (!threadId) {
        try {
          const newThread = await ThreadService.createThread(
            message.substring(0, 50) + (message.length > 50 ? '...' : '')
          );
          addThread(newThread);
          setCurrentThread(newThread.id);
          threadId = newThread.id;
        } catch (error) {
          console.error('Failed to create thread:', error);
          return;
        }
      }
      
      // Add user message to chat immediately
      const userMessage: Message = {
        id: `msg_${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
        displayed_to_user: true
      };
      addMessage(userMessage);
      
      // Send message via WebSocket with thread_id
      sendMessage({ 
        type: 'user_message', 
        payload: { 
          text: message, 
          references: [],
          thread_id: threadId 
        } 
      });
      setProcessing(true);
      setMessage('');
    }
  };

  return (
    <div className="flex items-center">
      <Input
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        placeholder={isProcessing ? 'Agent is thinking...' : 'Type your message...'}
        className="flex-grow rounded-full py-2 px-4 bg-gray-100 focus:bg-white focus:ring-2 focus:ring-blue-500 transition-all duration-300"
        disabled={isProcessing}
      />
      <Button onClick={handleSend} className="ml-4 rounded-full w-12 h-12 flex items-center justify-center bg-blue-500 hover:bg-blue-600 text-white" disabled={isProcessing} aria-label="Send">
        <Send className="w-6 h-6" />
      </Button>
    </div>
  );
};