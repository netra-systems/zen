
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { AuthProvider } from '@/contexts/AuthContext';
import { authService } from '@/services/auth';
import { mockUser, mockAuthConfig } from '@/mocks/auth';

// Mock the authService
jest.mock('@/services/auth', () => ({
  authService: {
    getAuthConfig: jest.fn(),
    handleLogin: jest.fn(),
    handleLogout: jest.fn(),
    useAuth: jest.fn(),
  },
}));

const TestComponent = () => {
  const { user, login, logout } = authService.useAuth();
  return user ? (
    <div>
      <span>Welcome, {user.full_name}</span>
      <button onClick={logout}>Logout</button>
    </div>
  ) : (
    <button onClick={login}>Login with Google</button>
  );
};

describe('AuthProvider', () => {
  beforeEach(() => {
    // Reset the mock before each test
    (authService.getAuthConfig as jest.Mock).mockClear();
    (authService.handleLogin as jest.Mock).mockClear();
    (authService.handleLogout as jest.Mock).mockClear();
    (authService.useAuth as jest.Mock).mockReturnValue({
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      loading: true,
    });
  });

  it('should show loading state initially, then login button', async () => {
    (authService.getAuthConfig as jest.Mock).mockResolvedValue(mockAuthConfig);
    (authService.useAuth as jest.Mock).mockReturnValueOnce({
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      loading: true,
    }).mockReturnValueOnce({
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });

    expect(screen.getByText('Login with Google')).toBeInTheDocument();
  });

  it('should show user info when authenticated', async () => {
    (authService.getAuthConfig as jest.Mock).mockResolvedValue({ ...mockAuthConfig, user: mockUser });
    (authService.useAuth as jest.Mock).mockReturnValueOnce({
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      loading: true,
    }).mockReturnValueOnce({
      user: mockUser,
      login: jest.fn(),
      logout: jest.fn(),
      loading: false,
    });

    const { getByText, queryByText } = render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(queryByText('Loading...')).not.toBeInTheDocument();
    });

    await waitFor(() => {
      expect(getByText(`Welcome, ${mockUser.full_name}`)).toBeInTheDocument();
    });
  });

  it('should call login function on button click', async () => {
    const mockLogin = jest.fn();
    (authService.getAuthConfig as jest.Mock).mockResolvedValue(mockAuthConfig);
    (authService.useAuth as jest.Mock).mockReturnValue({
      user: null,
      login: mockLogin,
      logout: jest.fn(),
      loading: false,
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      fireEvent.click(screen.getByText('Login with Google'));
    });

    expect(mockLogin).toHaveBeenCalled();
  });

  it('should call logout function on button click', async () => {
    const mockLogout = jest.fn();
    (authService.getAuthConfig as jest.Mock).mockResolvedValue({ ...mockAuthConfig, user: mockUser });
    (authService.useAuth as jest.Mock).mockReturnValue({
      user: mockUser,
      login: jest.fn(),
      logout: mockLogout,
      loading: false,
    });

    const { getByText } = render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      fireEvent.click(getByText('Logout'));
    });

    expect(mockLogout).toHaveBeenCalled();
  });
});
