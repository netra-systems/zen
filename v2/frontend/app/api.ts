import { config } from './config';
import { AgentRun, AgentEvent, Reference, AnalysisRequest } from '@/app/types';

// --- API Service ---
export const apiService = {
    async get<T>(endpoint: string, token: string | null): Promise<T> {
        const url = endpoint.startsWith('http') ? endpoint : `${config.api.baseUrl}${endpoint}`;
        const headers: Record<string, string> = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const response = await fetch(url, { headers });
        if (!response.ok) {
            throw await response.json().catch(() => new Error('An unknown error occurred.'));
        }
        return response.json();
    },

    async post<T>(endpoint: string, body: T, token?: string | null) {
        const url = endpoint.startsWith('http') ? endpoint : `${config.api.baseUrl}${endpoint}`;
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            throw await response.json().catch(() => new Error('An unknown error occurred.'));
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.indexOf('application/json') !== -1) {
            return response.json();
        } else {
            return;
        }
    },

    async startStreamingAgent(token: string, body: AnalysisRequest, clientId: string) {
        return this.post(`/start_agent_streaming/${clientId}`, body, token);
    },

    async getAgentStatus(runId: string, token: string | null): Promise<AgentRun> {
        return this.get<AgentRun>(`/agent/${runId}/status`, token);
    },

    async getAgentEvents(runId: string, token: string | null): Promise<AgentEvent[]> {
        return this.get<AgentEvent[]>(`/agent/${runId}/events`, token);
    },

    async getReferences(token: string | null): Promise<{ references: Reference[] }> {
        return this.get<{ references: Reference[] }>(`/references`, token);
    },

    async getExamples(): Promise<string[]> {
        return this.get<string[]>(`/examples`, null);
    }
};