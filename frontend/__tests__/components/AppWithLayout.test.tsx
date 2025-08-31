import { render, screen, fireEvent } from '@testing-library/react';
import { AppWithLayout } from '@/components/AppWithLayout';
import { Header } from '@/components/Header';
import { ChatSidebar } from '@/components/chat/ChatSidebar';
import { setupAntiHang, cleanupAntiHang } from '@/__tests__/utils/anti-hanging-test-utilities';

// Mock the store
jest.mock('@/store', () => ({
  useAppStore: jest.fn(),
}));

// Mock external dependencies that ChatSidebar needs
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: jest.fn(() => ({
    isProcessing: false,
    activeThreadId: null,
  })),
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: jest.fn(() => ({
    isDeveloperOrHigher: () => false,
  })),
}));

jest.mock('@/hooks/useAuthState', () => ({
  useAuthState: jest.fn(() => ({
    isAuthenticated: false,
    userTier: 'Free',
  })),
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: jest.fn(() => ({
    sendMessage: jest.fn(),
  })),
}));

jest.mock('@/components/Icons', () => ({
  Icons: {
    logo: () => <div data-testid="logo">Logo</div>,
  },
}));

jest.mock('@/components/LoginButton', () => ({
  __esModule: true,
  default: () => <div data-testid="login-button">Login</div>,
}));

describe('AppWithLayout', () => {
    jest.setTimeout(10000);
  beforeEach(() => {
    const { useAppStore } = require('@/store');
    jest.mocked(useAppStore).mockReturnValue({
      isSidebarCollapsed: false,
      toggleSidebar: jest.fn(),
    });
  });

  it('renders the Header and Sidebar when sidebar is not collapsed', () => {
    // Act
    render(<AppWithLayout><div>Child</div></AppWithLayout>);

    // Assert - Look for actual header element and sidebar content
    expect(screen.getByRole('banner')).toBeInTheDocument(); // Header has header role
    expect(screen.getByTestId('chat-sidebar')).toBeInTheDocument(); // ChatSidebar has this testid
  });

  it('does not render the Sidebar when it is collapsed', () => {
    // Arrange
    const { useAppStore } = require('@/store');
    const toggleSidebar = jest.fn();
    jest.mocked(useAppStore).mockReturnValue({
      isSidebarCollapsed: true,
      toggleSidebar,
    });

    // Act
    render(<AppWithLayout><div>Child</div></AppWithLayout>);

    // Assert
    expect(screen.getByRole('banner')).toBeInTheDocument(); // Header still present
    expect(screen.queryByTestId('chat-sidebar')).not.toBeInTheDocument(); // Sidebar hidden
  });

  it('calls toggleSidebar when header button is clicked', () => {
    // Arrange
    const { useAppStore } = require('@/store');
    const toggleSidebar = jest.fn();
    jest.mocked(useAppStore).mockReturnValue({
      isSidebarCollapsed: false,
      toggleSidebar,
    });

    // Act
    render(<AppWithLayout><div>Child</div></AppWithLayout>);
    
    // Find the toggle button in the Header component (outline variant with icon)
    const toggleButton = screen.getByRole('button', { name: /toggle navigation menu/i });
    fireEvent.click(toggleButton);

    // Assert
    expect(toggleSidebar).toHaveBeenCalled();
  });
});
