/**
 * Chat Home Page
 * 
 * Handles chat home state when no specific thread is selected.
 * Redirects to thread page if thread parameter is present.
 * Also handles OAuth callback tokens from auth service.
 * 
 * @compliance conventions.xml - Max 8 lines per function, under 300 lines
 * @compliance type_safety.xml - Strongly typed component with clear interfaces
 */

"use client";

import React, { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import MainChat from '@/components/chat/MainChat';

/**
 * Chat home page component
 */
const ChatPage: React.FC = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  useEffect(() => {
    handleOAuthTokens(searchParams);
    handleThreadParameterRedirect(searchParams, router);
  }, [searchParams, router]);
  
  // Render MainChat directly - no landing screen
  return <MainChat />;
};

/**
 * Handles OAuth tokens from auth service redirect
 */
const handleOAuthTokens = (searchParams: URLSearchParams): void => {
  const token = searchParams.get('token');
  const refreshToken = searchParams.get('refresh');
  
  if (token) {
    console.log('OAuth tokens received in chat page:', {
      tokenPresent: !!token,
      refreshTokenPresent: !!refreshToken,
      tokenLength: token.length
    });
    
    // Store tokens from OAuth callback
    localStorage.setItem('jwt_token', token);
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }
    
    // Verify tokens were stored
    const storedToken = localStorage.getItem('jwt_token');
    console.log('Token stored successfully:', storedToken === token);
    
    // Remove tokens from URL for cleaner display
    window.history.replaceState({}, '', '/chat');
  }
};

/**
 * Handles thread parameter redirect
 */
const handleThreadParameterRedirect = (
  searchParams: URLSearchParams,
  router: ReturnType<typeof useRouter>
): void => {
  const threadId = searchParams.get('thread');
  if (threadId && !searchParams.get('token')) {
    // Redirect to the proper thread route
    router.replace(`/chat/${threadId}`);
  }
};

export default ChatPage;