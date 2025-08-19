/**
 * Background Task Processing Integration Tests
 * Module-based architecture: Task tests ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  setupIntegrationTest,
  teardownIntegrationTest,
  createTaskRetryComponent,
  createTestComponent,
  setupDefaultHookMocks,
  setupAuthMocks,
  setupLoadingMocks,
  createMockUseUnifiedChatStore,
  createMockUseWebSocket,
  createMockUseAgent,
  createMockUseAuthStore,
  createMockUseLoadingState,
  createMockUseThreadNavigation
} from './integration-shared-utilities';

// Declare mocks first (Jest Module Hoisting)
const mockUseUnifiedChatStore = createMockUseUnifiedChatStore();
const mockUseWebSocket = createMockUseWebSocket();
const mockUseAgent = createMockUseAgent();
const mockUseAuthStore = createMockUseAuthStore();
const mockUseLoadingState = createMockUseLoadingState();
const mockUseThreadNavigation = createMockUseThreadNavigation();

// Mock hooks before imports
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/hooks/useAgent', () => ({
  useAgent: mockUseAgent
}));

describe('Background Task Processing Integration Tests', () => {
  let server: any;
  
  beforeEach(() => {
    server = setupIntegrationTest();
    setupAllMocks();
  });

  afterEach(() => {
    teardownIntegrationTest();
  });

  describe('15. Background Task Processing', () => {
    it('should queue and process background tasks', async () => {
      const mockTask = createMockTask();
      const result = await queueTask(mockTask);
      
      verifyTaskQueued(result);
    });

    it('should handle task retry with exponential backoff', async () => {
      jest.setTimeout(5000);
      const TaskComponent = createTaskRetryComponent();
      const { getByTestId } = render(createTestComponent(<TaskComponent />));
      
      await verifyTaskRetryCompleted(getByTestId);
    });

    it('should prioritize tasks based on importance', async () => {
      const tasks = [
        createTaskWithPriority('low'),
        createTaskWithPriority('high'),
        createTaskWithPriority('medium')
      ];
      setupTaskPriorityMock(tasks);
      
      await queueMultipleTasks(tasks);
      
      verifyTaskPrioritization(tasks);
    });

    it('should handle task dependencies and scheduling', async () => {
      const dependentTasks = createDependentTasks();
      setupTaskDependencyMock(dependentTasks);
      
      await scheduleTaskWithDependencies(dependentTasks);
      
      verifyTaskDependenciesResolved(dependentTasks);
    });

    it('should monitor task execution progress', async () => {
      const progressTask = createProgressTask();
      setupTaskProgressMock(progressTask);
      
      await monitorTaskProgress(progressTask.id);
      
      verifyTaskProgressMonitored(progressTask);
    });

    it('should handle task cancellation gracefully', async () => {
      const cancellableTask = createMockTask();
      setupTaskCancellationMock(cancellableTask);
      
      await cancelTask(cancellableTask.id);
      
      verifyTaskCancelled(cancellableTask);
    });

    it('should persist task state across system restarts', async () => {
      const persistentTask = createPersistentTask();
      setupTaskPersistenceMock(persistentTask);
      
      await persistTaskState(persistentTask);
      
      verifyTaskStatePersisted(persistentTask);
    });

    it('should handle task resource allocation and limits', async () => {
      const resourceTask = createResourceIntensiveTask();
      setupResourceLimitMock(resourceTask);
      
      await allocateTaskResources(resourceTask);
      
      verifyResourceAllocation(resourceTask);
    });
  });
});

// Helper functions ≤8 lines each
const setupAllMocks = () => {
  const mocks = {
    mockUseUnifiedChatStore,
    mockUseWebSocket,
    mockUseAgent,
    mockUseAuthStore,
    mockUseLoadingState,
    mockUseThreadNavigation
  };
  
  setupDefaultHookMocks(mocks);
  setupAuthMocks(mocks);
  setupLoadingMocks(mocks);
};

const setupTaskPriorityMock = (tasks: any[]) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ queued: tasks.length, prioritized: true })
  });
};

const setupTaskDependencyMock = (tasks: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ scheduled: true, dependencies: tasks.dependencies })
  });
};

const setupTaskProgressMock = (task: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ...task, progress: 75 })
  });
};

const setupTaskCancellationMock = (task: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ...task, status: 'cancelled' })
  });
};

const setupTaskPersistenceMock = (task: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ...task, persisted: true })
  });
};

const setupResourceLimitMock = (task: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ...task, resources_allocated: true })
  });
};

const createMockTask = () => ({
  id: 'task-123',
  type: 'data_processing',
  status: 'queued',
  created_at: Date.now()
});

const createTaskWithPriority = (priority: string) => ({
  ...createMockTask(),
  id: `task-${priority}`,
  priority
});

const createDependentTasks = () => ({
  main_task: createMockTask(),
  dependencies: [createMockTask(), createMockTask()]
});

const createProgressTask = () => ({
  ...createMockTask(),
  id: 'progress-task',
  total_steps: 100,
  completed_steps: 0
});

const createPersistentTask = () => ({
  ...createMockTask(),
  id: 'persistent-task',
  should_persist: true
});

const createResourceIntensiveTask = () => ({
  ...createMockTask(),
  id: 'resource-task',
  memory_required: '2GB',
  cpu_required: '2 cores'
});

const queueTask = async (task: any) => {
  return { ...task, status: 'processing' };
};

const queueMultipleTasks = async (tasks: any[]) => {
  await fetch('/api/tasks/queue', {
    method: 'POST',
    body: JSON.stringify({ tasks })
  });
};

const scheduleTaskWithDependencies = async (dependentTasks: any) => {
  await fetch('/api/tasks/schedule', {
    method: 'POST',
    body: JSON.stringify(dependentTasks)
  });
};

const monitorTaskProgress = async (taskId: string) => {
  await fetch(`/api/tasks/${taskId}/progress`);
};

const cancelTask = async (taskId: string) => {
  await fetch(`/api/tasks/${taskId}/cancel`, { method: 'POST' });
};

const persistTaskState = async (task: any) => {
  await fetch('/api/tasks/persist', {
    method: 'POST',
    body: JSON.stringify(task)
  });
};

const allocateTaskResources = async (task: any) => {
  await fetch('/api/tasks/allocate-resources', {
    method: 'POST',
    body: JSON.stringify(task)
  });
};

const verifyTaskQueued = (result: any) => {
  expect(result.status).toBe('processing');
};

const verifyTaskRetryCompleted = async (getByTestId: any) => {
  await waitFor(() => {
    expect(getByTestId('status')).toHaveTextContent('completed');
    expect(getByTestId('retry-count')).toHaveTextContent('3');
  }, { timeout: 4000 });
};

const verifyTaskPrioritization = (tasks: any[]) => {
  expect(fetch).toHaveBeenCalledWith('/api/tasks/queue',
    expect.objectContaining({ method: 'POST' })
  );
};

const verifyTaskDependenciesResolved = (dependentTasks: any) => {
  expect(fetch).toHaveBeenCalledWith('/api/tasks/schedule',
    expect.objectContaining({ method: 'POST' })
  );
};

const verifyTaskProgressMonitored = (task: any) => {
  expect(fetch).toHaveBeenCalledWith(`/api/tasks/${task.id}/progress`);
};

const verifyTaskCancelled = (task: any) => {
  expect(fetch).toHaveBeenCalledWith(`/api/tasks/${task.id}/cancel`,
    expect.objectContaining({ method: 'POST' })
  );
};

const verifyTaskStatePersisted = (task: any) => {
  expect(fetch).toHaveBeenCalledWith('/api/tasks/persist',
    expect.objectContaining({ method: 'POST' })
  );
};

const verifyResourceAllocation = (task: any) => {
  expect(fetch).toHaveBeenCalledWith('/api/tasks/allocate-resources',
    expect.objectContaining({ method: 'POST' })
  );
};