'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useAppStore from '@/store';

export default function AuthCallbackPage() {
  const router = useRouter();
  const { fetchUser } = useAppStore();

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    if (token) {
      document.cookie = `access_token=${token}; path=/; samesite=lax;`;
      fetchUser(token).then(() => {
        router.push('/');
      });
    } else {
      router.push('/login');
    }
  }, [fetchUser, router]);

  return <div>Loading...</div>;
}
