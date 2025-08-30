// Temporary fix for auth store mock - to be inserted into jest.setup.js

jest.mock('@/store/authStore', () => {
  // Create a proper Zustand store mock factory
  const createStoreMock = (initialState, actions) => {
    let state = { ...initialState, ...actions };
    const listeners = new Set();
    
    const storeMethods = {
      getState: () => state,
      setState: (partial) => {
        const newState = typeof partial === 'function' ? partial(state) : { ...state, ...partial };
        state = newState;
        listeners.forEach(listener => listener(state));
        // Update the hook's return value to reflect new state
        hookFunction.mockReturnValue(state);
      },
      subscribe: (listener) => {
        listeners.add(listener);
        return () => listeners.delete(listener);
      },
      destroy: () => {
        listeners.clear();
      }
    };

    // Create the hook function that returns current state
    const hookFunction = jest.fn(() => state);
    
    // Add store methods to the hook function
    Object.assign(hookFunction, storeMethods);
    
    return hookFunction;
  };

  // Initial auth state - start with secure defaults
  const getInitialState = () => ({
    isAuthenticated: false,
    user: null,
    token: null,
    loading: false,
    error: null
  });

  // Create the store mock first so we can reference it in actions
  const useAuthStore = createStoreMock(getInitialState(), {});
  
  // Now create actions that reference the store
  const storeActions = {
    // Actions
    login: jest.fn((user, token) => {
      if (global.localStorage) {
        global.localStorage.setItem('jwt_token', token || mockJWTToken);
        global.localStorage.setItem('token', token || mockJWTToken);
        global.localStorage.setItem('auth_token', token || mockJWTToken);
        global.localStorage.setItem('user_data', JSON.stringify(user || mockUser));
      }
      // Update global state
      global.mockAuthState = {
        ...global.mockAuthState,
        user: user || mockUser,
        token: token || mockJWTToken,
        isAuthenticated: true,
        error: null
      };
      // Update store state
      useAuthStore.setState({
        isAuthenticated: true,
        user: user || mockUser,
        token: token || mockJWTToken,
        error: null
      });
    }),
    logout: jest.fn(() => {
      if (global.localStorage) {
        global.localStorage.removeItem('jwt_token');
        global.localStorage.removeItem('token');
        global.localStorage.removeItem('auth_token');
        global.localStorage.removeItem('user_data');
      }
      // Update global state
      global.mockAuthState = {
        ...global.mockAuthState,
        user: null,
        token: null,
        isAuthenticated: false,
        error: null
      };
      // Update store state
      useAuthStore.setState({
        isAuthenticated: false,
        user: null,
        token: null,
        error: null
      });
    }),
    setLoading: jest.fn((loading) => {
      global.mockAuthState = {
        ...global.mockAuthState,
        loading
      };
      useAuthStore.setState({ loading });
    }),
    setError: jest.fn((error) => {
      global.mockAuthState = {
        ...global.mockAuthState,
        error
      };
      useAuthStore.setState({ error });
    }),
    updateUser: jest.fn((userUpdate) => {
      const currentState = useAuthStore.getState();
      if (currentState.user) {
        const updatedUser = { ...currentState.user, ...userUpdate };
        global.mockAuthState = {
          ...global.mockAuthState,
          user: updatedUser
        };
        useAuthStore.setState({ user: updatedUser });
      }
    }),
    updateToken: jest.fn((token) => {
      if (global.localStorage) {
        global.localStorage.setItem('jwt_token', token);
        global.localStorage.setItem('token', token);
        global.localStorage.setItem('auth_token', token);
      }
      global.mockAuthState = {
        ...global.mockAuthState,
        token: token
      };
      useAuthStore.setState({ token });
    }),
    reset: jest.fn(() => {
      if (global.localStorage) {
        global.localStorage.removeItem('jwt_token');
        global.localStorage.removeItem('token');
        global.localStorage.removeItem('auth_token');
        global.localStorage.removeItem('user_data');
      }
      global.mockAuthState = {
        isAuthenticated: false,
        user: null,
        token: null,
        loading: false,
        error: null
      };
      useAuthStore.setState({
        isAuthenticated: false,
        user: null,
        token: null,
        loading: false,
        error: null
      });
    }),
    initializeFromStorage: jest.fn(() => {
      // Mock initialization from storage
      const token = global.localStorage?.getItem('jwt_token') || global.localStorage?.getItem('token');
      const userData = global.localStorage?.getItem('user_data');
      
      if (token && userData) {
        try {
          const user = JSON.parse(userData);
          useAuthStore.setState({
            isAuthenticated: true,
            user: user,
            token: token,
            error: null
          });
        } catch (error) {
          useAuthStore.setState({
            isAuthenticated: false,
            user: null,
            token: null,
            error: null
          });
        }
      }
    }),
    
    // Permission helpers that work with current state
    hasPermission: jest.fn((permission) => {
      const state = useAuthStore.getState();
      if (!state.user) return false;
      return state.user.permissions?.includes(permission) || false;
    }),
    hasAnyPermission: jest.fn((permissions) => {
      const state = useAuthStore.getState();
      if (!state.user) return false;
      return permissions.some(p => state.user?.permissions?.includes(p)) || false;
    }),
    hasAllPermissions: jest.fn((permissions) => {
      const state = useAuthStore.getState();
      if (!state.user) return false;
      return permissions.every(p => state.user?.permissions?.includes(p)) || false;
    }),
    isAdminOrHigher: jest.fn(() => {
      const state = useAuthStore.getState();
      if (!state.user) return false;
      return ['admin', 'super_admin'].includes(state.user.role || '') || 
             state.user.is_superuser || false;
    }),
    isDeveloperOrHigher: jest.fn(() => {
      const state = useAuthStore.getState();
      if (!state.user) return false;
      return ['developer', 'admin', 'super_admin'].includes(state.user.role || '') || 
             state.user.is_developer || 
             state.user.is_superuser || false;
    })
  };

  // Add actions to the store state
  useAuthStore.setState({ ...useAuthStore.getState(), ...storeActions });

  return { useAuthStore };
});