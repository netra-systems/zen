import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { ied tool lifecycle integration test
// Tests basic tool tracking functionality

import { 
  createToolExecutionStatus,
  updateToolExecutionStatuses,
  removeToolFromStatuses,
  getActiveToolsFromStatuses
} from '@/store/websocket-tool-handlers-enhanced';
import type { ToolExecutionStatus } from '@/types/layer-types';

describe('Tool Lifecycle Integration - Simplified', () => {
    jest.setTimeout(10000);
  describe('Tool Status Management', () => {
      jest.setTimeout(10000);
    it('should create and track tool status', () => {
      const tool = createToolExecutionStatus('analyzer', Date.now());
      
      expect(tool.name).toBe('analyzer');
      expect(tool.isActive).toBe(true);
      expect(tool.startTime).toBeDefined();
    });

    it('should update tool statuses array correctly', () => {
      const statuses: ToolExecutionStatus[] = [];
      const tool1 = createToolExecutionStatus('tool1', Date.now());
      
      const updated1 = updateToolExecutionStatuses(statuses, tool1);
      expect(updated1).toHaveLength(1);
      expect(updated1[0].name).toBe('tool1');
      
      // Add another tool
      const tool2 = createToolExecutionStatus('tool2', Date.now());
      const updated2 = updateToolExecutionStatuses(updated1, tool2);
      expect(updated2).toHaveLength(2);
      
      // Update existing tool (should replace)
      const tool1Updated = createToolExecutionStatus('tool1', Date.now() + 1000);
      const updated3 = updateToolExecutionStatuses(updated2, tool1Updated);
      expect(updated3).toHaveLength(2);
      expect(updated3.find(t => t.name === 'tool1')?.startTime)
        .toBe(tool1Updated.startTime);
    });

    it('should remove tools correctly', () => {
      const statuses: ToolExecutionStatus[] = [
        createToolExecutionStatus('tool1', Date.now()),
        createToolExecutionStatus('tool2', Date.now()),
        createToolExecutionStatus('tool3', Date.now())
      ];
      
      const afterRemove = removeToolFromStatuses(statuses, 'tool2');
      expect(afterRemove).toHaveLength(2);
      expect(afterRemove.map(s => s.name)).toEqual(['tool1', 'tool3']);
    });

    it('should convert to active tools array for legacy support', () => {
      const statuses: ToolExecutionStatus[] = [
        { name: 'tool1', startTime: Date.now(), isActive: true },
        { name: 'tool2', startTime: Date.now(), isActive: false },
        { name: 'tool3', startTime: Date.now(), isActive: true }
      ];
      
      const activeTools = getActiveToolsFromStatuses(statuses);
      expect(activeTools).toEqual(['tool1', 'tool3']);
    });
  });

  describe('Tool Deduplication', () => {
      jest.setTimeout(10000);
    it('should prevent duplicate tools in statuses', () => {
      let statuses: ToolExecutionStatus[] = [];
      
      // Add tool once
      const tool = createToolExecutionStatus('duplicate', Date.now());
      statuses = updateToolExecutionStatuses(statuses, tool);
      expect(statuses).toHaveLength(1);
      
      // Try to add same tool again
      const toolAgain = createToolExecutionStatus('duplicate', Date.now() + 1000);
      statuses = updateToolExecutionStatuses(statuses, toolAgain);
      
      // Should still have only one, but updated
      expect(statuses).toHaveLength(1);
      expect(statuses[0].startTime).toBe(toolAgain.startTime);
    });

    it('should handle similar but different tool names correctly', () => {
      let statuses: ToolExecutionStatus[] = [];
      
      // Add tools with similar names
      statuses = updateToolExecutionStatuses(statuses, createToolExecutionStatus('tool', Date.now()));
      statuses = updateToolExecutionStatuses(statuses, createToolExecutionStatus('tool2', Date.now()));
      statuses = updateToolExecutionStatuses(statuses, createToolExecutionStatus('tool_sub', Date.now()));
      
      expect(statuses).toHaveLength(3);
      expect(statuses.map(s => s.name).sort()).toEqual(['tool', 'tool2', 'tool_sub']);
    });
  });
});