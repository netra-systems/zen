import { config } from './config';

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
    async post(endpoint: string, body: Record<string, unknown>, token: string | null) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            throw await response.json().catch(() => new Error('An unknown error occurred.'));
        }
        return response.json();
    },

    async startAgent(token: string | null, body: Record<string, unknown>) {
        return this.post(`${config.api.baseUrl}/apex/chat/start_agent`, body, token);
    },

    async startStreamingAgent(token: string | null, body: Record<string, unknown>, clientId: string) {
        return this.post(`${config.api.baseUrl}/streaming_agent/start_agent/${clientId}`, body, token);
    },

    async getAgentStatus(runId: string, token: string | null): Promise<AgentRun> {
        return this.get(`${config.api.baseUrl}/agent/${runId}/status`, token);
    },

    async getAgentEvents(runId: string, token: string | null): Promise<AgentEvent[]> {
        return this.get(`${config.api.baseUrl}/agent/${runId}/events`, token);
    }
};