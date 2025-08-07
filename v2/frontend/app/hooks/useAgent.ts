import { useState, useEffect } from 'react';
import { agent } from '../services/agent/Agent';
import { Message } from '../types';

interface AgentState {
    messages: Message[];
    isThinking: boolean;
    error: Error | null;
}

export function useAgent() {
    const [state, setState] = useState<AgentState>({ messages: [], isThinking: false, error: null });

    useEffect(() => {
        agent.initialize();
        const unsubscribe = agent.subscribe(setState);
        return () => {
            unsubscribe();
        };
    }, []);

    const startAgent = (message: string) => {
        agent.start(message);
    };

    return { startAgent, messages: state.messages, showThinking: state.isThinking, error: state.error };
}