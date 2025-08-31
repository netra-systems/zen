import { renderHook } from '@testing-library/react';
import { useThreadSidebarActions } from '@/components/chat/ThreadSidebarActions';

// Mock dependencies
jest.mock('@/store/threadStore', () => ({
  useThreadStore: jest.fn(() => ({}))
}));

jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => ({
    clearMessages: jest.fn()
  }))
}));

jest.mock('@/hooks/useThreadSwitching', () => ({
  useThreadSwitching: jest.fn(() => ({
    state: { isLoading: false },
    switchToThread: jest.fn()
  }))
}));

jest.mock('@/hooks/useThreadCreation', () => ({
  useThreadCreation: jest.fn(() => ({
    state: { isCreating: false },
    createAndNavigate: jest.fn()
  }))
}));

jest.mock('@/hooks/useAuthState', () => ({
  useAuthState: jest.fn(() => ({
    isAuthenticated: true
  }))
}));

describe('ThreadSidebarActions - Timestamp Handling', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  describe('formatDate function', () => {
        setupAntiHang();
      jest.setTimeout(10000);
    let result: ReturnType<typeof useThreadSidebarActions>;

    beforeEach(() => {
      const { result: hookResult } = renderHook(() => useThreadSidebarActions());
      result = hookResult.current;
    });

    describe('ISO string timestamps', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should correctly format ISO string timestamp from today', () => {
        const isoString = new Date().toISOString();
        const formatted = result.formatDate(isoString);
        expect(formatted).toBe('Today');
      });

      it('should correctly format ISO string timestamp from yesterday', () => {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const isoString = yesterday.toISOString();
        const formatted = result.formatDate(isoString);
        expect(formatted).toBe('Yesterday');
      });

      it('should correctly format ISO string timestamp from 3 days ago', () => {
        const threeDaysAgo = new Date();
        threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
        const isoString = threeDaysAgo.toISOString();
        const formatted = result.formatDate(isoString);
        expect(formatted).toBe('3 days ago');
      });

      it('should correctly format ISO string timestamp from 10 days ago', () => {
        const tenDaysAgo = new Date();
        tenDaysAgo.setDate(tenDaysAgo.getDate() - 10);
        const isoString = tenDaysAgo.toISOString();
        const formatted = result.formatDate(isoString);
        expect(formatted).toMatch(/^\d{1,2}\/\d{1,2}\/\d{4}$/);
      });

      it('should handle ISO string with timezone offset', () => {
        const isoString = '2024-01-15T10:30:00.000Z';
        const formatted = result.formatDate(isoString);
        expect(formatted).not.toBe('Invalid date');
        expect(formatted).toBeTruthy();
      });

      it('should handle ISO string without milliseconds', () => {
        const isoString = '2024-01-15T10:30:00Z';
        const formatted = result.formatDate(isoString);
        expect(formatted).not.toBe('Invalid date');
        expect(formatted).toBeTruthy();
      });
    });

    describe('Unix timestamp handling', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should correctly format Unix timestamp in seconds (backend format)', () => {
        const unixSeconds = Math.floor(Date.now() / 1000);
        const formatted = result.formatDate(unixSeconds);
        expect(formatted).toBe('Today');
      });

      it('should correctly format Unix timestamp from yesterday', () => {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const unixSeconds = Math.floor(yesterday.getTime() / 1000);
        const formatted = result.formatDate(unixSeconds);
        expect(formatted).toBe('Yesterday');
      });

      it('should correctly format Unix timestamp from 5 days ago', () => {
        const fiveDaysAgo = new Date();
        fiveDaysAgo.setDate(fiveDaysAgo.getDate() - 5);
        const unixSeconds = Math.floor(fiveDaysAgo.getTime() / 1000);
        const formatted = result.formatDate(unixSeconds);
        expect(formatted).toBe('5 days ago');
      });

      it('should NOT multiply Unix timestamps by 1000 again if already in milliseconds', () => {
        // This tests the regression - if we get milliseconds, don't multiply again
        const nowMs = Date.now();
        // The function should detect this is already in milliseconds (too large for seconds)
        // and handle it appropriately
        const formatted = result.formatDate(nowMs);
        // This would show a date far in the future if incorrectly multiplied by 1000
        expect(formatted).not.toMatch(/^\d{1,2}\/\d{1,2}\/\d{4}$/);
      });
    });

    describe('Edge cases and error handling', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should handle null timestamp gracefully', () => {
        const formatted = result.formatDate(null as any);
        expect(formatted).toBeTruthy();
        expect(formatted).not.toBe('Invalid date');
      });

      it('should handle undefined timestamp gracefully', () => {
        const formatted = result.formatDate(undefined as any);
        expect(formatted).toBeTruthy();
        expect(formatted).not.toBe('Invalid date');
      });

      it('should handle empty string gracefully', () => {
        const formatted = result.formatDate('');
        expect(formatted).toBeTruthy();
        expect(formatted).not.toBe('Invalid date');
      });

      it('should handle invalid date string gracefully', () => {
        const formatted = result.formatDate('not-a-date');
        expect(formatted).toBeTruthy();
        expect(formatted).not.toBe('Invalid date');
      });

      it('should handle negative Unix timestamp', () => {
        const formatted = result.formatDate(-1);
        expect(formatted).toBeTruthy();
        expect(formatted).not.toBe('Invalid date');
      });

      it('should handle zero timestamp', () => {
        const formatted = result.formatDate(0);
        expect(formatted).toBeTruthy();
        expect(formatted).not.toBe('Invalid date');
      });
    });

    describe('Regression prevention tests', () => {
          setupAntiHang();
        jest.setTimeout(10000);
      it('should NOT treat ISO strings as Unix timestamps', () => {
        // This is the core regression issue - ISO strings were being multiplied by 1000
        const isoString = '2024-01-15T10:30:00.000Z';
        const formatted = result.formatDate(isoString);
        
        // If incorrectly treated as Unix timestamp and multiplied by 1000,
        // this would show an invalid or far future date
        expect(formatted).not.toBe('Invalid date');
        expect(formatted).toBeTruthy();
        
        // Should show a reasonable date
        const date = new Date(isoString);
        const now = new Date();
        const daysDiff = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
        
        if (daysDiff === 0) {
          expect(formatted).toBe('Today');
        } else if (daysDiff === 1) {
          expect(formatted).toBe('Yesterday');
        } else if (daysDiff < 7) {
          expect(formatted).toBe(`${daysDiff} days ago`);
        } else {
          expect(formatted).toMatch(/^\d{1,2}\/\d{1,2}\/\d{4}$/);
        }
      });

      it('should handle mixed timestamp formats in the same session', () => {
        // Test that the function can handle both formats correctly in sequence
        const isoString = new Date().toISOString();
        const unixSeconds = Math.floor(Date.now() / 1000);
        
        const formattedIso = result.formatDate(isoString);
        const formattedUnix = result.formatDate(unixSeconds);
        
        expect(formattedIso).toBe('Today');
        expect(formattedUnix).toBe('Today');
      });

      it('should produce consistent results for the same date in different formats', () => {
        const testDate = new Date('2024-01-15T10:30:00.000Z');
        const isoString = testDate.toISOString();
        const unixSeconds = Math.floor(testDate.getTime() / 1000);
        
        const formattedIso = result.formatDate(isoString);
        const formattedUnix = result.formatDate(unixSeconds);
        
        expect(formattedIso).toBe(formattedUnix);
      });
    });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});