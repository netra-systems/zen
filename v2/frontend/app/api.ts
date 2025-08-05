import { config } from './config';

// --- Type Definitions for API data ---
export interface AgentRun {
    run_id: string;
    status: 'in_progress' | 'awaiting_confirmation' | 'complete' | 'failed';
    current_step: number;
    total_steps: number;
    last_step_result?: any;
    final_report?: string;
    error?: any;
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
    async post(endpoint: string, body: Record<string, unknown>, token: string | null, expectStatus: number = 202) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(body),
        });
        if (response.status !== expectStatus) {
            throw await response.json().catch(() => new Error('An unknown error occurred.'));
        }
        return response.json();
    },

    async startAgent(token: string | null, body: Record<string, unknown>) {
        return this.post(`${config.api.baseUrl}/api/v3/apex/chat/start_agent`, body, token);
    },

    async getAgentStatus(runId: string, token: string | null) {
        return this.get(`${config.api.baseUrl}/agent/${runId}/status`, token);
    }
};