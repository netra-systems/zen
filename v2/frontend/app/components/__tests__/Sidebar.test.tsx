
import React from 'react';
import { render, screen } from '@testing-library/react';
import { Sidebar } from '../Sidebar';

describe('Sidebar', () => {
  it('renders the sidebar with navigation links', () => {
    render(<Sidebar />);
    
    // Check for the logo and title
    expect(screen.getByText('Netra')).toBeInTheDocument();

    // Check for navigation links
    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /settings/i })).toBeInTheDocument();
  });
});
