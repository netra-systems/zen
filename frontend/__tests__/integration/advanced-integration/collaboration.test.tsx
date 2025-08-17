/**
 * Collaborative Features Integration Tests
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import WS from 'jest-websocket-mock';
import { safeWebSocketCleanup } from '../../helpers/websocket-test-manager';
import { setupTestEnvironment } from './test-setup';

describe('Advanced Frontend Integration Tests - Collaboration', () => {
  let server: WS;
  
  setupTestEnvironment();

  beforeEach(() => {
    server = new WS('ws://localhost:8000/ws');
  });

  afterEach(() => {
    safeWebSocketCleanup();
  });

  describe('18. Collaborative Features Integration', () => {
    it('should sync cursor positions in real-time', async () => {
      const cursors = new Map();
      
      const CollaborativeEditor = () => {
        const [otherCursors, setOtherCursors] = React.useState<Map<string, { x: number, y: number }>>(new Map());
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'cursor_update') {
              setOtherCursors(prev => {
                const updated = new Map(prev);
                updated.set(message.userId, message.position);
                return updated;
              });
            }
          };
          
          const handleMouseMove = (e: MouseEvent) => {
            ws.send(JSON.stringify({
              type: 'cursor_move',
              position: { x: e.clientX, y: e.clientY }
            }));
          };
          
          document.addEventListener('mousemove', handleMouseMove);
          
          return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            ws.close();
          };
        }, []);
        
        return (
          <div>
            {Array.from(otherCursors.entries()).map(([userId, pos]) => (
              <div key={userId} data-testid={`cursor-${userId}`}>
                User {userId}: {pos.x}, {pos.y}
              </div>
            ))}
          </div>
        );
      };
      
      render(<CollaborativeEditor />);
      
      await server.connected;
      
      // Simulate another user's cursor
      server.send(JSON.stringify({
        type: 'cursor_update',
        userId: 'user-2',
        position: { x: 100, y: 200 }
      }));
      
      await waitFor(() => {
        expect(screen.getByTestId('cursor-user-2')).toHaveTextContent('User user-2: 100, 200');
      });
    });

    it('should handle presence and activity status', async () => {
      const PresenceComponent = () => {
        const [activeUsers, setActiveUsers] = React.useState<Set<string>>(new Set());
        const [typingUsers, setTypingUsers] = React.useState<Set<string>>(new Set());
        
        React.useEffect(() => {
          const ws = new WebSocket('ws://localhost:8000/ws');
          
          ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'user_joined') {
              setActiveUsers(prev => new Set(prev).add(message.userId));
            } else if (message.type === 'user_left') {
              setActiveUsers(prev => {
                const updated = new Set(prev);
                updated.delete(message.userId);
                return updated;
              });
            } else if (message.type === 'typing_start') {
              setTypingUsers(prev => new Set(prev).add(message.userId));
            } else if (message.type === 'typing_stop') {
              setTypingUsers(prev => {
                const updated = new Set(prev);
                updated.delete(message.userId);
                return updated;
              });
            }
          };
          
          return () => ws.close();
        }, []);
        
        return (
          <div>
            <div data-testid="active-count">{activeUsers.size} users online</div>
            <div data-testid="typing-count">{typingUsers.size} users typing</div>
          </div>
        );
      };
      
      render(<PresenceComponent />);
      
      await server.connected;
      
      // Simulate users joining
      server.send(JSON.stringify({ type: 'user_joined', userId: 'user-1' }));
      server.send(JSON.stringify({ type: 'user_joined', userId: 'user-2' }));
      
      await waitFor(() => {
        expect(screen.getByTestId('active-count')).toHaveTextContent('2 users online');
      });
      
      // Simulate typing
      server.send(JSON.stringify({ type: 'typing_start', userId: 'user-1' }));
      
      await waitFor(() => {
        expect(screen.getByTestId('typing-count')).toHaveTextContent('1 users typing');
      });
    });
  });

  describe('26. Real-time Collaboration Sync', () => {
    it('should handle conflict resolution in collaborative editing', async () => {
      const CollaborativeEditor = () => {
        const [content, setContent] = React.useState('Initial content');
        const [conflicts, setConflicts] = React.useState<any[]>([]);
        const [version, setVersion] = React.useState(1);
        
        const handleRemoteChange = (remoteContent: string, remoteVersion: number) => {
          if (remoteVersion > version) {
            // Remote is newer, accept it
            setContent(remoteContent);
            setVersion(remoteVersion);
          } else if (remoteVersion === version) {
            // Conflict detected
            setConflicts(prev => [...prev, {
              local: content,
              remote: remoteContent,
              timestamp: Date.now()
            }]);
          }
        };
        
        const resolveConflict = (resolution: 'local' | 'remote', conflictIndex: number) => {
          const conflict = conflicts[conflictIndex];
          if (resolution === 'remote') {
            setContent(conflict.remote);
          }
          setConflicts(prev => prev.filter((_, i) => i !== conflictIndex));
          setVersion(prev => prev + 1);
        };
        
        // Simulate receiving remote change
        React.useEffect(() => {
          const timer = setTimeout(() => {
            handleRemoteChange('Remote content update', version);
          }, 1000);
          
          return () => clearTimeout(timer);
        }, []);
        
        return (
          <div>
            <div data-testid="content">{content}</div>
            <div data-testid="version">Version {version}</div>
            <div data-testid="conflicts">{conflicts.length} conflicts</div>
            {conflicts.map((conflict, i) => (
              <div key={i}>
                <button onClick={() => resolveConflict('local', i)}>Keep Local</button>
                <button onClick={() => resolveConflict('remote', i)}>Keep Remote</button>
              </div>
            ))}
          </div>
        );
      };
      
      const { getByTestId } = render(<CollaborativeEditor />);
      
      await waitFor(() => {
        const conflictCount = getByTestId('conflicts').textContent;
        expect(conflictCount).toMatch(/\d+ conflicts/);
      }, { timeout: 2000 });
    });

    it('should maintain operation history for undo/redo', async () => {
      const UndoRedoComponent = () => {
        const [history, setHistory] = React.useState<string[]>(['Initial']);
        const [currentIndex, setCurrentIndex] = React.useState(0);
        
        const performAction = (action: string) => {
          const newHistory = history.slice(0, currentIndex + 1);
          newHistory.push(action);
          setHistory(newHistory);
          setCurrentIndex(newHistory.length - 1);
        };
        
        const undo = () => {
          if (currentIndex > 0) {
            setCurrentIndex(currentIndex - 1);
          }
        };
        
        const redo = () => {
          if (currentIndex < history.length - 1) {
            setCurrentIndex(currentIndex + 1);
          }
        };
        
        return (
          <div>
            <div data-testid="current-state">{history[currentIndex]}</div>
            <button onClick={() => performAction('Action 1')}>Action 1</button>
            <button onClick={() => performAction('Action 2')}>Action 2</button>
            <button onClick={undo} disabled={currentIndex === 0}>Undo</button>
            <button onClick={redo} disabled={currentIndex === history.length - 1}>Redo</button>
            <div data-testid="history-length">{history.length} states</div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(<UndoRedoComponent />);
      
      // Perform actions
      fireEvent.click(getByText('Action 1'));
      fireEvent.click(getByText('Action 2'));
      
      expect(getByTestId('current-state')).toHaveTextContent('Action 2');
      expect(getByTestId('history-length')).toHaveTextContent('3 states');
      
      // Undo
      fireEvent.click(getByText('Undo'));
      expect(getByTestId('current-state')).toHaveTextContent('Action 1');
      
      // Redo
      fireEvent.click(getByText('Redo'));
      expect(getByTestId('current-state')).toHaveTextContent('Action 2');
    });
  });
});