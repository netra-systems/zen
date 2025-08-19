/**
 * Chat Home Page
 * 
 * Handles chat home state when no specific thread is selected.
 * Redirects to thread page if thread parameter is present.
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
    handleThreadParameterRedirect(searchParams, router);
  }, [searchParams, router]);
  
  // Render MainChat directly - no landing screen
  return <MainChat />;
};

/**
 * Handles thread parameter redirect
 */
const handleThreadParameterRedirect = (
  searchParams: URLSearchParams,
  router: ReturnType<typeof useRouter>
): void => {
  const threadId = searchParams.get('thread');
  if (threadId) {
    // Redirect to the proper thread route
    router.replace(`/chat/${threadId}`);
  }
};

export default ChatPage;