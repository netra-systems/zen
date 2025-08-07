import { useEffect, useState } from 'react';

const useAuth = () => {
  const [user, setUser] = useState(null);
  const [authEndpoints, setAuthEndpoints] = useState(null);

  useEffect(() => {
    const fetchAuthEndpoints = async () => {
      const response = await fetch('/api/v3/auth/endpoints');
      const data = await response.json();
      setAuthEndpoints(data);
    };

    const fetchUser = async () => {
      const response = await fetch('/api/v3/auth/user');
      if (response.ok) {
        const data = await response.json();
        setUser(data);
      }
    };

    fetchAuthEndpoints();
    fetchUser();
  }, []);

  const login = () => {
    if (authEndpoints) {
      window.location.href = authEndpoints.login;
    }
  };

  const logout = () => {
    if (authEndpoints) {
      window.location.href = authEndpoints.logout;
    }
  };

  return { user, login, logout };
};

export default useAuth;
