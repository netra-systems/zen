// Simplified tool lifecycle integration test
// Tests basic tool tracking functionality

import { 
  createToolStatus,
  updateToolStatuses,
  removeToolFromStatuses,
  getActiveToolsFromStatuses
} from '@/store/websocket-tool-handlers-enhanced';
import type { ToolStatus } from '@/types/layer-types';

describe('Tool Lifecycle Integration - Simplified', () => {
  describe('Tool Status Management', () => {
    it('should create and track tool status', () => {
      const tool = createToolStatus('analyzer', Date.now());
      
      expect(tool.name).toBe('analyzer');
      expect(tool.isActive).toBe(true);
      expect(tool.startTime).toBeDefined();
    });

    it('should update tool statuses array correctly', () => {
      const statuses: ToolStatus[] = [];
      const tool1 = createToolStatus('tool1', Date.now());
      
      const updated1 = updateToolStatuses(statuses, tool1);
      expect(updated1).toHaveLength(1);
      expect(updated1[0].name).toBe('tool1');
      
      // Add another tool
      const tool2 = createToolStatus('tool2', Date.now());
      const updated2 = updateToolStatuses(updated1, tool2);
      expect(updated2).toHaveLength(2);
      
      // Update existing tool (should replace)
      const tool1Updated = createToolStatus('tool1', Date.now() + 1000);
      const updated3 = updateToolStatuses(updated2, tool1Updated);
      expect(updated3).toHaveLength(2);
      expect(updated3.find(t => t.name === 'tool1')?.startTime)
        .toBe(tool1Updated.startTime);
    });

    it('should remove tools correctly', () => {
      const statuses: ToolStatus[] = [
        createToolStatus('tool1', Date.now()),
        createToolStatus('tool2', Date.now()),
        createToolStatus('tool3', Date.now())
      ];
      
      const afterRemove = removeToolFromStatuses(statuses, 'tool2');
      expect(afterRemove).toHaveLength(2);
      expect(afterRemove.map(s => s.name)).toEqual(['tool1', 'tool3']);
    });

    it('should convert to active tools array for legacy support', () => {
      const statuses: ToolStatus[] = [
        { name: 'tool1', startTime: Date.now(), isActive: true },
        { name: 'tool2', startTime: Date.now(), isActive: false },
        { name: 'tool3', startTime: Date.now(), isActive: true }
      ];
      
      const activeTools = getActiveToolsFromStatuses(statuses);
      expect(activeTools).toEqual(['tool1', 'tool3']);
    });
  });

  describe('Tool Deduplication', () => {
    it('should prevent duplicate tools in statuses', () => {
      let statuses: ToolStatus[] = [];
      
      // Add tool once
      const tool = createToolStatus('duplicate', Date.now());
      statuses = updateToolStatuses(statuses, tool);
      expect(statuses).toHaveLength(1);
      
      // Try to add same tool again
      const toolAgain = createToolStatus('duplicate', Date.now() + 1000);
      statuses = updateToolStatuses(statuses, toolAgain);
      
      // Should still have only one, but updated
      expect(statuses).toHaveLength(1);
      expect(statuses[0].startTime).toBe(toolAgain.startTime);
    });

    it('should handle similar but different tool names correctly', () => {
      let statuses: ToolStatus[] = [];
      
      // Add tools with similar names
      statuses = updateToolStatuses(statuses, createToolStatus('tool', Date.now()));
      statuses = updateToolStatuses(statuses, createToolStatus('tool2', Date.now()));
      statuses = updateToolStatuses(statuses, createToolStatus('tool_sub', Date.now()));
      
      expect(statuses).toHaveLength(3);
      expect(statuses.map(s => s.name).sort()).toEqual(['tool', 'tool2', 'tool_sub']);
    });
  });
});