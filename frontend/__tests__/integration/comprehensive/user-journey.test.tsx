/**
 * User Journey Stateful and Collaborative Tests
 * ULTRA DEEP THINK: Module-based architecture - Stateful tests extracted for 450-line compliance
 */

import {
  React, render, waitFor, fireEvent, TEST_TIMEOUTS,
  setupUserJourneyTest, teardownUserJourneyTest,
  createMockWebSocketServer, createWebSocketMessage,
  handleUserJoined, handleVoteCast, handleStepChange
} from './user-journey-utils';

describe('User Journey State Management Tests', () => {
  let server: any;
  
  beforeEach(() => {
    server = setupUserJourneyTest();
  });

  afterEach(() => {
    teardownUserJourneyTest();
  });

  it('should maintain state across component re-renders', async () => {
    const StatefulWorkflow = () => {
      const [data, setData] = React.useState(() => {
        // Load state from localStorage on mount
        const saved = localStorage.getItem('workflow_state');
        return saved ? JSON.parse(saved) : { step: 'start', progress: 0, history: [] };
      });
      
      // Save state to localStorage whenever data changes
      React.useEffect(() => {
        localStorage.setItem('workflow_state', JSON.stringify(data));
      }, [data]);
      
      const updateStep = (newStep: string) => {
        setData(prev => ({
          ...prev,
          step: newStep,
          progress: prev.progress + 1,
          history: [...prev.history, { step: newStep, timestamp: Date.now() }]
        }));
      };
      
      const resetWorkflow = () => {
        const initialState = { step: 'start', progress: 0, history: [] };
        setData(initialState);
        localStorage.removeItem('workflow_state');
      };
      
      return (
        <div>
          <div data-testid="current-step">{data.step}</div>
          <div data-testid="progress">{data.progress}</div>
          <div data-testid="history-length">{data.history.length}</div>
          
          <button onClick={() => updateStep('step-1')} data-testid="go-step-1">
            Go to Step 1
          </button>
          <button onClick={() => updateStep('step-2')} data-testid="go-step-2">
            Go to Step 2
          </button>
          <button onClick={() => updateStep('complete')} data-testid="complete">
            Complete
          </button>
          <button onClick={resetWorkflow} data-testid="reset">
            Reset
          </button>
        </div>
      );
    };
    
    const { getByTestId, unmount } = render(<StatefulWorkflow />);
    
    // Initial state
    expect(getByTestId('current-step')).toHaveTextContent('start');
    expect(getByTestId('progress')).toHaveTextContent('0');
    
    // Progress through steps
    fireEvent.click(getByTestId('go-step-1'));
    expect(getByTestId('current-step')).toHaveTextContent('step-1');
    expect(getByTestId('progress')).toHaveTextContent('1');
    
    fireEvent.click(getByTestId('go-step-2'));
    expect(getByTestId('progress')).toHaveTextContent('2');
    expect(getByTestId('history-length')).toHaveTextContent('2');
    
    // Verify state is saved to localStorage
    const savedState = JSON.parse(localStorage.getItem('workflow_state') || '{}');
    expect(savedState.step).toBe('step-2');
    expect(savedState.progress).toBe(2);
    
    // Unmount and remount to simulate page refresh
    unmount();
    const { getByTestId: getByTestIdNew } = render(<StatefulWorkflow />);
    
    // State should be restored
    expect(getByTestIdNew('current-step')).toHaveTextContent('step-2');
    expect(getByTestIdNew('progress')).toHaveTextContent('2');
    expect(getByTestIdNew('history-length')).toHaveTextContent('2');
  });

  it('should handle collaborative workflow with multiple users', async () => {
    const CollaborativeWorkflow = () => {
      const [users, setUsers] = React.useState<Map<string, any>>(new Map());
      const [sharedState, setSharedState] = React.useState({
        currentStep: 'planning',
        votes: new Map(),
        decisions: [],
        activeUsers: []
      });
      
      const processWebSocketMessage = (message: any) => {
        switch (message.type) {
          case 'user_joined':
            handleUserJoined(message, setUsers);
            break;
          case 'vote_cast':
            handleVoteCast(message, setSharedState);
            break;
          case 'step_change':
            handleStepChange(message, setSharedState);
            break;
        }
      };
      
      React.useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/ws');
        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);
          processWebSocketMessage(message);
        };
        return () => ws.close();
      }, []);
      
      const castVote = (vote: 'approve' | 'reject') => {
        const ws = new WebSocket('ws://localhost:8000/ws');
        ws.onopen = () => {
          ws.send(JSON.stringify({
            type: 'cast_vote',
            userId: 'current-user',
            vote,
            timestamp: Date.now()
          }));
        };
      };
      
      return (
        <div>
          <div data-testid="current-step">{sharedState.currentStep}</div>
          <div data-testid="user-count">{users.size} users</div>
          <div data-testid="vote-count">{sharedState.votes.size} votes</div>
          <div data-testid="decision-count">{sharedState.decisions.length} decisions</div>
          
          <button onClick={() => castVote('approve')} data-testid="vote-approve">
            Vote Approve
          </button>
          <button onClick={() => castVote('reject')} data-testid="vote-reject">
            Vote Reject
          </button>
        </div>
      );
    };
    
    const { getByTestId } = render(<CollaborativeWorkflow />);
    
    await server.connected;
    
    // Simulate users joining
    server.send(createWebSocketMessage('user_joined', {
      userId: 'user-1',
      userData: { name: 'Alice', role: 'admin' }
    }));
    
    server.send(createWebSocketMessage('user_joined', {
      userId: 'user-2',
      userData: { name: 'Bob', role: 'user' }
    }));
    
    await waitFor(() => {
      expect(getByTestId('user-count')).toHaveTextContent('2 users');
    });
    
    // Simulate voting
    server.send(createWebSocketMessage('vote_cast', {
      userId: 'user-1',
      vote: 'approve'
    }));
    
    await waitFor(() => {
      expect(getByTestId('vote-count')).toHaveTextContent('1 votes');
    });
  });
});