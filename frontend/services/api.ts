import { config } from '@/config';

class ApiSpecService {
  private spec: any = null;

  async getSpec() {
    if (this.spec) {
      return this.spec;
    }

    try {
      const response = await fetch(`${config.apiUrl}/openapi.json`);
      if (!response.ok) {
        console.error('Failed to fetch openapi.json', response.status, response.statusText);
        return null;
      }
      this.spec = await response.json();
      return this.spec;
    } catch (error) {
      console.error('Error fetching openapi.json', error);
      return null;
    }
  }
}

export const apiSpecService = new ApiSpecService();

export async function getEndpoint(endpointName: string, method: string) {
  const spec = await apiSpecService.getSpec();
  if (!spec) {
    return null;
  }

  for (const path in spec.paths) {
    if (spec.paths[path][method] && spec.paths[path].summary === endpointName) {
      return {
        path: path,
        method: method,
      };
    }
  }

  return null;
}

export function getApiUrl(path: string) {
  return `${config.apiUrl}${path}`;
}

// Re-export apiClient for backward compatibility
export { apiClient } from './apiClient';
