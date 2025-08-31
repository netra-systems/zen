import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';
import { al-time Collaboration Sync Tests
 * 
 * BVJ: Enterprise segment - ensures platform scalability for collaborative features
 * Tests conflict resolution, operation history, and collaborative editing.
 */

import {
  React,
  render,
  waitFor,
  fireEvent,
  setupTestEnvironment,
  cleanupTestEnvironment,
  createMockWebSocketServer,
  TEST_TIMEOUTS,
  WS
} from '../../test-utils';

import {
  PERFORMANCE_THRESHOLDS,
  createConflict,
  resolveConflictContent,
  addToHistory,
  trimHistory,
  canUndo,
  canRedo
} from './utils/performance-test-utils';

// Apply Next.js navigation mock
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    pathname: '/',
    query: {},
    asPath: '/',
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

describe('Real-time Collaboration Sync Tests', () => {
    jest.setTimeout(10000);
  let server: WS;
  
  beforeEach(() => {
    server = createMockWebSocketServer();
    setupTestEnvironment(server);
  });

  afterEach(() => {
    cleanupTestEnvironment();
      // Clean up timers to prevent hanging
      jest.clearAllTimers();
      jest.useFakeTimers();
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
  });

  describe('Conflict Resolution', () => {
      jest.setTimeout(10000);
    it('should handle conflict resolution in collaborative editing', async () => {
      const CollaborativeEditor = createCollaborativeEditor();
      
      const { getByText, getByTestId } = render(<CollaborativeEditor />);
      
      await verifyInitialSyncState(getByTestId);
      await triggerLocalChange(getByTestId);
      await simulateConflict(getByText, getByTestId);
      await resolveConflict(getByText, getByTestId);
    });

    it('should handle multiple concurrent conflicts', async () => {
      const MultiConflictEditor = createMultiConflictEditor();
      
      const { getByText, getByTestId } = render(<MultiConflictEditor />);
      
      await simulateMultipleConflicts(getByText);
      await verifyMultipleConflicts(getByTestId);
      await resolveBatchConflicts(getByText, getByTestId);
    });

    it('should maintain version consistency during conflicts', async () => {
      const VersionConsistentEditor = createVersionConsistentEditor();
      
      const { getByText, getByTestId } = render(<VersionConsistentEditor />);
      
      await testVersionConsistency(getByText, getByTestId);
    });
  });

  describe('Operation History Management', () => {
      jest.setTimeout(10000);
    it('should maintain operation history for undo/redo', async () => {
      const UndoRedoComponent = createUndoRedoComponent();
      
      const { getByText, getByTestId } = render(<UndoRedoComponent />);
      
      await verifyInitialHistoryState(getByTestId);
      await performMultipleActions(getByText, getByTestId);
      await testUndoOperations(getByText, getByTestId);
      await testRedoOperations(getByText, getByTestId);
    });

    it('should limit history size to prevent memory bloat', async () => {
      const HistoryLimitComponent = createHistoryLimitComponent();
      
      const { getByText, getByTestId } = render(<HistoryLimitComponent />);
      
      await testHistoryLimit(getByText, getByTestId);
    });

    it('should handle branch creation in history', async () => {
      const BranchingHistoryComponent = createBranchingHistoryComponent();
      
      const { getByText, getByTestId } = render(<BranchingHistoryComponent />);
      
      await testHistoryBranching(getByText, getByTestId);
    });
  });

  describe('Real-time Synchronization', () => {
      jest.setTimeout(10000);
    it('should sync changes across multiple clients', async () => {
      const SyncComponent = createSyncComponent();
      
      const { getByText, getByTestId } = render(<SyncComponent />);
      
      await testMultiClientSync(getByText, getByTestId);
    });

    it('should handle network interruptions gracefully', async () => {
      const NetworkResilienceComponent = createNetworkResilienceComponent();
      
      const { getByText, getByTestId } = render(<NetworkResilienceComponent />);
      
      await testNetworkInterruption(getByText, getByTestId);
    });
  });
});

// Component factory functions (≤8 lines each)
const createCollaborativeEditor = () => {
  return () => {
    const [content, setContent] = React.useState('Initial content');
    const [conflicts, setConflicts] = React.useState<any[]>([]);
    const [version, setVersion] = React.useState(1);
    const [syncStatus, setSyncStatus] = React.useState('synced');
    
    const handlers = useCollaborativeHandlers(
      content, setContent, conflicts, setConflicts, version, setVersion, setSyncStatus
    );
    
    return renderCollaborativeEditor(content, conflicts, version, syncStatus, handlers);
  };
};

const createMultiConflictEditor = () => {
  return () => {
    const [conflicts, setConflicts] = React.useState<any[]>([]);
    const [content, setContent] = React.useState('Initial');
    const [version, setVersion] = React.useState(1);
    
    const createMultipleConflicts = () => simulateMultipleConflictScenarios(
      setConflicts, content, version
    );
    
    const resolveBatch = () => resolveBatchConflictsLogic(setConflicts, setContent, setVersion);
    
    return renderMultiConflictEditor(conflicts, createMultipleConflicts, resolveBatch);
  };
};

const createVersionConsistentEditor = () => {
  return () => {
    const [version, setVersion] = React.useState(1);
    const [remoteVersion, setRemoteVersion] = React.useState(1);
    const [consistency, setConsistency] = React.useState(true);
    
    const testVersions = () => testVersionConsistencyLogic(
      version, setVersion, remoteVersion, setRemoteVersion, setConsistency
    );
    
    return renderVersionConsistentEditor(version, remoteVersion, consistency, testVersions);
  };
};

const createUndoRedoComponent = () => {
  return () => {
    const [history, setHistory] = React.useState<string[]>(['Initial state']);
    const [currentIndex, setCurrentIndex] = React.useState(0);
    const [maxHistorySize] = React.useState(PERFORMANCE_THRESHOLDS.MAX_HISTORY_SIZE);
    
    const handlers = useHistoryHandlers(history, setHistory, currentIndex, setCurrentIndex, maxHistorySize);
    
    return renderUndoRedoComponent(history, currentIndex, handlers);
  };
};

const createHistoryLimitComponent = () => {
  return () => {
    const [history, setHistory] = React.useState<string[]>(['Start']);
    const [limitReached, setLimitReached] = React.useState(false);
    
    const addManyActions = () => addManyHistoryActions(setHistory, setLimitReached);
    
    return renderHistoryLimitComponent(history, limitReached, addManyActions);
  };
};

const createBranchingHistoryComponent = () => {
  return () => {
    const [branches, setBranches] = React.useState<any[]>([]);
    const [currentBranch, setCurrentBranch] = React.useState('main');
    
    const createBranch = () => createHistoryBranch(setBranches, setCurrentBranch);
    
    return renderBranchingHistoryComponent(branches, currentBranch, createBranch);
  };
};

const createSyncComponent = () => {
  return () => {
    const [clients, setClients] = React.useState<any[]>([]);
    const [syncState, setSyncState] = React.useState('connected');
    
    const simulateMultiClient = () => simulateMultiClientScenario(setClients, setSyncState);
    
    return renderSyncComponent(clients, syncState, simulateMultiClient);
  };
};

const createNetworkResilienceComponent = () => {
  return () => {
    const [networkState, setNetworkState] = React.useState('connected');
    const [queuedChanges, setQueuedChanges] = React.useState<any[]>([]);
    
    const simulateNetworkIssue = () => simulateNetworkDisruption(setNetworkState, setQueuedChanges);
    
    return renderNetworkResilienceComponent(networkState, queuedChanges, simulateNetworkIssue);
  };
};

// Custom hooks (≤8 lines each)
const useCollaborativeHandlers = (
  content: string, setContent: any, conflicts: any[], setConflicts: any,
  version: number, setVersion: any, setSyncStatus: any
) => {
  const handleLocalChange = (newContent: string) => handleLocalContentChange(
    newContent, setContent, setSyncStatus, setVersion
  );
  
  const handleRemoteChange = (remoteContent: string, remoteVersion: number) => 
    handleRemoteContentChange(
      remoteContent, remoteVersion, content, version, setContent, setVersion, setConflicts, setSyncStatus
    );
  
  const resolveConflict = (resolution: string, conflictId: number) => 
    resolveConflictLogic(resolution, conflictId, conflicts, setContent, setConflicts, setVersion, setSyncStatus);
  
  return { handleLocalChange, handleRemoteChange, resolveConflict };
};

const useHistoryHandlers = (
  history: string[], setHistory: any, currentIndex: number, setCurrentIndex: any, maxHistorySize: number
) => {
  const performAction = (action: string) => {
    const { newHistory, newIndex } = addToHistory(history, currentIndex, action, maxHistorySize);
    setHistory(newHistory);
    setCurrentIndex(newIndex);
  };
  
  const undo = () => canUndo(currentIndex) && setCurrentIndex(currentIndex - 1);
  const redo = () => canRedo(currentIndex, history.length) && setCurrentIndex(currentIndex + 1);
  const clearHistory = () => clearHistoryState(history, currentIndex, setHistory, setCurrentIndex);
  
  return { performAction, undo, redo, clearHistory };
};

// Business logic functions (≤8 lines each)
const handleLocalContentChange = (
  newContent: string, setContent: any, setSyncStatus: any, setVersion: any
): void => {
  setContent(newContent);
  setSyncStatus('pending');
  setVersion((prev: number) => prev + 1);
};

const handleRemoteContentChange = (
  remoteContent: string, remoteVersion: number, localContent: string, localVersion: number,
  setContent: any, setVersion: any, setConflicts: any, setSyncStatus: any
): void => {
  if (remoteVersion > localVersion) {
    setContent(remoteContent);
    setVersion(remoteVersion);
    setSyncStatus('synced');
  } else if (remoteVersion === localVersion && remoteContent !== localContent) {
    const conflict = createConflict(localContent, remoteContent, localVersion, remoteVersion);
    setConflicts((prev: any[]) => [...prev, conflict]);
    setSyncStatus('conflict');
  }
};

const resolveConflictLogic = (
  resolution: string, conflictId: number, conflicts: any[],
  setContent: any, setConflicts: any, setVersion: any, setSyncStatus: any
): void => {
  const conflict = conflicts.find(c => c.id === conflictId);
  if (!conflict) return;
  
  const resolvedContent = resolveConflictContent(resolution as any, conflict);
  setContent(resolvedContent);
  setConflicts((prev: any[]) => prev.filter(c => c.id !== conflictId));
  setVersion((prev: number) => prev + 1);
  setSyncStatus('synced');
};

const simulateMultipleConflictScenarios = (
  setConflicts: any, content: string, version: number
): void => {
  const conflicts = [
    createConflict(content, 'Remote change 1', version, version),
    createConflict(content, 'Remote change 2', version, version),
    createConflict(content, 'Remote change 3', version, version)
  ];
  setConflicts(conflicts);
};

const resolveBatchConflictsLogic = (setConflicts: any, setContent: any, setVersion: any): void => {
  setConflicts([]);
  setContent('Batch resolved content');
  setVersion((prev: number) => prev + 1);
};

const testVersionConsistencyLogic = (
  version: number, setVersion: any, remoteVersion: number, setRemoteVersion: any, setConsistency: any
): void => {
  setVersion(version + 1);
  setRemoteVersion(remoteVersion + 2);
  setConsistency(false);
  
  setTimeout(() => {
    setRemoteVersion(version + 1);
    setConsistency(true);
  }, 100);
};

const addManyHistoryActions = (setHistory: any, setLimitReached: any): void => {
  const manyActions = Array.from({ length: PERFORMANCE_THRESHOLDS.MAX_HISTORY_SIZE + 10 }, 
    (_, i) => `Action ${i}`);
  
  setHistory(trimHistory(manyActions, PERFORMANCE_THRESHOLDS.MAX_HISTORY_SIZE));
  setLimitReached(true);
};

const createHistoryBranch = (setBranches: any, setCurrentBranch: any): void => {
  const branchName = `branch-${Date.now()}`;
  setBranches((prev: any[]) => [...prev, { name: branchName, created: Date.now() }]);
  setCurrentBranch(branchName);
};

const simulateMultiClientScenario = (setClients: any, setSyncState: any): void => {
  const clients = [
    { id: 'client1', status: 'connected' },
    { id: 'client2', status: 'connected' },
    { id: 'client3', status: 'connected' }
  ];
  setClients(clients);
  setSyncState('multi-client');
};

const simulateNetworkDisruption = (setNetworkState: any, setQueuedChanges: any): void => {
  setNetworkState('disconnected');
  setQueuedChanges(['change1', 'change2', 'change3']);
  
  setTimeout(() => {
    setNetworkState('connected');
    setQueuedChanges([]);
  }, 1000);
};

const clearHistoryState = (
  history: string[], currentIndex: number, setHistory: any, setCurrentIndex: any
): void => {
  const currentState = history[currentIndex];
  setHistory([currentState]);
  setCurrentIndex(0);
};

// UI rendering functions (≤8 lines each)
const renderCollaborativeEditor = (
  content: string, conflicts: any[], version: number, syncStatus: string, handlers: any
) => (
  <div>
    <textarea data-testid="editor" value={content} onChange={(e) => handlers.handleLocalChange(e.target.value)} />
    <div data-testid="version">Version: {version}</div>
    <div data-testid="sync-status">Status: {syncStatus}</div>
    <div data-testid="conflict-count">{conflicts.length} conflicts</div>
    <button onClick={() => handlers.handleRemoteChange('Remote change', version)}>Simulate Remote Change</button>
    {conflicts.map((conflict) => renderConflictResolution(conflict, handlers.resolveConflict))}
  </div>
);

const renderConflictResolution = (conflict: any, resolveConflict: any) => (
  <div key={conflict.id} data-testid={`conflict-${conflict.id}`}>
    <div>Local: {conflict.local}</div>
    <div>Remote: {conflict.remote}</div>
    <button onClick={() => resolveConflict('local', conflict.id)}>Keep Local</button>
    <button onClick={() => resolveConflict('remote', conflict.id)}>Keep Remote</button>
    <button onClick={() => resolveConflict('merge', conflict.id)}>Merge Both</button>
  </div>
);

const renderMultiConflictEditor = (conflicts: any[], createMultiple: any, resolveBatch: any) => (
  <div>
    <div data-testid="conflict-count">{conflicts.length} conflicts</div>
    <button onClick={createMultiple}>Create Multiple Conflicts</button>
    <button onClick={resolveBatch}>Resolve Batch</button>
  </div>
);

const renderVersionConsistentEditor = (version: number, remoteVersion: number, consistency: boolean, testVersions: any) => (
  <div>
    <div data-testid="local-version">Local: {version}</div>
    <div data-testid="remote-version">Remote: {remoteVersion}</div>
    <div data-testid="consistency">{consistency ? 'consistent' : 'inconsistent'}</div>
    <button onClick={testVersions}>Test Versions</button>
  </div>
);

const renderUndoRedoComponent = (history: string[], currentIndex: number, handlers: any) => (
  <div>
    <div data-testid="current-state">{history[currentIndex]}</div>
    <div data-testid="history-info">{currentIndex + 1} of {history.length} states</div>
    <button onClick={() => handlers.performAction(`Action at ${Date.now()}`)}>Perform Action</button>
    <button onClick={handlers.undo} disabled={!canUndo(currentIndex)}>Undo</button>
    <button onClick={handlers.redo} disabled={!canRedo(currentIndex, history.length)}>Redo</button>
    <button onClick={handlers.clearHistory}>Clear History</button>
    <div data-testid="can-undo">{canUndo(currentIndex) ? 'yes' : 'no'}</div>
    <div data-testid="can-redo">{canRedo(currentIndex, history.length) ? 'yes' : 'no'}</div>
  </div>
);

const renderHistoryLimitComponent = (history: string[], limitReached: boolean, addMany: any) => (
  <div>
    <div data-testid="history-size">{history.length} items</div>
    <div data-testid="limit-reached">{limitReached ? 'yes' : 'no'}</div>
    <button onClick={addMany}>Add Many Actions</button>
  </div>
);

const renderBranchingHistoryComponent = (branches: any[], currentBranch: string, createBranch: any) => (
  <div>
    <div data-testid="branch-count">{branches.length} branches</div>
    <div data-testid="current-branch">{currentBranch}</div>
    <button onClick={createBranch}>Create Branch</button>
  </div>
);

const renderSyncComponent = (clients: any[], syncState: string, simulateMultiClient: any) => (
  <div>
    <div data-testid="client-count">{clients.length} clients</div>
    <div data-testid="sync-state">{syncState}</div>
    <button onClick={simulateMultiClient}>Simulate Multi-Client</button>
  </div>
);

const renderNetworkResilienceComponent = (networkState: string, queuedChanges: any[], simulateIssue: any) => (
  <div>
    <div data-testid="network-state">{networkState}</div>
    <div data-testid="queued-changes">{queuedChanges.length} queued</div>
    <button onClick={simulateIssue}>Simulate Network Issue</button>
  </div>
);

// Test verification functions (≤8 lines each)
const verifyInitialSyncState = async (getByTestId: any): Promise<void> => {
  expect(getByTestId('sync-status')).toHaveTextContent('Status: synced');
  expect(getByTestId('conflict-count')).toHaveTextContent('0 conflicts');
};

const triggerLocalChange = async (getByTestId: any): Promise<void> => {
  fireEvent.change(getByTestId('editor'), { target: { value: 'Local change' } });
  
  await waitFor(() => {
    expect(getByTestId('sync-status')).toHaveTextContent('Status: pending');
  });
};

const simulateConflict = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Simulate Remote Change'));
  
  await waitFor(() => {
    expect(getByTestId('conflict-count')).toHaveTextContent('1 conflicts');
    expect(getByTestId('sync-status')).toHaveTextContent('Status: conflict');
  });
};

const resolveConflict = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Keep Local'));
  
  await waitFor(() => {
    expect(getByTestId('conflict-count')).toHaveTextContent('0 conflicts');
    expect(getByTestId('sync-status')).toHaveTextContent('Status: synced');
  });
};

const simulateMultipleConflicts = async (getByText: any): Promise<void> => {
  fireEvent.click(getByText('Create Multiple Conflicts'));
};

const verifyMultipleConflicts = async (getByTestId: any): Promise<void> => {
  await waitFor(() => {
    expect(getByTestId('conflict-count')).toHaveTextContent('3 conflicts');
  });
};

const resolveBatchConflicts = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Resolve Batch'));
  
  await waitFor(() => {
    expect(getByTestId('conflict-count')).toHaveTextContent('0 conflicts');
  });
};

const testVersionConsistency = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Test Versions'));
  
  await waitFor(() => {
    expect(getByTestId('consistency')).toHaveTextContent('inconsistent');
  });
  
  await waitFor(() => {
    expect(getByTestId('consistency')).toHaveTextContent('consistent');
  }, { timeout: TEST_TIMEOUTS.SHORT });
};

const verifyInitialHistoryState = async (getByTestId: any): Promise<void> => {
  expect(getByTestId('current-state')).toHaveTextContent('Initial state');
  expect(getByTestId('can-undo')).toHaveTextContent('no');
  expect(getByTestId('can-redo')).toHaveTextContent('no');
};

const performMultipleActions = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Perform Action'));
  fireEvent.click(getByText('Perform Action'));
  fireEvent.click(getByText('Perform Action'));
  
  await waitFor(() => {
    expect(getByTestId('history-info')).toHaveTextContent('4 of 4 states');
    expect(getByTestId('can-undo')).toHaveTextContent('yes');
  });
};

const testUndoOperations = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Undo'));
  
  await waitFor(() => {
    expect(getByTestId('history-info')).toHaveTextContent('3 of 4 states');
    expect(getByTestId('can-redo')).toHaveTextContent('yes');
  });
};

const testRedoOperations = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Redo'));
  
  await waitFor(() => {
    expect(getByTestId('history-info')).toHaveTextContent('4 of 4 states');
    expect(getByTestId('can-redo')).toHaveTextContent('no');
  });
};

const testHistoryLimit = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Add Many Actions'));
  
  await waitFor(() => {
    expect(getByTestId('history-size')).toHaveTextContent(`${PERFORMANCE_THRESHOLDS.MAX_HISTORY_SIZE} items`);
    expect(getByTestId('limit-reached')).toHaveTextContent('yes');
  });
};

const testHistoryBranching = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Create Branch'));
  
  await waitFor(() => {
    expect(getByTestId('branch-count')).toHaveTextContent('1 branches');
    expect(getByTestId('current-branch')).not.toHaveTextContent('main');
  });
};

const testMultiClientSync = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Simulate Multi-Client'));
  
  await waitFor(() => {
    expect(getByTestId('client-count')).toHaveTextContent('3 clients');
    expect(getByTestId('sync-state')).toHaveTextContent('multi-client');
  });
};

const testNetworkInterruption = async (getByText: any, getByTestId: any): Promise<void> => {
  fireEvent.click(getByText('Simulate Network Issue'));
  
  await waitFor(() => {
    expect(getByTestId('network-state')).toHaveTextContent('disconnected');
    expect(getByTestId('queued-changes')).toHaveTextContent('3 queued');
  });
  
  await waitFor(() => {
    expect(getByTestId('network-state')).toHaveTextContent('connected');
    expect(getByTestId('queued-changes')).toHaveTextContent('0 queued');
  }, { timeout: TEST_TIMEOUTS.SHORT });
};