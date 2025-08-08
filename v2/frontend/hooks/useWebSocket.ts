import { useContext, useEffect } from 'react';
import { WebSocketContext } from '../providers/WebSocketProvider';
import { useChatStore } from '../store';

export const useWebSocket = () => {
  const webSocketContext = useContext(WebSocketContext);
  const { addMessage, setSubAgentName, setSubAgentStatus } = useChatStore();

  useEffect(() => {
    if (webSocketContext?.lastMessage) {
      addMessage(webSocketContext.lastMessage);

      if (webSocketContext.lastMessage.type === 'sub_agent_update') {
        setSubAgentName(webSocketContext.lastMessage.payload.sub_agent_name);
        if (webSocketContext.lastMessage.payload.state.lifecycle) {
          setSubAgentStatus(webSocketContext.lastMessage.payload.state.lifecycle);
        }
      }
    }
  }, [webSocketContext?.lastMessage, addMessage, setSubAgentName, setSubAgentStatus]);

  return webSocketContext;
};