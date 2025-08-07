import { render, screen } from '@testing-library/react';
import { AppLayout } from '../AppLayout';
import { useAuth } from '@/hooks/useAuth';

jest.mock('@/hooks/useAuth');

describe('AppLayout', () => {
  it('renders the sidebar, header, and main content when authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({ isAuthenticated: true });
    render(<AppLayout><div>Main Content</div></AppLayout>);
    expect(screen.getByRole('banner')).toBeInTheDocument(); 
    expect(screen.getByRole('navigation')).toBeInTheDocument(); 
    expect(screen.getByText('Main Content')).toBeInTheDocument();
  });

  it('renders only the main content when not authenticated and not on the login page', () => {
    (useAuth as jest.Mock).mockReturnValue({ isAuthenticated: false });
    render(<AppLayout><div>Main Content</div></AppLayout>);
    expect(screen.queryByRole('banner')).not.toBeInTheDocument();
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.getByText('Main Content')).toBeInTheDocument();
  });
});