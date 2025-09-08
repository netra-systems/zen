/**
 * Unit test for ThreadOperationManager mock
 * 
 * Tests that the mock implementation actually executes operations
 */

import { ThreadOperationManager } from '@/lib/thread-operation-manager';

// Mock the lib module
jest.mock('@/lib/thread-operation-manager', () => require('../../__mocks__/lib/thread-operation-manager'));

describe('ThreadOperationManager Mock', () => {
  beforeEach(() => {
    ThreadOperationManager.reset();
  });

  it('should execute the provided function', async () => {
    const mockExecutor = jest.fn().mockResolvedValue({ success: true, threadId: 'test-123' });

    const result = await ThreadOperationManager.startOperation(
      'switch',
      'test-123',
      mockExecutor,
      {}
    );

    expect(mockExecutor).toHaveBeenCalled();
    expect(result.success).toBe(true);
    expect(result.threadId).toBe('test-123');
  });

  it('should track operation history', async () => {
    const mockExecutor = jest.fn().mockResolvedValue({ success: true, threadId: 'test-123' });

    await ThreadOperationManager.startOperation(
      'switch',
      'test-123',
      mockExecutor,
      {}
    );

    const history = ThreadOperationManager.getExecutionHistory();
    expect(history).toHaveLength(1);
    expect(history[0].type).toBe('switch');
    expect(history[0].threadId).toBe('test-123');
  });

  it('should handle operation failures', async () => {
    const testError = new Error('Test error');
    const mockExecutor = jest.fn().mockRejectedValue(testError);

    const result = await ThreadOperationManager.startOperation(
      'switch',
      'test-123',
      mockExecutor,
      {}
    );

    expect(result.success).toBe(false);
    expect(result.error).toBe(testError);
  });
});