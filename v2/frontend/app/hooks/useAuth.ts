
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export const useAuth = () => {
  const [user, setUser] = useState(null);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = async () => {
      if (process.env.NODE_ENV === 'development') {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          setUser(JSON.parse(storedUser));
        } else {
          try {
            const response = await fetch('/api/auth/dev-login');
            if (response.ok) {
              const devUser = await response.json();
              localStorage.setItem('user', JSON.stringify(devUser));
              setUser(devUser);
            } else {
              router.push('/login');
            }
          } catch (error) {
            console.error('Dev login failed', error);
            router.push('/login');
          }
        }
      } else {
        // In production, you would have a proper auth check here
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          setUser(JSON.parse(storedUser));
        } else {
          router.push('/login');
        }
      }
    };

    checkAuth();
  }, [router]);

  return { user };
};
