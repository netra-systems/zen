import { useState, useEffect, useRef, useCallback } from 'react';
import { apiService, AgentRun, AgentEvent } from '../api';
import React from 'react';

interface Message {
    role: 'user' | 'agent';
    content: React.ReactNode;
}

export const useAgentPolling = (token: string | null) => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const ws = useRef<WebSocket | null>(null);

    const addMessage = (role: 'user' | 'agent', content: React.ReactNode) => {
        setMessages(prev => [...prev, { role, content }]);
    };

    const startPolling = (runId: string) => {
        if (ws.current) {
            ws.current.close();
        }

        const wsUrl = `ws://localhost:8000/ws/${runId}`;
        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = () => {
            console.log('WebSocket connected');
            setIsLoading(true);
        };

        ws.current.onmessage = (event) => {
            const message = JSON.parse(event.data);
            addMessage('agent', <pre>{JSON.stringify(message, null, 2)}</pre>);
        };

        ws.current.onerror = (error) => {
            console.error('WebSocket error:', error);
            setError(new Error('WebSocket connection failed.'));
            setIsLoading(false);
        };

        ws.current.onclose = () => {
            console.log('WebSocket disconnected');
            setIsLoading(false);
        };
    };

    return { isLoading, error, messages, addMessage, startPolling, setIsLoading, setError };
};