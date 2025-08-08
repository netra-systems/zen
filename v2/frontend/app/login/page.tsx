'use client';

import React from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';

const LoginPage: React.FC = () => {
  const { login } = useAuth();

  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-8">Welcome to Netra</h1>
        <Button size="lg" onClick={login}>
          Login with Google
        </Button>
      </div>
    </div>
  );
};

export default LoginPage;