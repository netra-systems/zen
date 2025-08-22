import { config } from '@/config';
import { logger } from '@/lib/logger';

class ApiSpecService {
  private spec: any = null;
  private maxRetries = 2;

  async getSpec(retryCount = 0): Promise<any> {
    if (this.spec) {
      return this.spec;
    }

    try {
      const response = await fetch(`${config.apiUrl}/openapi.json`);
      if (!response.ok) {
        if (retryCount < this.maxRetries) {
          logger.warn(`Failed to fetch openapi.json (${response.status}), retrying... (${retryCount + 1}/${this.maxRetries})`, {
            component: 'ApiSpecService',
            action: 'fetch_openapi_json_retry',
            metadata: { status: response.status, retry: retryCount + 1 }
          });
          // Wait a bit before retrying
          await new Promise(resolve => setTimeout(resolve, 100));
          return this.getSpec(retryCount + 1);
        }
        
        logger.error('Failed to fetch openapi.json', undefined, {
          component: 'ApiSpecService',
          action: 'fetch_openapi_json',
          metadata: { status: response.status, statusText: response.statusText }
        });
        return null;
      }
      this.spec = await response.json();
      return this.spec;
    } catch (error) {
      if (retryCount < this.maxRetries) {
        logger.warn(`Error fetching openapi.json, retrying... (${retryCount + 1}/${this.maxRetries})`, {
          component: 'ApiSpecService',
          action: 'fetch_openapi_json_retry',
          metadata: { retry: retryCount + 1 }
        });
        // Wait a bit before retrying
        await new Promise(resolve => setTimeout(resolve, 100));
        return this.getSpec(retryCount + 1);
      }
      
      logger.error('Error fetching openapi.json', error as Error, {
        component: 'ApiSpecService',
        action: 'fetch_openapi_json_error'
      });
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
    const methodObj = spec.paths[path][method.toLowerCase()];
    if (methodObj && methodObj.summary === endpointName) {
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
