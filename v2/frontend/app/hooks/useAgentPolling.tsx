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

    useEffect(() => {
        const wsUrl = `ws://localhost:8000/ws/dev/test-client`;
        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = () => {
            console.log('WebSocket connected for testing');
            ws.current?.send('test message');
        };

        ws.current.onmessage = (event) => {
            console.log('WebSocket test message received:', event.data);
        };

        ws.current.onerror = (error) => {
            console.error('WebSocket test error:', error);
        };

        ws.current.onclose = () => {
            console.log('WebSocket test connection closed');
        };

        return () => {
            ws.current?.close();
        };
    }, []);

    return { isLoading, error, messages, addMessage, startPolling, setIsLoading, setError };
};