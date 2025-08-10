import React from 'react';
import { useWebSocketContext } from '@/providers/WebSocketProvider';
import { MessageItem } from './MessageItem';
import { Message } from '@/types/chat';

const ChatHistory: React.FC = () => {
  const ws = useWebSocketContext();

  if (!ws) {
    return <div>Loading...</div>;
  }

  // Transform WebSocket messages to Message type
  const transformedMessages: Message[] = ws.messages.map((msg, index) => {
    const payload = msg.payload as Record<string, unknown>;
    return {
      id: `msg-${index}`,
      type: msg.type,
      content: String(payload?.content || payload?.message || JSON.stringify(payload)),
      created_at: new Date().toISOString(),
      sender: msg.sender || undefined,
      payload: msg.payload,
      references: payload?.references,
      error: msg.type === 'error' ? String(payload?.error || payload?.message || '') : undefined,
      sub_agent_name: payload?.sub_agent_name,
      tool_info: payload?.tool_info,
      raw_data: payload?.raw_data,
    } as Message;
  });

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {transformedMessages.map((msg, index) => (
        <MessageItem 
          key={index} 
          message={msg} 
        />
      ))}
    </div>
  );
};

export default ChatHistory;