
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useAppStore from '@/store';
import { apiService } from '@/api';
import { config } from '@/config';

export default function DevLoginPage() {
  const router = useRouter();
  const { setToken, fetchUser } = useAppStore();

  useEffect(() => {
    const loginAsDev = async () => {
      try {
        const response = await apiService.post(config.api.endpoints.devLogin, {});
        const { access_token } = response;
        localStorage.setItem('authToken', access_token);
        setToken(access_token);
        await fetchUser(access_token);
        router.push('/');
      } catch (error) {
        console.error('Failed to login as dev user', error);
      }
    };

    loginAsDev();
  }, [router, setToken, fetchUser]);

  return <div>Loading...</div>;
}
