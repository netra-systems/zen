import { apiClient } from './services/apiClient';
import { AgentRun, AgentEvent, Reference, AnalysisRequest } from '@/types/index';

// --- API Service ---
export const apiService = {
    async startStreamingAgent(token: string, body: AnalysisRequest, clientId: string) {
        return apiClient.post(`/start_agent_streaming/${clientId}`, body, token);
    },

    async getAgentStatus(runId: string, token: string | null): Promise<AgentRun> {
        return apiClient.get(`/agent/${runId}/status`, token);
    },

    async getAgentEvents(runId: string, token: string | null): Promise<AgentEvent[]> {
        return apiClient.get(`/agent/${runId}/events`, token);
    },

    async getReferences(token: string | null): Promise<{ references: Reference[] }> {
        return apiClient.get(`/references`, token);
    },

    async getExamples(): Promise<string[]> {
        return apiClient.get(`/examples`, null);
    }
};