import React from 'react';
import { useChat } from '@/contexts/ChatContext';
import { useWebSocket } from '@/contexts/WebSocketContext';

export const ChatHeader = () => {
  const { state } = useChat();
  const { subAgentStatus } = state;
  const { sendMessage } = useWebSocket();

  const handleStop = () => {
    // This is a placeholder for the run_id. In a real application, you would get this from the state.
    const run_id = '123'; 
    sendMessage({ type: 'stop_agent', payload: { run_id } });
  };

  const isLoading = subAgentStatus?.status === 'running';

  return (
    <div className="p-4 bg-gray-200 flex justify-between items-center">
      <div>
        {subAgentStatus ? (
          <div>
            <h2 className="font-bold">{subAgentStatus.agent_name}</h2>
            <div className="flex items-center">
              <p>Status: {subAgentStatus.status}</p>
              {isLoading && <div className="ml-2 w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>}
            </div>
            <p>Tools: {subAgentStatus.tools.join(', ')}</p>
          </div>
        ) : (
          <h2 className="font-bold">Chat</h2>
        )}
      </div>
      <button onClick={handleStop} className="p-2 bg-red-500 text-white rounded">
        Stop
      </button>
    </div>
  );
};