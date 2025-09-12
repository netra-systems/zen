/**
 * Service Discovery Client
 * Handles dynamic port discovery for development environments
 */

import { logger } from '@/lib/logger';

interface ServiceInfo {
  port: number;
  url: string;
  api_url?: string;
  ws_url?: string;
  timestamp: string;
  cors_metadata?: Record<string, unknown>;
}

interface ServicesResponse {
  services: {
    backend?: ServiceInfo;
    frontend?: ServiceInfo;
    auth?: ServiceInfo;
  };
  timestamp: string;
  available: boolean;
}

interface DiscoveredUrls {
  apiUrl: string;
  wsUrl: string;
  authUrl: string;
}

class ServiceDiscoveryClient {
  private static instance: ServiceDiscoveryClient;
  private cache: DiscoveredUrls | null = null;
  private cacheTimestamp: number = 0;
  private readonly cacheTTL = 30000; // 30 seconds cache
  private readonly discoveryTimeout = 3000; // 3 second timeout

  private constructor() {}

  static getInstance(): ServiceDiscoveryClient {
    if (!ServiceDiscoveryClient.instance) {
      ServiceDiscoveryClient.instance = new ServiceDiscoveryClient();
    }
    return ServiceDiscoveryClient.instance;
  }

  /**
   * Get the discovery endpoint URL
   */
  private getDiscoveryEndpoint(): string {
    const environment = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development';
    
    if (environment === 'development') {
      // In development, try the backend discovery endpoint
      // Force port 8000 for consistency
      return 'http://localhost:8000';
    }
    
    // In staging/production, use environment-specific URLs
    if (environment === 'production') {
      return 'https://api.netrasystems.ai';
    } else {
      return 'https://api.staging.netrasystems.ai';
    }
  }

  /**
   * Fetch services from discovery endpoint
   */
  private async fetchServices(): Promise<ServicesResponse | null> {
    try {
      const baseUrl = this.getDiscoveryEndpoint();
      const discoveryUrl = `${baseUrl}/api/discovery/services`;
      
      logger.debug(`Fetching services from discovery endpoint: ${discoveryUrl}`);
      
      const response = await fetch(discoveryUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(this.discoveryTimeout),
      });

      if (!response.ok) {
        logger.warn(`Discovery endpoint returned ${response.status}: ${response.statusText}`);
        return null;
      }

      const data = await response.json();
      logger.debug('Discovery response:', data);
      return data;
      
    } catch (error) {
      logger.warn('Failed to fetch from discovery endpoint:', error);
      return null;
    }
  }

  /**
   * Get fallback URLs when discovery is not available
   */
  private getFallbackUrls(): DiscoveredUrls {
    const environment = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development';
    
    if (environment === 'development') {
      return {
        apiUrl: 'http://localhost:8000', // Force port 8000 for backend API
        wsUrl: 'ws://localhost:8000/websocket', // Force port 8000 for WebSocket
        authUrl: process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || process.env.NEXT_PUBLIC_AUTH_API_URL || 'http://localhost:8081',
      };
    } else if (environment === 'production') {
      return {
        apiUrl: 'https://api.netrasystems.ai',
        wsUrl: 'wss://api.netrasystems.ai/websocket',
        authUrl: 'https://auth.netrasystems.ai',
      };
    } else {
      return {
        apiUrl: 'https://api.staging.netrasystems.ai',
        wsUrl: 'wss://api.staging.netrasystems.ai/websocket',
        authUrl: 'https://auth.staging.netrasystems.ai',
      };
    }
  }

  /**
   * Check if cache is valid
   */
  private isCacheValid(): boolean {
    return this.cache !== null && (Date.now() - this.cacheTimestamp) < this.cacheTTL;
  }

  /**
   * Update cache with discovered URLs
   */
  private updateCache(urls: DiscoveredUrls): void {
    this.cache = urls;
    this.cacheTimestamp = Date.now();
  }

  /**
   * Discover service URLs dynamically
   */
  async discoverUrls(): Promise<DiscoveredUrls> {
    // Return cached result if valid
    if (this.isCacheValid() && this.cache) {
      logger.debug('Using cached service discovery results');
      return this.cache;
    }

    try {
      const servicesResponse = await this.fetchServices();
      
      if (servicesResponse?.available && servicesResponse.services) {
        const { backend, auth } = servicesResponse.services;
        
        const discoveredUrls: DiscoveredUrls = {
          apiUrl: backend?.api_url || backend?.url || this.getFallbackUrls().apiUrl,
          wsUrl: backend?.ws_url || this.getFallbackUrls().wsUrl,
          authUrl: auth?.api_url || auth?.url || this.getFallbackUrls().authUrl,
        };

        logger.info('Service discovery successful:', discoveredUrls);
        this.updateCache(discoveredUrls);
        return discoveredUrls;
      }
    } catch (error) {
      logger.warn('Service discovery failed, using fallbacks:', error);
    }

    // Fall back to environment variables or defaults
    const fallbackUrls = this.getFallbackUrls();
    logger.info('Using fallback service URLs:', fallbackUrls);
    this.updateCache(fallbackUrls);
    return fallbackUrls;
  }

  /**
   * Get discovered API URL
   */
  async getApiUrl(): Promise<string> {
    const urls = await this.discoverUrls();
    return urls.apiUrl;
  }

  /**
   * Get discovered WebSocket URL
   */
  async getWsUrl(): Promise<string> {
    const urls = await this.discoverUrls();
    return urls.wsUrl;
  }

  /**
   * Get discovered auth service URL
   */
  async getAuthUrl(): Promise<string> {
    const urls = await this.discoverUrls();
    return urls.authUrl;
  }

  /**
   * Clear the cache (useful for testing or forcing refresh)
   */
  clearCache(): void {
    this.cache = null;
    this.cacheTimestamp = 0;
  }

  /**
   * Check if service discovery is working
   */
  async isDiscoveryAvailable(): Promise<boolean> {
    try {
      const servicesResponse = await this.fetchServices();
      return servicesResponse?.available === true;
    } catch (error) {
      return false;
    }
  }
}

// Export singleton instance
export const serviceDiscovery = ServiceDiscoveryClient.getInstance();

// Export for testing
export { ServiceDiscoveryClient };

// Export types
export type { ServiceInfo, ServicesResponse, DiscoveredUrls };