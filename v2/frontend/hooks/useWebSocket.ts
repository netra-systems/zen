import { useContext, useEffect } from 'react';
import { WebSocketContext } from '../contexts/WebSocketContext';
import { useChatStore } from '../store';
import { WebSocketMessage } from '@/types/chat';

export const useWebSocket = () => {
  const webSocketContext = useContext(WebSocketContext);
  const { addMessage, setSubAgentName, setSubAgentStatus, setProcessing } = useChatStore();

  useEffect(() => {
    if (webSocketContext?.lastMessage) {
      const message: WebSocketMessage = JSON.parse(webSocketContext.lastMessage.data);

      if (message.type === 'message') {
        addMessage(message.payload);
      } else if (message.type === 'sub_agent_update') {
        setSubAgentName(message.payload.sub_agent_name);
        if (message.payload.state.lifecycle) {
          setSubAgentStatus(message.payload.state.lifecycle);
          if (['completed', 'failed', 'shutdown'].includes(message.payload.state.lifecycle)) {
            setProcessing(false);
          }
        }
      } else if (message.type === 'agent_started') {
        setProcessing(true);
      }
    }
  }, [webSocketContext?.lastMessage, addMessage, setSubAgentName, setSubAgentStatus, setProcessing]);

  if (!webSocketContext) {
    throw new Error("useWebSocket must be used within a WebSocketProvider");
  }

  return { ...webSocketContext };
};
