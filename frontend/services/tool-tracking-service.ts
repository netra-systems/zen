// Tool tracking service - Manages tool lifecycle, deduplication, auto-removal
// Modular service following 25-line function limits

import { 
  ToolLifecycleMap, 
  addToolWithTimeout, 
  removeToolFromLifecycle,
  getActiveToolNames,
  cleanupExpiredTools
} from '@/utils/tool-lifecycle-tracker';

export interface ToolTrackingConfig {
  autoRemovalTimeoutMs: number;
  cleanupIntervalMs: number;
  maxActiveTools: number;
  enableDeduplication: boolean;
}

export const DEFAULT_TOOL_TRACKING_CONFIG: ToolTrackingConfig = {
  autoRemovalTimeoutMs: 30000,  // 30 seconds
  cleanupIntervalMs: 5000,      // 5 seconds
  maxActiveTools: 10,           // Max 10 active tools
  enableDeduplication: true
};

/**
 * Tool tracking service class
 */
export class ToolTrackingService {
  private lifecycleMap: ToolLifecycleMap = {};
  private config: ToolTrackingConfig;
  private cleanupInterval?: NodeJS.Timeout;
  private onToolsUpdated?: (tools: string[]) => void;

  constructor(
    config: ToolTrackingConfig = DEFAULT_TOOL_TRACKING_CONFIG,
    onToolsUpdated?: (tools: string[]) => void
  ) {
    this.config = config;
    this.onToolsUpdated = onToolsUpdated;
    this.startCleanupInterval();
  }

  /**
   * Starts tool with auto-removal timeout
   */
  startTool(toolName: string): void {
    if (this.shouldAddTool(toolName)) {
      this.addToolWithCallback(toolName);
      this.notifyToolsUpdated();
    }
  }

  /**
   * Completes tool and removes from tracking
   */
  completeTool(toolName: string): void {
    this.lifecycleMap = removeToolFromLifecycle(this.lifecycleMap, toolName);
    this.notifyToolsUpdated();
  }

  /**
   * Gets current active tool names
   */
  getActiveTools(): string[] {
    return getActiveToolNames(this.lifecycleMap);
  }

  /**
   * Cleanup service and stop intervals
   */
  cleanup(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
    this.clearAllTimeouts();
  }

  /**
   * Checks if tool should be added (deduplication logic)
   */
  private shouldAddTool(toolName: string): boolean {
    const hasActiveTool = this.lifecycleMap[toolName]?.isActive;
    const underLimit = Object.keys(this.lifecycleMap).length < this.config.maxActiveTools;
    return !hasActiveTool && underLimit;
  }

  /**
   * Adds tool with timeout callback
   */
  private addToolWithCallback(toolName: string): void {
    this.lifecycleMap = addToolWithTimeout(
      this.lifecycleMap,
      toolName,
      (expiredTool) => this.handleToolTimeout(expiredTool),
      this.config.autoRemovalTimeoutMs
    );
  }

  /**
   * Handles tool timeout
   */
  private handleToolTimeout(toolName: string): void {
    this.completeTool(toolName);
  }

  /**
   * Notifies listeners of tool updates
   */
  private notifyToolsUpdated(): void {
    if (this.onToolsUpdated) {
      this.onToolsUpdated(this.getActiveTools());
    }
  }

  /**
   * Starts cleanup interval for expired tools
   */
  private startCleanupInterval(): void {
    this.cleanupInterval = setInterval(() => {
      this.performCleanup();
    }, this.config.cleanupIntervalMs);
  }

  /**
   * Performs cleanup of expired tools
   */
  private performCleanup(): void {
    const oldCount = Object.keys(this.lifecycleMap).length;
    this.lifecycleMap = cleanupExpiredTools(
      this.lifecycleMap, 
      this.config.autoRemovalTimeoutMs
    );
    
    if (Object.keys(this.lifecycleMap).length !== oldCount) {
      this.notifyToolsUpdated();
    }
  }

  /**
   * Clears all timeouts on cleanup
   */
  private clearAllTimeouts(): void {
    Object.values(this.lifecycleMap).forEach(entry => {
      if (entry.timeoutId) {
        clearTimeout(entry.timeoutId);
      }
    });
  }
}

/**
 * Creates tool tracking service instance
 */
export const createToolTrackingService = (
  config?: Partial<ToolTrackingConfig>,
  onToolsUpdated?: (tools: string[]) => void
): ToolTrackingService => {
  const fullConfig = { ...DEFAULT_TOOL_TRACKING_CONFIG, ...config };
  return new ToolTrackingService(fullConfig, onToolsUpdated);
};

/**
 * Singleton service instance management
 */
let globalToolTrackingService: ToolTrackingService | null = null;

export const getGlobalToolTracker = (): ToolTrackingService => {
  if (!globalToolTrackingService) {
    globalToolTrackingService = createToolTrackingService();
  }
  return globalToolTrackingService;
};

export const setGlobalToolTracker = (service: ToolTrackingService): void => {
  if (globalToolTrackingService) {
    globalToolTrackingService.cleanup();
  }
  globalToolTrackingService = service;
};