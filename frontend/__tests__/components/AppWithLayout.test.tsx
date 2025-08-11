import { render, screen, fireEvent } from '@testing-library/react';
import { AppWithLayout } from '@/components/AppWithLayout';

// Mock the store
jest.mock('@/store', () => ({
  useAppStore: jest.fn(),
}));

// Mock the ChatSidebar and Header components
jest.mock('@/components/chat/ChatSidebar', () => ({
  ChatSidebar: () => <div data-testid="sidebar">ChatSidebar</div>,
}));
jest.mock('@/components/Header', () => ({
  Header: ({ toggleSidebar }: { toggleSidebar: () => void }) => (
    <button onClick={toggleSidebar} data-testid="header">
      Header
    </button>
  ),
}));

describe('AppWithLayout', () => {
  beforeEach(() => {
    const { useAppStore } = require('@/store');
    (useAppStore as jest.Mock).mockReturnValue({
      isSidebarCollapsed: false,
      toggleSidebar: jest.fn(),
    });
  });

  it('renders the Header and Sidebar when sidebar is not collapsed', () => {
    // Act
    render(<AppWithLayout><div>Child</div></AppWithLayout>);

    // Assert
    expect(screen.getByTestId('header')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
  });

  it('does not render the Sidebar when it is collapsed', () => {
    // Arrange
    const { useAppStore } = require('@/store');
    const toggleSidebar = jest.fn();
    (useAppStore as jest.Mock).mockReturnValue({
      isSidebarCollapsed: true,
      toggleSidebar,
    });

    // Act
    render(<AppWithLayout><div>Child</div></AppWithLayout>);

    // Assert
    expect(screen.getByTestId('header')).toBeInTheDocument();
    expect(screen.queryByTestId('sidebar')).not.toBeInTheDocument();
  });

  it('calls toggleSidebar when header button is clicked', () => {
    // Arrange
    const { useAppStore } = require('@/store');
    const toggleSidebar = jest.fn();
    (useAppStore as jest.Mock).mockReturnValue({
      isSidebarCollapsed: false,
      toggleSidebar,
    });

    // Act
    render(<AppWithLayout><div>Child</div></AppWithLayout>);
    fireEvent.click(screen.getByTestId('header'));

    // Assert
    expect(toggleSidebar).toHaveBeenCalled();
  });
});
