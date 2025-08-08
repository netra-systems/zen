'use client';

import React, { createContext, useContext, useEffect } from 'react';
import { useAgent } from '../hooks/useAgent';
import { useWebSocketStore } from '@/store/websocket';
import { UseAgentReturn, WebSocketStatus } from '../types';

interface AgentContextValue extends UseAgentReturn {
    wsStatus: WebSocketStatus;
    sendWsMessage: (message: unknown) => void;
}

const AgentContext = createContext<AgentContextValue | undefined>(undefined);

export const AgentProvider = ({ children }: { children: React.ReactNode }) => {
    const agent = useAgent();
    const { status: wsStatus, lastJsonMessage, sendMessage: sendWsMessage } = useWebSocketStore();

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