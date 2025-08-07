import { useState, useEffect } from 'react';
import { agent } from '../services/agent/Agent';
import { AgentState, Message } from '../types';



export function useAgent() {
    const [state, setState] = useState<AgentState>({ messages: [], isThinking: false, error: null });

    useEffect(() => {
        agent.initialize();
        const unsubscribe = agent.subscribe((newState) => {
            setState({
                messages: newState.messages,
                isThinking: newState.isThinking,
                error: newState.error,
            });
        });
        return () => {
            unsubscribe();
        };
    }, []);

    const startAgent = (message: string) => {
        agent.start(message);
    };

    return { startAgent, messages: state.messages, showThinking: state.isThinking, error: state.error };
}