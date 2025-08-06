import { config } from './config';
import useAppStore from '@/store';

// --- Type Definitions for API data ---
export interface AgentRun {
    run_id: string;
    status: 'in_progress' | 'awaiting_confirmation' | 'complete' | 'failed';
    current_step: number;
    total_steps: number;
    last_step_result?: Record<string, unknown>;
    final_report?: string;
    error?: Record<string, unknown>;
}

export interface AgentEvent {
    event: string;
    data: Record<string, unknown>;
}

export interface Reference {
    id: string;
    name: string;
    friendly_name: string;
    description: string | null;
    type: string;
    value: string;
    version: string;
}

// --- API Service ---
export const apiService = {
    async get(endpoint: string, token: string | null) {
        const response = await fetch(endpoint, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        if (!response.ok) {
            throw await response.json().catch(() => new Error('An unknown error occurred.'));
        }
        return response.json();
    },

    async post(endpoint: string, body: Record<string, unknown>, token?: string | null) {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(endpoint, {
            method: 'POST',
            headers,
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            throw await response.json().catch(() => new Error('An unknown error occurred.'));
        }

        return response.json();
    },

    async startAgent(token: string | null, body: Record<string, unknown>) {
        const addMessage = useAppStore.getState().addMessage;
        addMessage({ role: 'user', content: JSON.stringify(body) });

        const response = await fetch(`${config.api.baseUrl}/apex/chat/start_agent`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify(body),
        });

        if (!response.body) {
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantMessage = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }
            const chunk = decoder.decode(value, { stream: true });
            assistantMessage += chunk;
            addMessage({ role: 'assistant', content: assistantMessage });
        }
    },

    async startStreamingAgent(token: string, body: Record<string, unknown>, clientId: string) {
        return this.post(`${config.api.baseUrl}/streaming_agent/start_agent/${clientId}`, body, token);
    },

    async getAgentStatus(runId: string, token: string | null): Promise<AgentRun> {
        return this.get(`${config.api.baseUrl}/agent/${runId}/status`, token);
    },

    async getAgentEvents(runId: string, token: string | null): Promise<AgentEvent[]> {
        return this.get(`${config.api.baseUrl}/agent/${runId}/events`, token);
    },

    async getReferences(token: string | null): Promise<{ references: Reference[] }> {
        return this.get(`${config.api.baseUrl}/references`, token);
    },

    async getExamples(): Promise<string[]> {
        return this.get(`${config.api.baseUrl}/examples`, null);
    }
};