/**
 * Simple Thread Switching Test
 * Basic verification of thread switching functionality
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
    forward: jest.fn()
  }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/chat'
}));

const SimpleThreadSwitcher: React.FC = () => {
  const [activeThread, setActiveThread] = React.useState<string | null>(null);
  const [switchCount, setSwitchCount] = React.useState(0);

  const threads = [
    { id: 'thread-1', title: 'First Thread' },
    { id: 'thread-2', title: 'Second Thread' },
    { id: 'thread-3', title: 'Third Thread' }
  ];

  const handleThreadSwitch = (threadId: string) => {
    setActiveThread(threadId);
    setSwitchCount(prev => prev + 1);
  };

  return (
    <div data-testid="simple-thread-switcher">
      <div data-testid="thread-list">
        {threads.map(thread => (
          <button
            key={thread.id}
            data-testid={`thread-${thread.id}`}
            className={activeThread === thread.id ? 'active' : ''}
            onClick={() => handleThreadSwitch(thread.id)}
          >
            {thread.title}
          </button>
        ))}
      </div>
      
      <div data-testid="active-thread">
        {activeThread || 'No thread selected'}
      </div>
      
      <div data-testid="switch-count">
        {switchCount}
      </div>
    </div>
  );
};

describe('Simple Thread Switching', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should switch threads correctly', async () => {
    const user = userEvent.setup();
    
    render(<SimpleThreadSwitcher />);

    // Initially no thread selected
    expect(screen.getByTestId('active-thread')).toHaveTextContent('No thread selected');
    expect(screen.getByTestId('switch-count')).toHaveTextContent('0');

    // Click first thread
    await user.click(screen.getByTestId('thread-thread-1'));
    
    expect(screen.getByTestId('active-thread')).toHaveTextContent('thread-1');
    expect(screen.getByTestId('switch-count')).toHaveTextContent('1');

    // Click second thread
    await user.click(screen.getByTestId('thread-thread-2'));
    
    expect(screen.getByTestId('active-thread')).toHaveTextContent('thread-2');
    expect(screen.getByTestId('switch-count')).toHaveTextContent('2');
  });

  it('should handle rapid switching', async () => {
    const user = userEvent.setup();
    
    render(<SimpleThreadSwitcher />);

    const thread1 = screen.getByTestId('thread-thread-1');
    const thread2 = screen.getByTestId('thread-thread-2');
    const thread3 = screen.getByTestId('thread-thread-3');

    // Perform rapid switches
    await user.click(thread1);
    await user.click(thread2);
    await user.click(thread3);
    await user.click(thread1);
    await user.click(thread2);

    expect(screen.getByTestId('switch-count')).toHaveTextContent('5');
    expect(screen.getByTestId('active-thread')).toHaveTextContent('thread-2');
  });

  it('should show active state correctly', async () => {
    const user = userEvent.setup();
    
    render(<SimpleThreadSwitcher />);

    await user.click(screen.getByTestId('thread-thread-2'));
    
    const activeButton = screen.getByTestId('thread-thread-2');
    expect(activeButton).toHaveClass('active');
    
    // Other buttons should not be active
    expect(screen.getByTestId('thread-thread-1')).not.toHaveClass('active');
    expect(screen.getByTestId('thread-thread-3')).not.toHaveClass('active');
  });
});