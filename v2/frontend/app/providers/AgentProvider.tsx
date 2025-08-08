'use client';

import React, { createContext, useContext, useEffect, useCallback } from 'react';
import { useAgent } from '../hooks/useAgent';
import { useWebSocket } from '@/app/hooks/useWebSocket';
import { UseAgentReturn, WebSocketStatus } from '../types';
import { agent } from '@/app/services/agent/Agent';

interface AgentContextValue extends UseAgentReturn {
    wsStatus: WebSocketStatus;
    sendWsMessage: (message: unknown) => void;
}

const AgentContext = createContext<AgentContextValue | undefined>(undefined);

export const AgentProvider = ({ children }: { children: React.ReactNode }) => {
    const agentState = useAgent();
    const { status: wsStatus, lastJsonMessage, sendMessage: sendWsMessage, connect } = useWebSocket();

    useEffect(() => {
        // For development, auto-connect with a dummy token.
        // In a real application, you would get the token from your auth context.
        connect('dummy-token');
    }, [connect]);

    useEffect(() => {
        if (lastJsonMessage) {
            agent.handleWebSocketMessage(lastJsonMessage);
        }
    }, [lastJsonMessage]);

    const startAgent = useCallback((message: string) => {
        agent.start(message, sendWsMessage);
    }, [sendWsMessage]);

    const stopAgent = useCallback(() => {
        agent.stop(sendWsMessage);
    }, [sendWsMessage]);

    const contextValue = {
        ...agentState,
        wsStatus,
        sendWsMessage,
        startAgent,
        stopAgent,
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