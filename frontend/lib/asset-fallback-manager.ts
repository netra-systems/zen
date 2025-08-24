/**
 * Asset Fallback Manager
 *
 * Business Value Justification:
 * - Segment: All (Free, Early, Mid, Enterprise)
 * - Business Goal: User experience & platform reliability
 * - Value Impact: Ensures static assets load reliably even when CDN fails
 * - Strategic Impact: Prevents user experience degradation during CDN outages
 *
 * Implements CDN health checking and local asset fallback for reliable asset delivery.
 */

import { logger } from './logger';

interface AssetConfig {
  cdnUrl: string;
  localPath: string;
  fallbackEnabled: boolean;
  timeout: number;
  retryAttempts: number;
}

interface CDNHealthStatus {
  isHealthy: boolean;
  lastCheck: Date;
  consecutiveFailures: number;
  responseTime: number;
}

export class AssetFallbackManager {
  private cdnHealthStatus: Map<string, CDNHealthStatus> = new Map();
  private healthCheckInterval = 60000; // 1 minute
  private healthCheckTimer?: NodeJS.Timeout;
  private assetCache: Map<string, string> = new Map();
  
  private defaultConfig: AssetConfig = {
    cdnUrl: '',
    localPath: '',
    fallbackEnabled: true,
    timeout: 5000,
    retryAttempts: 3
  };

  constructor() {
    this.startHealthChecking();
  }

  /**
   * Get asset URL with fallback logic
   */
  async getAssetUrl(assetPath: string, config?: Partial<AssetConfig>): Promise<string> {
    const fullConfig = { ...this.defaultConfig, ...config };
    
    // Check cache first
    const cacheKey = `${fullConfig.cdnUrl}${assetPath}`;
    if (this.assetCache.has(cacheKey)) {
      return this.assetCache.get(cacheKey)!;
    }

    // Construct CDN URL
    const cdnUrl = this.constructCdnUrl(fullConfig.cdnUrl, assetPath);
    
    // Check if CDN is healthy
    if (fullConfig.fallbackEnabled) {
      const isHealthy = await this.checkCdnHealth(fullConfig.cdnUrl);
      
      if (!isHealthy) {
        logger.warn(`CDN unhealthy, using local fallback for ${assetPath}`);
        const localUrl = this.constructLocalUrl(fullConfig.localPath, assetPath);
        this.assetCache.set(cacheKey, localUrl);
        return localUrl;
      }
    }

    // Try to validate CDN asset exists
    const isAvailable = await this.validateAssetAvailability(cdnUrl, fullConfig);
    
    if (isAvailable) {
      this.assetCache.set(cacheKey, cdnUrl);
      return cdnUrl;
    } else if (fullConfig.fallbackEnabled) {
      logger.warn(`CDN asset not available, using local fallback for ${assetPath}`);
      const localUrl = this.constructLocalUrl(fullConfig.localPath, assetPath);
      this.assetCache.set(cacheKey, localUrl);
      return localUrl;
    }

    // Return CDN URL anyway as last resort
    return cdnUrl;
  }

  /**
   * Check CDN health status
   */
  async checkCdnHealth(cdnBaseUrl: string): Promise<boolean> {
    const existing = this.cdnHealthStatus.get(cdnBaseUrl);
    const now = new Date();

    // Return cached status if recent
    if (existing && (now.getTime() - existing.lastCheck.getTime()) < 30000) {
      return existing.isHealthy;
    }

    try {
      const startTime = Date.now();
      const response = await fetch(`${cdnBaseUrl}/health`, {
        method: 'HEAD',
        signal: AbortSignal.timeout(5000)
      });

      const responseTime = Date.now() - startTime;
      const isHealthy = response.ok;

      this.cdnHealthStatus.set(cdnBaseUrl, {
        isHealthy,
        lastCheck: now,
        consecutiveFailures: isHealthy ? 0 : (existing?.consecutiveFailures ?? 0) + 1,
        responseTime
      });

      return isHealthy;

    } catch (error) {
      logger.error(`CDN health check failed for ${cdnBaseUrl}:`, error);
      
      const consecutiveFailures = (existing?.consecutiveFailures ?? 0) + 1;
      
      this.cdnHealthStatus.set(cdnBaseUrl, {
        isHealthy: false,
        lastCheck: now,
        consecutiveFailures,
        responseTime: -1
      });

      return false;
    }
  }

  /**
   * Validate that a specific asset is available
   */
  private async validateAssetAvailability(url: string, config: AssetConfig): Promise<boolean> {
    for (let attempt = 0; attempt < config.retryAttempts; attempt++) {
      try {
        const response = await fetch(url, {
          method: 'HEAD',
          signal: AbortSignal.timeout(config.timeout)
        });

        if (response.ok) {
          return true;
        }

        // If it's a client error (4xx), don't retry
        if (response.status >= 400 && response.status < 500) {
          return false;
        }

      } catch (error) {
        logger.debug(`Asset availability check failed (attempt ${attempt + 1}):`, error);
        
        // Wait before retry
        if (attempt < config.retryAttempts - 1) {
          await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
        }
      }
    }

    return false;
  }

  /**
   * Construct CDN URL
   */
  private constructCdnUrl(baseUrl: string, assetPath: string): string {
    const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    const cleanPath = assetPath.startsWith('/') ? assetPath : `/${assetPath}`;
    return `${cleanBase}${cleanPath}`;
  }

  /**
   * Construct local fallback URL
   */
  private constructLocalUrl(basePath: string, assetPath: string): string {
    if (!basePath) {
      // Default to Next.js public directory
      basePath = '';
    }

    const cleanBase = basePath.endsWith('/') ? basePath.slice(0, -1) : basePath;
    const cleanPath = assetPath.startsWith('/') ? assetPath : `/${assetPath}`;
    return `${cleanBase}${cleanPath}`;
  }

  /**
   * Start periodic health checking
   */
  private startHealthChecking(): void {
    this.healthCheckTimer = setInterval(() => {
      this.performPeriodicHealthChecks();
    }, this.healthCheckInterval);
  }

  /**
   * Perform periodic health checks for all tracked CDNs
   */
  private async performPeriodicHealthChecks(): Promise<void> {
    const cdns = Array.from(this.cdnHealthStatus.keys());
    
    await Promise.all(
      cdns.map(async (cdnUrl) => {
        try {
          await this.checkCdnHealth(cdnUrl);
        } catch (error) {
          logger.error(`Periodic health check failed for ${cdnUrl}:`, error);
        }
      })
    );
  }

  /**
   * Stop health checking
   */
  stop(): void {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = undefined;
    }
  }

  /**
   * Clear asset cache
   */
  clearCache(): void {
    this.assetCache.clear();
    logger.debug('Asset cache cleared');
  }

  /**
   * Get health status for all CDNs
   */
  getHealthStatus(): Record<string, CDNHealthStatus> {
    const result: Record<string, CDNHealthStatus> = {};
    
    for (const [url, status] of this.cdnHealthStatus) {
      result[url] = { ...status };
    }
    
    return result;
  }

  /**
   * Get statistics about asset fallback usage
   */
  getStatistics() {
    const totalCdns = this.cdnHealthStatus.size;
    const healthyCdns = Array.from(this.cdnHealthStatus.values())
      .filter(status => status.isHealthy).length;
    
    const cacheStats = {
      size: this.assetCache.size,
      entries: Array.from(this.assetCache.keys())
    };

    return {
      cdns: {
        total: totalCdns,
        healthy: healthyCdns,
        unhealthy: totalCdns - healthyCdns
      },
      cache: cacheStats,
      healthCheckInterval: this.healthCheckInterval
    };
  }

  /**
   * Preload critical assets
   */
  async preloadAssets(assetPaths: string[], config?: Partial<AssetConfig>): Promise<void> {
    logger.info(`Preloading ${assetPaths.length} critical assets`);
    
    const promises = assetPaths.map(async (path) => {
      try {
        await this.getAssetUrl(path, config);
      } catch (error) {
        logger.warn(`Failed to preload asset ${path}:`, error);
      }
    });

    await Promise.all(promises);
    logger.info('Asset preloading completed');
  }

  /**
   * Configure CDN for an environment
   */
  configureCdn(environment: 'development' | 'staging' | 'production'): AssetConfig {
    switch (environment) {
      case 'development':
        return {
          cdnUrl: 'http://localhost:3000',
          localPath: '/assets',
          fallbackEnabled: false, // No CDN in development
          timeout: 3000,
          retryAttempts: 1
        };
        
      case 'staging':
        return {
          cdnUrl: 'https://cdn.staging.netrasystems.ai',
          localPath: '/assets',
          fallbackEnabled: true,
          timeout: 5000,
          retryAttempts: 2
        };
        
      case 'production':
        return {
          cdnUrl: 'https://cdn.netrasystems.ai',
          localPath: '/assets',
          fallbackEnabled: true,
          timeout: 5000,
          retryAttempts: 3
        };
        
      default:
        return this.defaultConfig;
    }
  }
}

// Global instance
let assetFallbackManager: AssetFallbackManager | null = null;

export function getAssetFallbackManager(): AssetFallbackManager {
  if (!assetFallbackManager) {
    assetFallbackManager = new AssetFallbackManager();
  }
  return assetFallbackManager;
}

// Convenience functions
export async function getAssetUrl(assetPath: string, config?: Partial<AssetConfig>): Promise<string> {
  const manager = getAssetFallbackManager();
  return manager.getAssetUrl(assetPath, config);
}

export async function preloadCriticalAssets(assetPaths: string[]): Promise<void> {
  const manager = getAssetFallbackManager();
  
  // Configure based on environment
  const environment = process.env.NEXT_PUBLIC_ENVIRONMENT as 'development' | 'staging' | 'production' || 'development';
  const config = manager.configureCdn(environment);
  
  await manager.preloadAssets(assetPaths, config);
}

export function checkCdnHealth(cdnUrl: string): Promise<boolean> {
  const manager = getAssetFallbackManager();
  return manager.checkCdnHealth(cdnUrl);
}

export default AssetFallbackManager;