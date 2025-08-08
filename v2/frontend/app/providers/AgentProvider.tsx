'use client';

import React, { createContext, useContext, useEffect } from 'react';
import { useAgent } from '../hooks/useAgent';
import useWebSocket from '../hooks/useWebSocket';
import { UseAgentReturn, WebSocketStatus } from '../types';
import { WEBSOCKET_URL } from '../config';

interface AgentContextValue extends UseAgentReturn {
    wsStatus: WebSocketStatus;
    sendWsMessage: (message: any) => void;
}

const AgentContext = createContext<AgentContextValue | undefined>(undefined);

export const AgentProvider = ({ children }: { children: React.ReactNode }) => {
    const agent = useAgent();
    const { status: wsStatus, lastJsonMessage, sendMessage: sendWsMessage } = useWebSocket(WEBSOCKET_URL);

    useEffect(() => {
        if (lastJsonMessage) {
            console.log('Received WebSocket message:', lastJsonMessage);
            // Here you would add logic to handle the message and update the agent state
        }
    }, [lastJsonMessage]);

    const contextValue = {
        ...agent,
        wsStatus,
        sendWsMessage,
    };

    return (
        <AgentContext.Provider value={contextValue}>
            {children}
        </AgentContext.Provider>
    );
};

export const useAgentContext = () => {
    const context = useContext(AgentContext);
    if (!context) {
        throw new Error('useAgentContext must be used within an AgentProvider');
    }
    return context;
};
