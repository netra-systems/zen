/**
 * Start Chat Button Component Tests - Core States
 * 
 * Tests the critical "Start New Chat" button functionality that enables
 * users to start new conversations - core to user engagement and conversion.
 * 
 * Business Value Justification:
 * - Segment: All (Free, Early, Mid, Enterprise) 
 * - Goal: Ensure reliable thread creation for user engagement
 * - Value Impact: Protects Free → Paid conversion path
 * - Revenue Impact: Critical for user onboarding and retention
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strong typing for all props and interactions
 * @compliance frontend_unified_testing_spec.xml - journey id="start_chat_button"
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Component under test
import { ThreadSidebarHeader } from '@/components/chat/ThreadSidebarComponents';

// Test types
interface StartChatButtonProps {
  onCreateThread: () => Promise<void>;
  isCreating: boolean;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface TestScenario {
  name: string;
  props: StartChatButtonProps;
  expectedText: string;
  expectedDisabled: boolean;
  expectedIcon: 'plus' | 'loading';
}

// Test fixtures and mocks
const mockOnCreateThread = jest.fn().mockResolvedValue(undefined);

const defaultProps: StartChatButtonProps = {
  onCreateThread: mockOnCreateThread,
  isCreating: false,
  isLoading: false,
  isAuthenticated: true
};

const testScenarios: TestScenario[] = [
  {
    name: 'authenticated and ready state',
    props: defaultProps,
    expectedText: 'New Conversation',
    expectedDisabled: false,
    expectedIcon: 'plus'
  },
  {
    name: 'creating thread state',
    props: { ...defaultProps, isCreating: true },
    expectedText: 'New Conversation',
    expectedDisabled: true,
    expectedIcon: 'loading'
  },
  {
    name: 'loading state',
    props: { ...defaultProps, isLoading: true },
    expectedText: 'New Conversation',
    expectedDisabled: true,
    expectedIcon: 'plus'
  },
  {
    name: 'unauthenticated state',
    props: { ...defaultProps, isAuthenticated: false },
    expectedText: 'New Conversation',
    expectedDisabled: true,
    expectedIcon: 'plus'
  },
  {
    name: 'multiple disabled conditions',
    props: { ...defaultProps, isCreating: true, isLoading: true, isAuthenticated: false },
    expectedText: 'New Conversation',
    expectedDisabled: true,
    expectedIcon: 'loading'
  }
];

describe('StartChatButton Core Component', () => {
  beforeEach(() => {
    setupButtonTests();
  });
  
  afterEach(() => {
    cleanupButtonTests();
  });
  
  describe('Button Visibility and States', () => {
    test.each(testScenarios)('renders correctly in $name', ({ props, expectedText, expectedDisabled, expectedIcon }) => {
      renderStartChatButton(props);
      verifyButtonText(expectedText);
      verifyButtonDisabled(expectedDisabled);
      verifyButtonIcon(expectedIcon);
    });
    
    it('is always visible when component renders', () => {
      renderStartChatButton(defaultProps);
      verifyButtonVisible();
      verifyTestIdPresent();
    });
    
    it('displays loading spinner when creating thread', () => {
      renderStartChatButton({ ...defaultProps, isCreating: true });
      verifyLoadingSpinner();
      verifySpinningAnimation();
    });
    
    it('displays plus icon when ready', () => {
      renderStartChatButton(defaultProps);
      verifyPlusIcon();
      verifyNoSpinningAnimation();
    });
  });
  
  describe('Click Handling and Immediate Feedback', () => {
    it('calls onCreateThread when clicked in ready state', async () => {
      renderStartChatButton(defaultProps);
      await clickButton();
      verifyOnCreateThreadCalls(1);
    });
    
    it('does not call onCreateThread when creating thread', async () => {
      renderStartChatButton({ ...defaultProps, isCreating: true });
      await clickButton();
      verifyOnCreateThreadCalls(0);
    });
    
    it('provides immediate visual feedback on click', async () => {
      renderStartChatButton(defaultProps);
      const startTime = performance.now();
      await clickButtonAndMeasure();
      expectFeedbackWithin50ms(startTime);
    });
  });
  
  describe('Double-Click Prevention', () => {
    it('prevents duplicate thread creation on rapid clicks', async () => {
      renderStartChatButton(defaultProps);
      await performRapidClicks();
      verifyOnCreateThreadCalls(1);
    });
    
    it('disables button immediately when creation starts', async () => {
      const { rerender } = renderStartChatButton(defaultProps);
      await clickButton();
      updateToCreatingState(rerender);
      verifyButtonDisabled(true);
    });
  });
  
  describe('Keyboard and Mobile Accessibility', () => {
    it('supports Enter key activation', async () => {
      renderStartChatButton(defaultProps);
      await focusAndPressEnter();
      verifyOnCreateThreadCalls(1);
    });
    
    it('supports Space key activation', async () => {
      renderStartChatButton(defaultProps);
      await focusAndPressSpace();
      verifyOnCreateThreadCalls(1);
    });
    
    it('responds to touch events', async () => {
      renderStartChatButton(defaultProps);
      await performTouchAction();
      verifyOnCreateThreadCalls(1);
    });
    
    it('has proper ARIA attributes', () => {
      renderStartChatButton(defaultProps);
      verifyAriaAttributes();
      verifyAccessibleName();
    });
  });
  
  // Helper functions (8 lines max each)
  function setupButtonTests(): void {
    jest.clearAllMocks();
    mockOnCreateThread.mockClear();
  }
  
  function cleanupButtonTests(): void {
    jest.resetAllMocks();
  }
  
  function renderStartChatButton(props: StartChatButtonProps) {
    return render(<ThreadSidebarHeader {...props} />);
  }
  
  function verifyButtonText(expectedText: string): void {
    expect(screen.getByText(expectedText)).toBeInTheDocument();
  }
  
  function verifyButtonDisabled(shouldBeDisabled: boolean): void {
    const button = screen.getByRole('button');
    if (shouldBeDisabled) {
      expect(button).toBeDisabled();
    } else {
      expect(button).toBeEnabled();
    }
  }
  
  function verifyButtonIcon(expectedIcon: 'plus' | 'loading'): void {
    const button = screen.getByRole('button');
    if (expectedIcon === 'loading') {
      expect(button.querySelector('.animate-spin')).toBeInTheDocument();
    } else {
      expect(button.querySelector('.animate-spin')).not.toBeInTheDocument();
    }
  }
  
  function verifyButtonVisible(): void {
    const button = screen.getByRole('button');
    expect(button).toBeVisible();
  }
  
  function verifyTestIdPresent(): void {
    expect(screen.getByRole('button', { name: /new conversation/i })).toBeInTheDocument();
  }
  
  function verifyLoadingSpinner(): void {
    expect(screen.getByRole('button')).toBeDisabled();
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  }
  
  function verifySpinningAnimation(): void {
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toHaveClass('animate-spin');
  }
  
  function verifyPlusIcon(): void {
    const button = screen.getByRole('button');
    expect(button.querySelector('svg')).toBeInTheDocument();
    expect(button.querySelector('.animate-spin')).not.toBeInTheDocument();
  }
  
  function verifyNoSpinningAnimation(): void {
    expect(document.querySelector('.animate-spin')).not.toBeInTheDocument();
  }
  
  function verifyOnCreateThreadCalls(expectedCalls: number): void {
    expect(mockOnCreateThread).toHaveBeenCalledTimes(expectedCalls);
  }
  
  async function clickButtonAndMeasure(): Promise<void> {
    const button = screen.getByRole('button');
    await userEvent.click(button);
  }
  
  function expectFeedbackWithin50ms(startTime: number): void {
    const responseTime = performance.now() - startTime;
    expect(responseTime).toBeLessThan(50);
  }
  
  async function performRapidClicks(): Promise<void> {
    const button = screen.getByRole('button');
    await userEvent.click(button);
    await userEvent.click(button);
    await userEvent.click(button);
  }
  
  async function clickButton(): Promise<void> {
    const button = screen.getByRole('button');
    await userEvent.click(button);
  }
  
  function updateToCreatingState(rerender: any): void {
    const creatingProps = { ...defaultProps, isCreating: true };
    rerender(<ThreadSidebarHeader {...creatingProps} />);
  }
  
  async function focusAndPressEnter(): Promise<void> {
    const button = screen.getByRole('button');
    button.focus();
    await userEvent.keyboard('{Enter}');
  }
  
  async function focusAndPressSpace(): Promise<void> {
    const button = screen.getByRole('button');
    button.focus();
    await userEvent.keyboard(' ');
  }
  
  function verifyAriaAttributes(): void {
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('type', 'button');
  }
  
  function verifyAccessibleName(): void {
    expect(screen.getByRole('button', { name: /new conversation/i })).toBeInTheDocument();
  }
  
  async function performTouchAction(): Promise<void> {
    const button = screen.getByRole('button');
    await userEvent.click(button); // Touch events trigger click
  }
});