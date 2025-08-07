import React from 'react';
import { render, screen } from '@testing-library/react';
import { Sidebar } from '../Sidebar';

describe('Sidebar', () => {
  it('renders the sidebar with navigation links', () => {
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
});