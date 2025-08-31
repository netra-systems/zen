/**
 * Context State Management Test
 * Tests React Context for state management and data flow
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

interface AppState {
  user: { name: string; email: string } | null;
  theme: 'light' | 'dark';
  notifications: string[];
  isLoading: boolean;
}

type AppAction = 
  | { type: 'SET_USER'; payload: { name: string; email: string } }
  | { type: 'CLEAR_USER' }
  | { type: 'SET_THEME'; payload: 'light' | 'dark' }
  | { type: 'ADD_NOTIFICATION'; payload: string }
  | { type: 'CLEAR_NOTIFICATIONS' }
  | { type: 'SET_LOADING'; payload: boolean };

const initialState: AppState = {
  user: null,
  theme: 'light',
  notifications: [],
  isLoading: false
};

const appReducer = (state: AppState, action: AppAction): AppState => {
  switch (action.type) {
    case 'SET_USER':
      return { ...state, user: action.payload };
    case 'CLEAR_USER':
      return { ...state, user: null };
    case 'SET_THEME':
      return { ...state, theme: action.payload };
    case 'ADD_NOTIFICATION':
      return { ...state, notifications: [...state.notifications, action.payload] };
    case 'CLEAR_NOTIFICATIONS':
      return { ...state, notifications: [] };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    default:
      return state;
  }
};

const AppContext = React.createContext<{
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
} | null>(null);

const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = React.useReducer(appReducer, initialState);
  
  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
};

const useAppContext = () => {
  const context = React.useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return context;
};

describe('Context State Management', () => {
      setupAntiHang();
    jest.setTimeout(10000);
  it('should provide initial state to consumers', () => {
    const TestComponent: React.FC = () => {
      const { state } = useAppContext();
      
      return (
        <div>
          <div data-testid="user-status">
            User: {state.user ? state.user.name : 'Not logged in'}
          </div>
          <div data-testid="theme">{state.theme}</div>
          <div data-testid="notifications-count">
            Notifications: {state.notifications.length}
          </div>
          <div data-testid="loading-status">
            Loading: {state.isLoading ? 'true' : 'false'}
          </div>
        </div>
      );
    };

    render(
      <AppProvider>
        <TestComponent />
      </AppProvider>
    );

    expect(screen.getByTestId('user-status')).toHaveTextContent('User: Not logged in');
    expect(screen.getByTestId('theme')).toHaveTextContent('light');
    expect(screen.getByTestId('notifications-count')).toHaveTextContent('Notifications: 0');
    expect(screen.getByTestId('loading-status')).toHaveTextContent('Loading: false');
  });

  it('should handle user authentication state changes', () => {
    const AuthComponent: React.FC = () => {
      const { state, dispatch } = useAppContext();
      
      const login = () => {
        dispatch({
          type: 'SET_USER',
          payload: { name: 'John Doe', email: 'john@example.com' }
        });
      };
      
      const logout = () => {
        dispatch({ type: 'CLEAR_USER' });
      };
      
      return (
        <div>
          <div data-testid="auth-status">
            {state.user ? `Welcome, ${state.user.name}` : 'Please log in'}
          </div>
          <div data-testid="user-email">
            {state.user ? state.user.email : 'No email'}
          </div>
          {!state.user ? (
            <button data-testid="login-button" onClick={login}>
              Login
            </button>
          ) : (
            <button data-testid="logout-button" onClick={logout}>
              Logout
            </button>
          )}
        </div>
      );
    };

    render(
      <AppProvider>
        <AuthComponent />
      </AppProvider>
    );

    // Initially not logged in
    expect(screen.getByTestId('auth-status')).toHaveTextContent('Please log in');
    expect(screen.getByTestId('user-email')).toHaveTextContent('No email');

    // Login
    fireEvent.click(screen.getByTestId('login-button'));
    
    expect(screen.getByTestId('auth-status')).toHaveTextContent('Welcome, John Doe');
    expect(screen.getByTestId('user-email')).toHaveTextContent('john@example.com');

    // Logout
    fireEvent.click(screen.getByTestId('logout-button'));
    
    expect(screen.getByTestId('auth-status')).toHaveTextContent('Please log in');
    expect(screen.getByTestId('user-email')).toHaveTextContent('No email');
  });

  it('should manage notifications state', () => {
    const NotificationComponent: React.FC = () => {
      const { state, dispatch } = useAppContext();
      
      const addNotification = () => {
        dispatch({
          type: 'ADD_NOTIFICATION',
          payload: `Notification ${state.notifications.length + 1}`
        });
      };
      
      const clearNotifications = () => {
        dispatch({ type: 'CLEAR_NOTIFICATIONS' });
      };
      
      return (
        <div>
          <div data-testid="notification-count">
            Count: {state.notifications.length}
          </div>
          <div data-testid="notifications-list">
            {state.notifications.map((notification, index) => (
              <div key={index} data-testid={`notification-${index}`}>
                {notification}
              </div>
            ))}
          </div>
          <button data-testid="add-notification" onClick={addNotification}>
            Add Notification
          </button>
          <button data-testid="clear-notifications" onClick={clearNotifications}>
            Clear All
          </button>
        </div>
      );
    };

    render(
      <AppProvider>
        <NotificationComponent />
      </AppProvider>
    );

    // Initially no notifications
    expect(screen.getByTestId('notification-count')).toHaveTextContent('Count: 0');

    // Add first notification
    fireEvent.click(screen.getByTestId('add-notification'));
    
    expect(screen.getByTestId('notification-count')).toHaveTextContent('Count: 1');
    expect(screen.getByTestId('notification-0')).toHaveTextContent('Notification 1');

    // Add second notification
    fireEvent.click(screen.getByTestId('add-notification'));
    
    expect(screen.getByTestId('notification-count')).toHaveTextContent('Count: 2');
    expect(screen.getByTestId('notification-1')).toHaveTextContent('Notification 2');

    // Clear all notifications
    fireEvent.click(screen.getByTestId('clear-notifications'));
    
    expect(screen.getByTestId('notification-count')).toHaveTextContent('Count: 0');
    expect(screen.queryByTestId('notification-0')).not.toBeInTheDocument();
  });

  it('should handle theme switching', () => {
    const ThemeComponent: React.FC = () => {
      const { state, dispatch } = useAppContext();
      
      const toggleTheme = () => {
        dispatch({
          type: 'SET_THEME',
          payload: state.theme === 'light' ? 'dark' : 'light'
        });
      };
      
      return (
        <div style={{ backgroundColor: state.theme === 'dark' ? '#333' : '#fff' }}>
          <div data-testid="current-theme">Theme: {state.theme}</div>
          <button data-testid="toggle-theme" onClick={toggleTheme}>
            Toggle Theme
          </button>
        </div>
      );
    };

    render(
      <AppProvider>
        <ThemeComponent />
      </AppProvider>
    );

    // Initially light theme
    expect(screen.getByTestId('current-theme')).toHaveTextContent('Theme: light');

    // Toggle to dark theme
    fireEvent.click(screen.getByTestId('toggle-theme'));
    
    expect(screen.getByTestId('current-theme')).toHaveTextContent('Theme: dark');

    // Toggle back to light theme
    fireEvent.click(screen.getByTestId('toggle-theme'));
    
    expect(screen.getByTestId('current-theme')).toHaveTextContent('Theme: light');
  });

  it('should throw error when context is used outside provider', () => {
    const ComponentWithoutProvider: React.FC = () => {
      const { state } = useAppContext();
      return <div>{state.theme}</div>;
    };

    // Mock console.error to avoid error output in test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<ComponentWithoutProvider />);
    }).toThrow('useAppContext must be used within AppProvider');

    consoleSpy.mockRestore();
  });

  it('should handle loading state management', async () => {
    const LoadingComponent: React.FC = () => {
      const { state, dispatch } = useAppContext();
      
      const simulateAsyncOperation = async () => {
        dispatch({ type: 'SET_LOADING', payload: true });
        
        // Simulate async work
        await new Promise(resolve => setTimeout(resolve, 100));
        
        dispatch({ type: 'SET_LOADING', payload: false });
        dispatch({ type: 'ADD_NOTIFICATION', payload: 'Operation completed' });
      };
      
      return (
        <div>
          <div data-testid="loading-state">
            Loading: {state.isLoading ? 'true' : 'false'}
          </div>
          <button data-testid="start-operation" onClick={simulateAsyncOperation}>
            Start Operation
          </button>
          <div data-testid="operation-result">
            {state.notifications.includes('Operation completed') ? 'Completed' : 'Not started'}
          </div>
        </div>
      );
    };

    render(
      <AppProvider>
        <LoadingComponent />
      </AppProvider>
    );

    // Initially not loading
    expect(screen.getByTestId('loading-state')).toHaveTextContent('Loading: false');
    expect(screen.getByTestId('operation-result')).toHaveTextContent('Not started');

    // Start operation
    fireEvent.click(screen.getByTestId('start-operation'));
    
    // Should be loading
    expect(screen.getByTestId('loading-state')).toHaveTextContent('Loading: true');

    // Wait for operation to complete
    await waitFor(() => {
      expect(screen.getByTestId('loading-state')).toHaveTextContent('Loading: false');
      expect(screen.getByTestId('operation-result')).toHaveTextContent('Completed');
    }, { timeout: 200 });
  });
  afterEach(() => {
    cleanupAntiHang();
  });

});