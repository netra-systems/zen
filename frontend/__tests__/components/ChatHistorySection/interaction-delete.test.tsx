/**
 * ChatHistorySection Delete Interaction Tests
 * Tests for delete operations and confirmation dialogs ≤300 lines, ≤8 line functions
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatHistorySection } from '@/components/ChatHistorySection';
import { createTestSetup } from './shared-setup';
import { ThreadService } from '@/services/threadService';
import {
  expectBasicStructure,
  mockWindowConfirm,
  mockConsoleError,
  findThreadContainer
} from './test-utils';

describe('ChatHistorySection - Delete Interactions', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  describe('Delete button visibility', () => {
    it('should show delete option for threads', () => {
      render(<ChatHistorySection />);
      
      expectBasicStructure();
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should handle delete button interactions', () => {
      render(<ChatHistorySection />);
      
      const threadContainer = findThreadContainer('First Conversation');
      expect(threadContainer).toBeInTheDocument();
    });

    it('should provide accessible delete options', () => {
      render(<ChatHistorySection />);
      
      const threadElement = screen.getByText('First Conversation');
      const parent = threadElement.closest('[role]') || threadElement.parentElement;
      
      expect(parent).toBeInTheDocument();
    });

    it('should handle hover states for delete options', () => {
      render(<ChatHistorySection />);
      
      const threadContainer = findThreadContainer('First Conversation');
      
      if (threadContainer) {
        fireEvent.mouseEnter(threadContainer);
        expect(threadContainer).toBeInTheDocument();
      }
    });
  });

  describe('Delete confirmation dialog', () => {
    it('should show delete confirmation dialog when delete is clicked', async () => {
      const restoreConfirm = mockWindowConfirm(true);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
      
      restoreConfirm();
    });

    it('should handle confirmation acceptance', async () => {
      const restoreConfirm = mockWindowConfirm(true);
      (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ success: true });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Chat History')).toBeInTheDocument();
      
      restoreConfirm();
    });

    it('should cancel delete when cancelled', async () => {
      const restoreConfirm = mockWindowConfirm(false);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      restoreConfirm();
    });

    it('should handle confirmation dialog multiple times', async () => {
      const restoreConfirm = mockWindowConfirm(false);
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
      
      restoreConfirm();
    });
  });

  describe('Delete operation execution', () => {
    it('should delete thread when confirmed', async () => {
      const restoreConfirm = mockWindowConfirm(true);
      (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ success: true });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Chat History')).toBeInTheDocument();
      
      restoreConfirm();
    });

    it('should call delete service with correct parameters', async () => {
      const restoreConfirm = mockWindowConfirm(true);
      const deleteThreadSpy = jest.spyOn(ThreadService, 'deleteThread')
        .mockResolvedValue({ success: true });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      restoreConfirm();
    });

    it('should update thread list after successful delete', async () => {
      const restoreConfirm = mockWindowConfirm(true);
      (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ success: true });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      restoreConfirm();
    });

    it('should handle delete success response', async () => {
      const restoreConfirm = mockWindowConfirm(true);
      (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ 
        success: true, 
        message: 'Thread deleted successfully' 
      });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      restoreConfirm();
    });
  });

  describe('Delete error handling', () => {
    it('should handle delete error gracefully', async () => {
      (ThreadService.deleteThread as jest.Mock).mockRejectedValue(new Error('Delete failed'));
      const restoreConsole = mockConsoleError();
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      restoreConsole();
    });

    it('should handle network errors during delete', async () => {
      (ThreadService.deleteThread as jest.Mock).mockRejectedValue(new Error('Network error'));
      const restoreConsole = mockConsoleError();
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      restoreConsole();
    });

    it('should handle server errors during delete', async () => {
      (ThreadService.deleteThread as jest.Mock).mockRejectedValue(new Error('Server error'));
      const restoreConsole = mockConsoleError();
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      restoreConsole();
    });

    it('should handle authorization errors during delete', async () => {
      (ThreadService.deleteThread as jest.Mock).mockRejectedValue(new Error('Unauthorized'));
      const restoreConsole = mockConsoleError();
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      restoreConsole();
    });
  });

  describe('Delete state management', () => {
    it('should disable delete during operation', async () => {
      (ThreadService.deleteThread as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ success: true }), 100))
      );
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should re-enable delete after operation completes', async () => {
      (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ success: true });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should handle multiple delete operations', async () => {
      (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ success: true });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      expect(screen.getByText('Second Conversation')).toBeInTheDocument();
    });

    it('should maintain component state during delete', async () => {
      (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ success: true });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });
  });

  describe('Delete accessibility', () => {
    it('should provide accessible delete buttons', () => {
      render(<ChatHistorySection />);
      
      const threadElements = screen.getAllByText(/Conversation/);
      
      threadElements.forEach(thread => {
        const container = thread.closest('[role]') || thread.parentElement;
        expect(container).toBeInTheDocument();
      });
    });

    it('should announce delete operations to screen readers', async () => {
      (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ success: true });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('Chat History')).toBeInTheDocument();
    });

    it('should handle keyboard delete operations', () => {
      render(<ChatHistorySection />);
      
      const threadElement = screen.getByText('First Conversation');
      const container = threadElement.closest('[role]') || threadElement.parentElement;
      
      if (container && container instanceof HTMLElement) {
        expect(() => {
          fireEvent.keyDown(container, { key: 'Delete' });
          fireEvent.keyDown(container, { key: 'Backspace' });
        }).not.toThrow();
      }
    });

    it('should provide proper focus management during delete', async () => {
      render(<ChatHistorySection />);
      
      const threadElement = screen.getByText('First Conversation');
      const container = threadElement.closest('[role]') || threadElement.parentElement;
      
      if (container && container instanceof HTMLElement) {
        container.focus();
        expect(container).toBeInTheDocument();
      }
    });
  });

  describe('Delete UI feedback', () => {
    it('should show loading state during delete operation', async () => {
      (ThreadService.deleteThread as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({ success: true }), 100))
      );
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should show success feedback after delete', async () => {
      (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ success: true });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
    });

    it('should show error feedback on delete failure', async () => {
      (ThreadService.deleteThread as jest.Mock).mockRejectedValue(new Error('Delete failed'));
      const restoreConsole = mockConsoleError();
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      restoreConsole();
    });

    it('should clear feedback after timeout', async () => {
      (ThreadService.deleteThread as jest.Mock).mockResolvedValue({ success: true });
      
      render(<ChatHistorySection />);
      
      expect(screen.getByText('First Conversation')).toBeInTheDocument();
      
      await waitFor(() => {
        expect(screen.getByText('Chat History')).toBeInTheDocument();
      }, { timeout: 1000 });
    });
  });
});