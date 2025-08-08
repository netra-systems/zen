import { useState, useEffect, useCallback } from 'react';
import { agent } from '../services/agent/Agent';
import { AgentState, UseAgentReturn, Message, Reference } from '../types';

export function useAgent(): UseAgentReturn {
    const [state, setState] = useState<AgentState>({ messages: [], isThinking: false, error: null, toolArgBuffers: {} });

    useEffect(() => {
        agent.initialize();
        const unsubscribe = agent.subscribe((newState) => {
            setState(newState);
        });
        return () => {
            unsubscribe();
            agent.stop();
        };
    }, []);

    const startAgent = useCallback((message: string, references?: Reference[]) => {
        agent.start(message, references);
    }, []);

    const stopAgent = useCallback(() => {
        agent.stop();
    }, []);

    return { startAgent, stopAgent, messages: state.messages, showThinking: state.isThinking, error: state.error };
}