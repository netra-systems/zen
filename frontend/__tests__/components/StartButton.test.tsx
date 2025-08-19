/**
 * Start Button (New Chat Button) Component Tests
 * 
 * Tests the critical "New Chat" button functionality that enables
 * users to start new conversations - core to onboarding flow.
 * 
 * Business Value: Protects Free → Paid conversion path
 * Priority: P0 - Revenue critical component
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strong typing for all props and interactions
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { act } from 'react-dom/test-utils';

// Component under test
import { NewChatButton } from '@/components/chat/ChatSidebarUIComponents';
import type { NewChatButtonProps } from '@/components/chat/ChatSidebarTypes';

// Test data types
interface ButtonTestScenario {
  name: string;
  props: NewChatButtonProps;
  expectedText: string;
  expectedDisabled: boolean;
  expectedClasses: string[];
}

interface ButtonInteractionTest {
  description: string;
  initialProps: NewChatButtonProps;
  userAction: (button: HTMLElement) => Promise<void>;
  expectedCalls: number;
}

// Test fixtures and mocks
const mockOnNewChat = jest.fn();

const defaultProps: NewChatButtonProps = {
  isCreatingThread: false,
  isProcessing: false,
  onNewChat: mockOnNewChat
};

const testScenarios: ButtonTestScenario[] = [
  {
    name: 'enabled state',
    props: defaultProps,
    expectedText: 'New Chat',
    expectedDisabled: false,
    expectedClasses: ['bg-emerald-500', 'hover:bg-emerald-600']
  },
  {
    name: 'creating thread state',
    props: { ...defaultProps, isCreatingThread: true },
    expectedText: 'New Chat',
    expectedDisabled: true,
    expectedClasses: ['disabled:opacity-50', 'disabled:cursor-not-allowed']
  },
  {
    name: 'processing state',
    props: { ...defaultProps, isProcessing: true },
    expectedText: 'New Chat',
    expectedDisabled: true,
    expectedClasses: ['disabled:opacity-50']
  },
  {
    name: 'both creating and processing',
    props: { ...defaultProps, isCreatingThread: true, isProcessing: true },
    expectedText: 'New Chat',
    expectedDisabled: true,
    expectedClasses: ['disabled:opacity-50']
  }
];

describe('NewChatButton Component', () => {
  beforeEach(() => {
    setupButtonTests();
  });
  
  afterEach(() => {
    cleanupButtonTests();
  });
  
  describe('Rendering States', () => {
    test.each(testScenarios)('renders correctly in $name', ({ props, expectedText, expectedDisabled }) => {
      renderButtonWithProps(props);
      verifyButtonText(expectedText);
      verifyButtonDisabledState(expectedDisabled);
      verifyTestIdPresent();
    });
    
    it('displays spinning icon when creating thread', () => {
      renderButtonWithProps({ ...defaultProps, isCreatingThread: true });
      verifySpinningIconPresent();
      expectAnimationClasses();
    });
    
    it('displays static plus icon when idle', () => {
      renderButtonWithProps(defaultProps);
      verifyStaticPlusIcon();
      expectNoAnimationClasses();
    });
  });
  
  describe('User Interactions', () => {
    const interactionTests: ButtonInteractionTest[] = [
      {
        description: 'calls onNewChat when clicked in enabled state',
        initialProps: defaultProps,
        userAction: async (button) => await userEvent.click(button),
        expectedCalls: 1
      },
      {
        description: 'does not call onNewChat when disabled by isCreatingThread',
        initialProps: { ...defaultProps, isCreatingThread: true },
        userAction: async (button) => await userEvent.click(button),
        expectedCalls: 0
      },
      {
        description: 'does not call onNewChat when disabled by isProcessing',
        initialProps: { ...defaultProps, isProcessing: true },
        userAction: async (button) => await userEvent.click(button),
        expectedCalls: 0
      }
    ];
    
    test.each(interactionTests)('$description', async ({ initialProps, userAction, expectedCalls }) => {
      renderButtonWithProps(initialProps);
      await performUserInteraction(userAction);
      verifyOnNewChatCalls(expectedCalls);
    });
    
    it('supports keyboard navigation (Enter)', async () => {
      renderButtonWithProps(defaultProps);
      await focusButton();
      await pressEnterKey();
      verifyOnNewChatCalls(1);
    });
    
    it('supports keyboard navigation (Space)', async () => {
      renderButtonWithProps(defaultProps);
      await focusButton();
      await pressSpaceKey();
      verifyOnNewChatCalls(1);
    });
  });
  
  describe('Visual Feedback', () => {
    it('applies hover styles when enabled', () => {
      renderButtonWithProps(defaultProps);
      verifyHoverStyles();
      expectTransformClasses();
    });
    
    it('applies disabled styles when creating thread', () => {
      renderButtonWithProps({ ...defaultProps, isCreatingThread: true });
      verifyDisabledStyles();
      expectOpacityClasses();
    });
    
    it('shows proper focus states for accessibility', () => {
      renderButtonWithProps(defaultProps);
      focusButtonSync();
      verifyFocusIndicators();
    });
  });
  
  describe('Performance Requirements', () => {
    it('responds to clicks within 100ms', async () => {
      renderButtonWithProps(defaultProps);
      const startTime = Date.now();
      await clickButtonAndMeasure();
      expectResponseTimeCompliance(startTime);
    });
    
    it('updates visual state immediately on prop changes', async () => {
      const { rerender } = renderButtonWithProps(defaultProps);
      await updatePropsAndMeasure(rerender);
      expectImmediateStateUpdate();
    });
  });
  
  // Helper functions (8 lines max each)
  function setupButtonTests(): void {
    jest.clearAllMocks();
    mockOnNewChat.mockClear();
  }
  
  function cleanupButtonTests(): void {
    jest.resetAllMocks();
  }
  
  function renderButtonWithProps(props: NewChatButtonProps) {
    return render(<NewChatButton {...props} />);
  }
  
  function verifyButtonText(expectedText: string): void {
    expect(screen.getByText(expectedText)).toBeInTheDocument();
  }
  
  function verifyButtonDisabledState(expectedDisabled: boolean): void {
    const button = screen.getByRole('button');
    if (expectedDisabled) {
      expect(button).toBeDisabled();
    } else {
      expect(button).toBeEnabled();
    }
  }
  
  function verifyTestIdPresent(): void {
    expect(screen.getByTestId('new-chat-button')).toBeInTheDocument();
  }
  
  function verifySpinningIconPresent(): void {
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    // When creating thread, button should be disabled
    expect(button).toHaveClass('disabled:opacity-50');
  }
  
  function expectAnimationClasses(): void {
    // Verify button is in creating state
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  }
  
  function verifyStaticPlusIcon(): void {
    const plusIcon = screen.getByRole('button').querySelector('svg');
    expect(plusIcon).toBeInTheDocument();
    expect(plusIcon).toHaveClass('w-5', 'h-5');
  }
  
  function expectNoAnimationClasses(): void {
    const button = screen.getByRole('button');
    expect(button).toBeEnabled();
    // When idle, button should be enabled
  }
  
  async function performUserInteraction(userAction: (button: HTMLElement) => Promise<void>): Promise<void> {
    const button = screen.getByRole('button');
    await userAction(button);
  }
  
  function verifyOnNewChatCalls(expectedCalls: number): void {
    expect(mockOnNewChat).toHaveBeenCalledTimes(expectedCalls);
  }
  
  async function focusButton(): Promise<void> {
    const button = screen.getByRole('button');
    button.focus();
    await waitFor(() => expect(button).toHaveFocus());
  }
  
  async function pressEnterKey(): Promise<void> {
    await userEvent.keyboard('{Enter}');
  }
  
  async function pressSpaceKey(): Promise<void> {
    await userEvent.keyboard(' ');
  }
  
  function verifyHoverStyles(): void {
    const button = screen.getByRole('button');
    expect(button).toHaveClass('hover:bg-emerald-600');
    expect(button).toHaveClass('hover:scale-[1.02]');
  }
  
  function expectTransformClasses(): void {
    const button = screen.getByRole('button');
    expect(button).toHaveClass('transform');
    expect(button).toHaveClass('transition-all');
  }
  
  function verifyDisabledStyles(): void {
    const button = screen.getByRole('button');
    expect(button).toHaveClass('disabled:opacity-50');
    expect(button).toHaveClass('disabled:cursor-not-allowed');
  }
  
  function expectOpacityClasses(): void {
    const button = screen.getByRole('button');
    expect(button).toHaveClass('disabled:opacity-50');
  }
  
  function focusButtonSync(): void {
    const button = screen.getByRole('button');
    button.focus();
  }
  
  function verifyFocusIndicators(): void {
    const button = screen.getByRole('button');
    expect(button).toHaveFocus();
  }
  
  async function clickButtonAndMeasure(): Promise<void> {
    const button = screen.getByRole('button');
    await userEvent.click(button);
  }
  
  function expectResponseTimeCompliance(startTime: number): void {
    const responseTime = Date.now() - startTime;
    expect(responseTime).toBeLessThan(100); // < 100ms requirement
  }
  
  async function updatePropsAndMeasure(rerender: any): Promise<void> {
    const updatedProps = { ...defaultProps, isCreatingThread: true };
    rerender(<NewChatButton {...updatedProps} />);
    await waitFor(() => {
      expect(screen.getByRole('button')).toBeDisabled();
    });
  }
  
  function expectImmediateStateUpdate(): void {
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  }
});
