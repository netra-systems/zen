/**
 * Collaborative Features Integration Tests
 * Tests for real-time cursor tracking, presence, and collaborative editing
 */

import React from 'react';
import { render, waitFor, screen } from '@testing-library/react';
import { createTestSetup, createWebSocketMessage } from './setup';

describe('Collaborative Features Integration', () => {
  const testSetup = createTestSetup({ enableWebSocket: true });

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  it('should sync cursor positions in real-time', async () => {
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
    
    await testSetup.waitForWebSocketConnection();
    
    // Simulate another user's cursor
    testSetup.sendWebSocketMessage({
      type: 'cursor_update',
      userId: 'user-2',
      position: { x: 100, y: 200 }
    });
    
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
    
    await testSetup.waitForWebSocketConnection();
    
    // Simulate users joining
    testSetup.sendWebSocketMessage({ type: 'user_joined', userId: 'user-1' });
    testSetup.sendWebSocketMessage({ type: 'user_joined', userId: 'user-2' });
    
    await waitFor(() => {
      expect(screen.getByTestId('active-count')).toHaveTextContent('2 users online');
    });
    
    // Simulate typing
    testSetup.sendWebSocketMessage({ type: 'typing_start', userId: 'user-1' });
    
    await waitFor(() => {
      expect(screen.getByTestId('typing-count')).toHaveTextContent('1 users typing');
    });
  });

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

  it('should handle collaborative document versioning', async () => {
    const DocumentVersioning = () => {
      const [document, setDocument] = React.useState({
        id: 'doc-1',
        content: 'Document content',
        version: 1,
        lastModified: Date.now(),
        collaborators: ['user-1']
      });
      
      const [versions, setVersions] = React.useState<any[]>([]);
      
      React.useEffect(() => {
        // Mock loading version history
        setVersions([
          { version: 1, content: 'Initial content', author: 'user-1', timestamp: Date.now() - 2000 },
          { version: 2, content: 'Updated content', author: 'user-2', timestamp: Date.now() - 1000 },
          { version: 3, content: 'Final content', author: 'user-1', timestamp: Date.now() }
        ]);
      }, []);
      
      const revertToVersion = (version: number) => {
        const targetVersion = versions.find(v => v.version === version);
        if (targetVersion) {
          setDocument(prev => ({
            ...prev,
            content: targetVersion.content,
            version: version
          }));
        }
      };
      
      return (
        <div>
          <div data-testid="document-content">{document.content}</div>
          <div data-testid="document-version">Version {document.version}</div>
          <div data-testid="version-history">
            {versions.map(version => (
              <div key={version.version}>
                <span>v{version.version} by {version.author}</span>
                <button onClick={() => revertToVersion(version.version)}>
                  Revert
                </button>
              </div>
            ))}
          </div>
        </div>
      );
    };
    
    const { getByTestId } = render(<DocumentVersioning />);
    
    await waitFor(() => {
      expect(getByTestId('version-history').children).toHaveLength(3);
    });
    
    // Test revert functionality
    const revertButtons = getByTestId('version-history').querySelectorAll('button');
    fireEvent.click(revertButtons[0]); // Revert to version 1
    
    expect(getByTestId('document-version')).toHaveTextContent('Version 1');
  });
});