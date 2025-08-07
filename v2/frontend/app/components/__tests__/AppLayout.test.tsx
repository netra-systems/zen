
import { render, screen } from '@testing-library/react';
import { AppLayout } from '../AppLayout';
import { useAuth, AuthProvider } from '../../../hooks/useAuth';

jest.mock('../../../hooks/useAuth');

import { AuthProvider } from '../../../hooks/useAuth';

describe('AppLayout', () => {
  it('renders the sidebar, header, and main content when authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({ isAuthenticated: true });
    render(<AuthProvider><AppLayout><div>Main Content</div></AppLayout></AuthProvider>);
    expect(screen.getByRole('banner')).toBeInTheDocument(); 
    expect(screen.getByRole('navigation')).toBeInTheDocument(); 
    expect(screen.getByText('Main Content')).toBeInTheDocument();
  });

  it('renders only the main content when not authenticated and not on the login page', () => {
    (useAuth as jest.Mock).mockReturnValue({ isAuthenticated: false });
    render(<AuthProvider><AppLayout><div>Main Content</div></AppLayout></AuthProvider>);
    expect(screen.queryByRole('banner')).not.toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.getByText('Main Content')).toBeInTheDocument();
  });
});
