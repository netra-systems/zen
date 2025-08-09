import { render, screen, fireEvent } from '@testing-library/react';
import { AppWithLayout } from '@/components/AppWithLayout';
import { authService } from '@/services/auth';

// Mock the useAuth hook
jest.mock('@/services/auth', () => ({
  authService: {
    useAuth: jest.fn(),
  }
}));

// Mock the Sidebar and Header components
jest.mock('@/components/Sidebar', () => ({
  Sidebar: () => <div data-testid="sidebar">Sidebar</div>,
}));
jest.mock('@/components/Header', () => ({
  Header: ({ toggleSidebar }) => (
    <button onClick={toggleSidebar} data-testid="header">
      Header
    </button>
  ),
}));

describe('AppWithLayout', () => {
  it('renders the Header and Sidebar when the user is authenticated', () => {
    // Arrange
    (authService.useAuth as jest.Mock).mockReturnValue({ user: { full_name: 'Test User' } });

    // Act
    render(<AppWithLayout><div>Child</div></AppWithLayout>);

    // Assert
    expect(screen.getByTestId('header')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  it('does not render the Sidebar when it is toggled off', () => {
    // Arrange
    (authService.useAuth as jest.Mock).mockReturnValue({ user: { full_name: 'Test User' } });

    // Act
    render(<AppWithLayout><div>Child</div></AppWithLayout>);
    fireEvent.click(screen.getByTestId('header'));

    // Assert
    expect(screen.queryByTestId('sidebar')).not.toBeInTheDocument();
  });
});
