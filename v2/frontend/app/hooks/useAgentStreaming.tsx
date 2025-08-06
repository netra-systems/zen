import React, { useState, useCallback, useEffect, useRef } from 'react';
import { apiService } from '../api';
import { getUserId } from '../lib/user';

interface Message {
    role: 'user' | 'agent';
    content: React.ReactNode;
    isThinking?: boolean;
    artifacts?: any[];
}

const MAX_RETRIES = 5;
const INITIAL_RETRY_DELAY = 1000; // 1 second

export const useAgentStreaming = (getToken: () => Promise<string | null>) => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const ws = useRef<WebSocket | null>(null);
    const retryCount = useRef(0);
    const currentArtifacts = useRef<any[]>([]);

    const connect = useCallback((clientId: string) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) return;

        const wsUrl = `ws://localhost:8000/ws/dev/${clientId}`;
        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = () => {
            console.log('WebSocket connected');
            setIsLoading(true);
            retryCount.current = 0;
        };

        ws.current.onmessage = (event) => {
            const message = event.data;
            if (message.includes('FINISH')) {
                ws.current?.close();
                setIsLoading(false);
                return;
            }

            try {
                const parsedMessage = JSON.parse(message);

                if (parsedMessage.event && parsedMessage.data) {
                    currentArtifacts.current.push(parsedMessage);
                } else if (parsedMessage.chunk) {
                    setMessages(prev => {
                        const lastMessage = prev[prev.length - 1];
                        if (lastMessage?.role === 'agent' && typeof lastMessage.content === 'string') {
                            return [
                                ...prev.slice(0, -1),
                                { ...lastMessage, content: lastMessage.content + parsedMessage.chunk, isThinking: false }
                            ];
                        } else {
                            return [...prev, { role: 'agent', content: parsedMessage.chunk, isThinking: false }];
                        }
                    });
                } else {
                    setMessages(prev => [...prev, { role: 'agent', content: message, artifacts: [...currentArtifacts.current] }]);
                    currentArtifacts.current = [];
                }
            } catch (error) {
                setMessages(prev => {
                    const lastMessage = prev[prev.length - 1];
                    if (lastMessage?.role === 'agent' && typeof lastMessage.content === 'string' && !lastMessage.isThinking) {
                        return [
                            ...prev.slice(0, -1),
                            { ...lastMessage, content: lastMessage.content + message, artifacts: [...currentArtifacts.current] }
                        ];
                    } else {
                        return [...prev, { role: 'agent', content: message, artifacts: [...currentArtifacts.current] }];
                    }
                });
                currentArtifacts.current = [];
            }
        };

        ws.current.onerror = (event) => {
            console.error('WebSocket error:', event);
            setError(new Error('WebSocket connection failed.'));
            setIsLoading(false);
        };

        ws.current.onclose = () => {
            console.log('WebSocket disconnected');
            setIsLoading(false);
            if (retryCount.current < MAX_RETRIES) {
                setTimeout(() => {
                    retryCount.current++;
                    connect(clientId);
                }, INITIAL_RETRY_DELAY * Math.pow(2, retryCount.current));
            } else {
                setError(new Error('Could not reconnect to the WebSocket.'));
            }
        };
    }, []);

    const startAgent = useCallback(async (query: string) => {
        setIsLoading(true);
        setError(null);
        setMessages([{ role: 'user', content: query }]);
        currentArtifacts.current = [];

        const clientId = `client-${Date.now()}`;
        connect(clientId);

        try {
            const token = await getToken();
            if (!token && process.env.NODE_ENV !== 'development') {
                throw new Error("Authentication token not available.");
            }

            await apiService.startStreamingAgent(token || '', {
                settings: { debug_mode: false },
                request: {
                    user_id: getUserId() ?? '',
                    query,
                    workloads: [{
                        run_id: `run-${Date.now()}`,
                        query,
                        data_source: { source_table: 'synthetic_data' },
                        time_range: { start_time: '2025-01-01T00:00:00Z', end_time: '2025-12-31T23:59:59Z' }
                    }],
                    constraints: null
                }
            }, clientId);

        } catch (err) {
            console.error("Error starting analysis:", err);
            setError(err as Error);
            setMessages(prev => [...prev, { role: 'agent', content: `Error starting analysis.` }]);
            setIsLoading(false);
        }
    }, [getToken, connect]);

    useEffect(() => {
        return () => ws.current?.close();
    }, []);

    return { isLoading, error, messages, startAgent };
};