'use client';

import React from 'react';
import { Button, Card, CardHeader, CardBody } from '@nextui-org/react';

export default function LoginPage() {
  const handleGoogleLogin = () => {
    // This will be replaced with the actual Google OAuth URL
    window.location.href = 'http://localhost:8000/login/google';
  };

  return (
    <div className="flex justify-center items-center h-screen bg-gray-100">
      <Card className="w-full max-w-md">
        <CardHeader className="justify-center">
          <h1 className="text-2xl font-bold">Login with Google</h1>
        </CardHeader>
        <CardBody>
          <Button color="primary" fullWidth onPress={handleGoogleLogin}>
            Login with Google
          </Button>
        </CardBody>
      </Card>
    </div>
  );
}
