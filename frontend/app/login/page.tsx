'use client';

import { authService } from '@/auth';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

export default function LoginPage() {
  const { login, loading, user, authConfig } = authService.useAuth();
  const router = useRouter();
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [email, setEmail] = useState('dev@example.com');
  const [password, setPassword] = useState('dev');
  const [error, setError] = useState('');

  // Redirect if already logged in
  useEffect(() => {
    if (user && !loading) {
      router.push('/chat');
    }
  }, [user, loading, router]);

  // Development mode - use dev login directly
  const handleDevLogin = async () => {
    if (!authConfig?.development_mode) {
      setError('Not in development mode');
      return;
    }

    try {
      setIsLoggingIn(true);
      setError('');
      
      // Call dev login endpoint directly
      const response = await fetch(authConfig.endpoints.dev_login, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        throw new Error(`Login failed: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Store token and reload to trigger auth context update
      if (data.access_token) {
        localStorage.setItem('jwt_token', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token);
        }
        // Force reload to reinitialize auth context with new token
        window.location.href = '/chat';
      }
    } catch (err) {
      console.error('Dev login failed:', err);
      setError(err instanceof Error ? err.message : 'Login failed');
      setIsLoggingIn(false);
    }
  };

  // Production mode - use OAuth
  const handleOAuthLogin = async () => {
    try {
      setIsLoggingIn(true);
      await login();
    } catch (err) {
      console.error('OAuth login failed:', err);
      setError(err instanceof Error ? err.message : 'Login failed');
      setIsLoggingIn(false);
    }
  };

  // Show loading while checking auth status
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  // Development mode login
  if (authConfig?.development_mode) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="flex items-center justify-center gap-3 mb-4">
              <CardTitle className="text-3xl font-bold">Netra</CardTitle>
              <Badge variant="beta" className="text-sm px-3 py-1">DEV</Badge>
            </div>
            <CardDescription>Development Environment Login</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Quick access dev login */}
            <div className="space-y-2">
              <Button 
                onClick={() => handleDevLogin()} 
                disabled={isLoggingIn}
                className="w-full"
                size="lg"
                variant="default"
              >
                {isLoggingIn ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Logging in...
                  </>
                ) : (
                  'Quick Dev Login (dev@example.com)'
                )}
              </Button>
              <p className="text-xs text-center text-muted-foreground">
                One-click access with default dev account
              </p>
            </div>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-muted-foreground">Or use custom credentials</span>
              </div>
            </div>

            {/* Custom credentials form */}
            <div className="space-y-3">
              <Input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoggingIn}
              />
              <Input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoggingIn}
                onKeyPress={(e) => e.key === 'Enter' && handleDevLogin()}
              />
              <Button 
                onClick={handleDevLogin}
                disabled={isLoggingIn || !email || !password}
                className="w-full"
                variant="outline"
              >
                Login with Custom Credentials
              </Button>
            </div>

            {error && (
              <div className="text-sm text-red-600 text-center bg-red-50 p-2 rounded">
                {error}
              </div>
            )}

            <div className="text-xs text-center text-muted-foreground pt-2">
              Development mode active • No OAuth required
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Production mode login
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <div className="flex items-center justify-center gap-3 mb-8">
          <h1 className="text-4xl font-bold">Netra</h1>
          <Badge variant="beta" className="text-sm px-3 py-1">BETA</Badge>
        </div>
        <p className="text-muted-foreground mb-6">Welcome to the Netra Beta Program</p>
        <Button onClick={handleOAuthLogin} disabled={isLoggingIn} size="lg">
          {isLoggingIn ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Loading...
            </>
          ) : (
            'Access Beta'
          )}
        </Button>
        {error && (
          <div className="text-sm text-red-600 mt-4">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}