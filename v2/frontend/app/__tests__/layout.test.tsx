import { render, screen } from '@testing-library/react';
import { useAuth } from '../hooks/useAuth';
import { AppWithLayout } from '@/components/AppWithLayout';

jest.mock('@/hooks/useAuth');

describe('AppWithLayout', () => {
  it('renders sidebar and header for authenticated users', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: { full_name: 'Test User' } });
    render(<AppWithLayout><div>Test Content</div></AppWithLayout>);
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('complementary')).toBeInTheDocument();
  });

  it('renders sidebar and header for unauthenticated users', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: null });
    render(<AppWithLayout><div>Test Content</div></AppWithLayout>);
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('complementary')).toBeInTheDocument();
  });
});