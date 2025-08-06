import { useState, useEffect, useRef, useCallback } from 'react';
import { apiService } from '../api';
import React from 'react';

interface Message {
    role: 'user' | 'agent';
    content: React.ReactNode;
}

const MAX_RETRIES = 5;
const INITIAL_RETRY_DELAY = 1000; // 1 second

export const useAgentStreaming = (token: string | null) => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [artifacts, setArtifacts] = useState<any[]>([]);
    const ws = useRef<WebSocket | null>(null);
    const retryCount = useRef(0);

    const addMessage = (role: 'user' | 'agent', content: React.ReactNode) => {
        setMessages(prev => [...prev, { role, content }]);
    };

    const connect = useCallback((clientId: string) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            return;
        }

        const wsUrl = `ws://localhost:8000/ws/${clientId}${token ? `?token=${token}` : ''}`;
        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = () => {
            console.log('WebSocket connected');
            setIsLoading(true);
            retryCount.current = 0; // Reset retry count on successful connection
        };

        ws.current.onmessage = (event) => {
            const message = event.data;
            try {
                const parsedMessage = JSON.parse(message);
                setArtifacts(prev => [...prev, parsedMessage]);
            } catch (error) {
                addMessage('agent', message);
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
                const delay = INITIAL_RETRY_DELAY * Math.pow(2, retryCount.current);
                console.log(`Attempting to reconnect in ${delay / 1000} seconds...`);
                setTimeout(() => {
                    retryCount.current++;
                    connect(clientId);
                }, delay);
            } else {
                setError(new Error('Could not reconnect to the WebSocket after multiple attempts.'));
            }
        };
    }, []);

    const startAgent = useCallback(async (query: string) => {
        setIsLoading(true);
        setError(null);
        setArtifacts([]);
        setMessages([]);

        const clientId = `client-${Date.now()}`;
        connect(clientId);

        try {
            const newRun = await apiService.startStreamingAgent(token, {
                settings: {
                    debug_mode: false,
                },
                request: {
                    user_id: 'user-123',
                    query,
                    workloads: [
                        {
                            run_id: `run-${Date.now()}`,
                            query,
                            data_source: { source_table: 'synthetic_data' },
                            time_range: { start_time: '2025-01-01T00:00:00Z', end_time: '2025-12-31T23:59:59Z' }
                        }
                    ],
                    constraints: null
                }
            }, clientId);

            if (newRun && newRun.run_id) {
                addMessage('agent', `Starting analysis with Run ID: ${newRun.run_id}`);
            } else {
                const err = new Error("Failed to start analysis: No run ID returned.");
                setError(err);
                addMessage('agent', "Failed to start analysis: No run ID returned.");
                setIsLoading(false);
            }
        } catch (err) {
            console.error("Error starting analysis:", err);
            setError(err as Error);
            addMessage('agent', `Error starting analysis.`);
            setIsLoading(false);
        }
    }, [token, connect]);

    useEffect(() => {
        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, []);

    return { isLoading, error, messages, artifacts, addMessage, startAgent, setIsLoading, setError };
};