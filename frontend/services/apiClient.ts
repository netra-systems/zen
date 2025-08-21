import { getEndpoint, getApiUrl } from "./api";
import { authInterceptor } from '@/lib/auth-interceptor';
import { logger } from '@/lib/logger';

class ApiClient {
  async request(endpointName: string, method: string, options: RequestInit) {
    const endpoint = await getEndpoint(endpointName, method);
    if (!endpoint) {
      throw new Error(`Endpoint ${endpointName} not found`);
    }

    const url = getApiUrl(endpoint.path);
    
    // Use auth interceptor for all requests
    const response = await authInterceptor.authenticatedFetch(url, {
      ...options,
      method: method.toUpperCase()
    });
    
    if (!response.ok) {
      const errorData = await response.text();
      let errorMessage: string;
      try {
        const parsed = JSON.parse(errorData);
        errorMessage = parsed.detail || parsed.message || parsed.error || `Request failed with status ${response.status}`;
      } catch {
        errorMessage = errorData || `Request failed with status ${response.status}`;
      }
      
      const error = new Error(errorMessage);
      (error as any).status = response.status;
      throw error;
    }
    
    return response.json();
  }

  async get(endpointName: string, token?: string | null) {
    // Token handling is now centralized in auth interceptor
    // The token parameter is kept for backward compatibility but not used
    return this.request(endpointName, "get", {});
  }

  async post(endpointName: string, body: unknown, token?: string | null) {
    // Token handling is now centralized in auth interceptor
    // The token parameter is kept for backward compatibility but not used
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    return this.request(endpointName, "post", { headers, body: JSON.stringify(body) });
  }
}

export const apiClient = new ApiClient();