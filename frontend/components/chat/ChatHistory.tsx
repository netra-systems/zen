import React, { useMemo } from 'react';
import { useWebSocketContext } from '@/providers/WebSocketProvider';
import { MessageItem } from './MessageItem';
import { Message } from '@/types/registry';
import { generateUniqueId } from '@/lib/utils';

const ChatHistory: React.FC = React.memo(() => {
  const ws = useWebSocketContext();

  // Transform WebSocket messages to Message type (memoized for performance)
  const transformedMessages: Message[] = useMemo(() => {
    if (!ws) return [];
    
    return ws.messages.map((msg) => {
      const payload = msg.payload as Record<string, unknown>;
      return {
        id: generateUniqueId('msg'),
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
  }, [ws]);

  if (!ws) {
    return <div>Loading...</div>;
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {transformedMessages.map((msg) => (
        <MessageItem 
          key={msg.id} 
          message={msg} 
        />
      ))}
    </div>
  );
});

ChatHistory.displayName = 'ChatHistory';

export default ChatHistory;