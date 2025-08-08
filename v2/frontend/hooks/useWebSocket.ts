import { useContext, useEffect } from 'react';
import { WebSocketContext } from '../contexts/WebSocketContext';
import { useChatStore } from '../store';

export const useWebSocket = () => {
  const webSocketContext = useContext(WebSocketContext);
  const { addMessage, setSubAgentName, setSubAgentStatus, subAgentName, subAgentStatus } = useChatStore();

  useEffect(() => {
    if (webSocketContext?.lastMessage) {
      const message = JSON.parse(webSocketContext.lastMessage.data);
      addMessage(message);

      if (message.type === 'sub_agent_update') {
        setSubAgentName(message.payload.sub_agent_name);
        if (message.payload.state.lifecycle) {
          setSubAgentStatus(message.payload.state.lifecycle);
        }
      }
    }
  }, [webSocketContext?.lastMessage, addMessage, setSubAgentName, setSubAgentStatus]);

  if (!webSocketContext) {
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  }

  return { ...webSocketContext, subAgentName, subAgentStatus };
};