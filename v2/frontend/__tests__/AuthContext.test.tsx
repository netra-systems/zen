import { render, screen, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import * as auth from '@/services/auth';
import { mockAuthConfig, mockUser } from '@/mocks/auth';

jest.mock('@/services/auth');

const mockGetAuthConfig = auth.getAuthConfig as jest.Mock;

// A simple component that consumes the context and displays the user's ID.
const TestComponent = () => {
  const { user } = useAuth();
  return user ? <div data-testid="test-component-user-id">{user.id}</div> : null;
};

describe('AuthProvider', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should show loading state initially, then login button', async () => {
    mockGetAuthConfig.mockResolvedValue(mockAuthConfig);
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
    });
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Login with Google')).toBeInTheDocument();
    });
  });

  it('should show user info when authenticated', async () => {
    mockGetAuthConfig.mockResolvedValue({ ...mockAuthConfig, user: mockUser });
    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
    });
    await waitFor(() => {
      expect(screen.getByText(`Welcome, ${mockUser.full_name}`)).toBeInTheDocument();
      expect(screen.getByTestId('test-component-user-id')).toHaveTextContent(mockUser.id);
    });
  });

  it('should call login function on button click', async () => {
    mockGetAuthConfig.mockResolvedValue(mockAuthConfig);
    const mockLogin = jest.spyOn(auth, 'handleLogin').mockImplementation(() => {});

    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
    });

    const loginButton = await screen.findByText('Login with Google');
    await act(async () => {
      loginButton.click();
    });

    expect(mockLogin).toHaveBeenCalledWith(mockAuthConfig);
  });

  it('should call logout function on button click', async () => {
    const authConfigWithUser = { ...mockAuthConfig, user: mockUser };
    mockGetAuthConfig.mockResolvedValue(authConfigWithUser);
    const mockLogout = jest.spyOn(auth, 'handleLogout').mockImplementation(() => {});

    await act(async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );
    });

    const logoutButton = await screen.findByText('Logout');
    await act(async () => {
      logoutButton.click();
    });

    expect(mockLogout).toHaveBeenCalledWith(authConfigWithUser);
  });
});
