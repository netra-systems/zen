import React, { useEffect } from 'react';
import { useWebSocket } from '@/contexts/WebSocketContext';
import { useChat } from '@/contexts/ChatContext';
import { ChatHeader } from './ChatHeader';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';

export const ChatWindow = () => {
  const { lastMessage } = useWebSocket();
  const { dispatch } = useChat();

  useEffect(() => {
    if (lastMessage) {
      // Here you would add logic to dispatch different actions based on the message type
      // For now, we'll just add every message to the chat
      if(lastMessage.type !== 'pong') {
        dispatch({ type: 'ADD_MESSAGE', payload: lastMessage });
      }
    }
  }, [lastMessage, dispatch]);

  return (
    <div className="flex flex-col h-full">
      <ChatHeader />
      <MessageList />
      <MessageInput />
    </div>
  );
};