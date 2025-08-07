
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Sidebar } from '../Sidebar';
import { useAuth } from '@/providers/auth';

jest.mock('@/providers/auth');

describe('Sidebar', () => {
  it('renders the sidebar with navigation links for an authenticated user', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: { full_name: 'Test User' } });
    render(<Sidebar />);
    
    // Check for the logo and title
    expect(screen.getByText('Netra')).toBeInTheDocument();

    // Check for navigation links
    const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
    expect(dashboardLink).toBeInTheDocument();
    expect(dashboardLink).toHaveAttribute('href', '/');
    
    // Check for the disabled Settings link
    expect(screen.getByText(/Settings/i)).toHaveClass('cursor-not-allowed');
  });

  it('renders the sidebar with a login link for an unauthenticated user', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: null });
    render(<Sidebar />);
    
    // Check for the logo and title
    expect(screen.getByText('Netra')).toBeInTheDocument();

    // Check for navigation links
    const loginLink = screen.getByRole('link', { name: /login/i });
    expect(loginLink).toBeInTheDocument();
    expect(loginLink).toHaveAttribute('href', '/login');
  });
});
