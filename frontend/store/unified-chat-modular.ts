import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { UnifiedChatState } from '@/types/unified-chat';
import {
  createLayerDataSlice,
  createMessageSlice,
  createAgentTrackingSlice,
  createThreadSlice,
  createConnectionSlice,
  createSubAgentSlice,
  createPerformanceSlice,
  createWebSocketSlice,
  type LayerDataState,
  type MessageState,
  type AgentTrackingState,
  type ThreadSliceState,
  type ConnectionState,
  type SubAgentState,
  type PerformanceState
} from './slices';

// Combined state interface
interface ModularUnifiedChatState extends 
  LayerDataState,
  MessageState,
  AgentTrackingState,
  ThreadSliceState,
  ConnectionState,
  SubAgentState,
  PerformanceState,
  UnifiedChatState {
  handleWebSocketEvent: (event: any) => void;
}

export const useUnifiedChatStoreModular = create<ModularUnifiedChatState>()(
  devtools(
    (...args) => ({
      // Combine all slices
      ...createLayerDataSlice(...args),
      ...createMessageSlice(...args),
      ...createAgentTrackingSlice(...args),
      ...createThreadSlice(...args),
      ...createConnectionSlice(...args),
      ...createSubAgentSlice(...args),
      ...createPerformanceSlice(...args),
      ...createWebSocketSlice(...args),
    }),
    {
      name: 'unified-chat-store-modular',
    }
  )
);