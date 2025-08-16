// Component props types for three-layer response card system
// Modular props definitions with focused responsibilities

import type { 
  FastLayerData, 
  MediumLayerData, 
  SlowLayerData 
} from './layer-types';

// ============================================
// Component Props Types
// ============================================

export interface PersistentResponseCardProps {
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
  isProcessing: boolean;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export interface FastLayerProps {
  data: FastLayerData | null;
  isProcessing: boolean;
}

export interface MediumLayerProps {
  data: MediumLayerData | null;
}

export interface SlowLayerProps {
  data: SlowLayerData | null;
  isCollapsed?: boolean;
}

// ============================================
// Animation and Transition Types
// ============================================

export interface LayerTransition {
  duration: number;  // in ms
  easing: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
  delay?: number;    // in ms
}

export interface StreamingConfig {
  charactersPerSecond: number;
  useRequestAnimationFrame: boolean;
  debounceMs: number;
}

// ============================================
// Performance Monitoring Types
// ============================================

export interface PerformanceMetrics {
  renderTime: number;
  updateTime: number;
  memoryUsage?: number;
  frameRate?: number;
  eventProcessingTime: number;
}

// ============================================
// Configuration Types
// ============================================

export interface UnifiedChatConfig {
  maxMessages: number;              // Maximum messages to keep in memory
  messagePaginationSize: number;    // Number of messages to load at once
  streamingConfig: StreamingConfig;
  layerTransitions: {
    fast: LayerTransition;
    medium: LayerTransition;
    slow: LayerTransition;
  };
  autoCollapseDelay: number;       // ms after completion to auto-collapse
  performanceMonitoring: boolean;   // Enable performance tracking
}

// Default configuration
export const DEFAULT_UNIFIED_CHAT_CONFIG: UnifiedChatConfig = {
  maxMessages: 1000,
  messagePaginationSize: 50,
  streamingConfig: {
    charactersPerSecond: 30,
    useRequestAnimationFrame: true,
    debounceMs: 100,
  },
  layerTransitions: {
    fast: { duration: 0, easing: 'linear' },
    medium: { duration: 300, easing: 'ease-out' },
    slow: { duration: 400, easing: 'ease-out', delay: 100 },
  },
  autoCollapseDelay: 2000,
  performanceMonitoring: true,
};

// ============================================
// Admin Component Props (for admin features)
// ============================================

export interface AdminFeatureProps {
  adminType?: 'corpus' | 'synthetic' | 'users' | 'config' | 'logs';
  adminStatus?: 'pending' | 'in_progress' | 'completed';
  adminMetadata?: {
    totalRecords?: number;
    recordsProcessed?: number;
    estimatedTime?: string;
    auditInfo?: {
      user: string;
      timestamp: string;
      action: string;
    };
    rollbackAvailable?: boolean;
  };
}

// ============================================
// Collapse Feature Props
// ============================================

export interface CollapseFeatureProps {
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  autoCollapseDelay?: number;
  showCollapseButton?: boolean;
}

// ============================================
// Layer Management Props
// ============================================

export interface LayerManagerProps {
  fastLayerData: FastLayerData | null;
  mediumLayerData: MediumLayerData | null;
  slowLayerData: SlowLayerData | null;
  isProcessing: boolean;
  transitions: {
    fast: LayerTransition;
    medium: LayerTransition;
    slow: LayerTransition;
  };
}
