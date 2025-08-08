import React, { createContext, useContext, useState } from 'react';

const AgentContext = createContext(null);

export const useAgentContext = () => useContext(AgentContext);

export const AgentProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const [showThinking, setShowThinking] = useState(false);
  const [error, setError] = useState(null);

  const sendWsMessage = (message) => {
    // TODO: Implement WebSocket message sending
  };

  const value = {
    messages,
    showThinking,
    error,
    sendWsMessage,
  };

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
};
