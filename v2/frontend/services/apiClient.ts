import { getEndpoint, getApiUrl } from "./api";

class ApiClient {
  async request(endpointName: string, method: string, options: RequestInit) {
    const endpoint = await getEndpoint(endpointName, method);
    if (!endpoint) {
      throw new Error(`Endpoint ${endpointName} not found`);
    }

    const url = getApiUrl(endpointName);
    const response = await fetch(url, options);
    return response.json();
  }

  async get(endpointName: string, token: string | null) {
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return this.request(endpointName, "get", { headers });
  }

  async post(endpointName: string, body: unknown, token: string | null) {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return this.request(endpointName, "post", { method: "POST", headers, body: JSON.stringify(body) });
  }
}

export const apiClient = new ApiClient();