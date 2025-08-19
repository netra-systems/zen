/**
 * Test utilities for ChatComponents tests
 * Provides reusable utility functions for message list testing
 */

import React from 'react';
import { render } from '@testing-library/react';

// Helper to create test messages
export const createTestMessages = (count: number) => {
  return Array.from({ length: count }, (_, i) => ({
    id: `msg-${i}`,
    content: `Message ${i}`,
    timestamp: new Date().toISOString(),
    role: 'user',
    displayed_to_user: true,
  }));
};

// Helper to setup store with messages
export const setupStoreWithMessages = (messages: any[], useUnifiedChatStore: jest.Mock) => {
  useUnifiedChatStore.mockReturnValue({
    messages,
    isProcessing: false,
    isThreadLoading: false,
    currentRunId: null,
  });
};

// Helper to measure render performance
export const measureRenderTime = (Component: React.ComponentType) => {
  const startTime = performance.now();
  const result = render(<Component />);
  const renderTime = performance.now() - startTime;
  return { result, renderTime };
};

// Helper to verify performance within limits
export const expectPerformanceWithinLimit = (renderTime: number, maxTime: number = 30000) => {
  expect(renderTime).toBeLessThan(maxTime);
};