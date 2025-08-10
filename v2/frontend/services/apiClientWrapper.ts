/**
 * Axios-like wrapper for the apiClient to support ThreadService
 */

interface ApiResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
}

interface RequestConfig {
  params?: Record<string, any>;
  headers?: Record<string, string>;
}

class ApiClientWrapper {
  private baseURL: string;
  
  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
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

    try {
      const response = await fetch(fullUrl.toString(), options);
      
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
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      // Handle network errors or other unexpected cases
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