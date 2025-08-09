import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, AuthContext } from '@/contexts/AuthContext';
import { authService } from '@/services/auth';
import { mockUser, mockAuthConfig } from '@/mocks/auth';

// Mock the authService
jest.mock('@/services/auth', () => ({
  authService: {
    getAuthConfig: jest.fn(),
    handleLogin: jest.fn(),
    handleLogout: jest.fn(),
  },
}));

describe('AuthProvider', () => {
  beforeEach(() => {
    // Reset the mock before each test
    (authService.getAuthConfig as jest.Mock).mockClear();
    (authService.handleLogin as jest.Mock).mockClear();
    (authService.handleLogout as jest.Mock).mockClear();
  });

  it('should show loading state initially', () => {
    (authService.getAuthConfig as jest.Mock).mockResolvedValue(new Promise(() => {})); // Never resolves
    render(
      <AuthProvider>
        <AuthContext.Consumer>
          {value => <span>{value.loading ? 'Loading...' : 'Loaded'}</span>}
        </AuthContext.Consumer>
      </AuthProvider>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('should show user info when authenticated', async () => {
    (authService.getAuthConfig as jest.Mock).mockResolvedValue({ ...mockAuthConfig, user: mockUser });
    render(
      <AuthProvider>
        <AuthContext.Consumer>
          {value => (
            <div>
              <span>{value.loading ? 'Loading...' : 'Loaded'}</span>
              {value.user && <span>Welcome, {value.user.full_name}</span>}
            </div>
          )}
        </AuthContext.Consumer>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(`Welcome, ${mockUser.full_name}`)).toBeInTheDocument();
    });
  });

  it('should not show user info when not authenticated', async () => {
    (authService.getAuthConfig as jest.Mock).mockResolvedValue(mockAuthConfig);
    render(
      <AuthProvider>
        <AuthContext.Consumer>
          {value => (
            <div>
              <span>{value.loading ? 'Loading...' : 'Loaded'}</span>
              {value.user && <span>Welcome, {value.user.full_name}</span>}
            </div>
          )}
        </AuthContext.Consumer>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Loaded')).toBeInTheDocument();
    });

    expect(screen.queryByText(`Welcome, ${mockUser.full_name}`)).not.toBeInTheDocument();
  });
});