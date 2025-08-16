// Tool lifecycle tracker tests
// Testing the new tool lifecycle management functionality

import {
  createToolEntry,
  completeToolEntry,
  isToolExpired,
  getActiveToolNames,
  addToolWithTimeout,
  removeToolFromLifecycle,
  cleanupExpiredTools,
  type ToolLifecycleMap
} from '@/utils/tool-lifecycle-tracker';

describe('Tool Lifecycle Tracker', () => {
  let mockTimeoutId: NodeJS.Timeout;

  beforeEach(() => {
    jest.clearAllTimers();
    jest.useFakeTimers();
    mockTimeoutId = setTimeout(() => {}, 1000) as NodeJS.Timeout;
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('createToolEntry', () => {
    it('should create a new tool entry with default timestamp', () => {
      const entry = createToolEntry('test-tool');
      
      expect(entry.name).toBe('test-tool');
      expect(entry.isActive).toBe(true);
      expect(entry.startTime).toBeGreaterThan(0);
      expect(entry.endTime).toBeUndefined();
    });

    it('should create a tool entry with provided timestamp', () => {
      const customTime = 123456789;
      const entry = createToolEntry('test-tool', customTime);
      
      expect(entry.startTime).toBe(customTime);
    });
  });

  describe('completeToolEntry', () => {
    it('should mark tool entry as completed', () => {
      const entry = createToolEntry('test-tool');
      entry.timeoutId = mockTimeoutId;
      
      const completed = completeToolEntry(entry, 999999999);
      
      expect(completed.isActive).toBe(false);
      expect(completed.endTime).toBe(999999999);
      expect(completed.timeoutId).toBeUndefined();
    });
  });

  describe('isToolExpired', () => {
    it('should return false for non-expired tool', () => {
      const entry = createToolEntry('test-tool', Date.now() - 1000);
      
      const expired = isToolExpired(entry, 30000);
      
      expect(expired).toBe(false);
    });

    it('should return true for expired tool', () => {
      const entry = createToolEntry('test-tool', Date.now() - 60000);
      
      const expired = isToolExpired(entry, 30000);
      
      expect(expired).toBe(true);
    });

    it('should return false for inactive tool', () => {
      const entry = createToolEntry('test-tool', Date.now() - 60000);
      entry.isActive = false;
      
      const expired = isToolExpired(entry, 30000);
      
      expect(expired).toBe(false);
    });
  });

  describe('getActiveToolNames', () => {
    it('should return active tool names only', () => {
      const lifecycleMap: ToolLifecycleMap = {
        'tool1': createToolEntry('tool1'),
        'tool2': { ...createToolEntry('tool2'), isActive: false },
        'tool3': createToolEntry('tool3')
      };
      
      const activeTools = getActiveToolNames(lifecycleMap);
      
      expect(activeTools).toEqual(['tool1', 'tool3']);
    });

    it('should return empty array when no active tools', () => {
      const lifecycleMap: ToolLifecycleMap = {
        'tool1': { ...createToolEntry('tool1'), isActive: false }
      };
      
      const activeTools = getActiveToolNames(lifecycleMap);
      
      expect(activeTools).toEqual([]);
    });
  });

  describe('addToolWithTimeout', () => {
    it('should add tool with timeout callback', () => {
      const lifecycleMap: ToolLifecycleMap = {};
      const onTimeout = jest.fn();
      
      const updated = addToolWithTimeout(lifecycleMap, 'test-tool', onTimeout, 1000);
      
      expect(updated['test-tool']).toBeDefined();
      expect(updated['test-tool'].name).toBe('test-tool');
      expect(updated['test-tool'].isActive).toBe(true);
      expect(updated['test-tool'].timeoutId).toBeDefined();
    });
  });

  describe('removeToolFromLifecycle', () => {
    it('should remove tool and clear timeout', () => {
      const lifecycleMap: ToolLifecycleMap = {
        'tool1': { ...createToolEntry('tool1'), timeoutId: mockTimeoutId },
        'tool2': createToolEntry('tool2')
      };
      
      const updated = removeToolFromLifecycle(lifecycleMap, 'tool1');
      
      expect(updated['tool1']).toBeUndefined();
      expect(updated['tool2']).toBeDefined();
    });
  });

  describe('cleanupExpiredTools', () => {
    it('should remove expired tools', () => {
      const now = Date.now();
      const lifecycleMap: ToolLifecycleMap = {
        'fresh-tool': createToolEntry('fresh-tool', now - 1000),
        'expired-tool': createToolEntry('expired-tool', now - 60000),
        'another-fresh': createToolEntry('another-fresh', now - 5000)
      };
      
      const cleaned = cleanupExpiredTools(lifecycleMap, 30000);
      
      expect(cleaned['fresh-tool']).toBeDefined();
      expect(cleaned['another-fresh']).toBeDefined();
      expect(cleaned['expired-tool']).toBeUndefined();
    });
  });
});