'use client';

import { render, screen } from '@testing-library/react';
import { AppWithLayout } from '../layout';
import { useAuth } from '@/hooks/useAuth';

jest.mock('@/hooks/useAuth', () => ({
  useAuth: jest.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}));

describe('RootLayout', () => {
  it('renders the sidebar and header when authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({ isAuthenticated: true });
    render(<AppWithLayout><div>Main Content</div></AppWithLayout>);
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('complementary')).toBeInTheDocument();
  });

  it('does not render the sidebar and header when not authenticated and not on the login page', () => {
    (useAuth as jest.Mock).mockReturnValue({ isAuthenticated: false });
    render(<AppWithLayout><div>Main Content</div></AppWithLayout>);
    expect(screen.queryByRole('banner')).not.toBeInTheDocument();
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
  });
});
