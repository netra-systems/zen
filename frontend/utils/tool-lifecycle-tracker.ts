// Tool lifecycle tracking utilities - 25-line functions max
// Manages tool start/end times, timeouts, and deduplication

export interface ToolLifecycleEntry {
  name: string;
  startTime: number;
  endTime?: number;
  isActive: boolean;
  timeoutId?: NodeJS.Timeout;
}

export interface ToolLifecycleMap {
  [toolName: string]: ToolLifecycleEntry;
}

/**
 * Creates a new tool lifecycle entry
 */
export const createToolEntry = (
  name: string, 
  startTime: number = Date.now()
): ToolLifecycleEntry => {
  return {
    name,
    startTime,
    isActive: true
  };
};

/**
 * Marks tool as completed with end time
 */
export const completeToolEntry = (
  entry: ToolLifecycleEntry, 
  endTime: number = Date.now()
): ToolLifecycleEntry => {
  clearTimeout(entry.timeoutId);
  return { ...entry, endTime, isActive: false, timeoutId: undefined };
};

/**
 * Checks if tool has expired based on timeout
 */
export const isToolExpired = (
  entry: ToolLifecycleEntry, 
  timeoutMs: number = 30000
): boolean => {
  const now = Date.now();
  return entry.isActive && (now - entry.startTime) > timeoutMs;
};

/**
 * Gets currently active tool names
 */
export const getActiveToolNames = (lifecycleMap: ToolLifecycleMap): string[] => {
  return Object.values(lifecycleMap)
    .filter(entry => entry.isActive)
    .map(entry => entry.name);
};

/**
 * Adds tool with auto-removal timeout
 */
export const addToolWithTimeout = (
  lifecycleMap: ToolLifecycleMap,
  toolName: string,
  onTimeout: (toolName: string) => void,
  timeoutMs: number = 30000
): ToolLifecycleMap => {
  const entry = createToolEntry(toolName);
  const timeoutId = setTimeout(() => onTimeout(toolName), timeoutMs);
  
  return {
    ...lifecycleMap,
    [toolName]: { ...entry, timeoutId }
  };
};

/**
 * Removes tool from lifecycle tracking
 */
export const removeToolFromLifecycle = (
  lifecycleMap: ToolLifecycleMap,
  toolName: string
): ToolLifecycleMap => {
  const { [toolName]: removedTool, ...remaining } = lifecycleMap;
  if (removedTool?.timeoutId) {
    clearTimeout(removedTool.timeoutId);
  }
  return remaining;
};

/**
 * Cleanup expired tools from lifecycle map
 */
export const cleanupExpiredTools = (
  lifecycleMap: ToolLifecycleMap,
  timeoutMs: number = 30000
): ToolLifecycleMap => {
  const cleaned: ToolLifecycleMap = {};
  
  Object.entries(lifecycleMap).forEach(([name, entry]) => {
    if (!isToolExpired(entry, timeoutMs)) {
      cleaned[name] = entry;
    } else if (entry.timeoutId) {
      clearTimeout(entry.timeoutId);
    }
  });
  
  return cleaned;
};