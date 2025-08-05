import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Header } from '../Header';
import useAppStore from '../../store';

// A more robust mock for the Zustand store
const mockStore = {
  user: null,
  logout: () => {},
};

jest.mock('../../store', () => {
  return jest.fn((selector) => {
    if (!selector) {
      return mockStore;
    }
    return selector(mockStore);
  });
});

describe('Header', () => {
  afterEach(() => {
    // Reset the mock before each test
    mockStore.user = null;
    mockStore.logout = () => {};
    (useAppStore as jest.Mock).mockClear();
  });

  it('renders login button when user is not authenticated', () => {
    render(<Header />);
    const loginButton = screen.getByRole('link', { name: /login/i });
    expect(loginButton).toBeInTheDocument();
  });

  it('renders user menu when user is authenticated', () => {
    mockStore.user = { id: 1, full_name: 'John Doe', email: 'john.doe@example.com' };
    render(<Header />);
    const userMenu = screen.getByRole('button', { name: /toggle user menu/i });
    expect(userMenu).toBeInTheDocument();
  });

  it('calls logout when logout button is clicked', async () => {
    const logoutMock = jest.fn();
    mockStore.user = { id: 1, full_name: 'John Doe', email: 'john.doe@example.com' };
    mockStore.logout = logoutMock;

    render(<Header />);
    const userMenu = screen.getByRole('button', { name: /toggle user menu/i });
    await userEvent.click(userMenu);

    const logoutButton = await screen.findByText(/logout/i);
    await userEvent.click(logoutButton);

    expect(logoutMock).toHaveBeenCalled();
  });
});