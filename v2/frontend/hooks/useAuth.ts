import { useRouter } from 'next/navigation';
import useAppStore from '@/store';

export const useAuth = () => {
  const router = useRouter();
  const { setUser } = useAppStore();

  const login = () => {
    window.location.href = 'http://localhost:8000/api/v3/auth/login';
  };

  const logout = async () => {
    await fetch('http://localhost:8000/api/v3/auth/logout');
    setUser(null);
    router.push('/login');
  };

  const handleAuthCallback = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v3/auth/me');
      if (response.ok) {
        const user = await response.json();
        setUser(user);
        return true;
      } else {
        return false;
      }
    } catch (error) {
      console.error('Authentication callback failed:', error);
      return false;
    }
  };

  return { login, logout, handleAuthCallback };
};