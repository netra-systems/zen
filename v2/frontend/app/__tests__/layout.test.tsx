'use client';

import { render, screen } from '@testing-library/react';
import RootLayout, { AppWithLayout } from '../layout';
import { useAuth } from '@/hooks/useAuth';
import useAppStore from '@/store';

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
  usePathname: () => '/',
}));

import { useAuth } from '@/providers/auth';

jest.mock('@/providers/auth', () => ({
  useAuth: jest.fn()
}));

jest.mock('@/store', () => jest.fn());

describe('RootLayout', () => {
  it('renders the sidebar and header when authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: { email: 'test@example.com' } });
    (useAppStore as jest.Mock).mockReturnValue({ user: { email: 'test@example.com' } });
    render(<AppWithLayout><div>Main Content</div></AppWithLayout>);
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('complementary')).toBeInTheDocument();
  });

  it('does not render the sidebar and header when not authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: null });
    (useAppStore as jest.Mock).mockReturnValue({ user: null });
    render(<AppWithLayout><div>Main Content</div></AppWithLayout>);
    expect(screen.queryByRole('banner')).not.toBeInTheDocument();
    expect(screen.queryByRole('complementary')).not.toBeInTheDocument();
  });
});
