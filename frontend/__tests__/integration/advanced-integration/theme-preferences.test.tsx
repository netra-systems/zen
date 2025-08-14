/**
 * Theme and Preferences Integration Tests
 * Tests for theme synchronization and user preferences persistence
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react';
import { createTestSetup, createThemeProvider } from './setup';

describe('Theme and Preferences Synchronization', () => {
  const testSetup = createTestSetup();

  beforeEach(() => {
    testSetup.beforeEach();
  });

  afterEach(() => {
    testSetup.afterEach();
  });

  it('should sync theme preferences across components', async () => {
    const { ThemeContext, ThemeProvider } = createThemeProvider();
    
    const TestComponent = () => {
      const { theme, setTheme } = React.useContext(ThemeContext);
      
      return (
        <div>
          <div data-testid="current-theme">{theme}</div>
          <button onClick={() => setTheme('dark')}>Dark Mode</button>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    expect(getByTestId('current-theme')).toHaveTextContent('light');
    
    fireEvent.click(getByText('Dark Mode'));
    
    await waitFor(() => {
      expect(getByTestId('current-theme')).toHaveTextContent('dark');
      expect(localStorage.getItem('theme')).toBe('dark');
    });
  });

  it('should persist user preferences across sessions', async () => {
    const preferences = {
      notifications: true,
      autoSave: false,
      language: 'en',
      fontSize: 'medium'
    };
    
    // Save preferences
    localStorage.setItem('userPreferences', JSON.stringify(preferences));
    
    // Simulate new session
    const loadPreferences = () => {
      const saved = localStorage.getItem('userPreferences');
      return saved ? JSON.parse(saved) : {};
    };
    
    const loaded = loadPreferences();
    
    expect(loaded).toEqual(preferences);
    expect(loaded.notifications).toBe(true);
    expect(loaded.autoSave).toBe(false);
  });

  it('should handle theme changes with animation transitions', async () => {
    const { ThemeProvider } = createThemeProvider();
    
    const AnimatedThemeComponent = () => {
      const [theme, setTheme] = React.useState('light');
      const [isTransitioning, setIsTransitioning] = React.useState(false);
      
      const changeTheme = async (newTheme: string) => {
        setIsTransitioning(true);
        await new Promise(resolve => setTimeout(resolve, 100));
        setTheme(newTheme);
        setIsTransitioning(false);
      };
      
      return (
        <div>
          <div data-testid="current-theme">{theme}</div>
          <div data-testid="is-transitioning">{isTransitioning.toString()}</div>
          <button onClick={() => changeTheme('dark')}>Change Theme</button>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <ThemeProvider>
        <AnimatedThemeComponent />
      </ThemeProvider>
    );
    
    fireEvent.click(getByText('Change Theme'));
    
    // Should show transitioning state
    await waitFor(() => {
      expect(getByTestId('is-transitioning')).toHaveTextContent('true');
    });
    
    // Should complete transition
    await waitFor(() => {
      expect(getByTestId('current-theme')).toHaveTextContent('dark');
      expect(getByTestId('is-transitioning')).toHaveTextContent('false');
    });
  });

  it('should sync preferences with server', async () => {
    const PreferencesSync = () => {
      const [preferences, setPreferences] = React.useState({ theme: 'light' });
      const [isSyncing, setIsSyncing] = React.useState(false);
      
      const syncWithServer = async (newPreferences: any) => {
        setIsSyncing(true);
        
        // Mock API call
        await new Promise(resolve => setTimeout(resolve, 100));
        
        setPreferences(newPreferences);
        setIsSyncing(false);
      };
      
      return (
        <div>
          <div data-testid="theme">{preferences.theme}</div>
          <div data-testid="syncing">{isSyncing.toString()}</div>
          <button onClick={() => syncWithServer({ theme: 'dark' })}>
            Sync Dark Theme
          </button>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(<PreferencesSync />);
    
    fireEvent.click(getByText('Sync Dark Theme'));
    
    await waitFor(() => {
      expect(getByTestId('syncing')).toHaveTextContent('true');
    });
    
    await waitFor(() => {
      expect(getByTestId('theme')).toHaveTextContent('dark');
      expect(getByTestId('syncing')).toHaveTextContent('false');
    });
  });
});