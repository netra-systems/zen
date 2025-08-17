/**
 * UI Interaction Integration Tests
 * Tests for navigation, routing, and performance functionality
 */

import React from 'react';
import { render, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';
import { TestProviders } from '../test-utils/providers';
import { setupTestEnvironment, clearStorages, resetStores, cleanupWebSocket } from './helpers/test-setup';
import { assertTextContent } from './helpers/test-assertions';

// Mock Next.js
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
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

describe('UI Interaction Integration Tests', () => {
  let server: WS;
  
  beforeEach(() => {
    server = setupTestEnvironment();
    clearStorages();
    resetStores();
    mockPush.mockClear();
  });

  afterEach(() => {
    cleanupWebSocket();
  });

  describe('Navigation and Routing', () => {
    it('should handle navigation between views', async () => {
      const router = require('next/navigation').useRouter();
      
      const NavigationComponent = () => {
        const [currentView, setCurrentView] = React.useState('home');
        
        const navigate = (view: string) => {
          setCurrentView(view);
          router.push(`/${view}`);
        };
        
        return (
          <div>
            <nav>
              <button onClick={() => navigate('home')}>Home</button>
              <button onClick={() => navigate('chat')}>Chat</button>
              <button onClick={() => navigate('settings')}>Settings</button>
            </nav>
            <div data-testid="current-view">{currentView}</div>
          </div>
        );
      };
      
      const { getByText, getByTestId } = render(
        <TestProviders>
          <NavigationComponent />
        </TestProviders>
      );
      
      await assertTextContent(getByTestId('current-view'), 'home');
      
      fireEvent.click(getByText('Chat'));
      
      await assertTextContent(getByTestId('current-view'), 'chat');
      expect(router.push).toHaveBeenCalledWith('/chat');
      
      fireEvent.click(getByText('Settings'));
      
      await assertTextContent(getByTestId('current-view'), 'settings');
      expect(router.push).toHaveBeenCalledWith('/settings');
    });
  });

  describe('Performance and Optimization', () => {
    it('should debounce rapid input changes', async () => {
      let apiCallCount = 0;
      
      const DebouncedSearch = () => {
        const [query, setQuery] = React.useState('');
        const [results, setResults] = React.useState([]);
        
        React.useEffect(() => {
          const timer = setTimeout(() => {
            if (query) {
              apiCallCount++;
              setResults([`Result for ${query}`]);
            }
          }, 300);
          
          return () => clearTimeout(timer);
        }, [query]);
        
        return (
          <div>
            <input
              data-testid="search-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div data-testid="results">
              {results.map((r, i) => <div key={i}>{r}</div>)}
            </div>
            <div data-testid="api-calls">{apiCallCount}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(
        <TestProviders>
          <DebouncedSearch />
        </TestProviders>
      );
      const input = getByTestId('search-input');
      
      fireEvent.change(input, { target: { value: 't' } });
      fireEvent.change(input, { target: { value: 'te' } });
      fireEvent.change(input, { target: { value: 'test' } });
      
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 400));
      });
      
      expect(apiCallCount).toBe(1);
      await assertTextContent(getByTestId('results'), 'Result for test');
    });

    it('should implement virtual scrolling for large lists', async () => {
      const VirtualList = () => {
        const items = Array.from({ length: 10000 }, (_, i) => `Item ${i}`);
        const [visibleStart, setVisibleStart] = React.useState(0);
        const itemHeight = 30;
        const containerHeight = 300;
        const visibleCount = Math.ceil(containerHeight / itemHeight);
        
        const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
          const scrollTop = e.currentTarget.scrollTop;
          const newStart = Math.floor(scrollTop / itemHeight);
          setVisibleStart(newStart);
        };
        
        const visibleItems = items.slice(visibleStart, visibleStart + visibleCount);
        
        return (
          <div
            data-testid="virtual-list"
            style={{ height: containerHeight, overflow: 'auto' }}
            onScroll={handleScroll}
          >
            <div style={{ height: items.length * itemHeight }}>
              {visibleItems.map((item, index) => (
                <div
                  key={visibleStart + index}
                  style={{
                    height: itemHeight,
                    position: 'absolute',
                    top: (visibleStart + index) * itemHeight
                  }}
                >
                  {item}
                </div>
              ))}
            </div>
            <div data-testid="visible-count">{visibleItems.length}</div>
          </div>
        );
      };
      
      const { getByTestId } = render(
        <TestProviders>
          <VirtualList />
        </TestProviders>
      );
      
      const visibleCount = parseInt(getByTestId('visible-count').textContent || '0');
      expect(visibleCount).toBeLessThan(20);
    });
  });

  describe('Form Interactions', () => {
    it('should handle form validation and submission', async () => {
      const FormComponent = () => {
        const [email, setEmail] = React.useState('');
        const [errors, setErrors] = React.useState<string[]>([]);
        const [submitted, setSubmitted] = React.useState(false);
        
        const validateEmail = (email: string): boolean => {
          return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
        };
        
        const handleSubmit = (e: React.FormEvent) => {
          e.preventDefault();
          const newErrors: string[] = [];
          
          if (!email) newErrors.push('Email is required');
          else if (!validateEmail(email)) newErrors.push('Invalid email format');
          
          setErrors(newErrors);
          
          if (newErrors.length === 0) {
            setSubmitted(true);
          }
        };
        
        return (
          <form onSubmit={handleSubmit}>
            <input
              data-testid="email-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter email"
            />
            <button type="submit">Submit</button>
            <div data-testid="errors">
              {errors.map((error, i) => (
                <div key={i}>{error}</div>
              ))}
            </div>
            {submitted && (
              <div data-testid="success">Form submitted successfully!</div>
            )}
          </form>
        );
      };
      
      const { getByText, getByTestId } = render(
        <TestProviders>
          <FormComponent />
        </TestProviders>
      );
      
      fireEvent.click(getByText('Submit'));
      await assertTextContent(getByTestId('errors'), 'Email is required');
      
      const emailInput = getByTestId('email-input');
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
      fireEvent.click(getByText('Submit'));
      await assertTextContent(getByTestId('errors'), 'Invalid email format');
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.click(getByText('Submit'));
      await assertTextContent(getByTestId('success'), 'Form submitted successfully!');
    });

    it('should handle keyboard interactions', async () => {
      const KeyboardComponent = () => {
        const [keyPressed, setKeyPressed] = React.useState('');
        const [enterCount, setEnterCount] = React.useState(0);
        
        const handleKeyDown = (e: React.KeyboardEvent) => {
          setKeyPressed(e.key);
          if (e.key === 'Enter') {
            setEnterCount(prev => prev + 1);
          }
        };
        
        return (
          <div>
            <input
              data-testid="keyboard-input"
              onKeyDown={handleKeyDown}
              placeholder="Press keys..."
            />
            <div data-testid="key-pressed">Last key: {keyPressed}</div>
            <div data-testid="enter-count">Enter pressed: {enterCount} times</div>
          </div>
        );
      };
      
      const { getByTestId } = render(
        <TestProviders>
          <KeyboardComponent />
        </TestProviders>
      );
      const input = getByTestId('keyboard-input');
      
      fireEvent.keyDown(input, { key: 'a' });
      await assertTextContent(getByTestId('key-pressed'), 'Last key: a');
      
      fireEvent.keyDown(input, { key: 'Enter' });
      await assertTextContent(getByTestId('key-pressed'), 'Last key: Enter');
      await assertTextContent(getByTestId('enter-count'), 'Enter pressed: 1 times');
      
      fireEvent.keyDown(input, { key: 'Enter' });
      await assertTextContent(getByTestId('enter-count'), 'Enter pressed: 2 times');
    });
  });
});