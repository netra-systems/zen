"use client";

import React, { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import useAppStore from '@/app/store';

export default function AuthCallback() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { fetchUser } = useAppStore();

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      localStorage.setItem('authToken', token);
      fetchUser(token).then(() => {
        router.push('/');
      });
    } else {
      router.push('/login');
    }
  }, [router, searchParams, fetchUser]);

  return <div>Loading...</div>;
}
