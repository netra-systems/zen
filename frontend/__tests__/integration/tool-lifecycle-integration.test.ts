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
  let hookResult: any;

  beforeEach(() => {
    // Get fresh store instance
    hookResult = renderHook(() => useUnifiedChatStore());
    store = hookResult.result.current;
    
    // Reset store state completely
    act(() => {
      store.resetLayers();
      // Also reset agent tracking and optimistic messages
      store.resetAgentTracking();
      store.clearOptimisticMessages();
      store.clearMessages();
    });
  });

  it('should handle complete tool lifecycle: start -> display -> timeout -> cleanup', async () => {
    // Get fresh store for this test
    const { result } = renderHook(() => useUnifiedChatStore());
    const freshStore = result.current;
    
    // Initialize fast layer data
    act(() => {
      freshStore.updateFastLayer({
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
        freshStore,
        (partial) => {
          if (partial.fastLayerData) {
            freshStore.updateFastLayer(partial.fastLayerData);
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
        freshStore,
        (partial) => {
          if (partial.fastLayerData) {
            freshStore.updateFastLayer(partial.fastLayerData);
          }
        }
      );
    });

    // Get final store state
    const { result: finalResult } = renderHook(() => useUnifiedChatStore());
    const finalStore = finalResult.current;

    // Verify tool was removed
    expect(finalStore.fastLayerData?.activeTools).not.toContain('data_analyzer');
    expect(finalStore.fastLayerData?.toolStatuses).toHaveLength(0);
  });

  it('should prevent duplicate tools from being added', () => {
    // Get fresh store for this test
    const { result } = renderHook(() => useUnifiedChatStore());
    const freshStore = result.current;
    
    // Initialize fast layer data
    act(() => {
      freshStore.updateFastLayer({
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
      handleToolExecutingEnhanced(toolEvent, freshStore, (partial) => {
        if (partial.fastLayerData) {
          freshStore.updateFastLayer(partial.fastLayerData);
        }
      });
      handleToolExecutingEnhanced(toolEvent, freshStore, (partial) => {
        if (partial.fastLayerData) {
          freshStore.updateFastLayer(partial.fastLayerData);
        }
      });
    });

    // Get updated store state
    const { result: updatedResult } = renderHook(() => useUnifiedChatStore());
    const updatedStore = updatedResult.current;

    // Should only have one instance
    const activeToolCount = updatedStore.fastLayerData?.activeTools?.filter(
      tool => tool === 'duplicate_tool'
    ).length;
    
    expect(activeToolCount).toBe(1);
    expect(updatedStore.fastLayerData?.toolStatuses).toHaveLength(1);
  });

  it('should handle multiple tools simultaneously', () => {
    // Get fresh store for this test
    const { result } = renderHook(() => useUnifiedChatStore());
    const freshStore = result.current;
    
    // Initialize fast layer data
    act(() => {
      freshStore.updateFastLayer({
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
        handleToolExecutingEnhanced(event, freshStore, (partial) => {
          if (partial.fastLayerData) {
            freshStore.updateFastLayer(partial.fastLayerData);
          }
        });
      });
    });

    // Get updated store state
    const { result: afterAddResult } = renderHook(() => useUnifiedChatStore());
    const afterAddStore = afterAddResult.current;

    // Verify all tools are active
    expect(afterAddStore.fastLayerData?.activeTools).toHaveLength(3);
    expect(afterAddStore.fastLayerData?.toolStatuses).toHaveLength(3);
    
    tools.forEach(toolName => {
      expect(afterAddStore.fastLayerData?.activeTools).toContain(toolName);
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
      handleToolCompletedEnhanced(completeEvent, freshStore, (partial) => {
        if (partial.fastLayerData) {
          freshStore.updateFastLayer(partial.fastLayerData);
        }
      });
    });

    // Get final store state
    const { result: finalResult } = renderHook(() => useUnifiedChatStore());
    const finalStore = finalResult.current;

    // Verify tool2 was removed, others remain
    expect(finalStore.fastLayerData?.activeTools).toHaveLength(2);
    expect(finalStore.fastLayerData?.activeTools).toContain('tool1');
    expect(finalStore.fastLayerData?.activeTools).toContain('tool3');
    expect(finalStore.fastLayerData?.activeTools).not.toContain('tool2');
  });

  it('should maintain backward compatibility with legacy activeTools array', () => {
    // Get fresh store for this test
    const { result } = renderHook(() => useUnifiedChatStore());
    const freshStore = result.current;
    
    // Test that enhanced handlers work with legacy data structure
    act(() => {
      freshStore.updateFastLayer({
        agentName: 'Test Agent',
        runId: 'test-run-123',
        timestamp: Date.now(),
        activeTools: ['existing_tool'],
        toolStatuses: []
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
      handleToolExecutingEnhanced(toolEvent, freshStore, (partial) => {
        if (partial.fastLayerData) {
          freshStore.updateFastLayer(partial.fastLayerData);
        }
      });
    });

    // Get fresh store state after update
    const { result: updatedResult } = renderHook(() => useUnifiedChatStore());
    const updatedStore = updatedResult.current;

    // Should add to both activeTools and toolStatuses  
    expect(updatedStore.fastLayerData?.activeTools).toContain('new_tool');
    expect(updatedStore.fastLayerData?.activeTools).toContain('existing_tool');
    expect(updatedStore.fastLayerData?.toolStatuses).toHaveLength(1);
    expect(updatedStore.fastLayerData?.toolStatuses?.[0].name).toBe('new_tool');
  });
});