'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useAppStore from '@/store';
import { useAuth } from '@/hooks/useAuth';

export default function AuthCallbackPage() {
  const router = useRouter();
  const { fetchUser } = useAppStore();
  const { login } = useAuth();

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    if (token) {
      document.cookie = `access_token=${token}; path=/; samesite=lax;`;
      fetchUser(token).then(() => {
        router.push('/');
      });
    } else {
      login();
    }
  }, [fetchUser, router, login]);

  return <div>Loading...</div>;
}