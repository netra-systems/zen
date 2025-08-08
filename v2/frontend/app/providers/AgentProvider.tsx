'use client';

import React, { createContext, useContext } from 'react';
import { useAgent } from '../hooks/useAgent';
import { UseAgentReturn } from '../types';

const AgentContext = createContext<UseAgentReturn | undefined>(undefined);

export const AgentProvider = ({ children }: { children: React.ReactNode }) => {
    const agent = useAgent();

    return (
        <AgentContext.Provider value={agent}>
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