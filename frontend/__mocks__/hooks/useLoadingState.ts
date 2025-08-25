/**
 * Mock implementation of useLoadingState hook
 * Used in tests to provide controlled loading state behavior
 */

import { UseLoadingStateResult } from '../../hooks/useLoadingState';
import { ChatLoadingState } from '../../types/loading-state';

// Default mock return value - ready state with no loading
export const mockUseLoadingStateReturnValue: UseLoadingStateResult = {
  loadingState: ChatLoadingState.READY,
  shouldShowLoading: false,
  shouldShowEmptyState: true,
  shouldShowExamplePrompts: true,
  loadingMessage: 'Ready',
  isInitialized: true,
};

// Mock function that can be overridden in tests
export const useLoadingState = jest.fn().mockReturnValue(mockUseLoadingStateReturnValue);

export default { useLoadingState };