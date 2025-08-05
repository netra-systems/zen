import { useState, useEffect, useRef, useCallback } from 'react';
import { apiService, AgentRun } from '../api';
import React from 'react';

export const useAgentPolling = (token: string | null) => {
    const [isPolling, setIsPolling] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<any | null>(null);
    const [messages, setMessages] = useState<any[]>([]);
    const pollingRunIdRef = useRef<string | null>(null);

    const addMessage = (role: 'user' | 'agent', content: any) => {
        setMessages(prev => [...prev, { role, content }]);
    };

    """    const pollStatus = useCallback(async () => {
        if (!pollingRunIdRef.current) {
            return;
        }

        setError(null);

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
                    setError(data.error || 'Unknown error');
                    addMessage('agent', `Analysis failed.`);
                }
                setIsLoading(false);
            }
        } catch (err) {
            console.error("Polling failed:", err);
            setError(err);
            addMessage('agent', `Error polling for status.`);
            setIsPolling(false);
            pollingRunIdRef.current = null;
            setIsLoading(false);
        }
    }, [token]);

    useEffect(() => {
        if (!isPolling) {
            return;
        }
        const intervalId = setInterval(pollStatus, 3000);
        return () => clearInterval(intervalId);
    }, [isPolling, pollStatus]);

    const startPolling = (runId: string) => {
        pollingRunIdRef.current = runId;
        setIsPolling(true);
        setIsLoading(true);
    };""

    return { isPolling, isLoading, error, messages, addMessage, startPolling, setIsLoading, setError };
};