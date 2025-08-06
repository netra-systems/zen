"use client";

import React, { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import useAppStore from '@/store';

export default function CallbackClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setToken, fetchUser } = useAppStore();

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      setToken(token);
      localStorage.setItem('authToken', token);
      fetchUser(token).then(() => {
        router.push('/dashboard');
      });
    } else {
      router.push('/login');
    }
  }, [router, searchParams, setToken, fetchUser]);

  return <div>Loading...</div>;
}