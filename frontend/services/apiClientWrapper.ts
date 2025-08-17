/**
 * Axios-like wrapper for the apiClient to support ThreadService
 * Enhanced with secure URL handling to prevent mixed content errors
 */

import { secureApiConfig } from '@/lib/secure-api-config';

interface ApiResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
}

interface RequestConfig {
  params?: Record<string, any>;
  headers?: Record<string, string>;
  retry?: boolean;
  retryCount?: number;
  retryDelay?: number;
}

class ApiClientWrapper {
  private baseURL: string;
  private isConnected: boolean = false;
  private connectionCheckPromise: Promise<boolean> | null = null;
  
  constructor() {
    // Use secure API configuration to prevent mixed content errors
    this.baseURL = secureApiConfig.apiUrl;
    this.checkConnection();
  }

  private async checkConnection(): Promise<boolean> {
    if (this.connectionCheckPromise) {
      return this.connectionCheckPromise;
    }
    
    this.connectionCheckPromise = this.performConnectionCheck();
    const result = await this.connectionCheckPromise;
    this.connectionCheckPromise = null;
    return result;
  }

  private async performConnectionCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/health`, {
        method: 'GET',
        mode: 'cors',
      }).catch(() => null);
      
      this.isConnected = response?.ok || response?.status === 307 || false;
      return this.isConnected;
    } catch {
      this.isConnected = false;
      return false;
    }
  }

  private async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private async retryRequest<T>(
    fn: () => Promise<T>,
    retries = 3,
    delay = 1000
  ): Promise<T> {
    let lastError: Error | null = null;
    
    for (let i = 0; i < retries; i++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error as Error;
        if (i < retries - 1) {
          await this.sleep(delay * Math.pow(2, i));
        }
      }
    }
    
    throw lastError;
  }

  private async request<T>(
    method: string,
    url: string,
    data?: any,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    const fullUrl = new URL(url, this.baseURL);
    
    // Add query parameters if provided
    if (config?.params) {
      Object.entries(config.params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          fullUrl.searchParams.append(key, String(value));
        }
      });
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...config?.headers,
    };

    // Get token from localStorage or session
    const token = typeof window !== 'undefined' 
      ? localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token')
      : null;
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const options: RequestInit = {
      method,
      headers,
      credentials: 'include',
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      options.body = JSON.stringify(data);
    }

    const shouldRetry = config?.retry !== false;
    const retryCount = config?.retryCount || 3;
    const retryDelay = config?.retryDelay || 1000;

    const performFetch = async () => {
      if (!this.isConnected) {
        await this.checkConnection();
        if (!this.isConnected) {
          throw new Error('Unable to connect to backend API. Please ensure the backend is running.');
        }
      }

      const response = await fetch(fullUrl.toString(), options).catch(async (error) => {
        this.isConnected = false;
        await this.checkConnection();
        throw new Error(`Network error: ${error.message || 'Failed to fetch'}`);
      });
      
      let responseData: T;
      const contentType = response.headers.get('content-type');
      
      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      } else {
        responseData = await response.text() as unknown as T;
      }

      if (!response.ok) {
        const errorMessage = 
          (responseData as any)?.detail || 
          (responseData as any)?.message || 
          (responseData as any)?.error ||
          `Request failed with status ${response.status}`;
        
        const error = new Error(errorMessage);
        (error as any).status = response.status;
        (error as any).response = responseData;
        throw error;
      }

      return {
        data: responseData,
        status: response.status,
        statusText: response.statusText,
      };
    };

    try {
      if (shouldRetry) {
        return await this.retryRequest(
          performFetch,
          retryCount,
          retryDelay
        );
      } else {
        return await performFetch();
      }
    } catch (error) {
      if (error instanceof Error) {
        console.error('API Request failed:', {
          url: fullUrl.toString(),
          method,
          error: error.message
        });
        throw error;
      }
      const errorMessage = String(error) || 'An unexpected error occurred';
      throw new Error(errorMessage);
    }
  }

  async get<T = any>(url: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('GET', url, undefined, config);
  }

  async post<T = any>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('POST', url, data, config);
  }

  async put<T = any>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', url, data, config);
  }

  async patch<T = any>(url: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('PATCH', url, data, config);
  }

  async delete<T = any>(url: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', url, undefined, config);
  }
}

export const apiClient = new ApiClientWrapper();