"use client";

import React, { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import useAppStore from '@/store';
import { useAuth } from '@/hooks/useAuth';

export default function CallbackClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setToken, fetchUser } = useAppStore.getState();
  const { login } = useAuth();

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      setToken(token);
      localStorage.setItem('authToken', token);
      fetchUser(token).then(() => {
        router.push('/');
      });
    } else {
      login();
    }
  }, [router, searchParams, setToken, fetchUser, login]);

  return <div>Loading...</div>;
}
