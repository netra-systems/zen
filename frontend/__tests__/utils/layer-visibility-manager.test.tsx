import {
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
AL Layer Visibility Manager Tests
 * BVJ: Prevents $12K MRR loss from UI rendering failures
 */

import {
  calculateEnhancedLayerVisibility,
  debugLayerVisibility,
  type LayerVisibilityConfig
} from '@/utils/layer-visibility-manager';
import { logger } from '@/lib/logger';

describe('Layer Visibility Manager - REAL Tests', () => {
    jest.setTimeout(10000);
  let loggerSpy: {
    group: jest.SpyInstance;
    debug: jest.SpyInstance;
    groupEnd: jest.SpyInstance;
  };

  beforeEach(() => {
    loggerSpy = {
      group: jest.spyOn(logger, 'group'),
      debug: jest.spyOn(logger, 'debug'),
      groupEnd: jest.spyOn(logger, 'groupEnd')
    };
  });

  afterEach(() => {
    Object.values(loggerSpy).forEach(spy => spy.mockRestore());
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Fast Layer Visibility', () => {
      jest.setTimeout(10000);
    it('shows fast layer when processing', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: true
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showFastLayer).toBe(true);
      expect(result.fastLayerReason).toBe('processing');
    });

    it('shows fast layer with active tools', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: {
          agentName: 'TestAgent',
          activeTools: ['tool1', 'tool2'],
          toolStatuses: [],
          taskId: 'task-123',
          status: 'running',
          startTime: Date.now()
        },
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: false
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showFastLayer).toBe(true);
      expect(result.fastLayerReason).toBe('active_tools');
    });

    it('persists fast layer with recent tool activity', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: {
          agentName: 'Agent',
          activeTools: [],
          toolStatuses: [{
            tool: 'test-tool',
            isActive: false,
            startTime: Date.now() - 5000 // 5 seconds ago
          }],
          taskId: 'task-456',
          status: 'completed',
          startTime: Date.now() - 10000
        },
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: false
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showFastLayer).toBe(true);
      expect(result.fastLayerReason).toBe('active_tools');
    });
  });

  describe('Medium Layer Visibility', () => {
      jest.setTimeout(10000);
    it('shows medium layer with partial content', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: null,
        mediumLayerData: {
          thought: '',
          partialContent: 'Processing request...',
          stepNumber: 0,
          totalSteps: 0,
          messageId: 'msg-123'
        },
        slowLayerData: null,
        isProcessing: false
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showMediumLayer).toBe(true);
      expect(result.mediumLayerReason).toBe('partial_content');
    });

    it('shows medium layer with thought', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: null,
        mediumLayerData: {
          thought: 'Analyzing data patterns...',
          partialContent: '',
          stepNumber: 1,
          totalSteps: 3,
          messageId: 'msg-456'
        },
        slowLayerData: null,
        isProcessing: false
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showMediumLayer).toBe(true);
      expect(result.mediumLayerReason).toBe('thought');
    });

    it('shows medium layer with step progress', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: null,
        mediumLayerData: {
          thought: '',
          partialContent: '',
          stepNumber: 2,
          totalSteps: 5,
          messageId: 'msg-789'
        },
        slowLayerData: null,
        isProcessing: false
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showMediumLayer).toBe(true);
      expect(result.mediumLayerReason).toBe('step_progress');
    });
  });

  describe('Slow Layer Visibility', () => {
      jest.setTimeout(10000);
    it('shows slow layer with final report', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData: {
          finalReport: { summary: 'Task completed successfully' },
          completedAgents: [],
          totalDuration: 0,
          messageId: 'msg-final'
        },
        isProcessing: false
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showSlowLayer).toBe(true);
      expect(result.slowLayerReason).toBe('final_report');
    });

    it('shows slow layer with completed agents', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData: {
          finalReport: null,
          completedAgents: ['Agent1', 'Agent2'],
          totalDuration: 5000,
          messageId: 'msg-complete'
        },
        isProcessing: false
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showSlowLayer).toBe(true);
      expect(result.slowLayerReason).toBe('completed_agents');
    });

    it('shows slow layer with execution metrics', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData: {
          finalReport: null,
          completedAgents: [],
          totalDuration: 10000,
          messageId: 'msg-metrics'
        },
        isProcessing: false
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showSlowLayer).toBe(true);
      expect(result.slowLayerReason).toBe('execution_metrics');
    });
  });

  describe('Layer Persistence', () => {
      jest.setTimeout(10000);
    it('persists layers based on previous visibility', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: {
          agentName: 'PersistAgent',
          activeTools: [],
          toolStatuses: [],
          taskId: 'persist-task',
          status: 'idle',
          startTime: Date.now() - 60000
        },
        mediumLayerData: {
          thought: 'Previous thought',
          partialContent: '',
          stepNumber: 0,
          totalSteps: 0,
          messageId: 'persist-msg'
        },
        slowLayerData: {
          finalReport: { summary: 'Done' },
          completedAgents: [],
          totalDuration: 0,
          messageId: 'persist-slow'
        },
        isProcessing: false,
        previousVisibility: {
          showFastLayer: true,
          showMediumLayer: true,
          showSlowLayer: true,
          fastLayerReason: 'agent_data',
          mediumLayerReason: 'thought',
          slowLayerReason: 'final_report'
        }
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showFastLayer).toBe(true);
      expect(result.fastLayerReason).toBe('agent_data');
      expect(result.showMediumLayer).toBe(true);
      expect(result.showSlowLayer).toBe(true);
    });
  });

  describe('Debug Functionality', () => {
      jest.setTimeout(10000);
    it('logs debug information with logger groups', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: {
          agentName: 'DebugAgent',
          activeTools: ['debugTool'],
          toolStatuses: [],
          taskId: 'debug-task',
          status: 'running',
          startTime: Date.now()
        },
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: true
      };
      
      debugLayerVisibility(config);
      
      expect(loggerSpy.group).toHaveBeenCalledWith('Layer Visibility Debug');
      expect(loggerSpy.debug).toHaveBeenCalledTimes(4);
      expect(loggerSpy.debug).toHaveBeenCalledWith(
        'Fast Layer:',
        true,
        '-',
        'active_tools'
      );
      expect(loggerSpy.groupEnd).toHaveBeenCalled();
    });

    it('does not log in production', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';
      
      const config: LayerVisibilityConfig = {
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: false
      };
      
      debugLayerVisibility(config);
      
      expect(loggerSpy.group).not.toHaveBeenCalled();
      expect(loggerSpy.debug).not.toHaveBeenCalled();
      
      process.env.NODE_ENV = originalEnv;
    });
  });

  describe('Edge Cases', () => {
      jest.setTimeout(10000);
    it('handles all null data gracefully', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: null,
        mediumLayerData: null,
        slowLayerData: null,
        isProcessing: false
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showFastLayer).toBe(false);
      expect(result.showMediumLayer).toBe(false);
      expect(result.showSlowLayer).toBe(false);
      expect(result.fastLayerReason).toBe('no_data');
      expect(result.mediumLayerReason).toBe('no_content');
      expect(result.slowLayerReason).toBe('no_results');
    });

    it('handles empty strings and zero values', () => {
      const config: LayerVisibilityConfig = {
        fastLayerData: {
          agentName: '',
          activeTools: [],
          toolStatuses: [],
          taskId: '',
          status: '',
          startTime: 0
        },
        mediumLayerData: {
          thought: '   ',
          partialContent: '\n\t',
          stepNumber: 0,
          totalSteps: 0,
          messageId: ''
        },
        slowLayerData: {
          finalReport: null,
          completedAgents: [],
          totalDuration: 0,
          messageId: ''
        },
        isProcessing: false
      };
      
      const result = calculateEnhancedLayerVisibility(config);
      expect(result.showFastLayer).toBe(false);
      expect(result.showMediumLayer).toBe(false);
      expect(result.showSlowLayer).toBe(false);
    });
  });
});