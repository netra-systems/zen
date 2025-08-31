// Tool tracking service tests
// Testing the enhanced tool tracking service functionality

import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { ToolTrackingService,
  createToolTrackingService,
  DEFAULT_TOOL_TRACKING_CONFIG
} from '@/services/tool-tracking-service';

describe('ToolTrackingService', () => {
  setupAntiHang();
    jest.setTimeout(10000);
  let service: ToolTrackingService;
  let onToolsUpdated: jest.Mock;

  beforeEach(() => {
    jest.clearAllTimers();
    jest.useFakeTimers();
    onToolsUpdated = jest.fn();
    
    service = createToolTrackingService({
      autoRemovalTimeoutMs: 1000,
      cleanupIntervalMs: 500,
      maxActiveTools: 3
    }, onToolsUpdated);
  });

  afterEach(() => {
    service.cleanup();
    jest.useRealTimers();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
      cleanupAntiHang();
  });

  describe('startTool', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should start a new tool and notify listeners', () => {
      service.startTool('test-tool');
      
      expect(service.getActiveTools()).toContain('test-tool');
      expect(onToolsUpdated).toHaveBeenCalledWith(['test-tool']);
    });

    it('should not add duplicate tools', () => {
      service.startTool('test-tool');
      service.startTool('test-tool');
      
      const activeTools = service.getActiveTools();
      expect(activeTools.filter(tool => tool === 'test-tool')).toHaveLength(1);
    });

    it('should respect max active tools limit', () => {
      service.startTool('tool1');
      service.startTool('tool2');
      service.startTool('tool3');
      service.startTool('tool4'); // Should be ignored due to limit
      
      expect(service.getActiveTools()).toHaveLength(3);
      expect(service.getActiveTools()).not.toContain('tool4');
    });
  });

  describe('completeTool', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should complete a tool and notify listeners', () => {
      service.startTool('test-tool');
      onToolsUpdated.mockClear();
      
      service.completeTool('test-tool');
      
      expect(service.getActiveTools()).not.toContain('test-tool');
      expect(onToolsUpdated).toHaveBeenCalledWith([]);
    });

    it('should handle completing non-existent tool gracefully', () => {
      service.completeTool('non-existent-tool');
      
      expect(service.getActiveTools()).toEqual([]);
      expect(onToolsUpdated).toHaveBeenCalledWith([]);
    });
  });

  describe('auto-removal timeout', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should auto-remove tools after timeout', () => {
      service.startTool('test-tool');
      expect(service.getActiveTools()).toContain('test-tool');
      
      // Fast-forward past the timeout
      jest.advanceTimersByTime(1500);
      
      expect(service.getActiveTools()).not.toContain('test-tool');
      expect(onToolsUpdated).toHaveBeenCalledWith([]);
    });

    it('should not auto-remove manually completed tools', () => {
      service.startTool('test-tool');
      service.completeTool('test-tool');
      onToolsUpdated.mockClear();
      
      // Fast-forward past the timeout
      jest.advanceTimersByTime(1500);
      
      // Should not trigger additional callback
      expect(onToolsUpdated).not.toHaveBeenCalled();
    });
  });

  describe('cleanup interval', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should periodically cleanup expired tools', () => {
      service.startTool('tool1');
      
      // Fast-forward past cleanup interval but not tool timeout
      jest.advanceTimersByTime(600);
      
      // Tool should still be there (not expired yet)
      expect(service.getActiveTools()).toContain('tool1');
      
      // Fast-forward past tool timeout
      jest.advanceTimersByTime(500);
      
      // Now tool should be cleaned up
      expect(service.getActiveTools()).not.toContain('tool1');
    });
  });

  describe('service cleanup', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should cleanup all timeouts on service cleanup', () => {
      service.startTool('tool1');
      service.startTool('tool2');
      
      service.cleanup();
      
      // Fast-forward past timeout - tools should not be auto-removed
      // because cleanup cleared all timeouts
      jest.advanceTimersByTime(2000);
      
      // Service should still have tools (cleanup disabled)
      expect(service.getActiveTools()).toEqual(['tool1', 'tool2']);
    });
  });

  describe('configuration', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    it('should use default configuration when not provided', () => {
      const defaultService = createToolTrackingService();
      
      // Test that default config is used by checking behavior
      for (let i = 0; i < DEFAULT_TOOL_TRACKING_CONFIG.maxActiveTools + 1; i++) {
        defaultService.startTool(`tool${i}`);
      }
      
      expect(defaultService.getActiveTools()).toHaveLength(
        DEFAULT_TOOL_TRACKING_CONFIG.maxActiveTools
      );
      
      defaultService.cleanup();
    });

    it('should merge partial configuration with defaults', () => {
      const customService = createToolTrackingService({ maxActiveTools: 2 });
      
      customService.startTool('tool1');
      customService.startTool('tool2');
      customService.startTool('tool3'); // Should be ignored
      
      expect(customService.getActiveTools()).toHaveLength(2);
      
      customService.cleanup();
    });
  });
});