
'use client';

import { createContext, useContext, useState } from 'react';
import { useAgent } from '../hooks/useAgent';
import { Message } from '../types/types';

interface AgentContextType {
    startAgent: (input: string) => void;
    messages: Message[];
    showThinking: boolean;
    error: Error | null;
}

const AgentContext = createContext<AgentContextType | undefined>(undefined);

export const AgentProvider = ({ children }: { children: React.ReactNode }) => {
    const { startAgent, messages, showThinking, error } = useAgent();

    return (
        <AgentContext.Provider value={{ startAgent, messages, showThinking, error }}>
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
