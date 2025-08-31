/**
 * Axios-like wrapper for the apiClient to support ThreadService
 * Enhanced with secure URL handling and centralized auth with token refresh
 */

import { unifiedApiConfig } from '@/lib/unified-api-config';
import { authInterceptor } from '@/lib/auth-interceptor';
import { logger } from '@/lib/logger';
import { CircuitBreaker } from '@/lib/circuit-breaker';

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
  private environment: string;
  private circuitBreaker: CircuitBreaker;
  
  constructor() {
    // Use unified configuration for clear environment handling
    this.baseURL = unifiedApiConfig.urls.api;
    this.environment = unifiedApiConfig.environment;
    
    // Initialize circuit breaker with environment-specific settings
    const circuitBreakerConfig = this.environment === 'staging' ? {
      failureThreshold: 15,    // Higher threshold for staging network instability
      timeWindowMs: 120000,    // 2 minute window
      recoveryTimeoutMs: 60000 // 1 minute recovery
    } : {
      failureThreshold: 10,    // Default for prod/dev
      timeWindowMs: 60000,     // 1 minute window
      recoveryTimeoutMs: 30000 // 30s recovery
    };
    
    this.circuitBreaker = new CircuitBreaker(circuitBreakerConfig);
    
    logger.info(`API Client initialized for ${this.environment} environment`, { 
      baseURL: this.baseURL,
      circuitBreakerConfig
    });
    this.checkConnection();
  }

  /**
   * Get environment-specific timeout configurations
   */
  private getTimeoutConfig(): { request: number; connection: number; retry: { count: number; delay: number } } {
    switch (this.environment) {
      case 'staging':
        return {
          request: 60000,    // 60s request timeout for staging (GCP latency)
          connection: 30000, // 30s connection timeout
          retry: { count: 5, delay: 2000 } // More retries for staging network issues
        };
      case 'production':
        return {
          request: 45000,    // 45s request timeout for production
          connection: 20000, // 20s connection timeout
          retry: { count: 3, delay: 1500 }
        };
      case 'development':
      default:
        return {
          request: 30000,    // 30s request timeout for development
          connection: 10000, // 10s connection timeout
          retry: { count: 3, delay: 1000 }
        };
    }
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
      // Use direct URL for health check to bypass Next.js proxy issues
      const healthUrl = this.environment === 'development' 
        ? `${this.baseURL}/health/ready`
        : unifiedApiConfig.endpoints.ready;
      logger.debug(`Checking backend connection at: ${healthUrl}`);
      
      const response = await fetch(healthUrl, {
        method: 'GET',
        mode: 'cors',
      }).catch(() => null);
      
      this.isConnected = response?.ok || response?.status === 307 || false;
      logger.info(`Backend connection check result:`, { 
        connected: this.isConnected, 
        status: response?.status,
        environment: this.environment 
      });
      return this.isConnected;
    } catch (error) {
      logger.error('Backend connection check failed:', error);
      this.isConnected = false;
      return false;
    }
  }

  private validateUrl(url: string): string {
    // Remove double slashes except after protocol
    return url.replace(/([^:]\/)\/+/g, "$1");
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
        const errorMessage = error instanceof Error ? error.message : String(error);
        
        // Log retry attempts for debugging network issues
        logger.warn(`Request attempt ${i + 1}/${retries} failed:`, {
          error: errorMessage,
          environment: this.environment,
          retryIn: i < retries - 1 ? delay * Math.pow(2, i) : 0
        });
        
        // Check if error is retryable
        if (this.isRetryableError(error)) {
          if (i < retries - 1) {
            const backoffDelay = delay * Math.pow(2, i) + Math.random() * 1000; // Add jitter
            await this.sleep(backoffDelay);
          }
        } else {
          // Non-retryable error, fail fast
          logger.error('Non-retryable error encountered, failing fast:', errorMessage);
          throw error;
        }
      }
    }
    
    throw lastError;
  }

  /**
   * Determine if an error is retryable
   */
  private isRetryableError(error: any): boolean {
    const errorMessage = error instanceof Error ? error.message : String(error);
    const status = (error as any)?.status || 0;
    
    // Don't retry client errors (4xx) except for specific cases
    if (status >= 400 && status < 500 && status !== 408 && status !== 429) {
      return false;
    }
    
    // Retry network errors, server errors (5xx), timeouts, and connection issues
    return (
      status >= 500 || // Server errors
      status === 408 || // Request timeout
      status === 429 || // Rate limit
      status === 0 ||   // Network error
      errorMessage.includes('fetch') ||
      errorMessage.includes('network') ||
      errorMessage.includes('timeout') ||
      errorMessage.includes('ECONNRESET') ||
      errorMessage.includes('socket hang up') ||
      errorMessage.includes('ENOTFOUND') ||
      errorMessage.includes('ECONNREFUSED')
    );
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

    const validatedUrl = this.validateUrl(fullUrl.toString());
    const timeoutConfig = this.getTimeoutConfig();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...config?.headers,
    };

    // Create AbortController for request timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
      logger.warn('Request timed out', { 
        url: validatedUrl, 
        timeout: timeoutConfig.request,
        environment: this.environment
      });
    }, timeoutConfig.request);

    // Auth handling is now done by the auth interceptor
    // Token management and 401 handling is centralized

    const options: RequestInit = {
      method,
      headers,
      credentials: 'include',
      signal: controller.signal,
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      options.body = JSON.stringify(data);
    }

    const shouldRetry = config?.retry !== false;
    const retryCount = config?.retryCount || timeoutConfig.retry.count;
    const retryDelay = config?.retryDelay || timeoutConfig.retry.delay;

    const performFetch = async () => {
      // Check circuit breaker state
      if (this.circuitBreaker.isOpen()) {
        const error = new Error('Circuit breaker is open - service temporarily unavailable');
        (error as any).circuitBreakerOpen = true;
        logger.warn('Request blocked by circuit breaker', {
          url: validatedUrl,
          environment: this.environment,
          circuitState: this.circuitBreaker.getState()
        });
        throw error;
      }

      if (!this.isConnected) {
        await this.checkConnection();
        if (!this.isConnected) {
          const error = new Error('Unable to connect to backend API. Please ensure the backend is running.');
          this.circuitBreaker.recordFailure();
          throw error;
        }
      }

      try {
        // Use auth interceptor for authenticated requests
        const response = await authInterceptor.authenticatedFetch(validatedUrl, {
          ...options,
          skipAuth: config?.headers?.['skip-auth'] === 'true'
        }).catch(async (error) => {
          this.isConnected = false;
          await this.checkConnection();
          // Record network-level failures
          this.circuitBreaker.recordFailure();
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
          
          // Record failure for server errors and network issues
          if (response.status >= 500 || response.status === 408 || response.status === 429) {
            this.circuitBreaker.recordFailure();
          }
          
          // 401 handling is now done by auth interceptor
          // This will only be reached if auth interceptor fails
          throw error;
        }

        // Record success for circuit breaker
        this.circuitBreaker.recordSuccess();

        return {
          data: responseData,
          status: response.status,
          statusText: response.statusText,
        };
      } catch (error) {
        // Record failure if not already recorded
        if (!(error as any).circuitBreakerOpen) {
          this.circuitBreaker.recordFailure();
        }
        throw error;
      }
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
        // Enhanced error logging with environment context
        logger.error('API Request failed:', {
          url: validatedUrl,
          method,
          environment: this.environment,
          error: error.message,
          timeout: timeoutConfig.request,
          retrySettings: { count: retryCount, delay: retryDelay }
        });
        throw error;
      }
      const errorMessage = String(error) || 'An unexpected error occurred';
      throw new Error(errorMessage);
    } finally {
      // Clear timeout to prevent memory leaks
      clearTimeout(timeoutId);
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