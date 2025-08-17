/**
 * Performance Metrics Type Definitions
 * 
 * Single source of truth for all performance tracking across the application.
 * Used by hooks, store, and components for consistent metrics collection.
 * 
 * BVJ: Enterprise segment - Critical for SLA compliance and value demonstration
 */

// Core performance metrics interface
export interface PerformanceMetrics {
  // Render tracking
  renderCount: number;
  lastRenderTime: number;
  renderTime?: number; // Alternative naming for compatibility
  
  // Response and latency tracking
  averageResponseTime: number;
  wsLatency: number;
  eventProcessingTime?: number;
  
  // System performance
  memoryUsage: number;
  fps: number;
  frameRate?: number; // Alternative naming for compatibility
  
  // Component-specific tracking
  componentRenderTimes: Map<string, number>;
  updateTime?: number;
  
  // Error and efficiency tracking
  errorCount: number;
  cacheHitRate: number;
}

// Options for performance tracking configuration
export interface MetricsOptions {
  trackMemory?: boolean;
  trackFPS?: boolean;
  trackComponents?: boolean;
  updateInterval?: number;
}

// Metrics export format for debugging and reporting
export interface PerformanceReport {
  timestamp: string;
  metrics: PerformanceMetrics;
  componentRenderTimes: [string, number][];
  userAgent: string;
  viewport: {
    width: number;
    height: number;
  };
}

// Global performance monitoring interface
export interface PerformanceMonitorInterface {
  updateMetrics(component: string, metrics: Partial<PerformanceMetrics>): void;
  getMetrics(component?: string): PerformanceMetrics | Map<string, PerformanceMetrics> | null;
  subscribe(observer: (metrics: Map<string, PerformanceMetrics>) => void): () => void;
  exportReport(): string;
}

// Default performance metrics values
export const DEFAULT_PERFORMANCE_METRICS: PerformanceMetrics = {
  renderCount: 0,
  lastRenderTime: 0,
  averageResponseTime: 0,
  memoryUsage: 0,
  fps: 0,
  wsLatency: 0,
  componentRenderTimes: new Map<string, number>(),
  errorCount: 0,
  cacheHitRate: 0,
};

// Performance thresholds for alerts and monitoring
export const PERFORMANCE_THRESHOLDS = {
  MAX_RENDER_TIME: 16, // 60fps = 16.67ms per frame
  MAX_MEMORY_USAGE: 100, // MB
  MIN_FPS: 30,
  MAX_WS_LATENCY: 1000, // ms
  MAX_ERROR_COUNT: 10,
  MIN_CACHE_HIT_RATE: 70, // percentage
} as const;

// Performance metrics categories for organization
export type PerformanceCategory = 
  | 'render' 
  | 'memory' 
  | 'network' 
  | 'error' 
  | 'cache';

// Metrics field mapping for different use cases
export const METRICS_FIELD_MAPPING = {
  // Hook usage (comprehensive)
  hook: ['renderCount', 'lastRenderTime', 'averageResponseTime', 'memoryUsage', 
         'fps', 'wsLatency', 'componentRenderTimes', 'errorCount', 'cacheHitRate'],
  
  // Store usage (essential only)
  store: ['renderCount', 'lastRenderTime', 'averageResponseTime', 'memoryUsage'],
  
  // Component usage (render focused)
  component: ['renderTime', 'updateTime', 'memoryUsage', 'frameRate', 'eventProcessingTime']
} as const;