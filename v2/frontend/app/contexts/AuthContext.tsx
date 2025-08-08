import { createContext, useContext, useEffect, ReactNode } from 'react';
import useAppStore from '@/store';
import { User } from '@/types';
import { Button } from '@/components/ui/button';

interface AuthContextType {
  user: User | null;
  login: () => void;
  logout: () => void;
  loading: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { user, devLogin, logout, isLoading, setUser } = useAppStore();

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await fetch('/api/v3/auth/user');
        if (response.ok) {
          const user = await response.json();
          setUser(user);
        } else if (process.env.NODE_ENV === 'development') {
          devLogin();
        }
      } catch (error) {
        console.error('Failed to fetch user', error);
        if (process.env.NODE_ENV === 'development') {
          devLogin();
        }
      }
    };
    fetchUser();
  }, [devLogin, setUser]);

  const login = () => {
    window.location.href = '/api/v3/auth/login';
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading: isLoading }}>
      {isLoading ? (
        <div>Loading...</div>
      ) : user ? (
        children
      ) : (
        <div className="flex items-center justify-center h-screen">
          <Button onClick={login} size="lg">Login with Google</Button>
        </div>
      )}
    </AuthContext.Provider>
  );
}