import React, { useState, useEffect } from 'react';
import { useWebSocket } from '@/contexts/WebSocketContext';
import { WebSocketMessage, UserMessage, StopAgent } from '@/app/types';
import Header from './Header';
import MessageList from './MessageList';
import MessageInput from './MessageInput';

const Chat: React.FC = () => {
  const { messages, sendMessage } = useWebSocket();
  const [subAgentName, setSubAgentName] = useState('Triage');
  const [agentStatus, setAgentStatus] = useState('Idle');
  const [toolInUse, setToolInUse] = useState('None');

  const handleSendMessage = (message: string) => {
    const userMessage: WebSocketMessage = {
      type: 'user_message',
      payload: { text: message } as UserMessage,
    };
    sendMessage(userMessage);
  };

  const handleStopAgent = () => {
    const stopMessage: WebSocketMessage = {
      type: 'stop_agent',
      payload: { run_id: 'TODO' } as StopAgent, // TODO: Get the run_id from the agent
    };
    sendMessage(stopMessage);
  };

  return (
    <div className="flex flex-col h-full">
      <Header subAgentName={subAgentName} agentStatus={agentStatus} toolInUse={toolInUse} />
      <MessageList messages={messages} />
      <MessageInput onSendMessage={handleSendMessage} onStopAgent={handleStopAgent} />
    </div>
  );
};

export default Chat;