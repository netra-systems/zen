import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
// Using Jest, not vitest
import { ErrorFallback } from '@/components/ErrorFallback';
import { Header } from '@/components/Header';
import { NavLinks } from '@/components/NavLinks';
// react-router-dom not used in Next.js

// Test 62: ErrorFallback recovery
describe('test_ErrorFallback_recovery', () => {
  it('should display error boundary correctly', () => {
    const error = new Error('Test error');
    const resetErrorBoundary = jest.fn();
    
    render(
      <ErrorFallback error={error} resetErrorBoundary={resetErrorBoundary} />
    );
    
    expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument();
    expect(screen.getByText(/Test error/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Try again/i })).toBeInTheDocument();
  });

  it('should handle recovery actions', () => {
    const error = new Error('Test error');
    const resetErrorBoundary = jest.fn();
    
    render(
      <ErrorFallback error={error} resetErrorBoundary={resetErrorBoundary} />
    );
    
    const retryButton = screen.getByRole('button', { name: /Try again/i });
    fireEvent.click(retryButton);
    
    expect(resetErrorBoundary).toHaveBeenCalledTimes(1);
  });

  it('should display stack trace in development mode', () => {
    const error = new Error('Test error');
    error.stack = 'Error: Test error\n    at TestComponent (test.js:10:5)';
    const resetErrorBoundary = jest.fn();
    
    // Mock development environment
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';
    
    render(
      <ErrorFallback error={error} resetErrorBoundary={resetErrorBoundary} />
    );
    
    expect(screen.getByText(/test.js:10:5/i)).toBeInTheDocument();
    
    process.env.NODE_ENV = originalEnv;
  });
});

// Test 63: Header navigation
describe('test_Header_navigation', () => {
  it('should render header components correctly', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
    
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByAltText(/Netra/i)).toBeInTheDocument();
  });

  it('should handle navigation interactions', async () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
    
    const homeLink = screen.getByRole('link', { name: /Home/i });
    expect(homeLink).toHaveAttribute('href', '/');
    
    const chatLink = screen.getByRole('link', { name: /Chat/i });
    expect(chatLink).toHaveAttribute('href', '/chat');
  });

  it('should show responsive menu on mobile', () => {
    // Mock mobile viewport
    window.innerWidth = 375;
    window.dispatchEvent(new Event('resize'));
    
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
    
    const menuButton = screen.getByRole('button', { name: /Menu/i });
    expect(menuButton).toBeInTheDocument();
    
    fireEvent.click(menuButton);
    expect(screen.getByRole('navigation')).toHaveClass('mobile-menu');
  });
});

// Test 64: NavLinks routing  
describe('test_NavLinks_routing', () => {
  it('should render navigation links correctly', () => {
    render(
      <BrowserRouter>
        <NavLinks />
      </BrowserRouter>
    );
    
    expect(screen.getByRole('link', { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Chat/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Settings/i })).toBeInTheDocument();
  });

  it('should highlight active route', () => {
    window.history.pushState({}, '', '/chat');
    
    render(
      <BrowserRouter>
        <NavLinks />
      </BrowserRouter>
    );
    
    const chatLink = screen.getByRole('link', { name: /Chat/i });
    expect(chatLink).toHaveClass('active');
  });

  it('should handle navigation correctly', () => {
    const mockNavigate = jest.fn();
    
    render(
      <BrowserRouter>
        <NavLinks onNavigate={mockNavigate} />
      </BrowserRouter>
    );
    
    const settingsLink = screen.getByRole('link', { name: /Settings/i });
    fireEvent.click(settingsLink);
    
    expect(window.location.pathname).toBe('/settings');
  });
});