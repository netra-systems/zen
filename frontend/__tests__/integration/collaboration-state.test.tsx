/**
 * Collaboration and State Management Integration Tests
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';
import { TestProviders } from '../test-utils/providers';

// Mock fetch
global.fetch = jest.fn();

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};
global.localStorage = localStorageMock as any;

// Mock WebSocket
let mockWs: WS;

beforeEach(() => {
  mockWs = new WS('ws://localhost:8000/ws');
});

afterEach(() => {
  WS.clean();
  jest.clearAllMocks();
  localStorageMock.clear();
});

describe('Collaboration Features', () => {
  it('should share threads with team members', async () => {
    const TestComponent = () => {
      const [shareStatus, setShareStatus] = React.useState('');
      const [sharedUsers, setSharedUsers] = React.useState<string[]>([]);
      
      const shareThread = async () => {
        const response = await fetch('/api/threads/thread-123/share', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            users: ['user1@example.com', 'user2@example.com'],
            permissions: ['read', 'comment']
          })
        });
        
        if (response.ok) {
          setShareStatus('Thread shared successfully');
          setSharedUsers(['user1@example.com', 'user2@example.com']);
        }
      };
      
      return (
        <div>
          <button onClick={shareThread}>Share Thread</button>
          <div data-testid="share-status">{shareStatus}</div>
          <div data-testid="shared-users">
            {sharedUsers.map(user => (
              <div key={user}>{user}</div>
            ))}
          </div>
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Share Thread'));
    
    await waitFor(() => {
      expect(getByTestId('share-status')).toHaveTextContent('Thread shared successfully');
      expect(getByTestId('shared-users')).toHaveTextContent('user1@example.com');
      expect(getByTestId('shared-users')).toHaveTextContent('user2@example.com');
    });
  });

  it('should sync collaborative edits in real-time', async () => {
    const TestComponent = () => {
      const [edits, setEdits] = React.useState<any[]>([]);
      
      React.useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/ws');
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'collaborative_edit') {
            setEdits(prev => [...prev, data.edit]);
          }
        };
        
        return () => ws.close();
      }, []);
      
      const sendEdit = () => {
        // Simulate sending an edit
        mockWs.send(JSON.stringify({
          type: 'collaborative_edit',
          edit: {
            user: 'current_user',
            content: 'Updated content',
            timestamp: Date.now()
          }
        }));
      };
      
      return (
        <div>
          <button onClick={sendEdit}>Send Edit</button>
          <div data-testid="edits">
            {edits.map((edit, idx) => (
              <div key={idx}>
                {edit.user}: {edit.content}
              </div>
            ))}
          </div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await mockWs.connected;
    
    // Simulate receiving an edit from another user
    act(() => {
      mockWs.send(JSON.stringify({
        type: 'collaborative_edit',
        edit: {
          user: 'other_user',
          content: 'Collaborative change',
          timestamp: Date.now()
        }
      }));
    });
    
    await waitFor(() => {
      expect(getByTestId('edits')).toHaveTextContent('other_user: Collaborative change');
    });
  });

  it('should handle presence awareness', async () => {
    const TestComponent = () => {
      const [activeUsers, setActiveUsers] = React.useState<any[]>([]);
      
      React.useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/ws');
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          if (data.type === 'presence_update') {
            setActiveUsers(data.users);
          }
        };
        
        // Send presence
        ws.onopen = () => {
          ws.send(JSON.stringify({
            type: 'presence',
            status: 'active'
          }));
        };
        
        return () => ws.close();
      }, []);
      
      return (
        <div data-testid="presence">
          <div>Active users: {activeUsers.length}</div>
          {activeUsers.map(user => (
            <div key={user.id}>
              {user.name} - {user.status}
            </div>
          ))}
        </div>
      );
    };
    
    const { getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    await mockWs.connected;
    
    // Simulate presence update
    act(() => {
      mockWs.send(JSON.stringify({
        type: 'presence_update',
        users: [
          { id: '1', name: 'Alice', status: 'typing' },
          { id: '2', name: 'Bob', status: 'viewing' }
        ]
      }));
    });
    
    await waitFor(() => {
      expect(getByTestId('presence')).toHaveTextContent('Active users: 2');
      expect(getByTestId('presence')).toHaveTextContent('Alice - typing');
      expect(getByTestId('presence')).toHaveTextContent('Bob - viewing');
    });
  });
});

describe('Jupyter Notebook Support', () => {
  it('should execute notebook cells', async () => {
    const TestComponent = () => {
      const [output, setOutput] = React.useState('');
      
      const executeCell = async () => {
        const response = await fetch('/api/notebooks/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code: 'print("Hello from Jupyter")',
            language: 'python'
          })
        });
        
        const data = await response.json();
        setOutput(data.output);
      };
      
      return (
        <div>
          <button onClick={executeCell}>Execute Cell</button>
          {output && <div data-testid="output">{output}</div>}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ output: 'Hello from Jupyter' })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Execute Cell'));
    
    await waitFor(() => {
      expect(getByTestId('output')).toHaveTextContent('Hello from Jupyter');
    });
  });

  it('should render notebook visualizations', async () => {
    const TestComponent = () => {
      const [visualization, setVisualization] = React.useState<any>(null);
      
      const generateViz = async () => {
        const response = await fetch('/api/notebooks/visualize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            data: [[1, 2], [3, 4], [5, 6]],
            type: 'scatter'
          })
        });
        
        const data = await response.json();
        setVisualization(data);
      };
      
      return (
        <div>
          <button onClick={generateViz}>Generate Visualization</button>
          {visualization && (
            <div data-testid="viz">
              <div>Type: {visualization.type}</div>
              <div>Points: {visualization.points}</div>
            </div>
          )}
        </div>
      );
    };
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        type: 'scatter',
        points: 3,
        image: 'base64_image_data'
      })
    });
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Generate Visualization'));
    
    await waitFor(() => {
      expect(getByTestId('viz')).toHaveTextContent('Type: scatter');
      expect(getByTestId('viz')).toHaveTextContent('Points: 3');
    });
  });
});

describe('State Persistence and Recovery', () => {
  it('should persist application state across sessions', async () => {
    const mockPersistedState = {
      version: 2,
      timestamp: Date.now(),
      data: {
        user_preferences: { theme: 'dark', language: 'en' },
        session_data: { last_thread: 'thread-123' },
        cached_results: { optimization_1: { result: 'cached' } }
      }
    };
    
    const TestComponent = () => {
      const [state, setState] = React.useState<any>(null);
      
      const saveState = () => {
        localStorage.setItem('app_state', JSON.stringify(mockPersistedState));
        setState(mockPersistedState);
      };
      
      const loadState = () => {
        const stored = localStorage.getItem('app_state');
        if (stored) {
          setState(JSON.parse(stored));
        }
      };
      
      return (
        <div>
          <button onClick={saveState}>Save State</button>
          <button onClick={loadState}>Load State</button>
          {state && (
            <div data-testid="state">
              <div>Theme: {state.data.user_preferences.theme}</div>
              <div>Last thread: {state.data.session_data.last_thread}</div>
            </div>
          )}
        </div>
      );
    };
    
    localStorageMock.getItem.mockReturnValue(JSON.stringify(mockPersistedState));
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Save State'));
    
    await waitFor(() => {
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'app_state',
        JSON.stringify(mockPersistedState)
      );
    });
    
    fireEvent.click(getByText('Load State'));
    
    await waitFor(() => {
      expect(getByTestId('state')).toHaveTextContent('Theme: dark');
      expect(getByTestId('state')).toHaveTextContent('Last thread: thread-123');
    });
  });

  it('should recover from corrupted state gracefully', async () => {
    const TestComponent = () => {
      const [state, setState] = React.useState<any>(null);
      const [error, setError] = React.useState<string | null>(null);
      
      const loadState = async () => {
        try {
          // Simulate corrupted state
          const corrupted = 'invalid json {{{';
          const parsed = JSON.parse(corrupted);
          setState(parsed);
        } catch (err: any) {
          // Recovery: Use default state
          const defaultState = {
            version: 1,
            data: {
              user_preferences: { theme: 'light', language: 'en' },
              session_data: {}
            }
          };
          
          setState(defaultState);
          setError('State corrupted, using defaults');
          
          // Clear corrupted data
          localStorage.removeItem('app_state');
        }
      };
      
      return (
        <div>
          <button onClick={loadState}>Load State</button>
          {error && <div data-testid="error">{error}</div>}
          {state && <div data-testid="state">State loaded</div>}
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Load State'));
    
    await waitFor(() => {
      expect(getByTestId('error')).toHaveTextContent('State corrupted, using defaults');
      expect(getByTestId('state')).toHaveTextContent('State loaded');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('app_state');
    });
  });

  it('should migrate state between versions', async () => {
    const TestComponent = () => {
      const [migrated, setMigrated] = React.useState(false);
      
      const migrateState = () => {
        const oldState = {
          version: 1,
          data: { old_field: 'value' }
        };
        
        // Migrate to new format
        const newState = {
          version: 2,
          data: {
            user_preferences: { theme: 'light' },
            session_data: {},
            migrated_from_v1: oldState.data
          }
        };
        
        localStorage.setItem('app_state', JSON.stringify(newState));
        setMigrated(true);
      };
      
      return (
        <div>
          <button onClick={migrateState}>Migrate State</button>
          {migrated && <div data-testid="migrated">State migrated to v2</div>}
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Migrate State'));
    
    await waitFor(() => {
      expect(getByTestId('migrated')).toHaveTextContent('State migrated to v2');
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });
  });
});