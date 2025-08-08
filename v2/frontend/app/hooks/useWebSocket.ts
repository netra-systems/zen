import { useContext, useEffect } from 'react';
import { WebSocketContext } from '../providers/WebSocketProvider';
import { useChatStore } from '../store';
import { WebSocketMessage } from '../types';

export const useWebSocket = () => {
  const webSocketContext = useContext(WebSocketContext);
  const { addMessage, setSubAgentName, setSubAgentStatus } = useChatStore();

  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      addMessage(message);

      if (message.type === 'sub_agent_update') {
        setSubAgentName(message.payload.sub_agent_name);
        if (message.payload.state.lifecycle) {
          setSubAgentStatus(message.payload.state.lifecycle);
        }
      }
    };

    webSocketContext?.registerMessageHandler(handleMessage);

    return () => {
      webSocketContext?.unregisterMessageHandler(handleMessage);
    };
  }, [webSocketContext, addMessage, setSubAgentName, setSubAgentStatus]);

  return webSocketContext;
};