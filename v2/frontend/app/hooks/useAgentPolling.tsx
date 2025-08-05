import { useState, useEffect, useRef, useCallback } from 'react';
import { apiService, AgentRun, AgentEvent } from '../api';
import React from 'react';

interface Message {
    role: 'user' | 'agent';
    content: React.ReactNode;
}

export const useAgentPolling = (token: string | null) => {
    const [isPolling, setIsPolling] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const pollingRunIdRef = useRef<string | null>(null);

    const addMessage = (role: 'user' | 'agent', content: React.ReactNode) => {
        setMessages(prev => [...prev, { role, content }]);
    };

    const pollStatus = useCallback(async () => {
        if (!pollingRunIdRef.current) {
            setIsPolling(false);
            return;
        }

        try {
            const data: AgentRun = await apiService.getAgentStatus(pollingRunIdRef.current, token);

            if (data.last_step_result) {
                addMessage('agent', <pre>{JSON.stringify(data.last_step_result, null, 2)}</pre>);
            }

            if (data.status === 'complete' || data.status === 'failed') {
                setIsPolling(false);
                pollingRunIdRef.current = null;
                if (data.status === 'complete') {
                    addMessage('agent', data.final_report || 'Analysis complete.');
                } else {
                    setError(new Error(data.error?.toString() || 'Unknown error'));
                    addMessage('agent', `Analysis failed.`);
                }
                setIsLoading(false);
            }
        } catch (err) {
            console.error("Polling failed:", err);
            setError(err as Error);
            addMessage('agent', `Error polling for status.`);
            setIsPolling(false);
            pollingRunIdRef.current = null;
            setIsLoading(false);
        }
    }, [token]);

    const pollEvents = useCallback(async () => {
        if (!pollingRunIdRef.current) {
            return;
        }

        try {
            const events: AgentEvent[] = await apiService.getAgentEvents(pollingRunIdRef.current, token);
            if (events && events.length > 0) {
                events.forEach(event => {
                    addMessage('agent', <pre>{JSON.stringify(event, null, 2)}</pre>);
                });
            }
        } catch (err) {
            console.error("Event polling failed:", err);
        }
    }, [token]);

    useEffect(() => {
        if (!isPolling) {
            return;
        }
        const statusIntervalId = setInterval(pollStatus, 3000);
        const eventsIntervalId = setInterval(pollEvents, 3000);

        return () => {
            clearInterval(statusIntervalId);
            clearInterval(eventsIntervalId);
        };
    }, [isPolling, pollStatus, pollEvents]);

    const startPolling = (runId: string) => {
        pollingRunIdRef.current = runId;
        setIsPolling(true);
    };

    return { isPolling, isLoading, error, messages, addMessage, startPolling, setIsLoading, setError };
};