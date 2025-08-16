// Tool lifecycle integration test
// Tests the complete tool lifecycle from WebSocket events to UI display

import { renderHook, act } from '@testing-library/react';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { 
  handleToolExecutingEnhanced,
  handleToolCompletedEnhanced 
} from '@/store/websocket-tool-handlers-enhanced';
import type { UnifiedWebSocketEvent } from '@/types/websocket-event-types';

describe('Tool Lifecycle Integration', () => {
  let store: ReturnType<typeof useUnifiedChatStore>;

  beforeEach(() => {
    const { result } = renderHook(() => useUnifiedChatStore());
    store = result.current;
    
    // Reset store state
    act(() => {
      store.resetLayers();
    });
  });

  it('should handle complete tool lifecycle: start -> display -> timeout -> cleanup', async () => {
    // Initialize fast layer data
    act(() => {
      store.updateFastLayer({
        agentName: 'Test Agent',
        runId: 'test-run-123',
        timestamp: Date.now(),
        activeTools: [],
        toolStatuses: []
      });
    });

    // Simulate tool_executing event
    const toolExecutingEvent: UnifiedWebSocketEvent = {
      type: 'tool_executing',
      payload: {
        tool_name: 'data_analyzer',
        agent_id: 'test-agent',
        timestamp: Date.now()
      }
    };

    act(() => {
      handleToolExecutingEnhanced(
        toolExecutingEvent,
        store,
        (partial) => {
          if (partial.fastLayerData) {
            store.updateFastLayer(partial.fastLayerData);
          }
        }
      );
    });

    // Re-fetch store state after update
    const { result: updatedResult } = renderHook(() => useUnifiedChatStore());
    const updatedStore = updatedResult.current;

    // Verify tool was added
    expect(updatedStore.fastLayerData?.activeTools).toContain('data_analyzer');
    expect(updatedStore.fastLayerData?.toolStatuses).toHaveLength(1);
    expect(updatedStore.fastLayerData?.toolStatuses?.[0].name).toBe('data_analyzer');
    expect(updatedStore.fastLayerData?.toolStatuses?.[0].isActive).toBe(true);

    // Simulate tool_completed event
    const toolCompletedEvent: UnifiedWebSocketEvent = {
      type: 'tool_completed',
      payload: {
        tool_name: 'data_analyzer',
        agent_id: 'test-agent',
        result: { success: true }
      }
    };

    act(() => {
      handleToolCompletedEnhanced(
        toolCompletedEvent,
        store,
        (partial) => store.updateFastLayer(partial.fastLayerData)
      );
    });

    // Verify tool was removed
    expect(store.fastLayerData?.activeTools).not.toContain('data_analyzer');
    expect(store.fastLayerData?.toolStatuses).toHaveLength(0);
  });

  it('should prevent duplicate tools from being added', () => {
    // Initialize fast layer data
    act(() => {
      store.updateFastLayer({
        agentName: 'Test Agent',
        runId: 'test-run-123',
        timestamp: Date.now(),
        activeTools: [],
        toolStatuses: []
      });
    });

    const toolEvent: UnifiedWebSocketEvent = {
      type: 'tool_executing',
      payload: {
        tool_name: 'duplicate_tool',
        agent_id: 'test-agent',
        timestamp: Date.now()
      }
    };

    // Add tool twice
    act(() => {
      handleToolExecutingEnhanced(toolEvent, store, (partial) => store.updateFastLayer(partial.fastLayerData));
      handleToolExecutingEnhanced(toolEvent, store, (partial) => store.updateFastLayer(partial.fastLayerData));
    });

    // Should only have one instance
    const activeToolCount = store.fastLayerData?.activeTools?.filter(
      tool => tool === 'duplicate_tool'
    ).length;
    
    expect(activeToolCount).toBe(1);
    expect(store.fastLayerData?.toolStatuses).toHaveLength(1);
  });

  it('should handle multiple tools simultaneously', () => {
    // Initialize fast layer data
    act(() => {
      store.updateFastLayer({
        agentName: 'Test Agent',
        runId: 'test-run-123',
        timestamp: Date.now(),
        activeTools: [],
        toolStatuses: []
      });
    });

    const tools = ['tool1', 'tool2', 'tool3'];
    
    // Start multiple tools
    tools.forEach(toolName => {
      const event: UnifiedWebSocketEvent = {
        type: 'tool_executing',
        payload: {
          tool_name: toolName,
          agent_id: 'test-agent',
          timestamp: Date.now()
        }
      };

      act(() => {
        handleToolExecutingEnhanced(event, store, (partial) => store.updateFastLayer(partial.fastLayerData));
      });
    });

    // Verify all tools are active
    expect(store.fastLayerData?.activeTools).toHaveLength(3);
    expect(store.fastLayerData?.toolStatuses).toHaveLength(3);
    
    tools.forEach(toolName => {
      expect(store.fastLayerData?.activeTools).toContain(toolName);
    });

    // Complete one tool
    const completeEvent: UnifiedWebSocketEvent = {
      type: 'tool_completed',
      payload: {
        tool_name: 'tool2',
        agent_id: 'test-agent'
      }
    };

    act(() => {
      handleToolCompletedEnhanced(completeEvent, store, (partial) => store.updateFastLayer(partial.fastLayerData));
    });

    // Verify tool2 was removed, others remain
    expect(store.fastLayerData?.activeTools).toHaveLength(2);
    expect(store.fastLayerData?.activeTools).toContain('tool1');
    expect(store.fastLayerData?.activeTools).toContain('tool3');
    expect(store.fastLayerData?.activeTools).not.toContain('tool2');
  });

  it('should maintain backward compatibility with legacy activeTools array', () => {
    // Test that enhanced handlers work with legacy data structure
    act(() => {
      store.updateFastLayer({
        agentName: 'Test Agent',
        runId: 'test-run-123',
        timestamp: Date.now(),
        activeTools: ['existing_tool'],
        // No toolStatuses array (legacy mode)
      });
    });

    const toolEvent: UnifiedWebSocketEvent = {
      type: 'tool_executing',
      payload: {
        tool_name: 'new_tool',
        agent_id: 'test-agent',
        timestamp: Date.now()
      }
    };

    act(() => {
      handleToolExecutingEnhanced(toolEvent, store, (partial) => store.updateFastLayer(partial.fastLayerData));
    });

    // Should add to both activeTools and toolStatuses
    expect(store.fastLayerData?.activeTools).toContain('new_tool');
    expect(store.fastLayerData?.toolStatuses).toHaveLength(1);
    expect(store.fastLayerData?.toolStatuses?.[0].name).toBe('new_tool');
  });
});