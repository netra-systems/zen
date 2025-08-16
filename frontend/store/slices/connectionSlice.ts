import type { StateCreator } from 'zustand';
import type { ConnectionState } from './types';

export const createConnectionSlice: StateCreator<
  ConnectionState,
  [],
  [],
  ConnectionState
> = (set) => ({
  isConnected: false,
  connectionError: null,

  setConnectionStatus: (isConnected, error) => set({
    isConnected,
    connectionError: error || null
  })
});