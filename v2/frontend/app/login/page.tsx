
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import useAppStore from '@/store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Icons } from '@/components/Icons';
import { config } from '@/config';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, authError, isLoading } = useAppStore();
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    await login(formData);
    if (!authError) {
      router.push('/');
    }
  };

  const handleGoogleLogin = () => {
    const googleLoginUrl = `${config.api.baseUrl}${config.api.endpoints.googleLogin}`;
    console.log('Redirecting to Google Login:', googleLoginUrl);
    window.location.href = googleLoginUrl;
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-lg shadow-md">
        <div className="text-center">
          <h1 className="text-3xl font-bold">Login</h1>
          <p className="text-gray-500">Enter your credentials to access your account</p>
        </div>
        {authError && (
          <div className="p-4 text-center text-red-500 bg-red-100 rounded-md">
            {authError}
          </div>
        )}
        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1"
            />
          </div>
          <Button type="submit" className="w-full">
            Login
          </Button>
        </form>
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="px-2 bg-white text-muted-foreground">
              Or continue with
            </span>
          </div>
        </div>
        <div>
          <Button variant="outline" className="w-full" onClick={handleGoogleLogin}>
            <Icons.google className="w-4 h-4 mr-2" />
            Continue with Google
          </Button>
        </div>
      </div>
    </div>
  );
}
